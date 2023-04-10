# Asterisk systemd files
The normal install of Asterisk installs an init script to start, stop and restart Asterisk. For AllStar we find are own scripts work much better. 
Included are the files we've been using for years.

## Install
```
 cd
 mv /etc/init.d/asterisk .
 git clone https://github.com/AllStarLink/ASL3.git
 cd ASL3/post_install
 cp -v asl-asterisk.service file /lib/systems/system
 cp -v *.sh /usr/sbin
 systemctl daemon-reload
 systemctl enable asl-asterisk 
 reboot
```
Node should come running and forever happy.
