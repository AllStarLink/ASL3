bin_prefix ?= /usr/bin
libexec_prefix ?= /usr/libexec/asl3
sysconfdir ?= /etc/asterisk/broadcastify

BUILDABLES = \
	rpt_audio_writer

BINS = asl-broadcastify
BINS_EXP = $(patsubst %, $(DESTDIR)$(bin_prefix)/%, $(BINS))

LIBEXECS = rpt_audio_writer
LIBEXECS_EXP = $(patsubst %, $(DESTDIR)$(libexec_prefix)/%, $(LIBEXECS))

CONF = 1999.conf.example
CONF_EXP = $(patsubst %, $(DESTDIR)$(sysconfdir)/%, $(CONF))

build:	$(BUILDABLES)

install: build $(BINS_EXP) $(LIBEXECS_EXP) $(CONF_EXP)

clean:
	rm $(BUILDABLES)

%:	%.c
	cc -o $@ $<

$(DESTDIR)$(bin_prefix)/%:	%	
	install -D -m 0755 $< $@

$(DESTDIR)$(libexec_prefix)/%:	%
	install -D -m 0755 $< $@

$(DESTDIR)$(sysconfdir)/%:	%
	install -D -m 0644 $< $@
	chmod 750 $(DESTDIR)$(sysconfdir)

