sysconfdir ?= /etc/kernel/postinst.d

all: \
	kernel_postinst.d_asl

install:	all
	install -D -m 0755 kernel_postinst.d_asl $(DESTDIR)$(sysconfdir)/asl

