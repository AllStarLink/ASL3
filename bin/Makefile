BINS = $(filter-out Makefile $(wildcard *.md) , $(wildcard *))

prefix ?= /usr
exec_prefix ?= $(prefix)
bin_prefix ?= $(exec_prefix)/bin
	
BINS_EXP = $(patsubst %, $(DESTDIR)$(bin_prefix)/%, $(BINS))

install: $(BINS_EXP) 

$(DESTDIR)$(bin_prefix)/%:	%
	install -D -m 0755 $< $@
