#
# Build variables
#
RELVER = 3.0.0
DEBVER = 1

BUILDABLES = \
	bin 

instconf ?= no

ifeq ($(instconf),yes)
BUILDABLES += conf
endif

ifdef ${DESTDIR}
DESTDIR=${DESTDIR}
endif

ROOT_FILES = LICENSE README.md SECURITY.md
ROOT_INSTALLABLES = $(patsubst %, $(DESTDIR)$(docdir)/%, $(CONF_FILES))

default:
	@echo This does nothing because of dpkg-buildpkg - use 'make install'

install: $(ROOT_INSTALLABLES)
	@echo DESTDIR=$(DESTDIR)
	$(foreach dir, $(BUILDABLES), $(MAKE) -C $(dir) install;)

$(DESTDIR)$(docdir)/%: %
	install -D -m 0644  $< $@

verset:
	perl -pi -e 's/\@\@HEAD-DEVELOP\@\@/$(RELVER)/g' `grep -rl @@HEAD-DEVELOP@@ src/ web/`

deb:	debclean debprep
	debchange -r
	debuild


debchange:
	debchange -v $(RELVER)-$(DEBVER)


debprep:	debclean
	(cd .. && \
		rm -f asl3-$(RELVER) && \
		rm -f asl3-$(RELVER).tar.gz && \
		rm -f asl3_$(RELVER).orig.tar.gz && \
		ln -s ASL3 asl3-$(RELVER) && \
		tar --exclude=".git" -h -zvcf asl3-$(RELVER).tar.gz asl3-$(RELVER) && \
		ln -s asl3-$(RELVER).tar.gz asl3_$(RELVER).orig.tar.gz )

debclean:
	rm -f ../asl3_$(RELVER)*
	rm -rf debian/asl3
	rm -f debian/files
	
