prefix ?= /usr
exec_prefix ?= $(prefix)
bin_prefix ?= $(exec_prefix)/bin
mandir ?= $(prefix)/share/man

BINS = $(filter-out Makefile $(wildcard *.md) tmp, $(wildcard *))
BINS_EXP = $(patsubst %, $(DESTDIR)$(bin_prefix)/%, $(BINS))

MANS_SRC = $(wildcard *.1.md)
MANS_EXP = $(patsubst %.md, $(DESTDIR)$(mandir)/man1/%, $(MANS_SRC))

install: $(BINS_EXP) $(MANS_EXP)

mans:	$(MANS_EXP)

$(DESTDIR)$(bin_prefix)/%:	%
	install -D -m 0755 $< $@

$(DESTDIR)$(mandir)/man1/%: %.md
	mkdir -p $(DESTDIR)$(mandir)/man1
	pandoc $< -s -t man > $@

