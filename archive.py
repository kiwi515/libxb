from enum import IntEnum, unique, auto
from os.path import dirname
from os import makedirs
from .exceptions import (ArgumentError, ArchiveError, ArchiveNotFoundError,
                         ArchiveExistsError, BadArchiveError, NotAnArchiveError, DecompressionError)
from .stream import FileStream, BufferStream, SeekDir
from .compress import ClapHanzLZ, ClapHanzHuffman
from .util import align


@unique
class XBCompression(IntEnum):
    """XB file compression type
    """
    HUFFMAN_LZ = 0    # LZ + Huffman
    HUFFMAN = auto()  # Huffman
    LZ = auto()       # LZ
    NONE = auto()     # Uncompressed


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
                compression (XBCompression): File compression type
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
    def files(self) -> list["XBFile"]:
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
            self.__read()

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
                                                   based on the file extension, or LZ if unknown.
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
            compression = XBCompression.LZ

        try:
            with FileStream(path, f"r:{self.endian}") as f:
                data = f.read()
        except FileNotFoundError:
            raise ArchiveError(f"File does not exist: {path}")

        # Add the internal "../" prefix unless overridden
        if not xb_path:
            path = f"..\\{path}"

        file = XBFile(xb_path or path, data, compression)
        self._files.append(file)

    def extract_all(self, path=".", files: list["XBFile"] = None) -> None:
        """Extracts all specified files from the XB archive

        Args:
            path (str, optional): Destination path.
                                  Defaults to the current working directory (".").
            files (list[XBFile], optional): Specific files to extract.
                                            Ignore this field to extract all files.
        """
        for file in files or self._files:
            self.extract(file, path)

    def extract(self, file: "XBFile", path=".") -> None:
        """Extract one file from the XB archive

        Args:
            file (XBFile): Target file to extract
            path (str, optional): Destination path.
                                  Defaults to the current working directory (".").
        """
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
            if length >= self._strm.length() or offset >= self._strm.length():
                raise BadArchiveError("Filesystem table is broken")

            entry = self.FSTEntry(length, offset, compression)
            fst.append(entry)

        #######################################################################
        # Read the archive string table (LZ compressed)
        #######################################################################
        # String table is aligned to 4 byte boundary
        self._strm.align(4)

        strtab = []
        decomp_size = self._strm.read_u32()
        compress_size = self._strm.read_u32()

        try:
            strtab_buffer = ClapHanzLZ.decompress(self._strm, decomp_size)
        except DecompressionError:
            raise BadArchiveError("String table is broken")

        # Parse the string table
        with BufferStream(self.endian, strtab_buffer) as strtab_strm:
            try:
                while not strtab_strm.eof():
                    length = strtab_strm.read_u8()
                    hash = strtab_strm.read_u8()
                    value = strtab_strm.read_string()

                    entry = self.StringTableEntry(value)

                    # Integrity check
                    if length != len(value) or hash != entry.hash():
                        raise BadArchiveError("String table is broken")

                    strtab.append(entry)
            except EOFError:
                raise BadArchiveError("String table is broken")

            # String table and FST are both indexed the same way
            if len(strtab) != len(fst):
                raise BadArchiveError("String table is broken")

        #######################################################################
        # Read the contained files
        #######################################################################
        for index, entry in enumerate(fst):
            self._strm.seek(SeekDir.BEGIN, entry.offset)

            # No compression
            if entry.compression == XBCompression.NONE:
                data = self._strm.read(entry.length)
            else:
                decomp_size = self._strm.read_u32()
                compress_size = self._strm.read_u32()

                # MGP2 uses this heuristic
                if compress_size == 0:
                    raise BadArchiveError("Compressed data is broken")

            # fmt: off
                try:
                    # LZ compression only
                    if entry.compression == XBCompression.LZ:
                        data = ClapHanzLZ.decompress(self._strm, decomp_size)

                    # Huffman compression only
                    if entry.compression == XBCompression.HUFFMAN:
                        data = ClapHanzHuffman.decompress(self._strm, decomp_size)

                    # Huffman and LZ compression
                    if entry.compression == XBCompression.HUFFMAN_LZ:
                        # Huffman is applied first
                        first_pass = ClapHanzHuffman.decompress(self._strm, decomp_size)

                        # Resulting data is LZ compressed
                        with BufferStream(self.endian, first_pass) as lz_strm:
                            decomp_size = lz_strm.read_u32()
                            compress_size = lz_strm.read_u32()
                            data = ClapHanzLZ.decompress(lz_strm, decomp_size)

                except DecompressionError:
                    raise BadArchiveError("Compressed data is broken")
            # fmt: on

            # Remove internal "..\" prefix
            file_path = strtab[index].value.split("..\\")[-1]

            file = XBFile(file_path, data, entry.compression)
            self._files.append(file)

    def __write(self) -> None:
        """Serializes the currently open archive
        """
        #######################################################################
        # Build the archive string table (LZ compressed)
        #######################################################################
        with BufferStream(self.endian) as strtab_strm:
            for file in self._files:
                entry = self.StringTableEntry(file.path)

                strtab_strm.write_u8(len(entry.value))
                strtab_strm.write_u8(entry.hash())
                strtab_strm.write_string(entry.value)

            # Compress the string table
            strtab_strm.seek(SeekDir.BEGIN, 0)
            strtab_data = ClapHanzLZ.compress(strtab_strm)

            # Calculate size before/after compression
            strtab_decomp_size = strtab_strm.length()
            strtab_compress_size = len(strtab_data)

            # Align to 4 bytes to not break FST offsets
            strtab_data = align(strtab_data, 4)

        #######################################################################
        # Build the file-data section and FST at the same time
        #######################################################################
        fst_offset = 0
        fst_offset += 4 * 2                     # Header
        fst_offset += 4 * 2 * len(self._files)  # FST
        fst_offset += 4 * 2                     # String table sizes
        fst_offset += len(strtab_data)          # String table data

        with (BufferStream(self.endian) as files_strm,
              BufferStream(self.endian) as fst_strm):

            for file in self._files:
                decomp_size = len(file.data)

                match file.compression:
                    case XBCompression.NONE:
                        compress_data = file.data
                        compress_size = 0

                    case XBCompression.LZ:
                        strm = BufferStream(self.endian, file.data)
                        compress_data = ClapHanzLZ.compress(strm)
                        compress_size = len(compress_data)

                    case XBCompression.HUFFMAN:
                        raise NotImplementedError(
                            "Huffman compression is not implemented yet")

                    case XBCompression.HUFFMAN_LZ:
                        raise NotImplementedError(
                            "Huffman compression is not implemented yet")

                # Align to 4 bytes to not break FST offsets
                align(compress_data, 4)

                if file.compression != XBCompression.NONE:
                    files_strm.write_u32(decomp_size)
                    files_strm.write_u32(compress_size)

                files_strm.write(compress_data)

                # Offset is limited by bit size
                if (fst_offset // 4) >= 0xFFFFFFF - len(compress_data):
                    raise ArchiveError("FST is too big")

                # FST size is always before compression
                fst_strm.write_u32(decomp_size)

                # Compression/offset are packed as one 32-bit value
                assert fst_offset % 4 == 0, "WHY?!?!?!?!?"
                cmpoff = (fst_offset // 4) | file.compression << 28
                fst_strm.write_u32(cmpoff)

                # Size of file before/after compression
                if file.compression != XBCompression.NONE:
                    fst_offset += 4 * 2

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
        self._strm.write_u32(strtab_decomp_size)
        self._strm.write_u32(strtab_compress_size)
        self._strm.write(strtab_data)

        # File data
        self._strm.write(files_data)


class XBFile:
    """Represents one file inside of an XB archive
    """

    def __init__(self, path: str, data: bytes | bytearray,
                 compression: XBCompression):
        """Constructor

        Args:
            path (str): Path to the file inside the archive
            data (bytes | bytearray): File binary data
            compression (XBCompression): File compression type

        Raises:
            ArgumentError: Invalid argument(s) provided
        """
        if not data or len(data) == 0:
            raise ArgumentError("No data provided")

        # Use backslash only
        path = path.replace("/", "\\")

        self.path = path
        self.data = data
        self.compression = compression
