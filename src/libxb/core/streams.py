from abc import abstractmethod
from contextlib import AbstractContextManager
from enum import IntEnum, StrEnum, unique
from os import SEEK_CUR, SEEK_END, SEEK_SET
from struct import pack, unpack
from typing import TypeAlias, override

from .exceptions import ArgumentError, OperationError
from .utils import Util

ByteBuffer: TypeAlias = bytes | bytearray | memoryview


@unique
class Endian(StrEnum):
    """Byte-order/endianness.
    Designed to be compatible with struct functions."""

    LITTLE = "<"
    BIG = ">"


@unique
class OpenMode(StrEnum):
    """File access mode.
    Designed to be compatible with OS functions."""

    READ = "r"
    WRITE = "w"
    RW = "+"
    CREATE = "x"


@unique
class SeekDir(IntEnum):
    """Seek origin point.
    Designed to be compatible with OS functions.
    """

    BEGIN = SEEK_SET
    CURRENT = SEEK_CUR
    END = SEEK_END


class Stream(AbstractContextManager):
    """Base stream class.
    Derived classes can be used as context managers ('with' statements).
    """

    def __init__(self, mode: OpenMode, endian: Endian):
        """Constructor

        Args:
            mode (OpenMode): Stream access mode
            endian (Endian): Stream endianness

        Raises:
            ArgumentError: Invalid openmode provided
            ArgumentError: Invalid endianness provided
        """
        if mode not in OpenMode:
            raise ArgumentError("Invalid openmode")
        if endian not in Endian:
            raise ArgumentError("Invalid endianness")

        self._mode: OpenMode = mode
        self._endian: Endian = endian

    @property
    def mode(self):
        """Accesses the stream's openmode (read-only)"""
        return self._mode

    @property
    def endian(self):
        """Accesses the stream's endianness (read-only)"""
        return self._endian

    def __exit__(self, exc_type, exc_value, traceback):
        """Exits the runtime context, closing the stream"""
        self.close()

    @abstractmethod
    def read(self, size: int = -1) -> bytes:
        """Reads bytes from the stream

        Args:
            size (int, optional): Number of bytes to read. Defaults to -1 (go to EOF).

        Returns:
            bytes: Bytes read
        """
        raise NotImplementedError()

    @abstractmethod
    def write(self, data: ByteBuffer) -> None:
        """Writes bytes to the stream

        Args:
            data (ByteBuffer): Data to write
        """
        raise NotImplementedError()

    @abstractmethod
    def eof(self) -> bool:
        """Tests whether the stream has hit the end of the file

        Returns:
            bool: Whether the stream has hit the end of the file
        """
        raise NotImplementedError()

    @abstractmethod
    def seek(self, origin: SeekDir, offset: int = 0) -> None:
        """Seeks the stream position

        Args:
            origin (SeekDir): Seek origin point
            offset (int, optional): Seek distance. Defaults to zero.
        """
        raise NotImplementedError()

    @abstractmethod
    def tell(self) -> int:
        """Retrieves the stream position

        Returns:
            int: Stream position (from begin)
        """
        raise NotImplementedError()

    @abstractmethod
    def length(self) -> int:
        """Retrieves the stream length

        Returns:
            int: Stream length
        """
        raise NotImplementedError()

    def align(self, alignment: int) -> None:
        """Aligns the stream position to a byte boundary.

        Args:
            alignment (int): Byte alignment boundary

        Raises:
            ArgumentError: Invalid argument(s) provided
            OperationError: Stream is not open

        """
        if alignment < 0:
            raise ArgumentError("Invalid alignment")

        pos = self.tell()

        remain = Util.align(pos, alignment) - pos
        if remain == 0:
            return

        if self._mode == OpenMode.READ or not self.eof():
            self.seek(SeekDir.CURRENT, remain)
        else:
            self.write_padding(remain)

    def close(self) -> None:
        """Closes the stream"""
        pass

    def read_s8(self) -> int:
        """Reads a signed 8-bit integer from the stream

        Returns:
            int: Integer value
        """
        return self.__bytes_to_int(self.read(1), signed=True)

    def write_s8(self, value: int) -> None:
        """Writes a signed 8-bit integer to the stream

        Args:
            data (int): Integer value
        """
        return self.write(self.__int_to_bytes(value, size=1, signed=True))

    def read_u8(self) -> int:
        """Reads a unsigned 8-bit integer from the stream

        Returns:
            int: Integer value
        """
        return self.__bytes_to_int(self.read(1), signed=False)

    def write_u8(self, value: int) -> None:
        """Writes a unsigned 8-bit integer to the stream

        Args:
            value (int): Integer value
        """
        return self.write(self.__int_to_bytes(value, size=1, signed=False))

    def read_s16(self) -> int:
        """Reads a signed 16-bit integer from the stream

        Returns:
            int: Integer value
        """
        return self.__bytes_to_int(self.read(2), signed=True)

    def write_s16(self, value: int) -> None:
        """Writes a signed 16-bit integer to the stream

        Args:
            value (int): Integer value
        """
        return self.write(self.__int_to_bytes(value, size=2, signed=True))

    def read_u16(self) -> int:
        """Reads a unsigned 16-bit integer from the stream

        Returns:
            int: Integer value
        """
        return self.__bytes_to_int(self.read(2), signed=False)

    def write_u16(self, value: int) -> None:
        """Writes a unsigned 16-bit integer to the stream

        Args:
            value (int): Integer value
        """
        return self.write(self.__int_to_bytes(value, size=2, signed=False))

    def read_s32(self) -> int:
        """Reads a signed 32-bit integer from the stream

        Returns:
            int: Integer value
        """
        return self.__bytes_to_int(self.read(4), signed=True)

    def write_s32(self, value: int) -> None:
        """Writes a signed 32-bit integer to the stream

        Args:
            value (int): Integer value
        """
        return self.write(self.__int_to_bytes(value, size=4, signed=True))

    def read_u32(self) -> int:
        """Reads a unsigned 32-bit integer from the stream

        Returns:
            int: Integer value
        """
        return self.__bytes_to_int(self.read(4), signed=False)

    def write_u32(self, value: int) -> None:
        """Writes a unsigned 32-bit integer to the stream

        Args:
            value (int): Integer value
        """
        return self.write(self.__int_to_bytes(value, size=4, signed=False))

    def read_f32(self) -> float:
        """Reads a single-precision, floating-point value from the stream

        Returns:
            float: Single-precision, floating-point value
        """
        return self.__bytes_to_dec(self.read(4))

    def write_f32(self, value: float) -> None:
        """Writes a single-precision, floating-point value to the stream

        Args:
            value (float): Single-precision, floating-point value
        """
        return self.write(self.__dec_to_bytes(value, size=4))

    def read_f64(self) -> float:
        """Reads a double-precision, floating-point value from the stream

        Returns:
            float: Double-precision, floating-point value
        """
        return self.__bytes_to_dec(self.read(8))

    def write_f64(self, value: float) -> None:
        """Writes a double-precision, floating-point value to the stream

        Args:
            value (float): Double-precision, floating-point value
        """
        return self.write(self.__dec_to_bytes(value, size=8))

    def read_string(self, maxlen: int = -1) -> str:
        """Reads a UTF-8 string from the stream

        Args:
            maxlen (int, optional): Maximum number of characters to read.
                                    Defaults to -1 (go until null terminator or end-of-file).

        Returns:
            str: UTF-8 string
        """
        i = 0
        data = bytearray()

        while i < maxlen or maxlen == -1:
            if self.eof():
                break

            c = self.read(1)
            if c[0] == 0x00:
                break

            data += c
            i += 1

        return data.decode("utf-8")

    def write_string(
        self, string: str, maxlen: int = -1, terminate: bool = True
    ) -> None:
        """Writes a UTF-8 string to the stream

        Args:
            string (str): String value
            maxlen (int, optional): Maximum number of characters to write.
                                    Defaults to -1 (write the whole string).
            terminate (bool, optional): Whether to null terminate the string. Defaults to True.
        """
        # Truncate if string is too long
        if maxlen >= 0:
            # Reserve last space for null terminator
            term_size = 1 if terminate else 0
            string = string[: maxlen - term_size]

        self.write(string.encode("utf-8"))

        if terminate:
            self.write_u8(0x00)

    def read_wstring(self, maxlen: int = -1) -> str:
        """Reads a wide-char (UTF-16) string from the stream

        Args:
            maxlen (int, optional): Maximum number of characters to write.
                                    Defaults to -1 (write the whole string).

        Returns:
            str: UTF-16 string
        """
        i = 0
        data = bytearray()

        while i < maxlen or maxlen == -1:
            if self.eof():
                break

            c = self.read(2)
            if c[0] == 0x00 and c[1] == 0x00:
                break

            data += c
            i += 1

        return data.decode("utf-16")

    def write_wstring(
        self, string: str, maxlen: int = -1, terminate: bool = True
    ) -> None:
        """Writes a wide-char (UTF-16) string to the stream

        Args:
            string (str): String value
            maxlen (int, optional): Maximum number of characters to write.
                                    Defaults to -1 (write the whole string).
            terminate (bool, optional): Whether to null terminate the string. Defaults to True.
        """
        # Reserve last space for null terminator
        if maxlen >= 0:
            term_size = 1 if terminate else 0
            # Truncate if string is too long
            string = string[: maxlen - term_size]

        self.write(string.encode("utf-16-be"))

        if terminate:
            self.write_u16(0x0000)

    def read_sjis_string(self, maxlen: int = -1) -> str:
        """Reads a Shift-JIS string from the stream

        Args:
            maxlen (int, optional): Maximum number of characters to read.
                                    Defaults to -1 (go until null terminator or end-of-file).

        Returns:
            str: Shift-JIS string
        """
        i = 0
        data = bytearray()

        while i < maxlen or maxlen == -1:
            if self.eof():
                break

            c = self.read(1)
            if c[0] == 0x00:
                break

            data += c
            i += 1

        return data.decode("shift-jis")

    def write_sjis_string(
        self, string: str, maxlen: int = -1, terminate: bool = True
    ) -> None:
        """Writes a Shift-JIS string to the stream

        Args:
            string (str): String value
            maxlen (int, optional): Maximum number of characters to write.
                                    Defaults to -1 (write the whole string).
            terminate (bool, optional): Whether to null terminate the string. Defaults to True.
        """
        # Truncate if string is too long
        if maxlen >= 0:
            # Reserve last space for null terminator
            term_size = 1 if terminate else 0
            string = string[: maxlen - term_size]

        self.write(string.encode("shift-jis"))

        if terminate:
            self.write_u8(0x00)

    def write_padding(self, size: int) -> None:
        """Writes padding (zero bytes) to the stream.

        Args:
            size (int): Number of padding bytes to write

        Raises:
            ArgumentError: Invalid size provided
        """
        if size < 0:
            raise ArgumentError("Invalid size")

        self.write(bytes([0x00] * size))

    def __int_to_bytes(self, value: int, size: int, signed: bool) -> bytes:
        """Converts an integer value into bytes, based on the stream endianness

        Args:
            value (int): Integer value
            size (int): Number of bytes to use
            signed (bool): Whether the value should be expressed as signed

        Returns:
            bytes: Byte representations
        """
        endian = {
            Endian.LITTLE: "little",
            Endian.BIG: "big",
        }[self._endian]

        value &= (2 ** (size * 8)) - 1
        return int.to_bytes(value, length=size, byteorder=endian, signed=signed)

    def __bytes_to_int(self, data: bytes, signed: bool) -> int:
        """Converts bytes into an integer value, based on the stream endianness

        Args:
            data (bytes): Byte representation
            signed (bool): Whether the value should be treated as signed

        Returns:
            int: Integer value
        """
        endian = {
            Endian.LITTLE: "little",
            Endian.BIG: "big",
        }[self._endian]

        return int.from_bytes(data, byteorder=endian, signed=signed)

    def __dec_to_bytes(self, value: float, size: int) -> bytes:
        """Converts a decimal value into bytes, based on the stream endianness

        Args:
            value (float): Decimal value
            size (int): Number of bytes to use
            signed (bool): Whether the value should be expressed as signed

        Returns:
            bytes: Byte representations
        """
        t = "d" if size == 8 else "f"
        arr = pack(f"{self._endian}{t}", value)
        return bytes(arr)

    def __bytes_to_dec(self, data: bytes) -> float:
        """Converts bytes into a decimal value, based on the stream endianness

        Args:
            data (bytes): Byte representation

        Returns:
            float: Decimal value value
        """
        t = "d" if len(data) == 8 else "f"
        arr = unpack(f"{self._endian}{t}", data)
        return arr[0]


