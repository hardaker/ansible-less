"""Parses ansible log files and removes the boring 'it worked' bits."""

from __future__ import annotations
import re

__VERSION__ = "0.0.2"

try:
    from rich import print as pretty_print
except Exception:
    pretty_print = print


class AnsibleLess:
    """Parses ansible log files and removes the boring 'it worked' bits."""

    def __init__(
        self,
        show_headers: bool = False,
        strip_prefixes: bool = True,
        display_by_groups: bool = True,
        group_oks: bool = True,
        group_skipped: bool = True,
        display_all_sections: bool = False,
        status_prefix: str = ">",
    ):
        """Create an AnsibleLess instance."""
        self.printers = {
            "HEADER": self.print_nothing,
            "TASK": self.maybe_print_task,
            "HANDLER": self.maybe_print_task,
            "PLAY RECAP": self.print_task,
        }
        self.last_section: str = "HEADER"
        self.current_lines: list[str] = []

        if show_headers:
            self.printers["HEADER"] = self.print_section

        self.strip_prefixes = strip_prefixes
        self.display_by_groups = display_by_groups
        self.group_oks = group_oks
        self.group_skipped = group_skipped
        self.status_prefix = status_prefix
        self.display_all_sections = display_all_sections

    @property
    def strip_prefixes(self) -> bool:
        """Remove the date/time/etc prefixes of each line."""
        return self._strip_prefixes

    @strip_prefixes.setter
    def strip_prefixes(self, newval: bool) -> None:
        self._strip_prefixes = newval

    @property
    def group_by_hosts(self) -> bool:
        """Group hosts with similar output together."""
        return self._group_by_hosts

    @group_by_hosts.setter
    def group_by_hosts(self, newval: bool) -> None:
        self._group_by_hosts = newval

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

    def clean_blanks(self, lines: list[str]) -> list[str]:
        """Drop trailing blank lines from a list of lines."""
        while len(lines) > 0 and re.match(r"^\s*$", lines[-1]):
            lines.pop()
        return lines

    def filter_lines(self, lines: list[str]) -> list[str]:
        """Clean and filter lines to simplify the output.

        - Drop lines containing just date strings.
        - Drop line portions containing diffs of tmpfile names
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
        for line in lines:
            if results := re.match(
                r"(changed|ok|failed|fatal|skipping): \[([^]]+)\]:*(.*)", line
            ):
                # print("FOUND: " + results.group(1) + " -- " + results.group(2))
                if results.group(3) != "":
                    group_lines.insert(0, results.group(3) + "\n")
                groupings[str(results.group(2))] = {
                    "status": str(results.group(1)),
                    "lines": self.filter_lines(group_lines),
                }
                group_lines = []
            else:
                group_lines.append(line)
        # rich.print(groupings)
        return groupings

    def check_important(self, lines: list[str]) -> bool:
        """Decide which lines may indicate we need to display this section."""

        if self.display_all_sections:
            return True

        for line in lines:
            if "changed:" in line:
                return True
            if "FAILED" in line or "fatal" in line or "failed" in line:
                return True
            if "WARNING" in line:
                return True

        return False

    def print_section(
        self,
        lines: list[str],
    ) -> None:
        """Print a section of information after grouping it by hosts and cleaning."""
        # TODO(hardaker): make an CLI option for strip_prefixes
        # TODO(hardaker): make an CLI option for display_by_groups
        # TODO(hardaker): make an CLI option for group_oks

        # print("------------------------")
        if self.strip_prefixes:
            lines = [re.sub(r"^[^|]*\s*\| ", "", line) for line in lines]

        if self.display_by_groups:
            task_line = lines.pop(0)
            task_line = re.sub(r"\**$", "", task_line)
            print("==== " + task_line)

            buffer = []
            groupings = self.group_by_hosts(lines)
            sorted_keys = sorted(groupings, key=lambda x: groupings[x]["lines"])
            last_key = None

            if self.group_oks:
                # group 'ok' statuses into a single report line with a count
                ok_count = len(
                    [x for x in sorted_keys if groupings[x]["status"] == "ok"]
                )
                if ok_count > 0:
                    buffer.append(f"{self.status_prefix} ok: {ok_count} hosts\n")

            if self.group_skipped:
                # group 'ok' statuses into a single report line with a count
                ok_count = len(
                    [x for x in sorted_keys if groupings[x]["status"] == "skipping"]
                )
                if ok_count > 0:
                    buffer.append(f"{self.status_prefix} skipped: {ok_count} hosts\n")

            for key in sorted_keys:
                if self.group_oks and groupings[key]["status"] == "ok":
                    continue
                if self.group_skipped and groupings[key]["status"] == "skipping":
                    continue
                status_line = (
                    f"{self.status_prefix} {groupings[key]['status']}: {key}:\n"
                )
                if last_key and groupings[last_key]["lines"] == groupings[key]["lines"]:
                    buffer.insert(-1, status_line)
                    continue
                buffer.append(status_line)
                buffer.append("".join(groupings[key]["lines"]))
                last_key = key
            print("".join(buffer))
        else:
            print("".join(lines))

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
        pretty_print("".join(lines))

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
