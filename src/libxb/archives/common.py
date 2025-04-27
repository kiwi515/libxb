from abc import abstractmethod
from contextlib import AbstractContextManager
from enum import IntEnum, auto, unique
from os import makedirs, walk
from os.path import dirname, isdir, join
from typing import TypeAlias

from ..core.exceptions import (
    ArchiveError,
    ArchiveExistsError,
    ArchiveNotFoundError,
    ArgumentError,
)
from ..core.streams import Endian, FileStream, OpenMode

XBEndian: TypeAlias = Endian
XBOpenMode: TypeAlias = OpenMode


@unique
class XBCompression(IntEnum):
    """XB file compression strategy"""

    NONE = auto()  # Uncompressed
    LZS = auto()  # LZS
    HUFFMAN = auto()  # Huffman
    DEFLATE = auto()  # LZS + Huffman


class XBFile:
    """One file inside of an XB archive"""

    def __init__(
        self, path: str, data: bytes | bytearray, compression: XBCompression
    ):
        """Constructor

        Args:
            path (str): Path to the file inside the archive
            data (bytes | bytearray): File binary data
            compression (XBCompression): File compression strategy

        Raises:
            ArgumentError: Invalid argument(s) provided
        """
        if not data:
            raise ArgumentError("No data provided")

        self.path: str = path.replace("/", "\\")
        self.data: bytes | bytearray = data
        self.compression: XBCompression = compression


class XBArchiveBase(AbstractContextManager):
    """Generic interface for XB archives (.XB file format).
    Subclasses implement concepts which may differ between revisions of the XB format.
    """

    class FileSystemEntry:
        """Filesystem table (FST) entry"""

        def __init__(
            self, length: int, offset: int, compression: XBCompression
        ):
            """Constructor

            Args:
                length (int): File length
                offset (int): File offset
                compression (XBCompression): File compression strategy

            Raises:
                ArgumentError: Invalid argument(s) provided
            """
            if compression not in XBCompression:
                raise ArgumentError("Invalid XBCompression")
            if offset % 4 != 0:
                raise ArgumentError("Offset must be 4-byte aligned")

            self.length: int = length
            self.offset: int = offset
            self.compression: XBCompression = compression

    class StringTableEntry:
        """String table entry"""

        def __init__(self, value: str):
            """Constructor

            Args:
                value (str): String value
            """
            self.value: str = value
            self.__data: bytes = value.encode("shift-jis")

        def length(self) -> int:
            """Returns the length of the string, in bytes

            Returns:
                int: String length (excluding null terminator)
            """
            return len(self.__data)

        def hash(self) -> int:
            """Calculates the 8-bit hash value of the string

            Returns:
                int: Hash value
            """
            hash = 0

            for c in self.__data:
                hash = ((hash & 0x7F) << 1 | (hash & 0x80) >> 7) ^ c

            return hash & 0xFF

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
        self.open(path, mode, endian)

    @property
    def path(self) -> str:
        """Accesses the archive's filepath (read-only)"""
        return self._strm.path

    @property
    def endian(self) -> str:
        """Accesses the archive's endianness (read-only)"""
        return self._strm.endian

    @property
    def files(self) -> list[XBFile]:
        """Accesses the archive's files (read-only)"""
        return self._files

    def __iter__(self):
        """Iterates over the archive's files (read-only)"""
        return self._files.__iter__()

    def __exit__(self, exc_type, exc_value, traceback):
        """Exits the runtime context, closing the XB archive"""
        self.close()

    def open(self, path: str, mode: XBOpenMode, endian: XBEndian) -> None:
        """Opens an XB archive

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
        if mode not in XBOpenMode:
            raise ArgumentError("Invalid XBOpenMode")
        if endian not in XBEndian:
            raise ArgumentError("Invalid XBEndian")

        self._strm: FileStream = None
        self._files: list[XBFile] = []

        self._fst: list[XBArchiveBase.FileSystemEntry] = []
        self._strtab: list[XBArchiveBase.StringTableEntry] = []

        try:
            self._strm = FileStream(path, mode, endian)
        except FileNotFoundError:
            raise ArchiveNotFoundError(f"Archive does not exist: {path}")
        except FileExistsError:
            raise ArchiveExistsError(f"Archive already exists: {path}")

        # Need to read existing content
        if self._strm.mode in (XBOpenMode.READ, XBOpenMode.RW):
            self._read()

    def close(self) -> None:
        """Closes the XB archive, committing any changes made"""
        # Need to write existing content
        if self._strm.mode in (
            XBOpenMode.WRITE,
            XBOpenMode.RW,
            XBOpenMode.CREATE,
        ):
            self._write()

        self._strm.close()
        self._strm = None

    def add(
        self,
        path: str,
        xb_path=None,
        compression: XBCompression = XBCompression.NONE,
        recursive=True,
    ) -> None:
        """Adds a file or directory to the XB archive

        Args:
            path (str): Path to the file or directory
            xb_path (str, optional) Path to use in the XB archive instead of `path`.
                                    Defaults to the local file path.
            compression (XBCompression, optional): How to compress the file.
                                                   Defaults to no compression.
            recursive (bool, optional) Whether to add directories recursively.
                                       Defaults to True.

        Raises:
            ArgumentError: Invalid argument(s) provided
            ArchiveError: File could not be added to the archive
        """
        if compression not in XBCompression:
            raise ArgumentError("Invalid XBCompression")

        # Process all files in directory
        if isdir(path):
            for wpath, _, wfiles in walk(path):
                for file in wfiles:
                    self.add(
                        join(wpath, file),
                        join(xb_path, file),
                        compression,
                        recursive,
                    )

                if not recursive:
                    break
            return

        # Process a single file
        try:
            with open(path, "rb") as f:
                data = f.read()
        except FileNotFoundError:
            raise ArchiveError(f"File does not exist: {path}")

        file = XBFile(xb_path or path, data, compression)

        # Allow subclasses to modify/reject file
        if not self._on_add(file):
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
        # Default behavior attempts to extract all files
        if files is None:
            files = self._files

        for file in files:
            self.extract(file, path)

    def extract(self, file: XBFile, path=".") -> None:
        """Extracts one file from the XB archive

        Args:
            file (XBFile): Target file to extract
            path (str, optional): Destination path.
                                  Defaults to the current working directory (".").
        """
        # Allow subclasses to modify/reject file
        if not self._on_extract(file):
            return

        # Safety filter for some games
        file.path = file.path.replace("..\\", "")

        # Need to create directory structure
        dst_path = f"{path}/{file.path}"
        makedirs(dirname(dst_path), exist_ok=True)

        with open(dst_path, "wb+") as f:
            f.write(file.data)

    def _on_add(self, file: XBFile) -> bool:
        """Prepares a file for being added to the archive

        Args:
            file (XBFile): File to be added

        Returns:
            bool: Whether to add the file to the archive
        """
        return True

    def _on_extract(self, file: XBFile) -> bool:
        """Prepares a file for being extracted from the archive

        Args:
            file (XBFile): File to be extracted

        Returns:
            bool: Whether to extract the file from the archive
        """
        return True

    @abstractmethod
    def _read(self):
        """Deserializes the archive's data"""
        raise NotImplementedError()

    @abstractmethod
    def _write(self):
        """Serializes the archive's data"""
        raise NotImplementedError()
