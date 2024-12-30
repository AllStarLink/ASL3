sysconfdir ?= /etc/apt/apt.conf.d/

CONF_FILES = $(filter-out Makefile tmp , $(wildcard *))
CONF_INSTALLABLES = $(patsubst %, $(DESTDIR)$(sysconfdir)/%, $(CONF_FILES))

INSTALLABLES = $(CONF_INSTALLABLES) 

.PHONY:	install
install:	$(INSTALLABLES)

$(DESTDIR)$(sysconfdir)/%: %
	install -D -m 0644  $< $@

