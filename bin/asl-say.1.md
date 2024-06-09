% asl-say(1) ASL3 @@HEAD-DEVELOP@@
% Jason McCormick
% June 2024

# NAME
asl-say - Cause Asterisk to speak

# SYNOPSIS
usage: `asl-say -n NODE -w ( time | time24 | ip4 | ip6 )`

# DESCRIPTION
`asl-say` will speak the one of the following things
on the node specified with `-n` as directed by `-w`

**time** - The current time
**time24** - The current time in 24-hour format
**ip4** - The first IPv4 address of the system
**ip6** - The first global-scope IPv6 of the system

# ExAMPLE
`asl-day -n 1999 -w time` will speak the current time
on node 1999.

# BUGS
Report bugs to https://github.com/AllStarLink/ASL3/issues

# COPYRIGHT
Copyright (C) 2024 Jason McCormick and AllStarLink
under the terms of the AGPL v3.
