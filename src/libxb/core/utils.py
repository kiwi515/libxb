from enum import Enum
from typing import Type

from .exceptions import OperationError


class Util:
    """Utility functions"""

    @staticmethod
    def align(thing, alignment: int):
        """Aligns a supported object to a specified byte boundary.
        Non-integral objects are modified in-place.

        Args:
            thing (Alignable): Data to align
            alignment (int): Byte alignment boundary

        Returns:
            Alignable: Aligned object
            TypeError: Unsupported argument type
        """

        if isinstance(thing, int):
            remain = (alignment - (thing % alignment)) % alignment
            return thing + remain

        if isinstance(thing, (bytes, bytearray)):
            remain = (alignment - (len(thing) % alignment)) % alignment
            thing += bytes([0x00] * remain)
            return thing

        if not hasattr(thing, "align"):
            raise TypeError("Unsupported type")

        thing.align(alignment)
        return thing

    @staticmethod
    def convert_enum(from_value: Enum, to_type: Type[Enum]):
        """Attempts to convert an enum value to the same name in another enum

        Args:
            from_value (Enum): Value to convert
            to_type (Type[Enum]): Type to convert to

        Raises:
            OperationError: Invalid enum conversion

        Returns:
            to_type: Converted value
        """
        try:
            return to_type[from_value.name]
        except KeyError:
            raise OperationError(f"Invalid {to_type.__name__}")
