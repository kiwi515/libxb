# libxb
 Python library for the ClapHanz XB archive format

[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)


## User Interface
`libxb` provides a command-line interface for those who wish to use it as a tool:

### Example usage
TODO: I haven't wrote it yet :P

## Developer Interface
`libxb` provides a simple interface for XB files which resembles that of Python's `tarfile`:

### Example Usage
```py
import libxb

###############################################################################
## Extract archive
###############################################################################
with libxb.XBArchive("my-file.xb", XBOpenMode.READ, XBEndian.LITTLE) as arc:
    arc.extract_all(path="output-path/")

###############################################################################
## Create archive
###############################################################################
with libxb.XBArchive("my-file.xb", XBOpenMode.WRITE, XBEndian.LITTLE) as arc:
    arc.add(path="all-these-files/",
            xb_path="actually-go-here/",      # optional
            compression=XBCompression.DEFLATE # optional
            recursive=True)                   # optional

###############################################################################
## Modify archive
###############################################################################
with libxb.XBArchive("my-file.xb", XBOpenMode.RW, XBEndian.LITTLE) as arc:
    arc.add(path="just-one-file.XB",
            xb_path="/data/config.dat",  # optional
            compression=XBCompression.LZ # optional
            recursive=True)              # optional

###############################################################################
## Process files
###############################################################################
with libxb.XBArchive("my-file.xb", XBOpenMode.READ, XBEndian.LITTLE) as arc:
    for file in arc:
        ... # do whatever
```

### Helper Classes
Additionally, subclasses are provided for each title to remove the need to specify byteorder/endianness, and to allow shorthand strings for the access modes (`'r'`/`'w'`/`'+'`/`'x'`):

| Title                    | Class             |
| ------------------------ | ----------------- |
| Minna no Golf 3          | `MNG3Archive`     |
| Minna no Golf 4          | `MNG4Archive`     |
| Minna no Golf Portable   | `MNGPArchive`     |
| Minna no Golf 5          | `MNG5Archive`     |
| Minna no Golf 6          | Not yet supported |
| Minna no Tennis          | `MNTArchive`      |
| Minna no Tennis Portable | `MNTPArchive`     |

```py
from libxb import MNGPArchive

###############################################################################
## Create archive for Minna no Golf Portable
###############################################################################
with MNGPArchive("config.dat", "w") as arc:
    arc.add(path="config.txt",
            xb_path="/data/config.dat") # optional
```

### API Documentation
See the `XBArchive` implementation for more information about the methods and members provided.
