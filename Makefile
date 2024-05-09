#!/usr/bin/make -f
# Makefile for LADI/Claudia #
# ---------------------- #
# Claudia was created by falkTX
# This and related files were modified (post 2023) by Nedko Arnaudov (LADI)

CODETREENAME="ladi-claudia"
VERSION="2.5.0"

PREFIX  = /usr/local
DESTDIR =

LINK   = ln -s
PYUIC ?= pyuic5
PYRCC ?= pyrcc5
PYLUPDATE ?= pylupdate5
LRELEASE ?= lrelease

# -----------------------------------------------------------------------------------------------------------------------------------------
# Internationalization

I18N_LANGUAGES :=

# -----------------------------------------------------------------------------------------------------------------------------------------

default: RES UI

all: RES UI

# -----------------------------------------------------------------------------------------------------------------------------------------
# Resources

RES: src/resources_rc.py

src/resources_rc.py: resources/resources.qrc
	$(PYRCC) $< -o $@

# -----------------------------------------------------------------------------------------------------------------------------------------
# UI code

UI: claudia tools

claudia: src/ui_claudia.py \
	src/ui_claudia_studioname.py src/ui_claudia_studiolist.py \
	src/ui_claudia_createroom.py src/ui_claudia_projectname.py src/ui_claudia_projectproperties.py \
	src/ui_claudia_runcustom.py src/ui_claudia_launcher.py src/ui_claudia_launcher_app.py

tools: \
	src/ui_settings_app.py \
	src/ui_settings_jack.py

src/ui_%.py: resources/ui/%.ui
	$(PYUIC) $< -o $@

# -----------------------------------------------------------------------------------------------------------------------------------------

clean:
	rm -f *~ src/*~ src/*.pyc src/ui_*.py src/resources_rc.py

# -----------------------------------------------------------------------------------------------------------------------------------------

debug:
	$(MAKE) DEBUG=true

# -----------------------------------------------------------------------------------------------------------------------------------------

install:
	# Create directories
	install -d $(DESTDIR)/etc/xdg/autostart/
	install -d $(DESTDIR)$(PREFIX)/bin/
	install -d $(DESTDIR)$(PREFIX)/share/applications/
	install -d $(DESTDIR)$(PREFIX)/share/icons/hicolor/16x16/apps/
	install -d $(DESTDIR)$(PREFIX)/share/icons/hicolor/48x48/apps/
	install -d $(DESTDIR)$(PREFIX)/share/icons/hicolor/128x128/apps/
	install -d $(DESTDIR)$(PREFIX)/share/icons/hicolor/256x256/apps/
	install -d $(DESTDIR)$(PREFIX)/share/icons/hicolor/scalable/apps/
	install -d $(DESTDIR)$(PREFIX)/share/$(CODETREENAME)/
	install -d $(DESTDIR)$(PREFIX)/share/$(CODETREENAME)/src/
	install -d $(DESTDIR)$(PREFIX)/share/$(CODETREENAME)/icons/
	install -d $(DESTDIR)$(PREFIX)/share/$(CODETREENAME)/templates/

	# Install script files and binaries
	install -m 755 \
		data/claudia \
		$(DESTDIR)$(PREFIX)/bin/

	# Install desktop files
	install -m 644 data/*.desktop           $(DESTDIR)$(PREFIX)/share/applications/

	# Install icons, 16x16
	install -m 644 resources/16x16/claudia.png             $(DESTDIR)$(PREFIX)/share/icons/hicolor/16x16/apps/
#	install -m 644 resources/16x16/claudia-launcher.png    $(DESTDIR)$(PREFIX)/share/icons/hicolor/16x16/apps/

	# Install icons, 48x48
	install -m 644 resources/48x48/claudia.png             $(DESTDIR)$(PREFIX)/share/icons/hicolor/48x48/apps/
#	install -m 644 resources/48x48/claudia-launcher.png    $(DESTDIR)$(PREFIX)/share/icons/hicolor/48x48/apps/

	# Install icons, 128x128
	install -m 644 resources/128x128/claudia.png           $(DESTDIR)$(PREFIX)/share/icons/hicolor/128x128/apps/
#	install -m 644 resources/128x128/claudia-launcher.png  $(DESTDIR)$(PREFIX)/share/icons/hicolor/128x128/apps/

	# Install icons, 256x256
	install -m 644 resources/256x256/claudia.png           $(DESTDIR)$(PREFIX)/share/icons/hicolor/256x256/apps/
#	install -m 644 resources/256x256/claudia-launcher.png  $(DESTDIR)$(PREFIX)/share/icons/hicolor/256x256/apps/

	# Install icons, scalable
	install -m 644 resources/scalable/claudia.svg          $(DESTDIR)$(PREFIX)/share/icons/hicolor/scalable/apps/
#	install -m 644 resources/scalable/claudia-launcher.svg $(DESTDIR)$(PREFIX)/share/icons/hicolor/scalable/apps/

	# Install main code
	install -m 644 src/*.py $(DESTDIR)$(PREFIX)/share/$(CODETREENAME)/src/

	# compile python files
	python3 -m compileall $(DESTDIR)$(PREFIX)/share/$(CODETREENAME)/src/

	# Install addtional stuff for Claudia
	cp -r data/icons/*     $(DESTDIR)$(PREFIX)/share/claudia/icons/
	cp -r data/templates/* $(DESTDIR)$(PREFIX)/share/claudia/templates/

	# Adjust PREFIX value in script files
	sed -i "s?X-PREFIX-X?$(PREFIX)?" \
		$(DESTDIR)$(PREFIX)/bin/claudia
#		$(DESTDIR)$(PREFIX)/bin/claudia-launcher

# -----------------------------------------------------------------------------------------------------------------------------------------

uninstall:
	rm -f $(DESTDIR)$(PREFIX)/bin/claudia*
	rm -f $(DESTDIR)$(PREFIX)/share/applications/claudia.desktop
	rm -f $(DESTDIR)$(PREFIX)/share/icons/hicolor/*/apps/claudia.png
	rm -f $(DESTDIR)$(PREFIX)/share/icons/hicolor/scalable/apps/claudia.svg
	rm -rf $(DESTDIR)$(PREFIX)/share/$(CODETREENAME)/

TARBALL_NAME := $(CODETREENAME)-$(VERSION)
dist:
	git clean -xfd
	git describe --tags
	rm -rvf $(TARBALL_NAME)
	mkdir -v $(TARBALL_NAME)
	cp -v AUTHORS.adoc $(TARBALL_NAME)
	cp -v COPYING $(TARBALL_NAME)
	cp -v INSTALL.md $(TARBALL_NAME)
	cp -v MAINTAINERS.adoc $(TARBALL_NAME)
	cp -v Makefile $(TARBALL_NAME)
	cp -v NEWS.adoc $(TARBALL_NAME)
	cp -v README.md $(TARBALL_NAME)
#	cp -v TODO
	cp -rv c++ $(TARBALL_NAME)
	cp -rv data $(TARBALL_NAME)
	cp -rv resources $(TARBALL_NAME)
	cp -rv src $(TARBALL_NAME)
	tar cJf $(TARBALL_NAME).tar.xz $(TARBALL_NAME)
	gpg -b $(TARBALL_NAME).tar.xz
	gpg --verify $(TARBALL_NAME).tar.xz.sig
	rm -rvf $(TARBALL_NAME)
