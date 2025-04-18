class Util:
    """Utility functions
    """

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
