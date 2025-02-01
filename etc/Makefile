sysconfdir ?= /etc

all: \
	asl3-snd-usb-audio.conf
	

install:	all
	install -D -m 0644 asl3-snd-usb-audio.conf $(DESTDIR)$(sysconfdir)/modprobe.d/asl3-snd-usb-audio.conf

