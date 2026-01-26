"""Parses ansible log files and removes the boring 'it worked' bits."""

from __future__ import annotations
from argparse import ArgumentParser, ArgumentDefaultsHelpFormatter, FileType, Namespace
from logging import debug, info, warning, error, critical
from collections import defaultdict
from argparse_with_config import ArgumentParserWithConfig
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
    parser = ArgumentParserWithConfig(
        formatter_class=help_handler, description=__doc__, epilog="Example Usage: "
    )

    group = parser.add_argument_group("display", config_path="display")

    group.add_argument(
        "-H",
        "--show-header",
        action="store_true",
        help="Shows the top header from the file too.",
        config_path="show_header",
    )

    group.add_argument(
        "-T",
        "--show-trailer",
        action="store_true",
        help="Shows the trailer from the file too.",
        config_path="show_trailer",
    )

    group.add_argument(
        "-P",
        "--dont-show-prefixes",
        action="store_true",
        help="Do not strip the '|' line prefixes (dates, processes, users, ...).",
        config_path="dont_strip_prefixes",
    )

    group = parser.add_argument_group("groupings", config_path="groupings")

    group.add_argument(
        "--dont-use-groupings",
        action="store_true",
        help="Do not group identical output from hosts together",
        config_path="dont_use_groupings",
    )

    group.add_argument(
        "--dont-group-oks",
        action="store_true",
        help="Do not group ok hosts together",
        config_path="dont_group_oks",
    )
    
    group.add_argument(
        "--dont-group-skipped",
        action="store_true",
        help="Do not group ok hosts together",
        config_path="dont_group_skipped",
    )
    

    group = parser.add_argument_group("output", config_path="output")

    group.add_argument(
        "-o",
        "--output-to",
        type=FileType("w"),
        help="A file to write results to instead of using the pager",
        config_path="output_to",
    )

    group.add_argument(
        "-s",
        "--stdout",
        action="store_true",
        help="Just print the results to stdout, and don't use a pager",
        config_path="stdout",
    )

    group = parser.add_argument_group("debugging", config_path="debug")

    group.add_argument(
        "--log-level",
        "--ll",
        default="info",
        help="Define the logging verbosity level (debug, info, warning, error, fotal, critical).",
        config_path="log_level",
    )

    parser.add_argument(
        "input_file",
        type=FileType("r"),
        nargs="?",
        default=sys.stdin,
        help="Input log file to parse and display",
        config_path="input_file",
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

    return (args, parser.config)


def main():
    (args, config) = parse_args()

    # TODO(hardaker): clean this up
    if not args.output_to and not args.stdout:
        console = Console()
        with console.pager():
            ansible_less = AnsibleLess(config=config,
                                       output_to=console)
            ansible_less.process(args.input_file)
    else:
        output_to = args.output_to
        if args.stdout:
            output_to = sys.stdout
        ansible_less = AnsibleLess(config=config, output_to=output_to)
        ansible_less.process(args.input_file)

    output_to = args.output_to


if __name__ == "__main__":
    main()
