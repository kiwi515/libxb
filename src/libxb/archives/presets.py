from .common import XBEndian, XBOpenMode
from .version2 import XBArchiveVer2


class MNGPArchive(XBArchiveVer2):
    """XB archive for the Minna no Golf Portable / Hot Shots Golf: Open Tee games"""

    def __init__(self, path: str, mode: str):
        """Constructor

        Args:
            path (str): File path to open
            mode (str): File open mode ('r'/'w'/'+'/'x')
        """
        super().__init__(path, XBOpenMode(mode), XBEndian.LITTLE)
