from enum import IntEnum, unique
from os import makedirs
from os.path import dirname

from .compress import ClapHanzDeflate, ClapHanzHuffman, ClapHanzLZS
from .exception import (
    ArchiveError,
    ArchiveExistsError,
    ArchiveNotFoundError,
    ArgumentError,
    BadArchiveError,
    DecompressionError,
    NotAnArchiveError,
)
from .stream import BufferStream, FileStream, SeekDir
from .utility import Util


@unique
class XBCompression(IntEnum):
    """XB file compression strategy
    """
    DEFLATE = 0  # LZS + Huffman
    HUFFMAN = 1  # Huffman
    LZS = 2      # LZS
    NONE = 3     # Uncompressed


class XBFile:
    """One file inside of an XB archive
    """

    def __init__(self, path: str, data: bytes | bytearray,
                 compression: XBCompression):
        """Constructor

        Args:
            path (str): Path to the file inside the archive
            data (bytes | bytearray): File binary data
            compression (XBCompression): File compression strategy

        Raises:
            ArgumentError: Invalid argument(s) provided
        """
        if not data or len(data) == 0:
            raise ArgumentError("No data provided")

        self.path = path
        self.data = data
        self.compression = compression


class XBArchive:
    """Read/write support for XB archives (.XB file format)
    """

    # Looks like ZLIB signature, but it's not???
    SIGNATURE = b'\x78\x65\x00\x01'  # "xe.."

    class FSTEntry:
        """Filesystem entry
        """

        def __init__(self, length: int, offset: int,
                     compression: XBCompression):
            """Constructor

            Args:
                length (int): File length
                offset (int): File offset
                compression (XBCompression): File compression strategy
            """
            if compression not in XBCompression:
                raise ArgumentError("Invalid XBCompression")
            if offset % 4 != 0:
                raise ArgumentError("Offset must be 4-byte aligned")

            self.length = length
            self.offset = offset
            self.compression = compression

    class StringTableEntry:
        """String table entry
        """

        def __init__(self, value: str):
            self.value = value

        def hash(self) -> int:
            """Retrieves the 8-bit hash value of the string

            Returns:
                int: Hash value
            """
            hash = 0

            for c in self.value:
                hash = ((hash & 0x7F) << 1 | (hash & 0x80) >> 7) ^ ord(c)

            return hash & 0xFF

    def __init__(self, path: str, open_mode: str):
        """Constructor

        Args:
            path (str): File path to open
            open_mode (str): Open mode string: "r" (read) / "w" (write) / "x" (create),
                             followed by ':', and '<' for little endian or '>' for big endian.

        Raises:
            ArgumentError: Invalid argument(s) provided
            ArchiveNotFoundError: Archive file does not exist
            ArchiveExistsError: Archive file already exists
            BadArchiveError: Archive file is broken or corrupted
        """
        self.open(path, open_mode)

    @property
    def path(self) -> str:
        """Accesses the archive's filepath (read-only)
        """
        return self._strm.path

    @property
    def endian(self) -> str:
        """Accesses the archive's endianness (read-only)
        """
        return self._strm.endian

    @property
    def files(self) -> list[XBFile]:
        """Accesses the archives' files (read-only)
        """
        return self._files

    def __enter__(self):
        """Enters the runtime context, opening the XB archive
        """
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """Exits the runtime context, closing the XB archive
        """
        self.close()

    def _transform_in(self, file: XBFile) -> XBFile | None:
        """Transform function for files that will be added to the archive.
        Useful for subclasses to apply transformations/filters.

        Args:
            file (XBFile): File to be added

        Returns:
            XBFile | None: Resulting file ('None' to omit file)
        """
        return file

    def _transform_out(self, file: XBFile) -> XBFile | None:
        """Transform function for files that will be extracted from the archive.
        Useful for subclasses to apply transformations/filters.

        Args:
            file (XBFile): File to be extracted

        Returns:
            XBFile | None: Resulting file ('None' to omit file)
        """
        return file

    def open(self, path: str, open_mode: str) -> None:
        """Opens an XB archive

        Args:
            path (str): File path to open
            open_mode (str): Open mode string: "r" (read) / "w" (write) / "x" (create),
                             followed by ':', and '<' for little endian or '>' for big endian.

        Raises:
            ArgumentError: Invalid argument(s) provided
            ArchiveNotFoundError: Archive file does not exist
            ArchiveExistsError: Archive file already exists
            BadArchiveError: Archive file is broken or corrupted
        """
        try:
            self._strm = FileStream(path, open_mode)
        except ValueError:
            raise ArgumentError(f"Invalid archive openmode: {open_mode}")
        except FileNotFoundError:
            raise ArchiveNotFoundError(f"Archive does not exist: {path}")
        except FileExistsError:
            raise ArchiveExistsError(f"Archive already exists: {path}")

        self._open_mode = open_mode
        self._files = []

        # Need to read existing content
        if self._open_mode[0] == "r":
            try:
                self.__read()
            except EOFError:
                raise BadArchiveError("Archive data is incomplete")

    def close(self) -> None:
        """Closes the XB archive, committing any changes made
        """
        # Need to write existing content
        if self._open_mode[0] in ("w", "x"):
            self.__write()

        self._strm.close()
        self._strm = None

    def add(self, path: str, xb_path=None, compression: XBCompression = None,
            recursive=True) -> None:
        """Adds a file or directory to the XB archive

        Args:
            path (str): Path to the file or directory
            xb_path (str, optional) Path to use in the XB archive instead of `path`.
                                    Defaults to the local file path.
            compression (XBCompression, optional): How to compress the file.
                                                   By default, a compresssion type is chosen
                                                   based on the file extension, or LZS if unknown.
            recursive (bool, optional) Whether to add directories recursively.
                                       Defaults to True.

        Raises:
            ArgumentError: Invalid argument(s) provided
            ArchiveError: File could not be added to the archive
        """
        if compression and compression not in XBCompression:
            raise ArgumentError("Invalid XBCompression")

        # TODO: Implement rules for file extensions
        if not compression:
            compression = XBCompression.LZS

        try:
            with open(path, "rb") as f:
                data = f.read()
        except FileNotFoundError:
            raise ArchiveError(f"File does not exist: {path}")

        file = XBFile(xb_path or path, data, compression)

        # Apply transformation function
        file = self._transform_in(file)
        if not file:
            return

        self._files.append(file)

    def extract_all(self, path=".", files: list[XBFile] = None) -> None:
        """Extracts all specified files from the XB archive

        Args:
            path (str, optional): Destination path.
                                  Defaults to the current working directory (".").
            files (list[XBFile], optional): Specific files to extract.
                                            Ignore this field to extract all files.
        """
        for file in files or self._files:
            self.extract(file, path)

    def extract(self, file: XBFile, path=".") -> None:
        """Extract one file from the XB archive

        Args:
            file (XBFile): Target file to extract
            path (str, optional): Destination path.
                                  Defaults to the current working directory (".").
        """
        # Apply transformation function
        file = self._transform_out(file)
        if not file:
            return

        # Root path is provided
        abs_path = f"{path}/{file.path}"

        # Need to create directory structure
        makedirs(dirname(abs_path), exist_ok=True)

        with open(abs_path, "wb+") as f:
            f.write(file.data)

    def __read(self) -> None:
        """Deserializes the currently open archive

        Raises:
            NotAnArchiveError: The file is not a XB archive
            BadArchiveError: The archive is broken or corrupted
        """
        #######################################################################
        # Read the archive header
        #######################################################################
        signature = self._strm.read(4)
        if signature != self.SIGNATURE:
            raise NotAnArchiveError("This file is not an XB archive")

        file_num = self._strm.read_u32()

        #######################################################################
        # Read the archive FST
        #######################################################################
        fst = []
        for _ in range(file_num):
            length = self._strm.read_u32()
            cmpoff = self._strm.read_u32()

            # Compression/offset are packed as one 32-bit value
            compression = cmpoff >> 28
            offset = cmpoff & 0xFFFFFFF

            # Offset is divided by 4 to save space
            offset *= 4

            # Integrity check
            if offset >= self._strm.length():
                raise BadArchiveError("Filesystem table is broken")

            entry = self.FSTEntry(length, offset, compression)
            fst.append(entry)

        #######################################################################
        # Read the archive string table
        #######################################################################
        # String table is aligned to 4 byte boundary
        Util.align(self._strm, 4)

        strtab_decomp_size = self._strm.read_u32()
        strtab_compress_size = self._strm.read_u32()

        # String table is LZS compressed, but only sometimes?
        # I think the ClapHanz tools omit compression if it would waste space.
        if strtab_compress_size != 0:
            self._strm.seek(SeekDir.CURRENT, -8)

            try:
                strtab_strm = ClapHanzLZS.decompress(self._strm)
            except DecompressionError:
                raise BadArchiveError("String table is broken")
        else:
            strtab_strm = BufferStream(
                self.endian, self._strm.read(strtab_decomp_size))

        with open("DEBUG.BIN", "wb+") as f:
            f.write(strtab_strm.result())

        # Parse the string table
        try:
            strtab = []
            while not strtab_strm.eof():
                length = strtab_strm.read_u8()
                hash = strtab_strm.read_u8()
                value = strtab_strm.read_string()

                entry = self.StringTableEntry(value)

                if length != len(value) or hash != entry.hash():
                    raise BadArchiveError("String table is broken")

                strtab.append(entry)
        except EOFError:
            raise BadArchiveError("String table is broken")

        # String table must contain entries for all files
        if len(strtab) != len(fst):
            raise BadArchiveError("String table is broken")

        #######################################################################
        # Read the contained files
        #######################################################################
        for index, entry in enumerate(fst):
            self._strm.seek(SeekDir.BEGIN, entry.offset)

            try:
                if entry.compression == XBCompression.NONE:
                    data = self._strm.read(entry.length)

                elif entry.compression == XBCompression.LZS:
                    data = ClapHanzLZS.decompress(self._strm).result()

                elif entry.compression == XBCompression.HUFFMAN:
                    data = ClapHanzHuffman.decompress(self._strm).result()

                elif entry.compression == XBCompression.DEFLATE:
                    data = ClapHanzDeflate.decompress(self._strm).result()
            except DecompressionError:
                raise BadArchiveError("Compressed data is broken")

            file = XBFile(strtab[index].value, data, entry.compression)
            self._files.append(file)

    def __write(self) -> None:
        """Serializes the currently open archive

        Raises:
            ArchiveError: Archive cannot be created due to the XB format limitations
        """
        #######################################################################
        # Build the archive string table
        #######################################################################
        with BufferStream(self.endian) as strtab_strm:
            for file in self._files:
                entry = self.StringTableEntry(file.path)

                strtab_strm.write_u8(len(entry.value))
                strtab_strm.write_u8(entry.hash())
                strtab_strm.write_string(entry.value)

            # String table is always LZS compressed
            strtab_strm.seek(SeekDir.BEGIN, 0)
            strtab_data = ClapHanzLZS.compress(strtab_strm).result()

            # Align to 4 bytes to not break FST offsets
            Util.align(strtab_data, 4)

        #######################################################################
        # Build the file-data section and FST at the same time
        #######################################################################
        fst_offset = 0
        fst_offset += 4 * 2                     # Header
        fst_offset += 4 * 2 * len(self._files)  # FST
        fst_offset += len(strtab_data)          # String table data

        with (BufferStream(self.endian) as files_strm,
              BufferStream(self.endian) as fst_strm):

            for file in self._files:
                decomp_size = len(file.data)
                strm = BufferStream(self.endian, file.data)

                match file.compression:
                    case XBCompression.NONE:
                        compress_data = file.data

                    case XBCompression.LZS:
                        compress_data = ClapHanzLZS.compress(strm).result()

                    case XBCompression.HUFFMAN:
                        compress_data = ClapHanzHuffman.compress(strm).result()

                    case XBCompression.DEFLATE:
                        compress_data = ClapHanzDeflate.compress(strm).result()

                # Align to 4 bytes to not break FST offsets
                Util.align(compress_data, 4)
                files_strm.write(compress_data)

                # Offset is limited by bit size
                if (fst_offset // 4) >= 0xFFFFFFF - len(compress_data):
                    raise ArchiveError("FST is too big")

                # FST size is always before compression
                fst_strm.write_u32(decomp_size)

                # Compression/offset are packed as one 32-bit value
                assert fst_offset % 4 == 0, "WHY?!?!?!?!?"
                cmpoff = file.compression << 28 | (fst_offset // 4)
                fst_strm.write_u32(cmpoff)

                # Size of file data
                fst_offset += len(compress_data)

            files_data = files_strm.result()
            fst_data = fst_strm.result()

        #######################################################################
        # Write archive sections
        #######################################################################
        # Header
        self._strm.write(self.SIGNATURE)
        self._strm.write_u32(len(self._files))

        # Filesystem table
        self._strm.write(fst_data)

        # String table
        self._strm.write(strtab_data)

        # File data
        self._strm.write(files_data)
