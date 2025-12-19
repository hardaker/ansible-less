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


def clean_blanks(lines: list[str]) -> list[str]:
    """Drops trailing blank lines from a list of lines"""
    while len(lines) > 0 and re.match(r"^\s*$", lines[-1]):
        lines.pop()
    return lines


def filter_lines(lines: list[str]) -> list[str]:
    """Clean and filter lines to simplify the output.

    - Drop lines containing just date strings.
    - Drop line portions containing diffs of tmpfile names
    """

    line_counter = 0
    while line_counter < len(lines):
        current_line = lines[line_counter]

        # drop date only lines
        if re.match(r"\w+ \d+ \w+ \d+  \d{2}:\d{2}:\d{2}", current_line):
            lines.pop(line_counter)
            # note: don't increment line counter here, as we want the same spot
            continue

        if re.match(r"^skipping: .*", current_line):
            lines.pop(line_counter)
            # note: don't increment line counter here, as we want the same spot
            continue

        lines[line_counter] = re.sub(
            r"(.*after:.*/.ansible/tmp/)[^/]+.*/", "\\1.../", current_line
        )

        line_counter += 1

    return clean_blanks(lines)


def group_by_hosts(lines: list[str]) -> dict[str, list[str]]:
    """takes a collection of ansible log lines and groups them by hostname"""
    groupings = {}
    current_lines = []
    for line in lines:
        if results := re.match(r"(changed|ok|failed|fatal): \[([^]]+)\]:*(.*)", line):
            # print("FOUND: " + results.group(1) + " -- " + results.group(2))
            if results.group(3) != "":
                current_lines.insert(0, results.group(3) + "\n")
            groupings[str(results.group(2))] = {
                "status": str(results.group(1)),
                "lines": filter_lines(current_lines),
            }
            current_lines = []
        else:
            current_lines.append(line)
    # rich.print(groupings)
    return groupings


def check_important(lines: list[str]) -> bool:
    """Decide which lines may indicate we need to display this section."""
    for line in lines:
        if "changed:" in line:
            return True
        elif "FAILED" in line or "fatal" in line or "failed" in line:
            return True

    return False


def print_section(
    lines: list[str],
    strip_prefixes: bool = True,
    display_by_groups: bool = True,
    group_oks: bool = True,
    status_prefix: str = ">"
) -> None:
    """Prints a section of information after grouping it by hosts and cleaning."""
    # TODO(hardaker): make an CLI option for strip_prefixes
    # TODO(hardaker): make an CLI option for display_by_groups
    # TODO(hardaker): make an CLI option for group_oks

    # print("------------------------")
    if strip_prefixes:
        lines = [re.sub(r"^[^|]*\s*\| ", "", line) for line in lines]

    if display_by_groups:
        task_line = lines.pop(0)
        task_line = re.sub(r"\**$", "", task_line)
        print("==== " + task_line)

        buffer = []
        groupings = group_by_hosts(lines)
        sorted_keys = sorted(groupings, key=lambda x: groupings[x]["lines"])
        last_key = None

        if group_oks:
            # group 'ok' statuses into a single report line with a count
            ok_count = len([x for x in sorted_keys if groupings[x]["status"] == "ok"])
            if ok_count > 0:
                buffer.append(f"{status_prefix} ok: {ok_count} hosts\n")

        for key in sorted_keys:
            if group_oks and groupings[key]["status"] == "ok":
                continue
            status_line = f"{status_prefix} {groupings[key]['status']}: {key}:\n"
            if last_key and groupings[last_key]["lines"] == groupings[key]["lines"]:
                buffer.insert(-1, status_line)
                continue
            buffer.append(status_line)
            buffer.append("".join(groupings[key]["lines"]))
            last_key = key
        print("".join(buffer))
    else:
        print("".join(lines))


def print_nothing(lines: list[str]) -> None:
    """A no-op print handler"""
    return


def print_task(lines: list[str]) -> None:
    """Prints a list of lines for a section"""
    print_section(lines)


def maybe_print_task(lines: list[str]) -> None:
    if check_important(lines):
        print_task(lines)


def print_trailer(lines: list[str]) -> None:
    """Prints the final section"""
    rich.print("".join(lines))


def main():
    args = parse_args()

    printers: dict[str, callable] = {
        "HEADER": print_nothing,
        "TASK": maybe_print_task,
        "HANDLER": maybe_print_task,
        "PLAY RECAP": print_task,
    }

    if args.show_headers:
        printers["HEADER"] = print_section

    last_section: str = "HEADER"
    current_lines: list[str] = []

    for line in args.input_file:
        for section_words in ["TASK", "HANDLER", "PLAY RECAP"]:
            if line.startswith(section_words) or f" {section_words} " in line:
                printers[last_section](current_lines)
                current_lines = []
                last_section = section_words

        current_lines.append(line)

    print_trailer(current_lines)


if __name__ == "__main__":
    main()
