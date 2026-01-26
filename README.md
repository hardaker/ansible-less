# Overview

This script merely takes the output of an ansible log file and deletes
the less interesting parts.  IE, if all the section parts of a TASK
are "ok:" then why show the section?  On the other hand if a section
contains "changed:" or "failed" or..., when we better show it.  

See the /Features and Examples/ section below for details.

# Installation

Pick one to install from pypi:

```
uv tool install ansible-less
pipx install ansible-less
pip install ansible-less
```

# Usage

```
unbuffer ansible-playbook ... >& my.log
ansible-less my.log
```

# Features and Examples

`ansilbe-less` reduces the clutter from the output of an ansible log,
which is especially helpful when reviewing long runs.  The following
subsections gives examples of its features:

## Drops TASK output with only 'ok' statuses

These are boring and you likely don't need to see when nothing changed.

[note: also drops other boring lines, like blank and date-only lines]

## Aggregating "ok" and "skipping" hosts to a simple count

Hosts reporting 'ok' status for a /Task/ are aggregated into a single line:

``` text
TASK [base : base packages] ***************************************
Wednesday 17 December 2025  15:52:02 +0000 (0:00:04.372)       0:11:12.388 ****
ok: [host1.localdomain]
skipping: [host2.localdomain]
ok: [host5.localdomain]
skipping: [host6.localdomain]
changed: [host4.localdomain]
changed: [host3.localdomain]
```

Is changed to:

``` text
==== TASK [base : base packages]

> ok: 2 hosts
> skipping: 2 hosts
> changed: host4.localdomain:
> changed: host3.localdomain:
```

## Aggregating similar outputs from diff or other output

When running ansible-playbook with `--diff` (as everyone should) it
shows you the diff for every host even when they're the same.
`ansible-less` consolidates these into a single shorter summer showing
you all hosts that are the same.  It modifies some lines to help
consolidation, like temporary file names and atimes/mtimes second
fractions.

Note: when diffs/outputs are different in any way, they aren't
aggregated.

For example, this (actual diff dropped for brevity):

``` text
TASK [helper_scripts : copy in needed operational utility scripts] *********
ok: [host1.localdomain] => (item=my-script)
ok: [host2.localdomain] => (item=my-script)
ok: [host5.localdomain] => (item=my-script)
ok: [host6.localdomain] => (item=my-script)
--- before: /usr/local/bin/my-script
after: /home/hardaker/.ansible/tmp/ansible-local-129894647x9ctc5/tmpm7mt6_gh/my-script
@@ -10,7 +10,18 @@
...
changed: [host4.localdomain] => (item=my-script)
--- before: /usr/local/bin/my-script
after: /home/hardaker/.ansible/tmp/ansible-local-129894647x9ctc5/tmpm7mt6_gh/my-script
@@ -10,7 +10,18 @@
...
changed: [host4.localdomain] => (item=my-script)
```

To the greatly simplified:

``` text
==== TASK [helper_scripts : create needed scripts]

> ok: 4 hosts
> changed: host4.localdomain:
> changed: host3.localdomain:
 => (item=my-script)
--- before: /usr/local/bin/my-script
+++ after: /home/hardaker/.ansible/tmp/.../my-script
@@ -10,7 +10,18 @@
...
```

## Stripping date/etc prefixes

If the log lines contain prefixes with the date/time/etc, these are
stripped from the lines for better readability.

For example, this:

``` text
2025-12-17 15:41:09,848 p=1298946 u=hardaker n=ansible | TASK [take server offline]
****************************************************************************************
2025-12-17 15:41:09,848 p=1298946 u=hardaker n=ansible | Wednesday 17 December 2025
15:41:09 +0000 (0:00:02.805)       0:00:19.795 ****
2025-12-17 15:41:10,817 p=1298946 u=hardaker n=ansible | changed: [host1.localdomain] =>
(item=server)
2025-12-17 15:41:10,821 p=1298946 u=hardaker n=ansible | changed: [host2.localdomain] =>
(item=server)
2025-12-17 15:41:12,006 p=1298946 u=hardaker n=ansible | changed: [host6.localdomain] =>
(item=server)
2025-12-17 15:41:12,091 p=1298946 u=hardaker n=ansible | changed: [host5.localdomain] =>
(item=server)
2025-12-17 15:41:13,373 p=1298946 u=hardaker n=ansible | changed: [host3.localdomain] =>
(item=server)
2025-12-17 15:41:14,186 p=1298946 u=hardaker n=ansible | changed: [host4.localdomain] =>
(item=server)
2025-12-17 15:41:14,208 p=1298946 u=hardaker n=ansible | TASK [wait 3 seconds]
```

becomes:

``` text
==== TASK [take server offline]

> changed: host1.localdomain:
> changed: host2.localdomain:
> changed: host6.localdomain:
> changed: host5.localdomain:
> changed: host3.localdomain:
> changed: host4.localdomain:
 => (item=server)
```

# Configuration

`ansible-less` has many command line options for tailoring the output,
but also sports a YAML based configuration file.  Run `ansible-less
--dump-config` to see the current settings, which can be saved to a
file and passed in with the `--config` flag.

``` text
$ ansible-less --dump-config
display:
  all_sections: false
  dont_strip_prefixes: false
  show_header: false
  show_trailer: false
  status_prefix: ':'
groupings:
  dont_group_oks: false
  dont_group_skipped: false
  dont_use_groupings: false
```

# Testimonials

> This amazing tool reduced a required post-ansible-playbook reading from 9987 lines to only 1475 lines.  How did I ever live without ansible-less?  -- The author
