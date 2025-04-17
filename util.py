from .exceptions import ArgumentError


def align(thing: int | bytes | bytearray,
          alignment: int) -> int | bytes | bytearray:
    """Aligns an integer value or byte buffer to a specified byte boundary

    Args:
        thing (int | bytes | bytearray): Data to align
        alignment (int): Byte alignment boundary

    Raises:
        TypeError: Unsupported argument type
    """

    if isinstance(thing, (bytes, bytearray)):
        remain = alignment - (len(thing) % alignment)
        thing += bytes([0x00] * remain)
        return thing
    elif isinstance(thing, int):
        remain = alignment - (thing % alignment)
        return thing + remain
    else:
        raise TypeError("Unsupported type")
