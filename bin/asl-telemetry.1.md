% asl-telmetry(1) ASL3 @@HEAD-DEVELOP@@
% Jason McCormick
% June 2024

# NAME
Send anonymous/anonymized AllStarLink usage data
to the AlLStarLink project.

# SYNOPSIS
usage: `asl-telmetry [-h] [\-f CONFIG] [-u URL]`

optional arguments:
  -h, show help

  -f, use alternate config files; default /etc/asl-telemetry
    
  -u, use different URL (for development only)

# DESCRIPTION
The following data is anonymously collected from the `asl-telemetry`
process on AllStarLink v3+ servers. The `asl-telemetry` package
will only gather and send data about ASL servers that are configured
to register with allstarlink.org. Private nodes and such are ignored.

* A UUID Version 4 random unique ID
* Asterisk and app\_rpt version information
* List of nodes on the server
* Registration type of each node (HTTP or IAX2)
* Channel type of each node
* Asterisk uptime and reload time
* OS Platform information
* Architecture type
* List of installed packages related to ASL3 (allmon3, asl3\*, dahdi\*)

# BUGS
Report bugs to https://github.com/AllStarLink/ASL3/issues

# COPYRIGHT
Copyright (C) 2024 Jason McCormick and AllStarLink
under the terms of the AGPL v3.
