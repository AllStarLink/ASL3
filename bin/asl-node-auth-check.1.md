% asl-node-auth-check(1) ASL3 @@HEAD-DEVELOP@@
% Jason McCormick
% January 2026

# NAME
asl-node-auth-check - Check for Asterisk/app\_rpt registration issues

# SYNOPSIS
usage: `asl-node-auth-check [--json] [--node N]`

# DESCRIPTION
asl-node-auth-check - Check for Asterisk/app\_rpt registration issues

The check reads the node and registration configuration, asks several
AllStarLink servers which public IP address they see, and then checks the
registration, statistics and inbound reachability of each node. It must
run as root or as the asterisk user.

# OPTIONS
**-h**, **-\-help**
: Show a short help message and exit.

**-\-json**
: Print the results as one JSON document on standard output and nothing
  else. See **JSON OUTPUT**.

**-\-node** *N*
: Check only node *N*. The configuration checks still cover every node.
  If *N* has no registration, the run is aborted.

# EXIT STATUS
**0**
: No errors were found. Warnings alone exit 0.

**1**
: One or more errors were found.

**2**
: The run was aborted because it could not continue, for example when no
  nodes or registrations are configured, or registrations and node
  configuration do not match.

**3**
: Not running as root or asterisk.

# JSON OUTPUT
The document has schema version 1. Its top-level fields are:

**schema**
: The schema version, 1. Fields may be added within a version; their
  meaning does not change.

**tool\_version**
: The ASL3 version of this tool.

**started**, **finished**
: ISO 8601 UTC timestamps.

**result**
: The worst level found (**ok**, **warning** or **error**; **info**
  findings alone give **ok**), or **aborted** if the run could not
  continue.

**counts**
: The number of findings at each level: **error**, **warning**, **ok** and
  **info**.

**sections**
: A list of sections in run order. Each has an **id** (**run**,
  **config**, **public\_ip** or **node**), a **node** (the node number for
  **node** sections, otherwise null), **complete** (false when the section
  stopped early) and a list of **findings**.

Each finding has:

**id**
: A stable identifier such as **node.registration\_state**. An id never
  changes meaning; new checks get new ids.

**level**
: One of **ok**, **info**, **warning** or **error**, as in the text
  output.

**message**
: The same text the text output prints.

**data**
: The values behind the message, such as addresses, ports, timestamps
  (ISO 8601 UTC) and round-trip times. An empty object when there are none.

An aborted run still prints a complete document, with the finding that
stopped it, and leaves out the sections that did not run.

# BUGS
Report bugs to https://github.com/AllStarLink/ASL3/issues

# COPYRIGHT
Copyright (C) 2026 Jason McCormick and AllStarLink
under the terms of the AGPL v3.
