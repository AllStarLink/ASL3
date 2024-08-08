prefix ?= /usr
exec_prefix ?= $(prefix)
share_prefix ?= $(exec_prefix)/share/asl3

SHARES = $(filter-out Makefile, $(wildcard *))
SHARES_EXP = $(patsubst %, $(DESTDIR)$(share_prefix)/%, $(SHARES))

install: $(SHARES_EXP)

$(DESTDIR)$(share_prefix)/%:	%
	install -D -m 0644 $< $@

