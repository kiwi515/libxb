from argparse import ArgumentParser, Namespace
from os.path import basename, isdir, join

from ..archives.presets import (
    MNG3Archive,
    MNG4Archive,
    MNG5Archive,
    MNGPArchive,
    MNTArchive,
    MNTPArchive,
)
from .exceptions import XBError


class CLI:
    """Command-line interface"""

    GAME_TO_CLASS = {
        "mng3": MNG3Archive,
        "mng4": MNG4Archive,
        "mngp": MNGPArchive,
        "mng5": MNG5Archive,
        "mnt": MNTArchive,
        "mntp": MNTPArchive,
    }

    @classmethod
    def main(cls) -> int:
        """Command-line entrypoint

        Returns:
            int: Program exit code
        """
        parser = ArgumentParser(
            prog="libxb", description="libxb command line interface"
        )

        parser.add_argument(
            "-o",
            "--output",
            type=str,
            metavar="<path>",
            help="(optional) Output path for extraction/creation result",
        )

        parser.add_argument(
            "-g",
            "--game",
            type=str,
            choices=("mng3", "mng4", "mngp", "mng5", "mnt", "mntp"),
            required=True,
            metavar="<name>",
            help="Target game for the XB archive",
        )

        group = parser.add_mutually_exclusive_group(required=True)
        group.add_argument(
            "-x",
            "--extract",
            type=str,
            metavar="<archive>",
            help="""Extract an XB archive to the output path.
                    If no output path is specified, a directory with the same
                    name as the archive will be created (*.xb.d)""",
        )
        group.add_argument(
            "-c",
            "--create",
            nargs="+",
            type=str,
            metavar="<path>",
            help="""Create an XB archive from the specified files and/or directories.
                    If no output path is specified, and only a single input path is specified,
                    an archive with the same name as the input path will be created
                    (*.xb.d -> *.xb, otherwise: *.* -> *.*.xb)""",
        )

        parser.add_argument(
            "-r",
            "--root",
            default="",
            type=str,
            metavar="<path>",
            help="(optional) Root path/prefix for files in the XB archive (i.e. ../ for MNGP)",
        )

        parser.add_argument(
            "-v",
            "--verbose",
            action="store_true",
            help="(optional) Enable verbose log output",
        )

        args = parser.parse_args()

        if args.create and len(args.create) > 1 and not args.output:
            parser.error(
                "Can't automatically name the output archive. Please specify an output filename."
            )

        if args.extract:
            return 0 if cls.__extract(args) else 1
        elif args.create:
            return 0 if cls.__create(args) else 1
        else:
            return 0

    @classmethod
    def __extract(cls, args: Namespace) -> bool:
        """Performs the 'extract' command

        Args:
            args (Namespace): Command-line arguments

        Returns:
            bool: Success
        """
        archive_cls = cls.GAME_TO_CLASS.get(args.game)
        assert archive_cls != None, "Invalid game name (internal error)"

        src_path = args.extract

        # Output directory defaults to the same name
        if not args.output:
            args.output = f"{src_path}.d"

        try:
            with archive_cls(src_path, "r") as arc:
                arc.extract_all(path=args.output, verbose=args.verbose)
        except XBError as err:
            print(f"[ERROR] Failed to extract {src_path}:")
            print(err)
            return False

        return True

    @classmethod
    def __create(cls, args: Namespace) -> bool:
        """Performs the 'create' command

        Args:
            args (Namespace): Command-line arguments

        Returns:
            bool: Success
        """
        archive_cls = cls.GAME_TO_CLASS.get(args.game)
        assert archive_cls != None, "Invalid game name (internal error)"

        # Output directory defaults to the same name
        if not args.output:
            assert len(args.create) == 1, "Invalid create args (internal error)"

            if args.create[0].lower().endswith(".xb.d"):
                # Trim to preserve original capitalization
                args.output = args.create[0][:-2]
            else:
                args.output = f"{args.create[0]}.xb"

        try:
            with archive_cls(args.output, "w") as arc:
                for path in args.create:
                    # "xb_path" argument must be absolute
                    if not isdir(path):
                        xb_path = join(args.root, basename(path))
                    else:
                        xb_path = args.root

                    arc.add(path=path, xb_path=xb_path, verbose=args.verbose)
        except XBError as err:
            print(f"[ERROR] Failed to create {args.output}:")
            print(err)
            return False

        return True
