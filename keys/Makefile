prefix ?= /usr
exec_prefix ?= $(prefix)
share_prefix ?= $(exec_prefix)/share
ast_prefix ?= $(share_prefix)/asterisk/keys

KEYS = $(filter-out Makefile $(wildcard *.md) tmp, $(wildcard *.pub))
KEYS_EXP = $(patsubst %, $(DESTDIR)$(ast_prefix)/%, $(KEYS))

install: $(KEYS_EXP) 

$(DESTDIR)$(ast_prefix)/%:	%
	install -D -m 0644 $< $@
