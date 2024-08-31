sysconfdir      ?= /etc
polkitdir    	?= $(sysconfdir)/polkit-1/rules.d
astsrcdir		?= $(sysconfdir)/asterisk/scripts

POLKIT_RULES = \
	50-asl3.rules
POLKIT_INSTALLABLES = $(patsubst %, $(DESTDIR)$(polkitdir)/%, $(POLKIT_RULES))

AST_SCRIPTS = \
	allmon3-restart \
	allmon3-stop \
	asterisk-restart \
	asterisk-stop
AST_SCRIPTS_INSTALLABLES = $(patsubst %, $(DESTDIR)$(astsrcdir)/%, $(AST_SCRIPTS))

INSTALLABLES = $(POLKIT_INSTALLABLES) $(AST_SCRIPTS_INSTALLABLES)

.PHONY: install
install:    $(INSTALLABLES)


$(DESTDIR)$(polkitdir)/%:	%
	install -D -m 0644 $< $@

$(DESTDIR)$(astsrcdir)/%:	%
	install -D -m 0755 $< $@




