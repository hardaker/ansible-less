# Overview

This script merely takes the output of an ansible log file and deletes
the less interesting parts.  IE, if all the section parts of a TASK
are "ok:" then why show the section?  On the other hand if a section
contains "changed:" or "failed" or..., when we better show it.

# Installation

```
uv build .
uv tool install .
```

# Usage

```
unbuffer ansible-playbook ... >& my.log
ansible-less my.log
```
