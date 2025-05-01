# libxb
Python library for the ClapHanz XB archive format

[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)


## User Interface
libxb provides a command-line interface for those who wish to use it as a tool. You can run it as part of the `libxb` Python package (`python -m libxb ...`):

### Usage
```
usage: libxb [-h] [-o <path>] -g <name> (-x <archive> | -c <path> [<path> ...]) [-r <path>] [-v]

libxb command line interface

options:
  -h, --help            show this help message and exit
  -o <path>, --output <path>
                        (optional) Output path for extraction/creation result
  -g <name>, --game <name>
                        Target game for the XB archive
  -x <archive>, --extract <archive>
                        Extract an XB archive to the specified output path. If no output path is specified, a directory
                        with the same name as the archive will be created (*.xb.d)
  -c <path> [<path> ...], --create <path> [<path> ...]
                        Create an XB archive from the specified files and/or directories. If no output path is
                        specified, and only a single input path is specified, an archive with the same name as the
                        input path will be created (*.xb.d -> *.xb, otherwise: *.* -> *.*.xb)
  -r <path>, --root <path>
                        (optional) Root path/prefix for files in the XB archive (i.e. ../ for MNGP)
  -v, --verbose         (optional) Enable verbose log output
```

### Examples
```sh
# Extract mRoomSel.xb as MNGP archive (creates "mRoomSel.xb.d" directory)
python -m libxb -g mngp -x mRoomSel.xb
# Extract mRoomSel.xb as MNGP archive (creates "my_cool_path" directory)
python -m libxb -g mngp -o my_cool_path -x mRoomSel.xb

# Create a MNGP archive from files in mRoomSel.xb.d directory (creates "mRoomSel.xb" file)
python -m libxb -g mngp -c mRoomSel.xb.d
# Create a MNGP archive from files in mRoomSel.xb.d directory (creates "mRoomSelNew.xb" file)
python -m libxb -g mngp -o mRoomSelNew.xb -c mRoomSel.xb.d

# Create a MNGP archive from three specified files (creates "ss.xb" file)
# Root directory is specified as "../data/", so all files in the archive get that prefix.
python -m libxb -g mngp -o ss.xb -c config.dat ss.info sponsor.dat -r ../data/
```

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
