from .common import XBEndian, XBOpenMode
from .implement import XBArchive


class MNG3Archive(XBArchive):
    """XB archive for Minna no Golf 3 / Hot Shots Golf 3"""

    def __init__(self, path: str, mode: str):
        """Constructor

        Args:
            path (str): File path to open
            mode (str): File open mode ('r'/'w'/'+'/'x')
        """
        super().__init__(path, XBOpenMode(mode), XBEndian.LITTLE)


class MNG4Archive(XBArchive):
    """XB archive for Minna no Golf 4 / Hot Shots Golf Fore!"""

    def __init__(self, path: str, mode: str):
        """Constructor

        Args:
            path (str): File path to open
            mode (str): File open mode ('r'/'w'/'+'/'x')
        """
        super().__init__(path, XBOpenMode(mode), XBEndian.LITTLE)


class MNGPArchive(XBArchive):
    """XB archive for the Minna no Golf Portable / Hot Shots Golf: Open Tee games"""

    def __init__(self, path: str, mode: str):
        """Constructor

        Args:
            path (str): File path to open
            mode (str): File open mode ('r'/'w'/'+'/'x')
        """
        super().__init__(path, XBOpenMode(mode), XBEndian.LITTLE)


class MNG5Archive(XBArchive):
    """XB archive for Minna no Golf 5 / Hot Shots Golf: Out of Bounds"""

    def __init__(self, path: str, mode: str):
        """Constructor

        Args:
            path (str): File path to open
            mode (str): File open mode ('r'/'w'/'+'/'x')
        """
        super().__init__(path, XBOpenMode(mode), XBEndian.BIG)


class MNTArchive(XBArchive):
    """XB archive for Minna no Tennis / Hot Shots Tennis"""

    def __init__(self, path: str, mode: str):
        """Constructor

        Args:
            path (str): File path to open
            mode (str): File open mode ('r'/'w'/'+'/'x')
        """
        super().__init__(path, XBOpenMode(mode), XBEndian.LITTLE)


class MNTPArchive(XBArchive):
    """XB archive for Minna no Tennis Portable / Hot Shots Tennis: Get A Grip"""

    def __init__(self, path: str, mode: str):
        """Constructor

        Args:
            path (str): File path to open
            mode (str): File open mode ('r'/'w'/'+'/'x')
        """
        super().__init__(path, XBOpenMode(mode), XBEndian.LITTLE)
