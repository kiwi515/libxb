class XBError(Exception):
    """Base for libxb exceptions
    """


class ArchiveError(XBError):
    """Base for archive related exceptions
    """


class ArgumentError(XBError):
    """Invalid argument value
    """


class OperationError(XBError):
    """Invalid execution state
    """


class CompressionError(XBError):
    """Error while compressing data
    """


class DecompressionError(XBError):
    """Error while decompressing data
    """


class ArchiveNotFoundError(ArchiveError):
    """Archive file was not found and cannot be opened
    """


class ArchiveExistsError(ArchiveError):
    """Archive already exists and cannot be created
    """


class NotAnArchiveError(ArchiveError):
    """Opened file is not a XB archive
    """


class BadArchiveError(ArchiveError):
    """Archive is broken or corrupted and cannot be read
    """
