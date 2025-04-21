from abc import ABC, abstractmethod
from enum import IntEnum, unique
from os import SEEK_CUR, SEEK_END, SEEK_SET
from struct import pack, unpack
from typing import override

from .exceptions import ArgumentError, OperationError
from .utils import Util


@unique
class SeekDir(IntEnum):
    """Seek origin point.
    Compatible with OS file objects.
    """
    BEGIN = SEEK_SET
    CURRENT = SEEK_CUR
    END = SEEK_END


class Stream(ABC):
    """Base stream class.
    Derived classes can be used as context managers ('with' statements).
    """

    def __init__(self, endian: str):
        """Constructor

        Args:
            endian (Endian): Endianness ('<' for little endian, '>' for big endian)

        Raises:
            ArgumentError: Invalid endianness provided
        """
        if endian not in ("<", ">"):
            raise ArgumentError("Invalid endianness")

        self._endian = endian

    def __enter__(self):
        """Enters the runtime context, opening the stream
        """
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """Exits the runtime context, closing the stream
        """
        self.close()

    @property
    def endian(self):
        """Accesses the stream's endianness (read-only)
        """
        return self._endian

    @abstractmethod
    def read(self, size: int = -1) -> bytes:
        """Reads bytes from the stream

        Args:
            size (int, optional): Number of bytes to read. Defaults to -1 (go to EOF).

        Returns:
            bytes: Bytes read
        """
        pass

    @abstractmethod
    def write(self, data: bytes | bytearray) -> None:
        """Writes bytes to the stream

        Args:
            data (bytes | bytearray): Data to write
        """
        pass

    @abstractmethod
    def eof(self) -> bool:
        """Tests whether the stream has hit the end of the file

        Returns:
            bool: Whether the stream has hit the end of the file
        """
        pass

    @abstractmethod
    def seek(self, origin: SeekDir, offset: int) -> None:
        """Seeks the stream position

        Args:
            origin (SeekDir): Seek origin point
            offset (int): Seek distance
        """
        pass

    @abstractmethod
    def tell(self) -> int:
        """Retrieves the stream position

        Returns:
            int: Stream position (from begin)
        """
        pass

    @abstractmethod
    def align(self, alignment: int) -> None:
        """Aligns the stream position to a byte boundary.

        Args:
            alignment (int): Byte alignment boundary
        """
        pass

    @abstractmethod
    def length(self) -> int:
        """Retrieves the stream length

        Returns:
            int: Stream length
        """
        pass

    @abstractmethod
    def close(self) -> None:
        """Closes the stream
        """
        pass

    def read_s8(self) -> int:
        """Reads a signed 8-bit integer from the stream

        Returns:
            int: Integer value
        """
        return self.__bytes2int(self.read(1), signed=True)

    def write_s8(self, value: int) -> None:
        """Writes a signed 8-bit integer to the stream

        Args:
            data (int): Integer value
        """
        return self.write(self.__int2bytes(value, size=1, signed=True))

    def read_u8(self) -> int:
        """Reads a unsigned 8-bit integer from the stream

        Returns:
            int: Integer value
        """
        return self.__bytes2int(self.read(1), signed=False)

    def write_u8(self, value: int) -> None:
        """Writes a unsigned 8-bit integer to the stream

        Args:
            value (int): Integer value
        """
        return self.write(self.__int2bytes(value, size=1, signed=False))

    def read_s16(self) -> int:
        """Reads a signed 16-bit integer from the stream

        Returns:
            int: Integer value
        """
        return self.__bytes2int(self.read(2), signed=True)

    def write_s16(self, value: int) -> None:
        """Writes a signed 16-bit integer to the stream

        Args:
            value (int): Integer value
        """
        return self.write(self.__int2bytes(value, size=2, signed=True))

    def read_u16(self) -> int:
        """Reads a unsigned 16-bit integer from the stream

        Returns:
            int: Integer value
        """
        return self.__bytes2int(self.read(2), signed=False)

    def write_u16(self, value: int) -> None:
        """Writes a unsigned 16-bit integer to the stream

        Args:
            value (int): Integer value
        """
        return self.write(self.__int2bytes(value, size=2, signed=False))

    def read_s32(self) -> int:
        """Reads a signed 32-bit integer from the stream

        Returns:
            int: Integer value
        """
        return self.__bytes2int(self.read(4), signed=True)

    def write_s32(self, value: int) -> None:
        """Writes a signed 32-bit integer to the stream

        Args:
            value (int): Integer value
        """
        return self.write(self.__int2bytes(value, size=4, signed=True))

    def read_u32(self) -> int:
        """Reads a unsigned 32-bit integer from the stream

        Returns:
            int: Integer value
        """
        return self.__bytes2int(self.read(4), signed=False)

    def write_u32(self, value: int) -> None:
        """Writes a unsigned 32-bit integer to the stream

        Args:
            value (int): Integer value
        """
        return self.write(self.__int2bytes(value, size=4, signed=False))

    def read_f32(self) -> float:
        """Reads a single-precision, floating-point value from the stream

        Returns:
            float: Single-precision, floating-point value
        """
        return self.__bytes2dec(self.read(4))

    def write_f32(self, value: float) -> None:
        """Writes a single-precision, floating-point value to the stream

        Args:
            value (float): Single-precision, floating-point value
        """
        return self.write(self.__dec2bytes(value, size=4))

    def read_f64(self) -> float:
        """Reads a double-precision, floating-point value from the stream

        Returns:
            float: Double-precision, floating-point value
        """
        return self.__bytes2dec(self.read(8))

    def write_f64(self, value: float) -> None:
        """Writes a double-precision, floating-point value to the stream

        Args:
            value (float): Double-precision, floating-point value
        """
        return self.write(self.__dec2bytes(value, size=8))

    def read_string(self, maxlen: int = -1) -> str:
        """Reads a UTF-8 string from the stream

        Args:
            maxlen (int, optional): Maximum number of characters to read.
                                    Defaults to -1 (go until null terminator or end-of-file).

        Returns:
            str: UTF-8 string
        """
        string = ""
        i = 0

        while i < maxlen or maxlen == -1:
            if self.eof():
                break

            data = self.read(1)
            if data[0] == 0x00:
                break

            string += data.decode("utf-8")
            i += 1

        return string

    def write_string(self, string: str, maxlen: int = -1,
                     terminate: bool = True) -> None:
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
            string = string[:maxlen - term_size]

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
        string = ""
        i = 0

        while i < maxlen or maxlen == -1:
            if self.eof():
                break

            data = self.read(2)
            if data[0] == 0x00 and data[1] == 0x00:
                break

            string += data.decode("utf-16")
            i += 1

        return string

    def write_wstring(self, string: str, maxlen: int = -1,
                      terminate: bool = True) -> None:
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
            string = string[:maxlen - term_size]

        self.write(string.encode("utf-16-be"))

        if terminate:
            self.write_u16(0x0000)

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

    def __int2bytes(self, value: int, size: int, signed: bool) -> bytes:
        """Converts an integer value into bytes, based on the stream endianness

        Args:
            value (int): Integer value
            size (int): Number of bytes to use
            signed (bool): Whether the value should be expressed as signed

        Returns:
            bytes: Byte representations
        """
        endian = {
            "<": "little",
            ">": "big",
        }[self._endian]

        return int.to_bytes(value, length=size, byteorder=endian, signed=signed)

    def __bytes2int(self, data: bytes, signed: bool) -> int:
        """Converts bytes into an integer value, based on the stream endianness

        Args:
            data (bytes): Byte representation
            signed (bool): Whether the value should be treated as signed

        Returns:
            int: Integer value
        """
        endian = {
            "<": "little",
            ">": "big",
        }[self._endian]

        return int.from_bytes(data, byteorder=endian, signed=signed)

    def __dec2bytes(self, value: float, size: int) -> bytes:
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

    def __bytes2dec(self, data: bytes) -> float:
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
    """Physical file stream
    """

    def __init__(self, path: str, open_mode: str):
        """Constructor

        Args:
            path (str): File path to open
            open_mode (str): Open mode string: "r" (read) / "w" (write) / "x" (create),
                             followed by ':', and '<' for little endian or '>' for big endian.
        """
        super().__init__("<")

        self._file = None
        self.open(path, open_mode)

    @property
    def path(self):
        """Accesses the streams's filepath (read-only)
        """
        return self._path

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
        if not self._file:
            raise OperationError("No file is open")
        if self.eof():
            raise EOFError("Hit end-of-file")
        if "r" not in self._open_mode:
            raise OperationError("Not for this openmode")

        return self._file.read(size)

    @override
    def write(self, data: bytes | bytearray) -> None:
        """Writes bytes to the stream

        Args:
            data (bytes | bytearray): Data to write

        Raises:
            OperationError: Stream is not open
            OperationError: Stream is read-only
        """
        if not self._file:
            raise OperationError("No file is open")
        if "w" not in self._open_mode:
            raise OperationError("Not for this openmode")

        self._file.write(data)

    @override
    def eof(self) -> bool:
        """Tests whether the stream has hit the end of the file

        Returns:
            bool: Whether the stream has hit the end of the file

        Raises:
            OperationError: Stream is not open
        """
        if not self._file:
            raise OperationError("No file is open")

        if "r" not in self._open_mode:
            return False

        # Try to peek one byte
        if len(self._file.read(1)) == 0:
            return True

        # Undo read operation
        self._file.seek(-1, SeekDir.CURRENT)
        return False

    @override
    def seek(self, origin: SeekDir, offset: int) -> None:
        """Seeks the stream position

        Args:
            origin (SeekDir): Seek origin point
            offset (int): Seek distance

        Raises:
            OperationError: Stream is not open
        """
        if not self._file:
            raise OperationError("No file is open")

        self._file.seek(offset, origin)

    @override
    def tell(self) -> int:
        """Retrieves the stream position

        Returns:
            int: Stream position (from begin)

        Raises:
            OperationError: Stream is not open
        """
        if not self._file:
            raise OperationError("No file is open")

        return self._file.tell()

    @override
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
        if not self._file:
            raise OperationError("No file is open")

        remain = Util.align(self.tell(), alignment) - self.tell()
        if remain == 0:
            return

        match self._open_mode[0]:
            case "r":
                self.seek(SeekDir.CURRENT, remain)
            case "w" | "x":
                self.write_padding(remain)

    @override
    def length(self) -> int:
        """Retrives the stream length

        Returns:
            int: Stream length
        """
        if not self._file:
            raise OperationError("No file is open")

        return self._length

    def open(self, path: str, open_mode: str) -> None:
        """Opens the specified file

        Args:
            path (str): File path to open
            open_mode (str): Open mode string: "r" (read) / "w" (write) / "x" (create),
                             followed by ':', and '<' for little endian or '>' for big endian.
        """
        # Close existing file
        if self._file:
            self.close()

        self._path = path
        self.__set_open_mode(open_mode)
        self._file = open(self._path, self._open_mode)

        # Store filesize for later
        self._file.seek(0, SEEK_END)
        self._length = self._file.tell()
        self._file.seek(0, SEEK_SET)

    @override
    def close(self) -> None:
        """Closes the stream
        """
        if self._file:
            self._file.close()
            self._file = None

    def __set_open_mode(self, open_mode: str) -> None:
        """Sets the open mode of the stream

        Args:
            open_mode (str): Open mode string: "r" (read) / "w" (write) / "x" (create),
                             followed by ':', and '<' for little endian or '>' for big endian.

        Raises:
            ArgumentError: Invalid openmode provided
        """
        # Split open mode / endianness
        mode_tokens = open_mode.split(":")
        if len(mode_tokens) != 2:
            raise ArgumentError("Invalid stream openmode")

        self._open_mode = mode_tokens[0]
        self._endian = mode_tokens[1]

        # Force binary mode
        if self._open_mode[-1] != "b":
            self._open_mode += "b"

        if self._open_mode not in ("rb", "wb", "xb"):
            raise ValueError("Invalid stream openmode")


