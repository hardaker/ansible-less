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


def parse_args() -> Namespace:
    """Parse the command line arguments."""
    parser = ArgumentParser(
        formatter_class=help_handler, description=__doc__, epilog="Example Usage: "
    )

    parser.add_argument(
        "-H",
        "--show-headers",
        action="store_true",
        help="Shows the top headers from the file too.",
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


def group_by_hosts(lines: list[str]) -> dict[str, list[str]]:
    """takes a collection of ansible log lines and groups them by hostname"""
    groupings = {}
    current_lines = []
    for line in lines:
        if results := re.match(r"(changed|ok|failed): \[([^]]+)\]", line):
            # print("FOUND: " + results.group(1) + " -- " + results.group(2))
            groupings[str(results.group(2))] = {
                "status": str(results.group(1)),
                "lines": current_lines,
            }
            current_lines = []
        else:
            current_lines.append(line)
    # rich.print(groupings)
    return groupings


def check_important(lines: list[str]) -> bool:
    for line in lines:
        if "changed:" in line:
            return True
        elif "FAILED" in line or "fatal" in line:
            return True

    return False


def print_section(lines: list[str]) -> None:
    strip_prefixes: bool = True  # TODO(hardaker): make an option for this
    display_by_groups: bool = True  # TODO(hardaker): make an option for this

    # print("------------------------")
    if strip_prefixes:
        lines = [re.sub(r"^[^|]*\s*\| ", "", line) for line in lines]

    if display_by_groups:
        task_line = lines.pop(0)
        task_line = re.sub(r'\**$', '', task_line)
        print("==== " + task_line)

        buffer = []
        groupings = group_by_hosts(lines)
        sorted_keys = sorted(groupings, key=lambda x: groupings[x]["lines"])
        last_key = None
        for key in sorted_keys:
            status_line = "== " + groupings[key]["status"] + ": " + key + ":\n"
            if last_key and groupings[last_key]["lines"] == groupings[key]["lines"]:
                buffer.insert(-1, status_line)
                continue
            buffer.append(status_line)
            buffer.append("".join(groupings[key]["lines"]))
            last_key = key
        print("".join(buffer))
    else:
        print("".join(lines))


def maybe_print_nothing(lines: list[str]) -> None:
    return


def maybe_print_task(lines: list[str]) -> None:
    if check_important(lines):
        print_section(lines)


def main():
    args = parse_args()

    printers: dict[str, callable] = {
        "NONE": maybe_print_nothing,
        "TASK": maybe_print_task,
    }

    if args.show_headers:
        printers["NONE"] = print_section

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
