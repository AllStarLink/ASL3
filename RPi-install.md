# Raspberry Pi Installation

These directions cover, in detail, how to build ASL3 on a Raspberry Pi. It is **strongly**
recommended to do this only on Pi 3s and 4s as currently all software is compiled
from source. This will take a very long time on older or smaller Pi.

# Installation of Raspberry Pi OS (Raspian)

## Imaging

Follow the general steps for imaging the OS from [Raspberry Pi OS](https://www.youtube.com/watch?v=ntaXWS8Lk34]).
However make the following selections with the imager:

If you are using a Pi 4 platform you must use the 64-bit distribution to get a reasonable set of kernel headers to build the software. Raspian 11 is currently in a weird limbo land where the kernel will be 64-bit and userspace is 32-bit. That works fine in most cases but not for building and installing software that ties into the Linux kernel.

* For **Choose OS** select **Raspberry Pi OS (other) ** --> **Raspberry Pi OS Lite (32-bit)**. It should look like [this](https://github.com/AllStarLink/ASL3/blob/develop/RPiDebianDownload.png).

Note that the lite image does not have any desktop - the expectation is you're accessing
the system over SSH. You can use the desktop version if necessary for convenience.

Before clicking on the write button, click on the **Gear** icon in the lower
right and set the following options:

* **Enable SSH** and select **Use password authentication** unless you know
what you're doing for SSH keys
* **Set username and password** and set a user "asl" and a password for
the user "asl". Note the username and password as this will be used for
the setup.
* If you intend to connect it wirelessly, choose **Configure wireless LAN**
and set the relevant options for wireless.
* **Set locale settings** if you want to change the timezone or keyboard

Then go ahead and click the write button. After the imaging is complete,
insert the SD Card and start up the Pi.

## Updating the Image

* Login to the Pi using the "asl" user set above

* Change to root using sudo - `sudo -s`

* Upgrade Raspberry Pi OS 11 to all of the latest packages:
```
apt update && apt upgrade -y && apt dist-upgrade -y
```

## Raspberry Pi 4 Boards Need 32-bit Kernels
Currently, Raspberry Pi 4 boards are getting upgraded into 64-bit kernels with
a 32-bit userland toolchain. This works fine except when you need to build a
kernel module (ala DAHDI). Check the output of your system:
```
# uname -m
aarch64
```

If the `uname` command reports the platform is `aarch64` then
add `arm_64bit=0` to `/boot/config.txt`:
```
echo "arm_64bit=0" >> /boot/config.txt
reboot
```

After the system reboots, `uname` should report the system is armv7l:
```
$ uname -m
armv7l
```

# Asterisk Installation

This installation process uses the scripted installer from the [PhreakNet Community](https://phreaknet.org/). See [this Wikipedia article on Phreaking](https://en.wikipedia.org/wiki/Phreaking) to understand where that 
term came from. The final version of ASL3 may or may not use this installation method.

* Install the phreaknet installation script:
```
apt install -y git && \
cd /usr/src && \
wget https://docs.phreaknet.org/script/phreaknet.sh && \
chmod +x phreaknet.sh && \
./phreaknet.sh make
```

* Build and install Asterisk 20 and the DAHDI kernel module:
```
phreaknet dahdi
phreaknet install -b -s -v 20
```
Note: This will take a long time. 

* After the build is competed, test the running asterisk:
```
# asterisk -rx 'core show uptime'
System uptime: 1 minute, 27 seconds
Last reload: 1 minute, 27 seconds
```

* Stop the Asterisk service and delete the file `/etc/init.d/asterisk`
```
systemctl stop asterisk
rm /etc/init.d/asterisk
```

* Edit the file `/etc/systemd/system/asterisk.service`, copy in the following contents, and save the file:
```
[Unit]
Description=AllStar Asterisk
Documentation=man:asterisk(8)
Wants=network.target
After=network-online.target

[Service]
Type=simple
ExecStartPre=mkdir -p /run/asterisk
ExecStart=/usr/sbin/asterisk -g -f
ExecStop=/usr/sbin/asterisk -rx 'core stop now'
ExecReload=/usr/sbin/asterisk -rx 'core restart now'
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

* Enable the service and start asterisk
```
systemctl daemon-reload
systemctl enable asterisk
systemctl start asterisk
```

# app_rpt Installation

* `cd /usr/src`

* Pull down the app_rpt beta code. You will need to have [setup a GitHub access token](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens) for your Github account.
```
git clone https://github.com/InterLinked1/app_rpt.git
```

You should get output similar to:
```
# git clone https://github.com/InterLinked1/app_rpt.git

Cloning into 'app_rpt'...
Username for 'https://github.com': jxmx
Password for 'https://jxmx@github.com':
remote: Enumerating objects: 1679, done.
remote: Counting objects: 100% (389/389), done.
remote: Compressing objects: 100% (123/123), done.
remote: Total 1679 (delta 302), reused 334 (delta 266), pack-reused 1290
Receiving objects: 100% (1679/1679), 1.83 MiB | 6.26 MiB/s, done.
Resolving deltas: 100% (1003/1003), done.
```

* Build/install the apt_rpt system
```
cd app_rpt
bash rpt_install.sh
```

* Copy the stock configuration for ASL
```
cp /usr/src/app_rpt/configs/rpt/* /etc/asterisk
```

* Restart asterisk:
```
systemctl stop asterisk && sleep 2 &&  systemctl start asterisk
```

* Test the configuration:
```
asterisk -rx "rpt localnodes"
```

You should see node 1999. If so, you are now ready to configure your node.

# Configuration
[Continue to ASL Configuration](https://github.com/AllStarLink/ASL3/tree/develop#asl-configuration)
