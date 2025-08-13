% sa818-menu(1) ASL3 2024,2025

## NAME
`sa818-menu` - Configure SA818 device from menu

## SYNOPSIS
Usage: 

```
/usr/bin/sa818-menu [-h] [--apply] [--debug]
```

Optional arguments:

`-h`: show usage help

`--apply`: (Re-)apply the saved configuration from `/etc/sa818.conf` to the SA818 (without the menu)

`--debug`: change logging to debug level

## DESCRIPTION
sa818-menu - Configure an SA818 device using an interactive menu

With no options, executing `sudo sa818-menu` will open a menu driven utility for configuring an SA818 module.

The configuration will be saved in `/etc/sa818.conf`, and can be re-applied from the command line using `sudo sa818-menu --apply`.

The `sa818-menu` utility is a menu driven front end for the `sa818` programming utility. As such, see the [`sa818`](./sa818.md) man page for valid option ranges and defaults.

## SEE ALSO

sa818(1)

## BUGS
Report bugs to https://github.com/AllStarLink/ASL3/issues

## COPYRIGHT
Copyright (C) 2025 Allan Nathanson and AllStarLink under the terms of the AGPL v3.
