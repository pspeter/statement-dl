from argparse import ArgumentParser
from datetime import datetime, date
from pathlib import Path

from statement_dl.flatex import download_documents as download_flatex_documents

_prog_description = """\
statement_dl can be used to download files from online (mainly Austrian) brokers and 
banks. Call 'statement_dl <broker/bank> -h' for more help.
"""


def _str_to_date(date_string: str) -> date:
    if date_string == "today":
        return date.today()
    return datetime.strptime(date_string, "%Y-%m-%d").date()


def main():
    parser = ArgumentParser(description=_prog_description)

    subparser = parser.add_subparsers()

    download_parent_parser = ArgumentParser(add_help=False)
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
        "dest", type=str, help="Directory in which your downloaded files will be saved"
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

    flatex_parser = subparser.add_parser("flatex", parents=[download_parent_parser])
    flatex_parser.add_argument(
        "--de",
        action="store_true",
        help="Use 'de' domain instead of 'at' (experimental)",
    )

    args = parser.parse_args()
    download_flatex_documents(
        Path(args.dest),
        _str_to_date(args.from_date),
        _str_to_date(args.to_date),
        args.geckodriver,
        args.username,
        args.password,
        args.all_files,
        args.headless,
        args.de,
        args.wsl,
    )
