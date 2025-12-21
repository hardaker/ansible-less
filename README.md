# Overview

This script merely takes the output of an ansible log file and deletes
the less interesting parts.  IE, if all the section parts of a TASK
are "ok:" then why show the section?  On the other hand if a section
contains "changed:" or "failed" or..., when we better show it.

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
