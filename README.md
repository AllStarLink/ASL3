# AllStarLink Version 3 

## README documentation in progress. Do not use yet.

## Alpha Release Notes

AllStarLink’s app_rpt version 3 (ASL3) is the next generation of repeater control software.  This version of app_rpt has been redesigned to run on the latest operating systems and the current version of asterisk® 20.1.0.

The update from asterisk version 1.4 to 20.1.0 implements over 15 years of bug and security fixes and enhancements to the core asterisk application.  This update required app_rpt to be heavily modified to run on the latest version of asterisk®.  It brings with it the latest asterisk® applications, channels and extensions.

As part of this update, app_rpt has been refactored to make the code base easier to maintain and enhance.  This process has been going on for over one year and will continue.  The app_rpt code base will meet all current asterisk® coding guidelines.

*New Features and improvements* 
- DNS IP address resoultion
- HTTP AllStarLink registration
- EchoLink and other module memory leaks addressed
- Modules reload

## Install
In order to test this version, you must be accepted as an alpha tester.  During the alpha testing phase the repository is private.  This will require you to have a username on Github.  You will also need a personal access token.  See creating an access token on github. 

After you receive your access token, you should configure git to store your personal access token.  Run the following commands:
```
sudo apt-get update
sudo apt-get -y install git
git config —-global credential.helper store
```
As you follow the installation procedures, you will be prompted for a username and password.  Your username will be your github username.  Use your access token for the password.  git will store the access token in the credential manager.

Alpha testers are encouraged to use the latest version of Debian for testing.  At this time, the asterisk application and app_rpt must be compiled from source code.  There are no prebuilt images.

Configuration files from previous versions of ASL app_rpt are not compatible with the ASL3.  Some of the “conf” files may appear the same, while others will look completely different.

You should start with a fresh installation of Debian.  

After acceptance, follow these instructions to install and compile the source code.  

### Step 1:

Install the phreaknet script.
```
cd /usr/src && wget https://docs.phreaknet.org/script/phreaknet.sh && chmod +x phreaknet.sh && ./phreaknet.sh make
```
Next install Asterisk in developer mode
- The -t is for backtraces and thread debug. Use -b for backtraces only
- The -s is for sip if you need it still, leave off the -s if you don’t
- The -d is for DAHDI and is required
```
phreaknet install -t -s -d
```
Asterisk should be running at this point but not app_rpt. Now would be a good idea to check with `asterisk -r`. If so, congrats. Time to move on to the fun stuff.

### Step 2
Install app_rpt
```
cd /usr/src
git clone https://github.com/InterLinked1/app_rpt.git
cd app_rpt
./rpt_install.sh
cp /usr/src/app_rpt/configs/rpt/* /etc/asterisk #install our rpt configs
```

### Step 3
Instructions for installing the node updater
```
apt install curl gpg
cd /tmp
wget http://apt.allstarlink.org/repos/asl_builds/install-allstarlink-repository
chmod +x install-allstarlink-repository
./install-allstarlink-repository
apt -y install asl-update-node-list
```
reboot the system

You should now have the software compiled and installed.  Test the install.

```
asterisk -rx "rpt localnodes"
```
You should see nide 1999. If so, you are now ready to configure your node.  

The alpha does not include Allmon, Supermon or the asl-menu. All configuration must be done with the editor of your choice.

#### HTTP Registration
AllStarLink registration in moving from IAX to HTTP. IAX registration will remain in chan_iax but will be removed from the AllStarLink servers at some far off day. The ASL 2.0 beta supports both automatically.  beta The module res_rpt_http_registrations now handles the registrations.  It is configured by editing /etc/asterisk/rpt_http_registrations.conf.

```
[general]

[registrations]
register=1999:password@register.allstarlink.org    ; This must be changed to your node number, password

Change the register= line to match your assigned node number and password.

The app_rpt configuration file now makes use of asterisk templates.  This is a new concept for app_rpt users.  

You will see the following in rpt.conf:

;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;
;;;;; Template for all your nodes ;;;;;
;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;
; Set the defaults for your node(s) here. Add your nodes
; below the line that says Add you nodes here.
[node-main](!)

[node-main](!) is the template for all of your nodes associated with this install.  These are base settings that can be used for every node.  You can think of them as the defaults.

Further down in rpt.conf, you will find this section:

;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;
;;;;;;;;;;;;;;;;;;; Add your nodes here ;;;;;;;;;;;;;;;;;;;
;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;
; No need to duplicate entire settings. Only place settings different than template.

;;;;;;;;;;;;;;;;;;; Your node settings here ;;;;;;;;;;;;;;;;;;;
[1999](node-main)
rxchannel = Radio/usb_1999       ; USBRadio (DSP)
startup_macro = *8132000

[1999] (node-main) defines your node.  [1999] should be changed to your node number.  (node-main) tells asterisk to use the template named “node-main” as the default settings.

Entries that are added below [1999] (node-main) override the default settings.  You will notice that rxchannel = Radio/usb_1999 was added here to override the default found in the template.  The same goes for startup_macro, it overrides the default in the template.

The rpt.conf file is documented with comments to help you make changes.  Please review the comments in the file as you setup your node.  You are now ready to config app_rpt.  Edit /etc/asterisk/rpt.conf and enter the changes for your node.

After you have completed these changes, enter the command:

systemctl restart asterisk

The node should now come alive and register with the AllStarLink servers.

If you are using usbradio or simpleusb, you will have to edit usbradio.conf or simpleusb.conf and change the [usb_??????] section to match your node number.

Since asl-menu is not available in the Alpha release, you will have to use one of the following commands to tune the radio adapter.

/usr/lib/asterisk/radio-tune-menu
Or
/usr/lib/asterisk/simpleusb-tune-menu

New or updated rpt commands

rpt show registrations  should be used to view your registration to the AllStarLink servers.

Enhancements

DNS Lookup
The software now implements DNS lookup of node information.  By default the software will now query the AllStarLink DNS servers first to resolve node information.  It will fall back to the external rpt_extnodes file if the node cannot be resolved by DNS.

The operation of this feature can be controlled by changing the following information in rpt.conf.

[general]
node_lookup_method = both	;method used to lookup nodes
					;both = dns lookup first, followed by external file (default)
					;dns = dns lookup only
					;file = external file lookup only

The node lookup routines will output debug information showing the node lookups if the debug level is set to 4 or higher.



This document was created by Danny Lloyd/KB4MDD


