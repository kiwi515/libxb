from typing import override

from .archive.archive import XBArchive, XBFile


class MNG3Archive(XBArchive):
    """XB archive for Minna no Golf 3 / Hot Shots Golf 3"""

    ENDIAN = "<"

    def __init__(self, path: str, open_mode: str):
        """Constructor

        Args:
            path (str): File path to open
            open_mode (str): Open mode string: "r" (read) / "w" (write) / "x" (create).

        Raises:
            ArgumentError: Invalid argument(s) provided
            ArchiveNotFoundError: Archive file does not exist
            ArchiveExistsError: Archive file already exists
            BadArchiveError: Archive file is broken or corrupted
        """
        raise NotImplementedError("MNG3 not yet supported")


class MNG4Archive(XBArchive):
    """XB archive for Minna no Golf 4 / Hot Shots Golf Fore!"""

    ENDIAN = "<"

    def __init__(self, path: str, open_mode: str):
        """Constructor

        Args:
            path (str): File path to open
            open_mode (str): Open mode string: "r" (read) / "w" (write) / "x" (create).

        Raises:
            ArgumentError: Invalid argument(s) provided
            ArchiveNotFoundError: Archive file does not exist
            ArchiveExistsError: Archive file already exists
            BadArchiveError: Archive file is broken or corrupted
        """
        raise NotImplementedError("MNG4 not yet supported")


class MNGPArchive(XBArchive):
    """XB archive for the Minna no Golf Portable / Hot Shots Golf: Open Tee games"""

    ENDIAN = "<"

    def __init__(self, path: str, open_mode: str, create_outside: bool = True):
        """Constructor

        Args:
            path (str): File path to open
            open_mode (str): Open mode string: "r" (read) / "w" (write) / "x" (create).
            create_outside (str): Make paths relative to the data/ directory ("../" prefix).
                                  Only disable this if you want to make XB archives for the web server.

        Raises:
            ArgumentError: Invalid argument(s) provided
            ArchiveNotFoundError: Archive file does not exist
            ArchiveExistsError: Archive file already exists
            BadArchiveError: Archive file is broken or corrupted
        """
        super().__init__(path, f"{open_mode}:{self.ENDIAN}")
        self._create_outside = create_outside

    @override
    def _transform_in(self, file: XBFile) -> XBFile | None:
        """Transform function for files that will be added to the archive.

        Args:
            file (XBFile): File to be added

        Returns:
            XBFile | None: Resulting file ('None' to omit file)
        """
        # Backslashes are expected
        file.path = file.path.replace("/", "\\")

        # Outside-path prefix
        if self._create_outside:
            file.path = f".\\{file.path}"

        return file

    @override
    def _transform_out(self, file: XBFile) -> XBFile | None:
        """Transform function for files that will be extracted from the archive.
        Useful for subclasses to apply transformations/filters.

        Args:
            file (XBFile): File to be extracted

        Returns:
            XBFile | None: Resulting file ('None' to omit file)
        """
        # Remove outside-path prefix
        file.path = file.path.replace("..\\", "")
        return file


class MNG5Archive(XBArchive):
    """XB archive for Minna no Golf 5 / Hot Shots Golf: Out of Bounds"""

    ENDIAN = ">"

    def __init__(self, path: str, open_mode: str):
        """Constructor

        Args:
            path (str): File path to open
            open_mode (str): Open mode string: "r" (read) / "w" (write) / "x" (create).

        Raises:
            ArgumentError: Invalid argument(s) provided
            ArchiveNotFoundError: Archive file does not exist
            ArchiveExistsError: Archive file already exists
            BadArchiveError: Archive file is broken or corrupted
        """
        super().__init__(path, f"{open_mode}:{self.ENDIAN}")

    @override
    def _transform_in(self, file: XBFile) -> XBFile | None:
        """Transform function for files that will be added to the archive.

        Args:
            file (XBFile): File to be added

        Returns:
            XBFile | None: Resulting file ('None' to omit file)
        """
        # Backslashes are expected
        file.path = file.path.replace("/", "\\")

        return file


class MNG6Archive(XBArchive):
    """XB archive for Minna no Golf 6 / Hot Shots Golf: World Invitational"""

    def __init__(self, path: str, open_mode: str):
        """Constructor

        Args:
            path (str): File path to open
            open_mode (str): Open mode string: "r" (read) / "w" (write) / "x" (create).

        Raises:
            ArgumentError: Invalid argument(s) provided
            ArchiveNotFoundError: Archive file does not exist
            ArchiveExistsError: Archive file already exists
            BadArchiveError: Archive file is broken or corrupted
        """
        raise NotImplementedError("MNG6 not yet supported")
