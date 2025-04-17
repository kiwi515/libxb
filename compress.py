from abc import abstractmethod
from typing import override
from enum import IntFlag, auto
from dataclasses import dataclass
from .stream import Stream, SeekDir, BufferStream
from .exceptions import ArgumentError, DecompressionError, CompressionError


class CompressionStrategy:
    """Data compression/decompression algorithm
    """

    @classmethod
    @abstractmethod
    def compress(strm: Stream) -> bytes:
        """Compresses the input data

        Args:
            strm (Stream): Stream to decompressed data

        Returns:
            bytes: Compressed data
        """
        pass

    @classmethod
    @abstractmethod
    def decompress(strm: Stream, expand_size: int) -> bytes:
        """Decompresses the input data

        Args:
            strm (Stream): Stream to compressed data
            expand_size (int): Size of decompressed (expanded) data

        Returns:
            bytes: Decompressed data
        """
        pass


class ClapHanzLZ(CompressionStrategy):
    """ClapHanz's implementation of LZ data compression
    """

    MIN_RUN = 3

    class ChunkFlag(IntFlag):
        """Compression chunk flags"""
        LITERAL = 0
        SHORTRUN = auto()
        LONGRUN = auto()
        MASK = SHORTRUN | LONGRUN

    @classmethod
    @override
    def compress(cls, strm: Stream) -> bytes:
        """Compresses the input data

        Args:
            strm (Stream): Stream to decompressed data

        Returns:
            bytes: Compressed data
        """

        # TODO: Fake compression
        with BufferStream(strm.endian) as out:
            while not strm.eof():
                chunk = strm.read(64)
                code = (len(chunk) - 1) << 2
                code |= cls.ChunkFlag.LITERAL
                out.write_u8(code)
                out.write(chunk)

            return out.result()

    @classmethod
    @override
    def decompress(cls, strm: Stream, expand_size: int) -> bytes:
        """Decompresses the input data

        Args:
            strm (Stream): Stream to compressed data
            expand_size (int): Size of decompressed (expanded) data

        Returns:
            bytes: Decompressed data

        Raises
            ArgumentError: Invalid argument(s) provided
            DecompressionError: Decompression cannot be completed
        """
        if expand_size <= 0:
            raise ArgumentError("Invalid expanded size")

        output = bytearray(expand_size)
        out_idx = 0

        try:
            while out_idx < expand_size:
                code = strm.read_u8()

                # Literal copy
                if (code & cls.ChunkFlag.MASK) == cls.ChunkFlag.LITERAL:
                    copy_len = (code >> 2) + 1

                    for _ in range(copy_len):
                        output[out_idx] = strm.read_u8()
                        out_idx += 1
                # Run decode
                else:
                    run_offset = 0
                    run_len = 0

                    # Short-distance run
                    # 3 bits for the run length
                    if code & cls.ChunkFlag.SHORTRUN:
                        b0 = strm.read_u8()
                        value = b0 << 8 | code

                        run_len = ((value & 0b1110) >> 1) + cls.MIN_RUN
                        run_offset = value >> 4
                    # Long-distance run
                    # 14 bits for the run length
                    else:
                        b0 = strm.read_u8()
                        b1 = strm.read_u8()
                        value = b1 << 16 | b0 << 8 | code

                        run_len = ((value & 0b111111111100) >> 2) + cls.MIN_RUN
                        run_offset = value >> 12

                    # Copy block
                    run_idx = out_idx - run_offset
                    for _ in range(run_len):
                        output[out_idx] = output[run_idx]
                        out_idx += 1
                        run_idx += 1
        except IndexError:
            raise DecompressionError("Compressed data is malformed")
        except EOFError:
            raise DecompressionError("Hit the end-of-file while decompressing")

        return bytes(output)


