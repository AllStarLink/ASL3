# AllStarLink Version 3 

## ASL3 Alpha Release Notes

AllStarLink’s app\_rpt version 3 (ASL3) is the next generation of repeater control software.  This version of app\_rpt has been redesigned to run on the latest operating systems and the current LTS version of Asterisk® 20.

The update from Asterisk version 1.4 to 20 implements over 15 years of bug fixes, security improvements and enhancements to the core asterisk application.  This update required app\_rpt to be heavily modified to run on the latest version of asterisk®.  It brings with it the latest Asterisk® applications, channel drivers and other functionality.

As part of this update, app\_rpt has been refactored to make the code base easier to maintain and enhance.  This process has been going on for over one year and will continue.  The app\_rpt code base will meet all current Asterisk® coding guidelines.

**New Features and improvements** 
- DNS IP address resolution
- HTTP AllStarLink registration
- EchoLink and other module memory leaks addressed
- EchoLink chat has been enabled
- EchoLink now honors the app\_rpt timeout timer.  A text message is sent to the client when they time out.
- EchoLink will no longer allow clients to double.  A text message is sent to the client when they are doubling.
- All modules reload or refresh 
- Compile directives for more archicetures

## Installation

### Operating System
ASL3 is targeting Debian 12 and testing should be done in a fresh(ish) installation of Debian 12. Currently supported platforms are x86\_64 and arm64/aarch64. For Raspberry Pi platforms, install the 64-bit version of Raspberry Pi OS 12 (Raspbian 12) on a Pi3 or Pi4 system. There are currently no builds for the 32-bit legacy version of RPi OS (armhf).

### asl3-asterisk installation
At the moment, since the release is not public, the ASL3 system must be downloaded from GitHub rather than `apt install`. The beta and production relases of ASL3 will be installed from a normal Apt repository. Download the latest tarball from https://github.com/AllStarLink/asl3-asterisk/releases/latest and save it to `/root`. Note that the tarballs are architecture-specific so retrieve the "amd64" version for x86\_64 and the arm64 for Pi/Arm/aarch64 platforms.

Expand the installation using `tar xvfz`. As an example:
```
tar xvfz asl3-asterisk-20.5.0+asl3-0.0.10.fadead4.deb12-1-amd64.tar.gz 
```

This will result in 5 packages starting with asl3-asterisk and 3 starting with dahdi. Install Dahdi first:
```
apt install dkms linux-headers-`uname -r`
dpkg -i dahdi-dkms_3.2.0+asl-8_all.deb dahdi-linux_3.2.0+asl-8_all.deb dahdi-source_3.2.0+asl-8_all.deb
modprobe dahdi
```

Now install the asl3-asterisk packages. The `dpkg` command will issue errors about missing dependencies. This is okay and fixed with the `apt install -f` command. For example:
```
dpkg -i asl3-asterisk*.deb
apt install -f
```

You should now have a complete ASL3 alpha install.
```
asterisk -rx "rpt localnodes"
```
You should see node 1999.

## ASL3 Configuration
The alpha does not include asl-menu. All configuration must be done with the editor of your choice.
Inspect the directions listed in `/etc/asterisk/rpt.conf` closely as the configuration files
have greatly changed and there are very few things that need to be edited for standard
installs. You can minimally create a functional networked node with the following using node
number 71234 as **an example** node number:
```
cd /etc/asterisk
perl -pi -e 's/1999/71234/g' *
mv simpleusb_tune_usb_1999.conf simpleusb_tune_usb_71234.conf
mv usbradio_tune_usb_1999.conf usbradio_tune_usb_71234.conf
```

Note that all files in `/etc/asterisk` must be owned and writable by the asterisk user. This
is an important, major change in ASL3. To fix them:
```
chown -R asterisk:asterisk /etc/asterisk
```

### HTTP Registration
AllStarLink registration is moving from IAX2 to HTTP registration.  IAX2 registration will remain in `chan_iax2` as part of Asterisk but may be removed from the AllStarLink servers at some far-off day. The module `res_rpt_http_registrations` handles HTTP registrations, `chan_iax2` still handles IAX2 registration. Please use and test either but do not configure both at the same time.

HTTP registration is configured by editing `/etc/asterisk/rpt_http_registrations.conf`.
```
[General]

[registrations]
;Change the register => line to match your assigned node number and password.
register => 1999:password@register.allstarlink.org    ; This must be changed to your node number, password
```

