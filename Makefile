#
# Build variables
#
SRCNAME = ASL3
PKGNAME = asl3
RELVER = 3.18
DEBVER = 2
RELPLAT ?= deb$(shell lsb_release -rs 2> /dev/null)

BUILDABLES = \
	apt.conf.d \
	bin \
	etc \
	keys \
	polkit \
	share

ifdef ${DESTDIR}
DESTDIR=${DESTDIR}
endif

ROOT_FILES = LICENSE README.md 
ROOT_INSTALLABLES = $(patsubst %, $(DESTDIR)$(docdir)/%, $(CONF_FILES))

default:
	@echo This does nothing because of dpkg-buildpkg - use 'make install'

install: $(ROOT_INSTALLABLES)
	@echo DESTDIR=$(DESTDIR)
	@for dir in $(BUILDABLES); do \
		$(MAKE) -C $$dir install || exit $$?; \
	done

$(DESTDIR)$(docdir)/%: %
	install -D -m 0644  $< $@

verset:
	perl -pi -e 's/\@\@HEAD-DEVELOP\@\@/$(RELVER)/g' `grep -rl @@HEAD-DEVELOP@@ bin/`

deb:	debclean debprep
	debchange --distribution stable --package $(PKGNAME) \
		--newversion $(EPOCHVER)$(RELVER)-$(DEBVER).$(RELPLAT) \
		"Autobuild of $(EPOCHVER)$(RELVER)-$(DEBVER) for $(RELPLAT)"
	dpkg-buildpackage -b --no-sign
	git checkout debian/changelog
	git checkout bin/*

debchange:
	debchange -v $(RELVER)-$(DEBVER)
	debchange -r


debprep:	debclean
	(cd .. && \
		rm -f $(PKGNAME)-$(RELVER) && \
		rm -f $(PKGNAME)-$(RELVER).tar.gz && \
		rm -f $(PKGNAME)_$(RELVER).orig.tar.gz && \
		ln -s $(SRCNAME) $(PKGNAME)-$(RELVER) && \
		tar --exclude=".git" -h -zvcf $(PKGNAME)-$(RELVER).tar.gz asl3-$(RELVER) && \
		ln -s $(PKGNAME)-$(RELVER).tar.gz $(PKGNAME)_$(RELVER).orig.tar.gz )

debclean:
	rm -f ../$(PKGNAME)_$(RELVER)*
	rm -f ../$(PKGNAME)-$(RELVER)*
	rm -rf debian/$(PKGNAME)
	rm -f debian/files
	rm -rf debian/.debhelper/
	rm -f debian/debhelper-build-stamp
	rm -f debian/*.substvars
	rm -rf debian/$(SRCNAME)/ debian/.debhelper/
	rm -f debian/debhelper-build-stamp debian/files debian/$(SRCNAME).substvars
	rm -f debian/*.debhelper debian/*.debhelper.log

.PHONY: test test-all test-python test-shell

test: test-python
	@echo "All tests passed!"

test-all: test-python test-shell
	@echo "All tests (Python + Shell) passed!"

test-python:
	@echo "Running all Python tests"
	python3 -m pytest tests/ -v

test-shell:
	@echo "Running shell script tests..."
	find tests -type f -name '*.bats' -exec chmod +x {} + 2>/dev/null || true
	if find . -type f -name '*.bats' -print0 | xargs -0 bats; then \
	    echo "BATS tests passed"; \
	else \ 
	    echo "BATS tests not configured or not found"; \
		exit 1; \
	fi
	
