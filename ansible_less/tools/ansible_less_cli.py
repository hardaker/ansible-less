"""Parses ansible log files and removes the boring 'it worked' bits."""

from __future__ import annotations
from argparse import ArgumentParser, ArgumentDefaultsHelpFormatter, FileType, Namespace
from logging import debug, info, warning, error, critical
from collections import defaultdict
import logging
import sys
import re

# optionally use rich
try:
    # from rich import print
    import rich
    from rich.logging import RichHandler
    from rich.theme import Theme
    from rich.console import Console
except Exception:
    debug("install rich and rich.logging for prettier results")

# optionally use rich_argparse too
help_handler = ArgumentDefaultsHelpFormatter
try:
    from rich_argparse import RichHelpFormatter

    help_handler = RichHelpFormatter
except Exception:
    debug("install rich_argparse for prettier help")

from ansible_less import AnsibleLess


def parse_args() -> Namespace:
    """Parse the command line arguments."""
    parser = ArgumentParser(
        formatter_class=help_handler, description=__doc__, epilog="Example Usage: "
    )

    parser.add_argument(
        "-H",
        "--show-header",
        action="store_true",
        help="Shows the top header from the file too.",
    )

    parser.add_argument(
        "--log-level",
        "--ll",
        default="info",
        help="Define the logging verbosity level (debug, info, warning, error, fotal, critical).",
    )

    parser.add_argument(
        "input_file", type=FileType("r"), nargs="?", default=sys.stdin, help=""
    )

    args = parser.parse_args()
    log_level = args.log_level.upper()
    handlers = []
    datefmt = None
    messagefmt = "%(levelname)-10s:\t%(message)s"

    # see if we're rich
    try:
        handlers.append(
            RichHandler(
                rich_tracebacks=True,
                tracebacks_show_locals=True,
                console=Console(
                    stderr=True, theme=Theme({"logging.level.success": "green"})
                ),
            )
        )
        datefmt = " "
        messagefmt = "%(message)s"
    except Exception:
        debug("failed to install RichHandler")

    logging.basicConfig(
        level=log_level, format=messagefmt, datefmt=datefmt, handlers=handlers
    )
    return args


def main():
    args = parse_args()

    ansible_less = AnsibleLess(show_header=args.show_header)

    ansible_less.process(args.input_file)


if __name__ == "__main__":
    main()
