#!/usr/bin/make -f
# Makefile for Cadence #
# ---------------------- #
# Created by falkTX
#

PREFIX  = /usr/local
DESTDIR =

LINK   = ln -s
PYUIC ?= pyuic5
PYRCC ?= pyrcc5
PYLUPDATE ?= pylupdate5
LRELEASE ?= lrelease

# Detect X11 rules dir
ifeq "$(wildcard /etc/X11/Xsession.d/ )" ""
	X11_RC_DIR = $(DESTDIR)/etc/X11/xinit/xinitrc.d/
else
	X11_RC_DIR = $(DESTDIR)/etc/X11/Xsession.d/
endif

# -----------------------------------------------------------------------------------------------------------------------------------------
# Internationalization

I18N_LANGUAGES :=

# -----------------------------------------------------------------------------------------------------------------------------------------

all: CPP RES UI locale

# -----------------------------------------------------------------------------------------------------------------------------------------
# C++ code

CPP: jackmeter xycontroller

jackmeter:
	$(MAKE) -C c++/jackmeter

xycontroller:
	$(MAKE) -C c++/xycontroller

# -----------------------------------------------------------------------------------------------------------------------------------------
# Resources

RES: src/resources_rc.py

src/resources_rc.py: resources/resources.qrc
	$(PYRCC) $< -o $@

# -----------------------------------------------------------------------------------------------------------------------------------------
# Translations
locale: locale/cadence_en.qm locale/cadence_fr.qm
	
locale/%.qm: locale/%.ts
	$(LRELEASE) $< -qm $@

# -----------------------------------------------------------------------------------------------------------------------------------------
# UI code

UI: cadence catarina catia tools

cadence: src/ui_cadence.py \
	src/ui_cadence_tb_alsa.py src/ui_cadence_tb_a2j.py  \
	src/ui_cadence_rwait.py src/ui_pulse_bridge.py

catarina: src/ui_catarina.py \
	src/ui_catarina_addgroup.py src/ui_catarina_removegroup.py src/ui_catarina_renamegroup.py \
	src/ui_catarina_addport.py src/ui_catarina_removeport.py src/ui_catarina_renameport.py \
	src/ui_catarina_connectports.py src/ui_catarina_disconnectports.py

catia: src/ui_catia.py

tools: \
	src/ui_logs.py src/ui_render.py \
	src/ui_settings_app.py src/ui_settings_jack.py

src/ui_%.py: resources/ui/%.ui
	$(PYUIC) $< -o $@

# -----------------------------------------------------------------------------------------------------------------------------------------

