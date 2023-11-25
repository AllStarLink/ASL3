With Asterisk now running as user asterisk, ports below 1024 are not accessable. This impacts the Voter/RTCM port 667.
AllStarlink recommends using port 1667 for Voters/RTCMs going forward. However if that is temporally not possible
we recommend the following:
```
cd /etc/sysctl.d
echo net.ipv4.ip_unprivileged_port_start=667 > alsport667.conf
```