class FileStream(Stream):
    """Physical file stream"""

    def __init__(self, path: str, mode: OpenMode, endian: Endian):
        """Constructor

        Args:
            path (str): File path to open
            mode (OpenMode): File access mode
            endian (Endian): File endianness
        """
        super().__init__(mode, endian)

        self.__path: str = ""
        self.__file = None

        self.open(path, mode, endian)

    @property
    def path(self) -> str:
        """Accesses the streams's filepath (read-only)"""
        return self.__path

    @override
    def read(self, size: int = -1) -> bytes:
        """Reads bytes from the stream

        Args:
            size (int, optional): Number of bytes to read. Defaults to -1 (go to EOF).

        Returns:
            bytes: Bytes read

        Raises:
            OperationError: Stream is not open
            EOFError: Stream has hit the end-of-file (EOF)
            OperationError: Stream is write-only
        """
        if not self.__file:
            raise OperationError("No file is open")
        if self.eof():
            raise EOFError("Hit end-of-file")
        if self._mode not in (OpenMode.READ, OpenMode.RW):
            raise OperationError("Stream is write-only")

        return self.__file.read(size)

    @override
    def write(self, data: ByteBuffer) -> None:
        """Writes bytes to the stream

        Args:
            data (ByteBuffer): Data to write

        Raises:
            OperationError: Stream is not open
            OperationError: Stream is read-only
        """
        if not self.__file:
            raise OperationError("No file is open")
        if self._mode not in (OpenMode.WRITE, OpenMode.RW, OpenMode.CREATE):
            raise OperationError("Stream is read-only")

        self.__file.write(data)

    @override
    def eof(self) -> bool:
        """Tests whether the stream has hit the end of the file

        Returns:
            bool: Whether the stream has hit the end of the file

        Raises:
            OperationError: Stream is not open
        """
        if not self.__file:
            raise OperationError("No file is open")

        # With write permission, you can kinda just do whatever
        if self._mode not in (OpenMode.READ, OpenMode.RW):
            return False

        # Try to peek one byte
        if not self.__file.read(1):
            return True

        # Undo read operation
        self.__file.seek(-1, SeekDir.CURRENT)

        return False

    @override
    def seek(self, origin: SeekDir, offset: int = 0) -> None:
        """Seeks the stream position

        Args:
            origin (SeekDir): Seek origin point
            offset (int, optional): Seek distance. Defaults to zero.

        Raises:
            OperationError: Stream is not open
        """
        if origin not in SeekDir:
            raise ArgumentError("Invalid SeekDir")
        if not self.__file:
            raise OperationError("No file is open")

        if origin == SeekDir.BEGIN and offset < 0:
            raise ArgumentError("Invalid seek offset from begin")
        if origin == SeekDir.END and offset > 0:
            raise ArgumentError("Invalid seek offset from end")

        self.__file.seek(offset, origin)

    @override
    def tell(self) -> int:
        """Retrieves the stream position

        Returns:
            int: Stream position (from begin)

        Raises:
            OperationError: Stream is not open
        """
        if not self.__file:
            raise OperationError("No file is open")

        return self.__file.tell()

    @override
    def length(self) -> int:
        """Retrives the stream length

        Returns:
            int: Stream length
        """
        if not self.__file:
            raise OperationError("No file is open")

        return self.__length

    def open(self, path: str, mode: OpenMode, endian: Endian) -> None:
        """Opens the specified file

        Args:
            path (str): File path to open
            mode (OpenMode): File access mode
            endian (Endian): File endianness

        Raises:
            ArgumentError: Invalid argument(s) provided
        """
        if mode not in OpenMode:
            raise ArgumentError("Invalid OpenMode")
        if endian not in Endian:
            raise ArgumentError("Invalid Endian")

        # Close existing file
        if self.__file:
            self.close()

        self.__path = path
        self._mode = mode
        self._endian = endian

        # Force binary mode
        os_mode = f"{self._mode}b"
        self.__file = open(self.__path, os_mode)

        self.__file.seek(0, SeekDir.END)
        self.__length = self.__file.tell()
        self.__file.seek(0, SeekDir.BEGIN)

    @override
    def close(self) -> None:
        """Closes the stream"""
        if self.__file:
            self.__file.close()
            self.__file = None


