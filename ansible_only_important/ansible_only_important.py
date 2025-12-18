"""Parses ansible log files and removes the boring 'it worked' bits."""

from __future__ import annotations
from argparse import ArgumentParser, ArgumentDefaultsHelpFormatter, FileType, Namespace
from logging import debug, info, warning, error, critical
import logging
import sys

# optionally use rich
try:
    from rich import print
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

def parse_args() -> Namespace:
    """Parse the command line arguments."""
    parser = ArgumentParser(formatter_class=help_handler,
                            description=__doc__,
                            epilog="Example Usage: ")

    parser.add_argument("--log-level", "--ll", default="info",
                        help="Define the logging verbosity level (debug, info, warning, error, fotal, critical).")

    parser.add_argument("input_file", type=FileType('r'),
                        nargs='?', default=sys.stdin,
                        help="")

    parser.add_argument("output_file", type=FileType('w'),
                        nargs='?', default=sys.stdout,
                        help="")

    args = parser.parse_args()
    log_level = args.log_level.upper()
    handlers = []
    datefmt = None
    messagefmt = "%(levelname)-10s:\t%(message)s"

    # see if we're rich
    try:
        handlers.append(RichHandler(rich_tracebacks=True,
                                    tracebacks_show_locals=True,
                                    console=Console(stderr=True,
                                                    theme=Theme({"logging.level.success": "green"}))))
        datefmt = " "
        messagefmt = "%(message)s"
    except Exception:
        debug("failed to install RichHandler")

    logging.basicConfig(level=log_level,
                        format=messagefmt,
                        datefmt=datefmt,
                        handlers=handlers)
    return args


def check_important(lines) -> bool:
    for line in lines:
        if line.startswith('TASK'):
            continue
        elif "ok:" in line:
            continue
        elif "skipping:" in line:
            continue
        elif "changed:" in line:
            return True
        elif "FAILED" in line or "fatal" in line:
            return True

    return False


def maybe_print_nothing(lines) -> None:
    return


def maybe_print_task(lines) -> None:
    if check_important(lines):
        print("---------------------------------")
        print("".join(lines))


def main():
    args = parse_args()

    printers: dict[str, callable] = {
        "NONE": maybe_print_nothing,
        "TASK": maybe_print_task,
    }

    last_section: str = "NONE"
    current_lines: list[str] = []

    for line in args.input_file:
        if line.startswith("TASK") or " TASK " in line:
            # this starts a new section
            printers[last_section](current_lines)
            current_lines = []
            last_section = "TASK"

        current_lines.append(line)

    printers[last_section](current_lines)
            


if __name__ == "__main__":
    main()
