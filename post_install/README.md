# systemd files
The normal install of Asterisk installs an init script to start, stop and restart Asterisk. For Allstar we find these scripts work much better. 
Included are the files we've been using for years.

## Install
As root or sudo
- First move or remove /etc/init.d/asterisk
- Copy the .service file to /lib/systems/system
- Copy the .sh files to /usr/sbin
- Do a systemctl reload
- Reboot

Node should come running and forever happy.