class BufferStream(Stream):
    """Byte-buffer file stream"""

    def __init__(
        self, mode: OpenMode, endian: Endian, buffer: ByteBuffer = None
    ):
        """Constructor

        Args:
            mode (OpenMode): Stream access mode
            endian (Endian): Stream endianness
            buffer (ByteBuffer, optional): Byte buffer to read from. If you want to
                                           build a buffer, use None. Defaults to None.

        Raises:
            ArgumentError: Invalid argument(s) provided
        """
        super().__init__(mode, endian)

        self.__buffer: ByteBuffer = None
        self.__position: int = 0

        self.open(buffer, mode, endian)

    @override
    def read(self, size: int = -1) -> bytes:
        """Reads bytes from the stream

        Args:
            size (int, optional): Number of bytes to read. Defaults to -1 (go to EOF).

        Returns:
            bytes: Bytes read

        Raises:
            OperationError: Stream is not open
            OperationError: Stream is write-only
            EOFError: Stream has hit the end-of-file (EOF)
        """
        if self.__buffer is None:
            raise OperationError("No buffer is open")
        if self._mode == OpenMode.WRITE:
            raise OperationError("Stream is write-only")
        if self.__position >= len(self.__buffer):
            raise EOFError("Hit end of the buffer")

        # -1 size means read until EOF
        if size == -1:
            size = len(self.__buffer) - self.__position
        # Don't read past EOF
        else:
            size = min(size, len(self.__buffer) - self.__position)

        data = self.__buffer[self.__position : self.__position + size]
        self.__position += size

        return data

    @override
    def write(self, data: ByteBuffer) -> None:
        """Writes bytes to the stream

        Args:
            data (ByteBuffer): Data to write

        Raises:
            OperationError: Stream is not open
            OperationError: Stream is read-only
        """
        if self.__buffer is None:
            raise OperationError("No buffer is open")
        if self._mode == OpenMode.READ:
            raise OperationError("Stream is read-only")

        self.__buffer[self.__position : self.__position + len(data)] = data
        self.__position += len(data)

    @override
    def eof(self) -> bool:
        """Tests whether the stream has hit the end of the buffer

        Returns:
            bool: Whether the stream has hit the end of the buffer

        Raises:
            OperationError: Stream is not open
        """
        if self.__buffer is None:
            raise OperationError("No buffer is open")

        return self.__position >= len(self.__buffer)

    @override
    def seek(self, origin: SeekDir, offset: int = 0) -> None:
        """Seeks the stream position

        Args:
            origin (SeekDir): Seek origin point
            offset (int, optional): Seek distance. Defaults to zero.

        Raises:
            ArgumentError: Invalid argument(s) provided
            OperationError: Stream is not open
        """
        if origin not in SeekDir:
            raise ArgumentError("Invalid SeekDir")
        if self.__buffer is None:
            raise OperationError("No buffer is open")

        match origin:
            case SeekDir.BEGIN:
                if offset < 0:
                    raise ArgumentError("Invalid seek offset from begin")

                self.__position = offset

            case SeekDir.CURRENT:
                self.__position += offset

            case SeekDir.END:
                if offset > 0:
                    raise ArgumentError("Invalid seek offset from end")

                self.__position = len(self.__buffer) + offset

    @override
    def tell(self) -> int:
        """Retrieves the stream position

        Returns:
            int: Stream position (from begin)

        Raises:
            OperationError: Stream is not open
        """
        if self.__buffer is None:
            raise OperationError("No buffer is open")

        return self.__position

    @override
    def length(self) -> int:
        """Retrives the stream length

        Returns:
            int: Stream length
        """
        if self.__buffer is None:
            raise OperationError("No buffer is open")

        return len(self.__buffer)

    def open(self, buffer: ByteBuffer, mode: OpenMode, endian: Endian) -> None:
        """Opens the specified byte buffer

        Args:
            buffer (ByteBuffer, optional): Byte buffer to read from. If you want to
                                           build a buffer, use None. Defaults to None.
            mode (OpenMode): Stream access mode
            endian (Endian): Stream endianness

        Raises:
            ArgumentError: Invalid argument(s) provided
        """
        if buffer == None and mode == OpenMode.READ:
            raise ArgumentError("No buffer specified")

        # Create is not supported
        if mode == OpenMode.CREATE:
            mode = OpenMode.WRITE

        self._endian = endian
        self._mode = mode
        self.__buffer = buffer
        self.__position = 0

        # Create empty buffer for building
        if self.__buffer is None:
            self.__buffer = bytearray()

        # Read-only buffers use memoryview to avoid copying
        if self._mode == OpenMode.READ:
            self.__buffer = memoryview(self.__buffer)
        elif not isinstance(self.__buffer, bytearray):
            self.__buffer = bytearray(self.__buffer)

    @override
    def close(self) -> None:
        """Closes the stream"""
        self.__buffer = None
        self.__position = 0

    def get(self) -> ByteBuffer:
        """Accesses the stream buffer

        Returns:
            ByteBuffer: Resulting buffer

        Raises:
            OperationError: Stream is not open
        """
        if self.__buffer is None:
            raise OperationError("No buffer is open")

        return self.__buffer