clean:
	$(MAKE) clean -C c++/jackmeter
	$(MAKE) clean -C c++/xycontroller
	rm -f *~ src/*~ src/*.pyc src/ui_*.py src/resources_rc.py resources/locale/*.qm

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
	install -d $(DESTDIR)$(PREFIX)/share/cadence/
	install -d $(DESTDIR)$(PREFIX)/share/cadence/src/
	install -d $(DESTDIR)$(PREFIX)/share/cadence/pulse2jack/
	install -d $(DESTDIR)$(PREFIX)/share/cadence/pulse2loopback/
	install -d $(DESTDIR)$(PREFIX)/share/cadence/icons/
	install -d $(DESTDIR)$(PREFIX)/share/cadence/templates/
	install -d $(DESTDIR)$(PREFIX)/share/cadence/locale/
	install -d $(X11_RC_DIR)

	# Install script files and binaries
	install -m 755 \
		data/cadence \
		data/cadence-aloop-daemon \
		data/cadence-jacksettings \
		data/cadence-logs \
		data/cadence-pulse2jack \
		data/cadence-pulse2loopback \
		data/cadence-render \
		data/cadence-session-start \
		data/catarina \
		data/catia \
		c++/jackmeter/cadence-jackmeter \
		c++/xycontroller/cadence-xycontroller \
		$(DESTDIR)$(PREFIX)/bin/

	# Install desktop files
	install -m 644 data/autostart/*.desktop $(DESTDIR)/etc/xdg/autostart/
	install -m 644 data/*.desktop           $(DESTDIR)$(PREFIX)/share/applications/

	# Install icons, 16x16
	install -m 644 resources/16x16/cadence.png             $(DESTDIR)$(PREFIX)/share/icons/hicolor/16x16/apps/
	install -m 644 resources/16x16/catarina.png            $(DESTDIR)$(PREFIX)/share/icons/hicolor/16x16/apps/
	install -m 644 resources/16x16/catia.png               $(DESTDIR)$(PREFIX)/share/icons/hicolor/16x16/apps/

	# Install icons, 48x48
	install -m 644 resources/48x48/cadence.png             $(DESTDIR)$(PREFIX)/share/icons/hicolor/48x48/apps/
	install -m 644 resources/48x48/catarina.png            $(DESTDIR)$(PREFIX)/share/icons/hicolor/48x48/apps/
	install -m 644 resources/48x48/catia.png               $(DESTDIR)$(PREFIX)/share/icons/hicolor/48x48/apps/

	# Install icons, 128x128
	install -m 644 resources/128x128/cadence.png           $(DESTDIR)$(PREFIX)/share/icons/hicolor/128x128/apps/
	install -m 644 resources/128x128/catarina.png          $(DESTDIR)$(PREFIX)/share/icons/hicolor/128x128/apps/
	install -m 644 resources/128x128/catia.png             $(DESTDIR)$(PREFIX)/share/icons/hicolor/128x128/apps/

	# Install icons, 256x256
	install -m 644 resources/256x256/cadence.png           $(DESTDIR)$(PREFIX)/share/icons/hicolor/256x256/apps/
	install -m 644 resources/256x256/catarina.png          $(DESTDIR)$(PREFIX)/share/icons/hicolor/256x256/apps/
	install -m 644 resources/256x256/catia.png             $(DESTDIR)$(PREFIX)/share/icons/hicolor/256x256/apps/

	# Install icons, scalable
	install -m 644 resources/scalable/cadence.svg          $(DESTDIR)$(PREFIX)/share/icons/hicolor/scalable/apps/
	install -m 644 resources/scalable/catarina.svg         $(DESTDIR)$(PREFIX)/share/icons/hicolor/scalable/apps/
	install -m 644 resources/scalable/catia.svg            $(DESTDIR)$(PREFIX)/share/icons/hicolor/scalable/apps/

	# Install main code
	install -m 755 src/*.py $(DESTDIR)$(PREFIX)/share/cadence/src/

	# Install translations
	install -m 644 locale/*.qm $(DESTDIR)$(PREFIX)/share/cadence/locale/

	# compile python files
	python3 -m compileall $(DESTDIR)$(PREFIX)/share/cadence/src/
	
	# Install addtional stuff for Cadence
	install -m 644 data/pulse2jack/*     $(DESTDIR)$(PREFIX)/share/cadence/pulse2jack/
	install -m 644 data/pulse2loopback/* $(DESTDIR)$(PREFIX)/share/cadence/pulse2loopback/
	install -m 755 data/61cadence-session-inject $(X11_RC_DIR)

	# Adjust PREFIX value in script files
	sed -i "s?X-PREFIX-X?$(PREFIX)?" \
		$(DESTDIR)$(PREFIX)/bin/cadence \
		$(DESTDIR)$(PREFIX)/bin/cadence-aloop-daemon \
		$(DESTDIR)$(PREFIX)/bin/cadence-jacksettings \
		$(DESTDIR)$(PREFIX)/bin/cadence-logs \
		$(DESTDIR)$(PREFIX)/bin/cadence-pulse2jack \
		$(DESTDIR)$(PREFIX)/bin/cadence-pulse2loopback \
		$(DESTDIR)$(PREFIX)/bin/cadence-render \
		$(DESTDIR)$(PREFIX)/bin/cadence-session-start \
		$(DESTDIR)$(PREFIX)/bin/catarina \
		$(DESTDIR)$(PREFIX)/bin/catia \
		$(X11_RC_DIR)/61cadence-session-inject

	# Delete old files
	rm -f $(X11_RC_DIR)/21cadence-session-inject
	rm -f $(X11_RC_DIR)/70cadence-plugin-paths
	rm -f $(X11_RC_DIR)/99cadence-session-start

# -----------------------------------------------------------------------------------------------------------------------------------------

uninstall:
	rm -f $(DESTDIR)$(PREFIX)/bin/cadence*
	rm -f $(DESTDIR)$(PREFIX)/bin/catarina
	rm -f $(DESTDIR)$(PREFIX)/bin/catia
	rm -f $(DESTDIR)$(PREFIX)/bin/claudia*
	rm -f $(DESTDIR)$(PREFIX)/share/applications/cadence.desktop
	rm -f $(DESTDIR)$(PREFIX)/share/applications/catarina.desktop
	rm -f $(DESTDIR)$(PREFIX)/share/applications/catia.desktop
	rm -f $(DESTDIR)$(PREFIX)/share/applications/claudia.desktop
	rm -f $(DESTDIR)$(PREFIX)/share/applications/claudia-launcher.desktop
	rm -f $(DESTDIR)$(PREFIX)/share/icons/hicolor/*/apps/cadence.png
	rm -f $(DESTDIR)$(PREFIX)/share/icons/hicolor/*/apps/catarina.png
	rm -f $(DESTDIR)$(PREFIX)/share/icons/hicolor/*/apps/catia.png
	rm -f $(DESTDIR)$(PREFIX)/share/icons/hicolor/*/apps/claudia.png
	rm -f $(DESTDIR)$(PREFIX)/share/icons/hicolor/*/apps/claudia-launcher.png
	rm -f $(DESTDIR)$(PREFIX)/share/icons/hicolor/scalable/apps/cadence.svg
	rm -f $(DESTDIR)$(PREFIX)/share/icons/hicolor/scalable/apps/catarina.svg
	rm -f $(DESTDIR)$(PREFIX)/share/icons/hicolor/scalable/apps/catia.svg
	rm -f $(DESTDIR)$(PREFIX)/share/icons/hicolor/scalable/apps/claudia.svg
	rm -f $(DESTDIR)$(PREFIX)/share/icons/hicolor/scalable/apps/claudia-launcher.svg
	rm -f $(DESTDIR)/etc/xdg/autostart/cadence-session-start.desktop
	rm -f $(X11_RC_DIR)/61cadence-session-inject
	rm -rf $(DESTDIR)$(PREFIX)/share/cadence/

	# Old stuff
	rm -f $(X11_RC_DIR)/21cadence-session-inject
	rm -f $(X11_RC_DIR)/70cadence-plugin-paths
	rm -f $(X11_RC_DIR)/99cadence-session-start
