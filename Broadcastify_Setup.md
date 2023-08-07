# Streaming Node Audio to Broadcastify 


To broadcast your node's audio on [Broadcastify](https://www.broadcastify.com/), you will need a Broadcastify account. You can then apply for a feed. This [link](https://support.broadcastify.com/hc/en-us/articles/204740055-Becoming-a-Feed-Provider) provides information on applying for a feed.

After you have your account and feed credentials, you a ready to setup Allstar.

## Install required software

As of 8/5/2023, ezstream, version 1.0.2, contains a bug that prevents it from streaming MP3 data.  The following instructions will walk you through the steps to download and compile the necessary packages.

Log into your node and type the following commands.

```
sudo -s
cd /usr/src

git clone https://gitlab.xiph.org/xiph/ezstream.git
cd ezstream
git checkout master

wget https://gitlab.xiph.org/xiph/ezstream/uploads/ba768fa1349c65b60affd496cf4282ed/ezstream-1.0.2.patch

patch src/stream.c ezstream-1.0.2.patch

apt-get update
apt-get install check libshout-dev libtagc0-dev lame

./autogen.sh
./configure
make
make install

```

Press control-d to exit from superuser.

This will compile and install ezstream.  It will also install lame.

## Setup Ezstream Configuration

Edit /etc/ezstream.xml with your favorite editor.  You will be creating a new file.

Add the following to the file.

```
<ezstream>
	<servers>
		<server>
			<protocol>HTTP</protocol>
			<hostname>Replace with Broadcastify URL</hostname>
			<port>80</port>
			<password>Replace with your stream password</password>
			<tls>none</tls>
		</server>
	</servers>

	<streams>
		<stream>
			<mountpoint>Replace with your mount point path</mountpoint>
			<format>MP3</format>
    			<stream_name>Replace with your feed name</stream_name>
    			<stream_url>Your web page</stream_url>
    			<stream_genre>Amateur Radio</stream_genre>
    			<stream_description>Replace with your stream description</stream_description>
    			<stream_bitrate>16</stream_bitrate>
    			<stream_channels>1</stream_channels>
    			<stream_samplerate>22050</stream_samplerate>
    			<stream_public>Yes</stream_public>
		</stream>
	</streams>

	<intakes>
		<intake>
			<type>stdin</type>
		</intake>
	</intakes>


</ezstream>
```

Save the file.

Edit /etc/asterisk/rpt.conf.  Add the following line to the bottom of the node that you want to broadcast.

```
outstreamcmd = /bin/sh,-c,/usr/bin/lame --preset cbr 16 -r -m m -s 8 --bitwidth 16 - - | /usr/local/bin/ezstream -qvc /etc/ezstream.xml 2>/tmp/ezstreamlog.txt
```

The above parameters have these meanings.
	
	-- preset cbr 16 = use constant bit rate 16
	-r = Assume the input file is raw pcm
	-m m = Mode mono
	-s 8 = sample rate 8
	--bitwidth 16 = bit width is 16 (default)
	

After these changes have been made, you will need to restart asterisk with the following command.

```
sudo systemctl restart asterisk
```

If you experience any problems, look at /tmp/ezstreamlog.txt for error messages.

## Migrating an existing feed

If you have an existing feed, you will need to upgrade your existing xml file to the new format.  You can use the following commands.

```
cd /etc
ezstream-cfgmigrate -0 ezstream.xml > ezstream.xml.new
cp ezstream.xml ~/
mv ezstream.new ezstream.xml
```