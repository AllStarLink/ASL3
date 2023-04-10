# Asterisk systemd files
The normal install of Asterisk installs an init script to start, stop and restart Asterisk. For AllStar we find are own scripts work much better. 
Included are the files we've been using for years.

## Install
- cd
- mv /etc/init.d/asterisk .
- git clone 
- cp -v asl-asterisk.service file /lib/systems/system
- cp -v *.sh /usr/sbin
- Do a `systemctl reload`
- Reboot

Node should come running and forever happy.
