# AllStarLink Version 3 

## ASL3 Alpha Release Notes

AllStarLink’s app_rpt version 3 (ASL3) is the next generation of repeater control software.  This version of app_rpt has been redesigned to run on the latest operating systems and the current version of Asterisk® 20.x.x.

The update from Asterisk version 1.4 to 20 implements over 15 years of bug fixes, security improvements and enhancements to the core asterisk application.  This update required app_rpt to be heavily modified to run on the latest version of asterisk®.  It brings with it the latest Asterisk® applications, channel drivers and other functionality.

As part of this update, app_rpt has been refactored to make the code base easier to maintain and enhance.  This process has been going on for over one year and will continue.  The app_rpt code base will meet all current Asterisk® coding guidelines.

**New Features and improvements** 
- DNS IP address resolution
- HTTP AllStarLink registration
- EchoLink and other module memory leaks addressed
- EchoLink chat has been enabled
- EchoLink now honors the app_rpt timeout timer.  A text message is sent to the client when they time out.
- EchoLink will no longer allow clients to double.  A text message is sent to the client when they are doubling.
- All modules reload or refresh 
- Compile directives for more archicetures

## Install
In order to test this version, you must be accepted as an alpha tester.  During the alpha testing phase the repository is private.  Contact Naveen on Slack for access to the private repo. You need a username on Github and a personal access token.  See creating an access token on github. 

Configuration files from previous versions of ASL app_rpt are not compatible with the ASL3.  Some of the “conf” files may appear the same, while others will look completely different.

Much of these instructions are from [Naveen's repo](https://github.com/InterLinked1/app_rpt) with added detail for newbies.

### Download OS
Alpha testers are encouraged to use the latest version of Debian for testing. Download the netinstall iso. Don't install a desktop or any servers other than ssh.

### For Raspberry Pi
OS install instructions are at [Pi-instll.md](https://github.com/AllStarLink/ASL3/blob/develop/RPi-install.md) then come back by following the link at the end of the Pi-install.

### Install PhreakScript
```
cd /usr/src && wget https://docs.phreaknet.org/script/phreaknet.sh && chmod +x phreaknet.sh && ./phreaknet.sh make
```
### Install Asterisk
Use PhreakScript to install Asterisk. Use either `-t` or `-b` for developer mode. 
- The `-t` is for backtraces and thread debug. Please note that -t will cause performance issues with app_rpt and is not recommended unless actively doing heavy thread debugging, and performance issues should not be opened against versions compiled with this option. Alternatively use `-b` for backtraces only, recommended on 386.
- The `-s` is for sip. PJSIP is recommended as SIP was deprecated 5 years ago and will not appear in any future Asterisk release. PJSIP setup instructions are in this repo.   
- The `-d` is for DAHDI and is required
- The `-v` is for the Asterisk version. This additional instruction is to prevent the install of Asterisk 21.x which is [not LTS](https://docs.asterisk.org/About-the-Project/Asterisk-Versions/) and thus not AllStarLink supported. Use `phreaknet install --version=20`, for example, to always get the latest 20 version (asterisk-20-current), and then the sub-version (ie 20.5.0) doesn't need to be provided. 
```
phreaknet install -b -d -v 20
```
You'll need to reboot at this point.

Asterisk should be running at this point but not app_rpt. Now would be a good idea to check with `asterisk -r`. If so, congrats. Time to move on to the fun stuff.

### Clone ASL3 Source
As you follow the installation procedures, you will be prompted for a username and password.  Your username will be your github username.  Use your access token for the password.  

```
cd /usr/src
git clone https://github.com/InterLinked1/app_rpt.git

```

This will save your git credentials in your home directory next time you use them. Be sure global is preceded with two dashes rather than one long dash. 

```
git config --global user.name
git config --global user.email
git config --global credential.helper store
```

### Install ASL3
```
cd app_rpt
./rpt_install.sh
```

### Install ASL3 configs
This adds ASL3 configs to a full set of Asterisk configuration files. However, `modules.conf` limits what actually runs to a miminal ASL configuration. 
```
cp /usr/src/app_rpt/configs/rpt/* /etc/asterisk
```

> reboot the system

You should now have a complete ASL3 alpha install.

```
asterisk -rx "rpt localnodes"
```
You should see node 1999. If so,  

### Install Node Updater
Because ASL3 alpha includes DNS IP address resolution the node updater is not needed. However, for testing installing the node updater is recommended.

```
apt install curl gpg
cd /tmp
wget http://apt.allstarlink.org/repos/asl_builds/install-allstarlink-repository
chmod +x install-allstarlink-repository
./install-allstarlink-repository
apt -y install asl-update-node-list

```

### Install Systemd
See the post install [README.md](https://github.com/AllStarLink/ASL3/tree/develop/post_install#systemd-files).

You are now ready to configure your node.

# ASL Configuration
The alpha does not include Allmon, Supermon or the asl-menu. All configuration must be done with the editor of your choice.

### HTTP Registration
AllStarLink registration is moving from IAX2 to HTTP registration.  IAX2 registration will remain in `chan_iax2` as part of Asterisk but may be removed from the AllStarLink servers at some far-off day. The module `res_rpt_http_registrations` handles HTTP registrations, `chan_iax2` still handles IAX2 registration. Please use and test either but do not configure both at the same time.

HTTP registration is configured by editing `/etc/asterisk/rpt_http_registrations.conf`.

```
[General]

[registrations]
;Change the register => line to match your assigned node number and password.
register => 1999:password@register.allstarlink.org    ; This must be changed to your node number, password
```

### Asterisk Templates Explained

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

## Rpt.conf Edits
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

# New or updated app_rpt commands

## HTTP Registrations
`rpt show registrations`  is used to view your registration to the AllStarLink servers.

## DNS Lookup
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

## rpt showvars
The `rpt showvars <nodenum>` has changed to `rpt show variables <nodenum>`.

## Echolink Show Nodes
`echolink show nodes`  is used to view the currently connected echolink users.

## Echolink Show Stats
`echolink show stats`  is used to view the channel statistics for echolink.  
It shows the number of in-bound and out-bound connections.  It also shows the cumulative system statistics, along with the statistics for each connected nodes.

## Debugging

Previously app_rpt and associated channels supported setting the debug level with an associated app / channel command.  These app / channel commands have been removed and replaced with the asterisk command: 

**core set debug x module**

Where x is the debug level and module is the name of the app or module.

Example:  
**core set debug 5 app_rpt.so**  
**core set debug 3 chan_echolink.so**

# Operational Changes

## EEPROM Operation
chan_simpleusb and chan_usbradio allows users to store configuration information in the EEPROM attached to their CM-xxx device(s).  The CM119A can have manufacturer information in the same area that stores the user configuration.  The CM119B does have manufacturer data in the area that stores user configuration.  The manufacturer data cannot be overwriten.  The user configuration data has been moved higher in memory to prevent overwriting the manufacturer data.  If you use the EEPROM to store configuration data, you will need to save it to the EEPROM after upgrading.  Use `susb tune save` or `radio tune save`.


This document was created by Danny Lloyd/KB4MDD and modified to death by WD6AWP
