# AllStarLink Version 3 

## ASL3 Alpha Release Notes

AllStarLink’s app_rpt version 3 (ASL3) is the next generation of repeater control software.  This version of app_rpt has been redesigned to run on the latest operating systems and the current version of asterisk® 20.1.0.

The update from asterisk version 1.4 to 20.1.0 implements over 15 years of bug fixes, security improvements and enhancements to the core asterisk application.  This update required app_rpt to be heavily modified to run on the latest version of asterisk®.  It brings with it the latest asterisk® applications, channels and extensions.

As part of this update, app_rpt has been refactored to make the code base easier to maintain and enhance.  This process has been going on for over one year and will continue.  The app_rpt code base will meet all current asterisk® coding guidelines.

**New Features and improvements** 
- DNS IP address resolution
- HTTP AllStarLink registration
- EchoLink and other module memory leaks addressed
- All modules reload or refresh 
- Compile directives for more archicetures

## Install
In order to test this version, you must be accepted as an alpha tester.  During the alpha testing phase the repository is private.  Contact Naveen on Slack for access to the private repo. You need a username on Github and a personal access token.  See creating an access token on github. 

Alpha testers are encouraged to use the latest version of Debian for testing.  At this time, the asterisk application and app_rpt must be compiled from source code.  There are no prebuilt images.

Configuration files from previous versions of ASL app_rpt are not compatible with the ASL3.  Some of the “conf” files may appear the same, while others will look completely different.

Much of these instructions are from Naveen's repo with added detail for newbees.

### Install phreaknet script
```
cd /usr/src && wget https://docs.phreaknet.org/script/phreaknet.sh && chmod +x phreaknet.sh && ./phreaknet.sh make
```
### Install Asterisk
Use the phreaknet script to install Asterisk. Use -t or -b for developer mode. 
- The -t is for backtraces and thread debug. Use -b for backtraces only, recommended on 386.
- The -s is for sip if you need it still, leave off the -s if you don’t
- The -d is for DAHDI and is required
```
phreaknet install -t -s -d
```
Asterisk should be running at this point but not app_rpt. Now would be a good idea to check with `asterisk -r`. If so, congrats. Time to move on to the fun stuff.

### Clone ASL3 repo
As you follow the installation procedures, you will be prompted for a username and password.  Your username will be your github username.  Use your access token for the password.  

```
sudo apt-get update
sudo apt-get -y install git
cd /usr/src
git clone https://github.com/InterLinked1/app_rpt.git

```

This will save your git credentials next time you use them. 

```
git config —-global credential.helper store
```

### Install ASL3
```
cd app_rpt
./rpt_install.sh
```

### Install ASL3 configs
This adds ASL3 configs to a full set of Asterisk configuration files. However, modules.conf limits what actually runs to a miminal ASL configuration. 
```
cp /usr/src/app_rpt/configs/rpt/* /etc/asterisk
```

> reboot the system

You should now have a complete ASL3 alpha install.

```
asterisk -rx "rpt localnodes"
```
You should see node 1999. If so, you are now ready to configure your node.  

## ASL Configuration
The alpha does not include Allmon, Supermon or the asl-menu. All configuration must be done with the editor of your choice.

### HTTP Registration
AllStarLink registration is moving from IAX to HTTP registration.  IAX registration will remain in chan_iax as part of Asterisk but may be removed from the AllStarLink servers at some far-off day. The module res_rpt_http_registrations handles http registrations, chan_iax still handels IAX registration. Please use and test either but do not configure both at the same time.

HTTP registration is configured by editing /etc/asterisk/rpt_http_registrations.conf.

```
[General]

[registrations]
;Change the register => line to match your assigned node number and password.
register => 1999:password@register.allstarlink.org    ; This must be changed to your node number, password
```


### Node Updater
Because ASL3 alpha includes DNS IP address resolution the node updater is not needed. However, for testing, installing the node updater is recommended.

```
apt install curl gpg
cd /tmp
wget http://apt.allstarlink.org/repos/asl_builds/install-allstarlink-repository
chmod +x install-allstarlink-repository
./install-allstarlink-repository
apt -y install asl-update-node-list

```

### Rpt.conf Template Explained

The app_rpt configuration file now makes use of asterisk templates.  This is a new concept for app_rpt users.  

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

The ASterisk CLI comand `rpt lookup 2000` for example will show the IP address of node 2000. IP address on the Linux CLI is `nslookup 2000.nodes.allstarlink.org`, for example. 

This document was created by Danny Lloyd/KB4MDD


