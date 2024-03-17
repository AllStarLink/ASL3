# AllStarLink Version 3 from Source

Source install is for developers. 
- ASL3 has many changes. See the main README.md first.
- See the README.md for configuration details, new commands, and other changes.
- Source install does not include any helpers, Allmon3, asl3-menu, etc.
- Installs and runs Asterisk as root

### Install phreaknet script

The phreaknet script compiles and patches Asterisk and DAHDI.
```
cd /usr/src && wget https://docs.phreaknet.org/script/phreaknet.sh && chmod +x phreaknet.sh && ./phreaknet.sh make
```

### Install Asterisk 20 LTS

Use -t or -b for developer mode. 
- The -t is for backtraces and thread debug. Thread debugging is resource intensive.
- Use -b for backtraces only, recommended on 386.
- The -s is for sip if you need it still, leave off the -s if you don’t
- The -d is for DAHDI and is required
- The -v is to install the latest of the major version specified, 20 in this case
```
phreaknet install -d -b -v 20
```
Asterisk should be running at this point but not app_rpt. Check install with `asterisk -r`.

### Clone ASL3 repo

```
cd /usr/src
git clone https://github.com/AllStarLink/app_rpt.git
```

### Install ASL3
This script does a git pull of app_rpt and compiles the branch you are on.
```
cd app_rpt
./rpt_install.sh
```

### Install ASL3 configs
This adds ASL3 configs to the full set of Asterisk configuration files. ASL3 modules.conf limits what actually runs. 
```
cp /usr/src/app_rpt/configs/rpt/* /etc/asterisk
```

> reboot the system

You should now have a complete ASL3 install.

```
asterisk -rx "rpt localnodes"
```
You should see node 1999. 

Configure per README.md