class BufferStream(Stream):
    """Byte-buffer file stream (read+write)
    """

    def __init__(self, endian: str, buffer: bytes | bytearray = None):
        """Constructor

        Args:
            endian (str): Endianness string ('<' for little endian or '>' for big endian)
            buffer (bytes | bytearray, optional): Byte buffer to read from. If you want to
                                                  build a buffer, use None. Defaults to None.

        Raises:
            ArgumentError: Invalid argument(s) provided
        """
        super().__init__(endian)

        self._buffer = None
        self.open(buffer, endian)

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
        if self._buffer == None:
            raise OperationError("No buffer is open")
        if self.eof():
            raise EOFError("Hit end of the buffer")

        # -1 size means read until EOF
        if size == -1:
            size = self.length() - self._position

        # Don't read past EOF
        if self._position + size >= self.length():
            data = self._buffer[self._position:]
            self._position = self.length()
        else:
            data = self._buffer[self._position: self._position + size]
            self._position += size

        return data

    @override
    def write(self, data: bytes | bytearray) -> None:
        """Writes bytes to the stream

        Args:
            data (bytes | bytearray): Data to write

        Raises:
            OperationError: Stream is not open
            OperationError: Stream is read-only
        """
        if self._buffer == None:
            raise OperationError("No buffer is open")

        self._buffer[self._position: self._position + len(data)] = data
        self._position += len(data)

    @override
    def eof(self) -> bool:
        """Tests whether the stream has hit the end of the buffer

        Returns:
            bool: Whether the stream has hit the end of the buffer

        Raises:
            OperationError: Stream is not open
        """
        if self._buffer == None:
            raise OperationError("No buffer is open")

        return self._position >= self.length()

    @override
    def seek(self, origin: SeekDir, offset: int) -> None:
        """Seeks the stream position

        Args:
            origin (SeekDir): Seek origin point
            offset (int): Seek distance

        Raises:
            OperationError: Stream is not open
        """
        if self._buffer == None:
            raise OperationError("No buffer is open")

        self._position = {
            SeekDir.BEGIN: offset,
            SeekDir.CURRENT: self._position + offset,
            SeekDir.END: self.length() + offset
        }[origin]

    @override
    def tell(self) -> int:
        """Retrieves the stream position

        Returns:
            int: Stream position (from begin)

        Raises:
            OperationError: Stream is not open
        """
        if self._buffer == None:
            raise OperationError("No buffer is open")

        return self._position

    @override
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
        if self._buffer == None:
            raise OperationError("No buffer is open")

        remain = Util.align(self.tell(), alignment) - self.tell()
        if remain == 0:
            return

        if not self.eof():
            self.seek(SeekDir.CURRENT, remain)
        else:
            self.write_padding(remain)

    @override
    def length(self) -> int:
        """Retrives the stream length

        Returns:
            int: Stream length
        """
        if self._buffer == None:
            raise OperationError("No buffer is open")

        return len(self._buffer)

    def open(self, buffer: bytes | bytearray, endian: str) -> None:
        """Opens the specified byte buffer

        Args:
            buffer (bytes | bytearray, optional): Byte buffer to read from. If you want to
                                                  build a buffer, use None. Defaults to None.
            endian (str): Endianness string ('<' for little endian or '>' for big endian)
        """
        self._buffer = buffer
        self._endian = endian
        self._position = 0

        if not self._buffer:
            self._buffer = bytearray()

        if isinstance(self._buffer, bytes):
            self._buffer = bytearray(self._buffer)

    @override
    def close(self) -> None:
        """Closes the stream
        """
        self._buffer = None
        self._position = 0

    def result(self) -> bytes | bytearray:
        """Accesses the built buffer (read-only)

        Returns:
            bytes | bytearray: Resulting buffer

        Raises:
            OperationError: Stream is not open
        """
        if self._buffer == None:
            raise OperationError("No buffer is open")

        return self._buffer
