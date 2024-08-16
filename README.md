> [!CAUTION]
> For installation of AllStarLink v3, see the [ASL3 Manual](https://allstarlink.github.io) and follow
> the directions found there. Installation of `.deb` files or source from this repository will not
> result in a working system. AllStarLink is an ecosystem of software, not a single package.

# AllStarLink Version 3

AllStarLink’s app\_rpt version 3 (ASL3) is the next generation of repeater and hotspot software.  This version of app\_rpt has been redesigned to run on the latest operating systems and the current LTS version of Asterisk® 20. ASL3 runs on Raspberry Pi 3, 4, 5, and Zero 2 W as well as amd64 and x86.

The update from Asterisk version 1.4 to 20 implements over 15 years of bug fixes, security improvements and enhancements to the core asterisk application.  This update required app\_rpt to be heavily modified to run on the latest version of Asterisk®.  It brings with it the latest Asterisk® applications, channel drivers and other functionality.

As part of this update, app\_rpt has been refactored to make the code base easier to maintain and enhance.  This process has been going on for over a year and will continue.  The app\_rpt code base will meet all current Asterisk® coding guidelines.


**New Features and improvements**
- New HTTP AllStarLink registration
- DNS IP address resolution with fallback to file
- Memory leaks addressed
- All modules reload or refresh
- Improved uptime
- USB tune settings improvements
- Rpt.conf template
- Improved ASL menu
- EchoLink improvements
   - Chat has been enabled
   - Honors the app\_rpt timeout timer.  A text message is sent to the client when they time out.
   - No longer allows clients to double.  A text message is sent to the client when they are doubling.
- Blacklist and whitelist improvements
- Compile directives for more archicetures
- Asterisk runs as non-root **(need to clean up this)**
   - RTCM configs: See README-port667.md
   - USB configs: `cat /etc/udev/rules.d.90-asl3.rules` 
SUBSYSTEM=="usb", ATTRS{idVendor}=="0d8c", GROUP="plugdev", TAG+="uaccess"

## Updating from ASL2
There is no update or migration from ASL2. You’re going to be installing a new Debian OS on your computer, VM or microSD card.

The ASL3 conf files are different. Do not try to use the ASL2 configs. They won't work.

The new ASL3 menu will walk you through setting up a basic USB or hub node quickly. Switching between menu and config edits is non-destructive.  When editing configs or using the Asterisk CLI consider:
- Registration is now set in `rpt_http_registration.conf` not in `iax.conf`. IAX registration still works but is discouraged. Don't register both http and IAX. The new CLI command is`rpt show registrations`.
- A template is now used in `rpt.conf`. Editing is much easier but it's different than ASL2. Node settings are much simpler requiring only a few added lines per node. The ASL3 menu handles the templated config.
- The USB configuration files now contain the tune settings. There is no tune file for each node as in ASL2. The tune menus and Asterisk CLI write to the new tune setting locations.
- There is a new blacklist and whitelist.
- Most of this new stuff is explained with more detail in the ASL3 Configuration section below.

