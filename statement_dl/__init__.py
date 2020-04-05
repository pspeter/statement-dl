from argparse import ArgumentParser

from .flatex import download_documents_from_args as flatex_dl

_prog_description = """\
statement_dl can be used to download files from online (mainly Austrian) brokers and
banks. Call 'statement_dl <broker/bank> -h' for more help.
"""


def main():
    parser = ArgumentParser(prog="statement_dl", description=_prog_description)

    subparser = parser.add_subparsers(title="Available brokers/banks")

    download_parent_parser = ArgumentParser(add_help=False)
    download_parent_parser.add_argument(
        "dest", type=str, help="Directory in which your downloaded files will be saved",
    )
    download_parent_parser.add_argument(
        "-f",
        "--from-date",
        type=str,
        default="2010-01-01",
        metavar="DATE",
        help="Date from which you want to download your files"
        " (in the format YYYY-MM-DD or 'today'). Defaults to '2010-01-01'",
    )
    download_parent_parser.add_argument(
        "-t",
        "--to-date",
        type=str,
        default="today",
        metavar="DATE",
        help="Date until which you want to download your files"
        " (in the format YYYY-MM-DD or 'today'). Defaults to 'today'",
    )
    download_parent_parser.add_argument(
        "-g",
        "--geckodriver",
        type=str,
        default=None,
        metavar="PATH",
        help="Path to geckodriver executable. If not specified, it will look for"
        " it in the Path",
    )
    download_parent_parser.add_argument(
        "-u", "--username", type=str, default=None, help="Username for automatic login"
    )
    download_parent_parser.add_argument(
        "-p", "--password", type=str, default=None, help="Password for automatic login"
    )
    download_parent_parser.add_argument(
        "--wsl",
        action="store_true",
        help="Set this option when running the script in WSL while using a geckodriver "
        "executable that was installed on Windows",
    )
    download_parent_parser.add_argument(
        "--headless",
        action="store_true",
        help="Launch browser in headless mode. This only works if username and"
        " password are set",
    )
    download_parent_parser.add_argument(
        "-a",
        "--all-files",
        action="store_true",
        help="Automatically download all files instead of only unread",
    )
    download_parent_parser.add_argument(
        "-k",
        "--keep-filenames",
        action="store_true",
        help="Keep the original filenames instead of renaming them to a more "
        "useful format",
    )

    flatex_parser = subparser.add_parser("flatex", parents=[download_parent_parser])
    flatex_parser.set_defaults(func=flatex_dl)
    flatex_parser.add_argument(
        "--de",
        action="store_true",
        help="Use 'de' domain instead of 'at' (experimental)",
    )

    args = parser.parse_args()

    if "func" in args:
        args.func(args)
    else:
        parser.print_usage()
