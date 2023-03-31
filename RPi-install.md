# RPI install steps
```
cd /usr/src && wget https://docs.phreaknet.org/script/phreaknet.sh && chmod +x phreaknet.sh && ./phreaknet.sh make
CFLAGS=-Wno-error phreaknet install -b -s -d
modprobe dahdi
cd /usr/src
git clone https://github.com/InterLinked1/app_rpt.git
cd app_rpt
bash ./rpt_install.sh
>> do rpt.conf and other configuration <<
systemctl stop asterisk && sleep 2 &&  systemctl start asterisk
```
