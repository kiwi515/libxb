from enum import IntEnum, unique
from typing import override

from ..core.compress import ClapHanzDeflate, ClapHanzHuffman, ClapHanzLZS
from ..core.exceptions import (
    ArchiveError,
    ArgumentError,
    BadArchiveError,
    DecompressionError,
    NotAnArchiveError,
    OperationError,
)
from ..core.streams import BufferStream, SeekDir
from ..core.utils import Util
from .common import XBArchiveBase, XBCompression, XBEndian, XBFile, XBOpenMode


@unique
class XBCompressionImpl(IntEnum):
    """Binary form of XB file compression strategy"""

    DEFLATE = 0  # LZS + Huffman
    HUFFMAN = 1  # Huffman
    LZS = 2  # LZS
    NONE = 3  # Uncompressed


class XBArchive(XBArchiveBase):
    """XB archive implementation"""

    # File "magic" / "signature"
    SIGNATURE = b"\x78\x65\x00\x01"  # "xe.."

    def __init__(self, path: str, mode: XBOpenMode, endian: XBEndian):
        """Constructor

        Args:
            path (str): File path to open
            mode (XBOpenMode): File open mode
            endian (XBEndian): File endianness


        Raises:
            ArgumentError: Invalid argument(s) provided
            ArchiveNotFoundError: Archive file does not exist
            ArchiveExistsError: Archive file already exists
            BadArchiveError: Archive file is broken or corrupted
        """
        super().__init__(path, mode, endian)

    @override
    def open(self, path: str, mode: XBOpenMode, endian: XBEndian) -> None:
        """Opens an XB archive

        Args:
            path (str): File path to open
            mode (XBOpenMode): File open mode
            endian (XBEndian): File endianness

        Raises:
            ArgumentError: Invalid argument(s) provided
        """
        if mode not in XBOpenMode:
            raise ArgumentError("Invalid XBOpenMode")
        if endian not in XBEndian:
            raise ArgumentError("Invalid XBEndian")

        self.__file_num: int = 0

        self.__header_work: BufferStream = None
        self.__fst_work: BufferStream = None
        self.__strtab_work: BufferStream = None
        self.__files_work: list[bytes] = []

        super().open(path, mode, endian)

    @override
    def _read(self):
        """Deserializes the archive's data"""
        self.__read_header()
        self.__read_file_system()
        self.__read_string_table()
        self.__read_file_data()

        # String table must contain entries for all files
        if len(self._fst) != len(self._strtab):
            raise BadArchiveError("Filesystem/string table mismatch")

    @override
    def _write(self):
        """Serializes the archive's data"""
        self.__prepare_write()

        self._strm.write(self.__header_work.get())
        self._strm.write(self.__fst_work.get())
        self._strm.write(self.__strtab_work.get())

        for file in self.__files_work:
            self._strm.write(file)

    def __read_header(self) -> None:
        """Reads the header section of the archive

        Raises:
            NotAnArchiveError: The file is not an XB archive
        """
        signature = self._strm.read(len(self.SIGNATURE))
        if signature != self.SIGNATURE:
            raise NotAnArchiveError("This file is not an XB archive")

        self.__file_num = self._strm.read_u32()

    def __read_file_system(self) -> None:
        """Reads the filesystem table (FST) section of the archive

        Raises:
            BadArchiveError: The archive filesystem is broken
        """
        # Sections are aligned to 4-byte boundary
        Util.align(self._strm, 4)

        for _ in range(self.__file_num):
            length = self._strm.read_u32()
            cmpoff = self._strm.read_u32()

            # Compression/offset are packed as one 32-bit value
            # cccc oooo oooo oooo oooo oooo oooo oooo
            compression = XBCompressionImpl(cmpoff >> 28)
            offset = cmpoff & 0x0FFFFFFF

            # Offset is stored divided by 4 so all values are expressable
            offset *= 4

            if offset >= self._strm.length():
                raise BadArchiveError("Filesystem table is broken")

            compression = Util.convert_enum(compression, XBCompression)
            entry = self.FileSystemEntry(length, offset, compression)
            self._fst.append(entry)

    def __read_string_table(self) -> None:
        """Reads the string table (strtab) section of the archive

        Raises:
            BadArchiveError: The archive string table is broken
        """
        # Sections are aligned to 4-byte boundary
        Util.align(self._strm, 4)

        expand_size = self._strm.read_u32()
        compress_size = self._strm.read_u32()

        # String table is *sometimes* LZS compressed.
        # Seems like the ClapHanz tools omit compression if it would have wasted space.
        if compress_size != 0:
            try:
                strtab_strm = ClapHanzLZS.decompress(
                    self._strm, expand_size, compress_size
                )
            except DecompressionError:
                raise BadArchiveError("String table is broken")
        else:
            strtab_strm = BufferStream(
                self.endian, self._strm.read(expand_size)
            )

        # Parse the string table
        try:
            while not strtab_strm.eof():
                length = strtab_strm.read_u8()
                hash = strtab_strm.read_u8()

                value = strtab_strm.read_sjis_string()
                entry = self.StringTableEntry(value)

                if length != entry.length() or hash != entry.hash():
                    raise BadArchiveError("String table is broken")

                self._strtab.append(entry)
        except EOFError:
            raise BadArchiveError("String table is broken")

    def __read_file_data(self) -> None:
        """Reads the file data section of the archive

        Raises:
            BadArchiveError: The archive file data is broken
        """
        # Sections are aligned to 4-byte boundary
        Util.align(self._strm, 4)

        for index, entry in enumerate(self._fst):
            self._strm.seek(SeekDir.BEGIN, entry.offset)

            try:
                match entry.compression:
                    case XBCompression.NONE:
                        data = self._strm.read(entry.length)
                    case XBCompression.LZS:
                        data = ClapHanzLZS.decompress(self._strm).get()
                    case XBCompression.HUFFMAN:
                        data = ClapHanzHuffman.decompress(self._strm).get()
                    case XBCompression.DEFLATE:
                        data = ClapHanzDeflate.decompress(self._strm).get()
            except DecompressionError:
                raise BadArchiveError("Compressed data is broken")

            file = XBFile(self._strtab[index].value, data, entry.compression)
            self._files.append(file)

    def __prepare_write(self):
        """Prepares the archive state for writing"""
        self.__build_header()
        self.__build_string_table()
        self.__build_file_data()
        self.__build_file_system()

        # Sections are aligned to 4-byte boundary
        assert self.__header_work.length() % 4 == 0
        assert self.__strtab_work.length() % 4 == 0
        assert self.__fst_work.length() % 4 == 0

    def __build_header(self) -> None:
        """Prepares the archive header for writing

        Raises:
            ArchiveError: Archive cannot be created due to the XB format limitations
        """
        if len(self._files) > 0xFFFFFFFF:
            raise ArchiveError("Archive contains too many files")

        self.__header_work = BufferStream(self.endian)

        self.__header_work.write(self.SIGNATURE)
        self.__header_work.write_u32(len(self._files))

    def __build_file_system(self) -> None:
        """Prepares the archive filesystem table (FST) for writing

        Raises:
            OperationError: Other section(s) must be built first
            ArchiveError: Archive cannot be created due to the XB format limitations
        """
        if not self.__header_work:
            raise OperationError("Header must be built before FST")
        if not self.__strtab_work:
            raise OperationError("String table must be built before FST")
        if not self.__files_work:
            raise OperationError("File data must be built before FST")

        self.__fst_work = BufferStream(self.endian)

        # Calculate the offset of the file data section
        offset = 0
        offset += self.__header_work.length()
        offset += self.__fst_work.length()
        offset += self.__strtab_work.length()

        for index, file in enumerate(self._files):
            expand_size = len(file.data)
            compress_size = len(self.__files_work[index])

            # Offset is limited by bit size
            if (offset // 4) & ~0xFFFFFFF:
                raise ArchiveError("FST is too big")

            assert offset % 4 == 0, "Invalid FST offset (internal error)"

            # Compression/offset are packed as one 32-bit value
            # cccc oooo oooo oooo oooo oooo oooo oooo
            compression = Util.convert_enum(file.compression, XBCompressionImpl)
            cmpoff = (compression & 0b1111) << 28 | (offset // 4)

            self.__fst_work.write_u32(expand_size)
            self.__fst_work.write_u32(cmpoff)

            offset += compress_size

    def __build_string_table(self) -> None:
        """Prepares the archive string table (strtab) for writing"""
        self.__strtab_work = BufferStream(self.endian)

        for file in self._files:
            entry = self.StringTableEntry(file.path)

            self.__strtab_work.write_u8(len(entry.value))
            self.__strtab_work.write_u8(entry.hash())
            self.__strtab_work.write_sjis_string(entry.value)

        # String table is LZS compressed
        self.__strtab_work.seek(SeekDir.BEGIN)
        data = ClapHanzLZS.compress(self.__strtab_work).get()

        # Only compress the string table if it saves space
        if len(data) < self.__strtab_work.length():
            self.__strtab_work.close()
            self.__strtab_work = BufferStream(self.endian, data)

        # Sections are aligned to 4-byte boundary
        Util.align(self.__strtab_work, 4)

    def __build_file_data(self) -> None:
        """Prepares the archive file data for writing"""
        for file in self._files:
            strm = BufferStream(self.endian, file.data)

            match file.compression:
                case XBCompression.NONE:
                    data = file.data
                case XBCompression.LZS:
                    data = ClapHanzLZS.compress(strm).get()
                case XBCompression.HUFFMAN:
                    data = ClapHanzHuffman.compress(strm).get()
                case XBCompression.DEFLATE:
                    data = ClapHanzDeflate.compress(strm).get()

            # Files are aligned to 4-byte boundaries
            Util.align(data, 4)
            self.__files_work.append(data)