## Asterisk Templates Explained

The app_rpt configuration file now optionally makes use of asterisk templates.  This is a new concept for app_rpt users.  

You will see the following in rpt.conf:

```
;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;
;;;;; Template for all your nodes ;;;;;
;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;
; Set the defaults for your node(s) here. Add your nodes
; below the line that says Add you nodes here.
[node-main](!)
```

`[node-main](!)` is the template for all of your nodes associated with this install.  These are base settings that can be used for every node.  You can think of them as the defaults.

Further down in rpt.conf, you will find this section:

```
;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;
;;;;;;;;;;;;;;;;;;; Add your nodes here ;;;;;;;;;;;;;;;;;;;
;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;
; No need to duplicate entire settings. Only place settings different than template.

;;;;;;;;;;;;;;;;;;; Your node settings here ;;;;;;;;;;;;;;;;;;;

[1999](node-main)
rxchannel = Radio/usb_1999       ; USBRadio (DSP)
;startup_macro = *8132000
```

`[1999](node-main)` defines your node.  `[1999]` should be changed to your node number.  `(node-main)` tells asterisk to use the template stanza `[node-main](!)` as the default settings.

Entries that are added below `[1999](node-main)` override or add to the default settings.  You will notice that `rxchannel = Radio/usb_1999` was added here to override the default found in the template.  The same goes for startup_macro. If uncommented, it overrides the default in the template.

### Rpt.conf Edits
The rpt.conf file is documented with comments to help you make changes.  Please review the comments in the file as you make edits to setup your node.

After you have completed these changes, enter the command:

```
systemctl restart asterisk
```

The node should now come alive and register with the AllStarLink servers.

If you are using usbradio or simpleusb, you will have to edit usbradio.conf or simpleusb.conf and change the `[usb_??????]` section to match your node number.

Since asl-menu is not available in the Alpha release, you will have to use one of the following commands to tune the radio adapter.

`/usr/lib/asterisk/radio-tune-menu`
Or
`/usr/lib/asterisk/simpleusb-tune-menu`

## New or updated app_rpt commands

### HTTP Registrations
`rpt show registrations`  is used to view your registration to the AllStarLink servers.

### DNS Lookup
Asterisk CLI comand `rpt lookup 2000` for example will show the IP address of node 2000.
Linux CLI is `nslookup 2000.nodes.allstarlink.org`, for example. 

The software now implements DNS lookup of node information.  By default the software will now query the AllStarLink DNS servers first to resolve node information.  It will fall back to the external rpt_extnodes file if the node cannot be resolved by DNS.

The operation of this ASL3 feature can be controlled by changing the following information in rpt.conf.

```
[general]
node_lookup_method = both	;method used to lookup nodes
					;both = dns lookup first, followed by external file (default)
					;dns = dns lookup only
					;file = external file lookup only
```
The node lookup routines will output debug information showing the node lookups if the debug level is set to 4 or higher.

### rpt showvars
The `rpt showvars <nodenum>` has changed to `rpt show variables <nodenum>`.

### Echolink Show Nodes
`echolink show nodes`  is used to view the currently connected echolink users.

### Echolink Show Stats
`echolink show stats`  is used to view the channel statistics for echolink.  
It shows the number of in-bound and out-bound connections.  It also shows the cumulative system statistics, along with the statistics for each connected nodes.

## Debugging

Previously app\_rpt and associated channels supported setting the debug level with an associated app / channel command.  These app / channel commands have been removed and replaced with the asterisk command: 

**core set debug x module**

Where x is the debug level and module is the name of the app or module.

Example:  
**core set debug 5 app_rpt.so**  
**core set debug 3 chan_echolink.so**

## EEPROM Operation
chan\_simpleusb and chan\_usbradio allows users to store configuration information in the EEPROM attached to their CM-xxx device(s).  The CM119A can have manufacturer information in the same area that stores the user configuration.  The CM119B does have manufacturer data in the area that stores user configuration.  The manufacturer data cannot be overwriten.  The user configuration data has been moved higher in memory to prevent overwriting the manufacturer data.  If you use the EEPROM to store configuration data, you will need to save it to the EEPROM after upgrading.  Use `susb tune save` or `radio tune save`.

This document was created by Danny Lloyd/KB4MDD and modified to death by WD6AWP and further hacked up by N8EI.
