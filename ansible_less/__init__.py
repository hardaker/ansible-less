"""Parses ansible log files and removes the boring 'it worked' bits."""

from __future__ import annotations
from logging import debug
from collections import defaultdict
import re
import sys

__VERSION__ = "0.1.0"

try:
    from rich import print as pretty_print
except Exception:
    pretty_print = print

try:
    import rich.console
except Exception:
    pass


default_config = {
    'display': {
        'show_header': False,
        'show_trailer': False,
        'dont_strip_prefixes': False,
    }
}


class AnsibleLess:
    """Parses ansible log files and removes the boring 'it worked' bits."""

    def __init__(
        self,
        config: dict | defaultdict = default_config,
        display_by_groups: bool = True,
        group_oks: bool = True,
        group_skipped: bool = True,
        display_all_sections: bool = False,
        status_prefix: str = ":",
        debug: bool = False,
        output_to: IO[str] = sys.stdout,
    ):
        """Create an AnsibleLess instance."""
        self.printers = {
            "HEADER": self.print_header,
            "TASK": self.maybe_print_task,
            "HANDLER": self.maybe_print_task,
            "PLAY RECAP": self.print_task,
        }
        self.last_section: str = "HEADER"
        self.current_lines: list[str] = []

        self.show_header = config['display']['show_header']
        self.show_trailer = config['display']['show_trailer']
        self.strip_prefixes = not config['display']['dont_strip_prefixes']
        self.display_by_groups = display_by_groups
        self.group_oks = group_oks
        self.group_skipped = group_skipped
        self.status_prefix = status_prefix
        self.display_all_sections = display_all_sections
        self.debug = debug
        self.output_to = output_to

        self.hosts = []

    @property
    def strip_prefixes(self) -> bool:
        """Remove the date/time/etc prefixes of each line."""
        return self._strip_prefixes

    @strip_prefixes.setter
    def strip_prefixes(self, newval: bool) -> None:
        self._strip_prefixes = newval

    @property
    def display_by_groups(self) -> bool:
        """Group hosts with similar output together."""
        return self._display_by_groups

    @display_by_groups.setter
    def display_by_groups(self, newval: bool) -> None:
        self._display_by_groups = newval

    @property
    def group_oks(self) -> bool:
        """Group ok: lines from different hosts into just a count."""
        return self._group_oks

    @group_oks.setter
    def group_oks(self, newval: bool) -> None:
        self._group_oks = newval

    @property
    def group_skipped(self) -> bool:
        """Group skipping: lines from different hosts into just a count."""
        return self._group_skipped

    @group_skipped.setter
    def group_skipped(self, newval: bool) -> None:
        self._group_skipped = newval

    @property
    def status_prefix(self) -> str:
        """Add this string to the beginning of all lines referencing hosts."""
        return self._status_prefix

    @status_prefix.setter
    def status_prefix(self, newval: str) -> None:
        self._status_prefix = newval

    @property
    def printers(self) -> dict[str, callable]:
        """The individual functions that do printing for a section."""
        return self._printers

    @printers.setter
    def printers(self, newval: dict[str, callable]) -> None:
        self._printers = newval

    def print(self, data):
        if getattr(self.output_to, "print", None):
            self.output_to.print(data)
        else:
            self.output_to.write(data)

    def escape(self, line: str) -> str:
        if getattr(self.output_to, "print", None):
            return rich.console.escape(line)
        return line

    def pretty_print(self, data):  ## TODO(hardaker): use rich for this printing
        self.print(data)

    def clean_blanks(self, lines: list[str]) -> list[str]:
        """Drop trailing blank lines from a list of lines."""
        while len(lines) > 0 and re.match(r"^\s*$", lines[-1]):
            lines.pop()
        return lines

    def filter_lines(self, lines: list[str]) -> list[str]:
        """Clean and filter lines to simplify the output.

        - Drop lines containing just date strings.
        - Drop line portions containing diffs of tmpfile names
        - Simplify some timestamps
        """
        line_counter = 0
        while line_counter < len(lines):
            current_line = lines[line_counter]

            # drop date only lines
            if re.match(r"^\w+ \d+ \w+ \d+  \d{2}:\d{2}:\d{2}", current_line):
                lines.pop(line_counter)
                # note: don't increment line counter here, as we want the same spot
                continue

            if re.match(r"^skipping: .*", current_line):
                lines.pop(line_counter)
                # note: don't increment line counter here, as we want the same spot
                continue

            # drop dates with fractional seconds for better aggregation
            current_line = re.sub(
                r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\.\d+", "\\1", current_line
            )

            # drop delta times
            current_line = re.sub(
                r'("delta": "\d+:\d{2}:\d{2})\.\d+', "\\1", current_line
            )

            # drop atime/mtime sub-second changes
            current_line = re.sub(r'("[am]time": \d+)\.\d+', "\\1", current_line)

            current_line = re.sub(
                r"(.*after:.*/.ansible/tmp/)[^/]+.*/", "\\1.../", current_line
            )

            lines[line_counter] = current_line

            line_counter += 1

        return self.clean_blanks(lines)

    def group_by_hosts(self, lines: list[str]) -> dict[str, list[str]]:
        """Take a collection of ansible log lines and group them by hostname."""
        groupings = {}
        group_lines = []
        group_host = None

        replacement_statuses = {
            'changed': { 'ok': True, 'skipping': True },
            'failed': {'ok': True, 'changed': True, 'skipping': True},
            'fatal': {'ok': True, 'changed': True, 'skipping': True, 'failed': True},
        }

        for n, line in enumerate(lines):
            if line == "":
                continue
            if "...ignoring" in line:
                # this is actually for the previous host, not the next
                groupings[group_host]["lines"].append(line)
                continue
            if results := re.match(
                r".*(changed|ok|failed|fatal|skipping): \[([^]]+)\]:*\s*(.*)", line
            ):
                # print("FOUND: " + results.group(1) + " -- " + results.group(2))
                group_host = str(results.group(2))
                status = str(results.group(1))
                suffix = str(results.group(3))
                if group_host not in groupings:
                    groupings[group_host] = {
                        "status": status,
                        "lines": self.filter_lines(group_lines),
                    }
                else:
                    # TODO(hardaker): what if there is an ok and a failure // take the worst and update the status!
                    groupings[group_host]['lines'].extend(group_lines)
                    if status in replacement_statuses and groupings[group_host]['status'] in replacement_statuses[status]:
                        groupings[group_host]['status'] = status

                # start collecting lines again for the next host
                group_lines = []
                    
                if suffix != "" and status != "ok" and status != "skipping":
                    groupings[group_host]["lines"].append(suffix + "\n")
            else:
                group_lines.append(line)
        # rich.print(groupings)
        return groupings

    def check_important(self, lines: list[str]) -> bool:
        """Decide which lines may indicate we need to display this section."""
        if self.display_all_sections:
            return True

        # this is really "check_boring"

        boring_line_pieces = [
            "Gathering",
            "Facts",
            "ok:",
            "PLAY",
            "skipping:",
            "Nothing to do",
        ]
        boring_line_pieces.extend(list(self.printers.keys()))

        # find any line that we can't classify as boring, if so return True
        # note: stripping off prefixes
        for line in [re.sub(r"^[^|]*\s*\| ", "", line.strip()) for line in lines]:
            line_is_boring: bool = False

            # check empty
            if line == "":
                line_is_boring = True
                continue  # just continue here, it is

            # check for boring words in a line
            for word in boring_line_pieces:
                if word in line:
                    line_is_boring = True
                    debug(f"found boring word: {word}")
                    break

            # should be able to do this with a fancy for/else thingy
            if line_is_boring:
                continue  # it is

            # check if it looks like a host line
            if re.match(r"^\[\w+\]$", line):
                debug("line is a host")
                continue

            # find display lines
            if re.match(r"^\[*=-]*$", line):
                debug("separator line")
                continue

            # drop date only lines
            if re.match(r"^\w+ \d+ \w+ \d+  \d{2}:\d{2}:\d{2}", line):
                debug("date only line")
                continue
            # this line isn't boring, thus the whole group is important
            if self.debug:
                self.print(f"  IMPORTANT: {line}")
            return True

        # every line was flagged as boring, so it's not important
        if self.debug:
            self.print("BORING:")
            for line in lines:
                self.print(f"  B: {line.strip()}")
        return False

    def print_section(
        self,
        lines: list[str],
    ) -> None:
        """Print a section of information after grouping it by hosts and cleaning."""
        # TODO(hardaker): make an CLI option for strip_prefixes
        # TODO(hardaker): make an CLI option for display_by_groups
        # TODO(hardaker): make an CLI option for group_oks

        if self.debug:
            self.print("=======================================")
            self.print("".join(lines))
            self.print("=====----------------------------------")

        if self.strip_prefixes:
            lines = [re.sub(r"^[^|]*\s*\| ", "", line) for line in lines]

        if self.display_by_groups:
            # print the task itself
            task_line = lines.pop(0)

            buffer = []
            groupings = self.group_by_hosts(lines)

            # check if we have seen the list of hosts yet before
            if len(self.hosts) == 0:
                self.hosts = list(groupings.keys())

            # sort the hostnames based on text
            sorted_hosts = sorted(groupings, key=lambda x: groupings[x]["lines"])
            last_host = None
            skip_headers = set()

            if self.group_oks:
                # group 'ok' statuses into a single report line with a count
                ok_count = len(
                    [x for x in sorted_hosts if groupings[x]["status"] == "ok"]
                )
                if ok_count > 1:
                    if len(self.hosts) > 0 and ok_count == len(self.hosts):
                        buffer.append(f"{self.status_prefix} ok: all hosts\n")
                    elif ok_count > 0:
                        buffer.append(f"{self.status_prefix} ok: {ok_count} hosts\n")
                    skip_headers.add("ok")

            if self.group_skipped:
                # group 'skipped' statuses into a single report line with a count
                skipped_count = len(
                    [x for x in sorted_hosts if groupings[x]["status"] == "skipping"]
                )
                if skipped_count > 1:
                    if len(self.hosts) > 0 and skipped_count == len(self.hosts):
                        buffer.append(f"{self.status_prefix} skipped: all hosts\n")
                    elif skipped_count > 0:
                        buffer.append(
                            f"{self.status_prefix} skipped: {skipped_count} hosts\n"
                        )
                    skip_headers.add("skipping")

            if True:  # bogus just for consistent indentation till refactor
                # group 'changed' statuses into a single report line with a count
                changed_count = len(
                    [x for x in sorted_hosts if groupings[x]["status"] == "changed"]
                )
                if changed_count > 1:
                    if len(self.hosts) > 0 and changed_count == len(self.hosts):
                        buffer.append(f"{self.status_prefix} changed: all hosts\n")
                        skip_headers.add("changed")

            if True:  # bogus just for consistent indentation till refactor
                # group 'failed' statuses into a single report line with a count
                failed_count = len(
                    [x for x in sorted_hosts if groupings[x]["status"] == "failed"]
                )
                if failed_count > 1:
                    if len(self.hosts) > 0 and failed_count == len(self.hosts):
                        buffer.append(f"{self.status_prefix} failed: all hosts\n")
                        skip_headers.add("failed")


            # if everything was ok or skipped, don't print it at all.
            if failed_count == 0 and changed_count == 0:
                return

            # actually print the task at this point

            # strip off trailing garbage
            task_line = re.sub(r"\**$", "", task_line.strip())

            # escape the []s since rich interprets them otherwise
            # task_line = re.sub("\\]", "\]", task_line)
            task_line = re.sub("\\[", "\\[", task_line)

            self.print("==== " + self.escape(task_line))

            for host in sorted_hosts:
                if groupings[host]["status"] in skip_headers:
                    continue
                status_line = (
                    f"{self.status_prefix} {groupings[host]['status']}: {host}:\n"
                )
                if last_host and groupings[last_host]["lines"] == groupings[host]["lines"]:
                    buffer.insert(-1, status_line)
                    continue
                buffer.append(status_line)
                buffer.append("".join(groupings[host]["lines"]))
                last_host = host
            self.print("".join(buffer))
        else:
            self.print("".join(lines))

    def print_header(self, lines: list[str]) -> None:
        """Print the header lines and calculate full host list."""
        if self.show_header:
            self.print("".join(lines))

    def print_nothing(self, _lines: list[str]) -> None:
        """Do nothing."""
        return

    def print_task(self, lines: list[str]) -> None:
        """Print a list of lines for a section."""
        self.print_section(lines)

    def maybe_print_task(self, lines: list[str]) -> None:
        """Print a task if it's important."""
        if self.check_important(lines):
            self.print_task(lines)

    def print_trailer(self, lines: list[str]) -> None:
        """Print the final section."""
        if self.show_trailer:
            self.pretty_print("".join(lines))

    def process(self, input_file) -> None:
        """Read a stream of input lines, process them and print results."""
        self.last_section: str = "HEADER"
        self.current_lines: list[str] = []

        for line in input_file:
            for section_words in ["TASK", "HANDLER", "PLAY RECAP"]:
                if line.startswith(section_words) or f" {section_words} " in line:
                    self.printers[self.last_section](self.current_lines)
                    self.current_lines = []
                    self.last_section = section_words

            self.current_lines.append(line)

        self.print_trailer(self.current_lines)