class ClapHanzHuffman(CompressionStrategy):
    """ClapHanz's implementation of Huffman data compression
    """

    MAX_DEPTH = 10
    TABLE_SIZE = pow(2, MAX_DEPTH)

    @dataclass
    class Symbol:
        """Flat Huffman decode table entry
        """
        length: int
        symbol: int

    @classmethod
    @override
    def compress(cls, strm: Stream) -> bytes:
        """Compresses the input data

        Args:
            strm (Stream): Stream to decompressed data

        Returns:
            bytes: Compressed data
        """
        raise NotImplementedError()

    @classmethod
    @override
    def decompress(cls, strm: Stream, expand_size: int) -> bytes:
        """Decompresses the input data

        Args:
            strm (Stream): Stream to compressed data
            expand_size (int): Size of decompressed (expanded) data

        Returns:
            bytes: Decompressed data

        Raises
            ArgumentError: Invalid argument(s) provided
            DecompressionError: Decompression cannot be completed
        """
        if expand_size <= 0:
            raise ArgumentError("Invalid expanded size")

        # Build the Huffman decoding table
        try:
            table = cls.__create_huffman_table(strm)
        except (IndexError, EOFError):
            raise DecompressionError("Failed to create Huffman table")

        output = bytearray(expand_size)
        out_idx = 0

        bit_num = 0
        bit_strm = 0

        try:
            while out_idx < expand_size:
                # Read Huffman code and find the table entry
                if bit_num < cls.MAX_DEPTH:
                    bit_strm |= strm.read_u16() << bit_num
                    bit_num += 16

                index = bit_strm & (cls.TABLE_SIZE - 1)
                entry = table[index]

                # Huffman symbol
                if entry.length <= cls.MAX_DEPTH:
                    # Consume bits based on the symbol length
                    output[out_idx] = entry.symbol
                    out_idx += 1
                    bit_strm >>= entry.length
                    bit_num -= entry.length
                # Literal byte
                else:
                    bit_strm >>= cls.MAX_DEPTH
                    bit_num -= cls.MAX_DEPTH

                    # Refresh stream if needed
                    if bit_num < 16:
                        bit_strm |= strm.read_u16() << bit_num
                        bit_num += 16

                    # Consume one byte (8 bits)
                    output[out_idx] = bit_strm & 0xFF
                    out_idx += 1
                    bit_strm >>= 8
                    bit_num -= 8
        except IndexError:
            raise DecompressionError("Compressed data is malformed")
        except EOFError:
            raise DecompressionError("Hit the end-of-file while decompressing")

        return output

    @classmethod
    def __create_huffman_table(cls, strm: Stream) -> list[Symbol]:
        """Reconstructs a flat Huffman decoding table from input code data

        Args:
            strm (Stream): Stream to Huffman code data

        Raises
            ArgumentError: Invalid argument(s) provided
            DecompressionError: Decompression cannot be completed

        Returns:
            list[Symbol]: List of Huffman symbols
        """
        # Table has a fixed size
        table = [None for _ in range(cls.TABLE_SIZE)]

        max_length = strm.read_u8()
        if max_length <= 0:
            raise DecompressionError("Compressed data is malformed")

        code = 0
        length = 1

        try:
            while length <= max_length:
                code_num = strm.read_u8()

                # Read all codes of the current length
                for _ in range(code_num):
                    code_bits = code
                    index = 0

                    # Build the table index
                    for _ in range(length):
                        index = index << 1 | (code_bits & 0b1)
                        code_bits >>= 1

                    symbol = strm.read_u8()

                    # Duplicate symbols which match the prefix?
                    while index < len(table):
                        table[index] = cls.Symbol(length, symbol)
                        index += 1 << length

                    if length <= cls.MAX_DEPTH:
                        code += 1

                length += 1
                code <<= 1
        except IndexError:
            raise DecompressionError("Compressed data is malformed")
        except EOFError:
            raise DecompressionError("Hit the end-of-file while decompressing")

        # Data is aligned to two byte boundary
        if strm.tell() % 2 != 0:
            strm.seek(SeekDir.CURRENT, 1)

        return table
