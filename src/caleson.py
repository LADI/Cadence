#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Caleson, JACK utilities
# Copyright (C) 2010-2018 Filipe Coelho <falktx@falktx.com>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# For a full copy of the GNU General Public License see the COPYING file


# Imports (Global)

import os
import sys
from platform import architecture

from PyQt5.QtCore import (
    QFileSystemWatcher, QSize, Qt, QTimer, pyqtSlot, pyqtSignal,
    QSettings)
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import (
    QApplication, QDialogButtonBox, QMainWindow, QFrame,
    QListWidgetItem, QComboBox, QDialog, QMessageBox,
    QFileDialog)


# Imports (Custom Stuff)

import force_restart
import systray
import pulse2jack_tool
import ui_caleson
import ui_caleson_tb_alsa
import ui_pulse_bridge
from shared import (
    LINUX, HAIKU, MACOS, WINDOWS, DEBUG, VERSION, getIcon,
    CustomMessageBox, setUpSignals)
from shared_caleson import (
    getProcList, GlobalSettings, DEFAULT_PLUGIN_PATH,
    iAlsaFileNone, iAlsaFileLoop, iAlsaFileJACK,
    iAlsaFilePulse, iAlsaFileMax,
    startAlsaAudioLoopBridge, wantJackStart)
from shared_canvasjack import (
    jacklib, gDBus, BUFFER_SIZE_LIST, jacksettings)
from shared_settings import HOME
from shared_i18n import setup_i18n

# Import getoutput
from subprocess import getoutput

# Try Import DBus
try:
    import dbus
    from dbus.mainloop.pyqt5 import DBusQtMainLoop as DBusMainLoop
    haveDBus = True
except:
    try:
        # Try falling back to GMainLoop
        from dbus.mainloop.glib import DBusGMainLoop as DBusMainLoop
        haveDBus = True
    except:
        haveDBus = False

# Check for PulseAudio and Wine

havePulseAudio = os.path.exists("/usr/bin/pulseaudio")
haveWine = os.path.exists("/usr/bin/regedit")

if haveWine:
    WINEPREFIX = os.getenv("WINEPREFIX")
    if not WINEPREFIX:
        WINEPREFIX = os.path.join(HOME, ".wine")

# ---------------------------------------------------------------------


DESKTOP_X_IMAGE = [
    "eog.desktop",
    "kde4/digikam.desktop",
    "kde4/gwenview.desktop",
    "org.kde.digikam.desktop",
    "org.kde.gwenview.desktop",
]

DESKTOP_X_MUSIC = [
    "audacious.desktop",
    "clementine.desktop",
    "smplayer.desktop",
    "vlc.desktop",
    "kde4/amarok.desktop",
    "org.kde.amarok.desktop",
]

DESKTOP_X_VIDEO = [
    "smplayer.desktop",
    "vlc.desktop",
]

DESKTOP_X_TEXT = [
    "gedit.desktop",
    "kde4/kate.desktop",
    "kde4/kwrite.desktop",
    "org.kde.kate.desktop",
    "org.kde.kwrite.desktop",
]

DESKTOP_X_BROWSER = [
    "chrome.desktop",
    "firefox.desktop",
    "iceweasel.desktop",
    "kde4/konqbrowser.desktop",
    "org.kde.konqbrowser.desktop",
]

XDG_APPLICATIONS_PATH = [
    "/usr/share/applications",
    "/usr/local/share/applications"
]

# ---------------------------------------------------------------------
class PulseAudioJackBridgeValues(object):
    clientIdCapture = -1
    clientIdPlayback = -1
    portCaptureNumber =  0
    portPlaybackNumber =  0 


global jackClientIdALSA
jackClientIdALSA = -1
pA_bridge_values = PulseAudioJackBridgeValues()

# jackdbus indexes
iGraphVersion = 0
iJackClientId = 1
iJackClientName = 2
iJackPortId = 3
iJackPortName = 4
iJackPortNewName = 5
iJackPortFlags = 5
iJackPortType = 6

asoundrc_aloop = (""
"# ------------------------------------------------------\n"
"# Custom asoundrc file for use with snd-aloop and JACK\n"
"#\n"
"# use it like this:\n"
"# env JACK_SAMPLE_RATE=44100 JACK_PERIOD_SIZE=1024 alsa_in (...)\n"
"#\n"
"\n"
"# ------------------------------------------------------\n"
"# playback device\n"
"pcm.aloopPlayback {\n"
"  type dmix\n"
"  ipc_key 1\n"
"  ipc_key_add_uid true\n"
"  slave {\n"
"    pcm \"hw:Loopback,0,0\"\n"
"    format S32_LE\n"
"    rate {\n"
"      @func igetenv\n"
"      vars [ JACK_SAMPLE_RATE ]\n"
"      default 44100\n"
"    }\n"
"    period_size {\n"
"      @func igetenv\n"
"      vars [ JACK_PERIOD_SIZE ]\n"
"      default 1024\n"
"    }\n"
"    buffer_size 4096\n"
"  }\n"
"}\n"
"\n"
"# capture device\n"
"pcm.aloopCapture {\n"
"  type dsnoop\n"
"  ipc_key 2\n"
"  ipc_key_add_uid true\n"
"  slave {\n"
"    pcm \"hw:Loopback,0,1\"\n"
"    format S32_LE\n"
"    rate {\n"
"      @func igetenv\n"
"      vars [ JACK_SAMPLE_RATE ]\n"
"      default 44100\n"
"    }\n"
"    period_size {\n"
"      @func igetenv\n"
"      vars [ JACK_PERIOD_SIZE ]\n"
"      default 1024\n"
"    }\n"
"    buffer_size 4096\n"
"  }\n"
"}\n"
"\n"
"# duplex device\n"
"pcm.aloopDuplex {\n"
"  type asym\n"
"  playback.pcm \"aloopPlayback\"\n"
"  capture.pcm \"aloopCapture\"\n"
"}\n"
"\n"
"# ------------------------------------------------------\n"
"# default device\n"
"pcm.!default {\n"
"  type plug\n"
"  slave.pcm \"aloopDuplex\"\n"
"}\n"
"\n"
"# ------------------------------------------------------\n"
"# alsa_in -j alsa_in -dcloop -q 1\n"
"pcm.cloop {\n"
"  type dsnoop\n"
"  ipc_key 3\n"
"  ipc_key_add_uid true\n"
"  slave {\n"
"    pcm \"hw:Loopback,1,0\"\n"
"    channels 2\n"
"    format S32_LE\n"
"    rate {\n"
"      @func igetenv\n"
"      vars [ JACK_SAMPLE_RATE ]\n"
"      default 44100\n"
"    }\n"
"    period_size {\n"
"      @func igetenv\n"
"      vars [ JACK_PERIOD_SIZE ]\n"
"      default 1024\n"
"    }\n"
"    buffer_size 32768\n"
"  }\n"
"}\n"
"\n"
"# ------------------------------------------------------\n"
"# alsa_out -j alsa_out -dploop -q 1\n"
"pcm.ploop {\n"
"  type plug\n"
"  slave.pcm \"hw:Loopback,1,1\"\n"
"}")

asoundrc_aloop_check = asoundrc_aloop.split("pcm.aloopPlayback", 1)[0]

asoundrc_jack = (""
"pcm.!default {\n"
"    type plug\n"
"    slave { pcm \"jack\" }\n"
"}\n"
"\n"
"pcm.jack {\n"
"    type jack\n"
"    playback_ports {\n"
"        0 system:playback_1\n"
"        1 system:playback_2\n"
"    }\n"
"    capture_ports {\n"
"        0 system:capture_1\n"
"        1 system:capture_2\n"
"    }\n"
"}\n"
"\n"
"ctl.mixer0 {\n"
"    type hw\n"
"    card 0\n"
"}")

asoundrc_pulse = (""
"pcm.!default {\n"
"    type plug\n"
"    slave { pcm \"pulse\" }\n"
"}\n"
"\n"
"pcm.pulse {\n"
"    type pulse\n"
"}\n"
"\n"
"ctl.mixer0 {\n"
"    type hw\n"
"    card 0\n"
"}")

# ---------------------------------------------------------------------

def get_architecture():
    return architecture()[0]

def get_haiku_information():
    # TODO
    return ("Haiku OS", "Unknown")

def get_linux_information():
    # TODO informs about Librazik
    if os.path.exists("/etc/lsb-release"):
        distro = getoutput(". /etc/lsb-release && echo $DISTRIB_DESCRIPTION")
    elif os.path.exists("/etc/arch-release"):
        distro = "ArchLinux"
    else:
        distro = os.uname()[0]

    kernel = os.uname()[2]

    return (distro, kernel)

def get_mac_information():
    # TODO
    return ("Mac OS", "Unknown")

def get_windows_information():
    major = sys.getwindowsversion()[0]
    minor = sys.getwindowsversion()[1]
    servp = sys.getwindowsversion()[4]

    os = "Windows"
    version = servp

    if major == 4 and minor == 0:
        os = "Windows 95"
        version = "RTM"
    elif major == 4 and minor == 10:
        os = "Windows 98"
        version = "Second Edition"
    elif major == 5 and minor == 0:
        os = "Windows 2000"
    elif major == 5 and minor == 1:
        os = "Windows XP"
    elif major == 5 and minor == 2:
        os = "Windows Server 2003"
    elif major == 6 and minor == 0:
        os = "Windows Vista"
    elif major == 6 and minor == 1:
        os = "Windows 7"
    elif major == 6 and minor == 2:
        os = "Windows 8"

    return (os, version)

# ---------------------------------------------------------------------

def isAlsaAudioBridged():
    global jackClientIdALSA
    return bool(jackClientIdALSA != -1)

def isPulseAudioStarted():
    return bool("pulseaudio" in getProcList())

def isDesktopFileInstalled(desktop):
    for X_PATH in XDG_APPLICATIONS_PATH:
        if os.path.exists(os.path.join(X_PATH, desktop)):
            return True
    return False

def getDesktopFileContents(desktop):
    for X_PATH in XDG_APPLICATIONS_PATH:
        if os.path.exists(os.path.join(X_PATH, desktop)):
            fd = open(os.path.join(X_PATH, desktop), "r")
            contents = fd.read()
            fd.close()
            return contents
    return None

def getXdgProperty(fileRead, key):
    fileReadSplit = fileRead.split(key, 1)

    if len(fileReadSplit) > 1:
        fileReadLine = fileReadSplit[1].split("\n",1)[0]
        fileReadLineStripped = fileReadLine.rsplit(";",1)[0].strip()
        value = fileReadLineStripped.replace("=","",1)
        return value

    return None

def getWineAsioKeyValue(key, default):
  wineFile = os.path.join(WINEPREFIX, "user.reg")

  if not os.path.exists(wineFile):
      return default

  wineDumpF = open(wineFile, "r")
  wineDump = wineDumpF.read()
  wineDumpF.close()

  wineDumpSplit = wineDump.split("[Software\\\\Wine\\\\WineASIO]")

  if len(wineDumpSplit) <= 1:
      return default

  wineDumpSmall = wineDumpSplit[1].split("[")[0]
  keyDumpSplit = wineDumpSmall.split('"%s"' % key)

  if len(keyDumpSplit) <= 1:
      return default

  keyDumpSmall = keyDumpSplit[1].split(":")[1].split("\n")[0]
  return keyDumpSmall

def searchAndSetComboBoxValue(comboBox: QComboBox, value):
    for i in range(comboBox.count()):
        if comboBox.itemText(i).replace("/","-") == value:
            comboBox.setCurrentIndex(i)
            comboBox.setEnabled(True)
            return True
    return False

def smartHex(value, length):
  hexStr = hex(value).replace("0x","")

  if len(hexStr) < length:
      zeroCount = length - len(hexStr)
      hexStr = "%s%s" % ("0"*zeroCount, hexStr)

  return hexStr

# ---------------------------------------------------------------------

class CalesonSystemCheck(object):
    ICON_ERROR = 0
    ICON_WARN = 1
    ICON_OK = 2

    def __init__(self):
        object.__init__(self)

        self.name = self.tr("check")
        self.icon = self.ICON_OK
        self.result = self.tr("yes")

        self.moreInfo = self.tr("nothing to report")

    def tr(self, text):
        return app.translate("CalesonSystemCheck", text)
    
    def get_id(self)->str:
        return ''


class CalesonSystemCheck_audioGroup(CalesonSystemCheck):
    def __init__(self):
        CalesonSystemCheck.__init__(self)

        self.name = self.tr("User in audio group")

        user = getoutput("whoami").strip()
        groups = getoutput("groups").strip().split(" ")

        if "audio" in groups:
            self.icon = self.ICON_OK
            self.result = self.tr("Yes")
            self.moreInfo = None

        else:
            fd = open("/etc/group", "r")
            groupRead = fd.read().strip().split("\n")
            fd.close()

            onAudioGroup = False
            for lineRead in groupRead:
                if lineRead.startswith("audio:"):
                    groups = lineRead.split(":")[-1].split(",")
                    if user in groups:
                        onAudioGroup = True
                    break

            if onAudioGroup:
                self.icon = self.ICON_WARN
                self.result = self.tr("Yes, but needs relogin")
                self.moreInfo = None
            else:
                self.icon = self.ICON_ERROR
                self.result = self.tr("No")
                self.moreInfo = None

    def get_id(self)->str:
        return 'audio_group'

    def tr(self, text):
        return app.translate("CalesonSystemCheck_audioGroup", text)


class CalesonSystemCheck_kernel(CalesonSystemCheck):
    def __init__(self):
        CalesonSystemCheck.__init__(self)

        self.name = self.tr("Current kernel")

        uname3 = os.uname()[2]
        uname4 = getoutput("uname -a").strip().split()

        versionInt = []
        versionStr = uname3.split("-",1)[0]
        versionSplit = versionStr.split(".")

        for split in versionSplit:
            if split.isdigit():
                versionInt.append(int(split))
            else:
                versionInt = [0, 0, 0]
                break

        self.result = versionStr + " "

        if "PREEMPT" in uname4 or "PREEMPT_RT" in uname4:
            self.icon = self.ICON_OK
            if "PREEMPT" in uname4:
                self.moreInfo = self.tr("Be sure to properly configure your kernel.")
                self.result  += self.tr("PREEMPT")
            else:
                self.moreInfo = None
            #elif versionInt >= [2, 6, 39]:
                self.result  += self.tr("PREEMPT_RT")

        else:
            if versionInt >= [2, 6, 11]:
                #Linux kernel versions 2.6.11 and up can be patched for PREEMPT_RT and
                #versions 2.6.13 and up can be configured for CONFIG_PREEMPT
                # sources
                # https://wiki.linuxfoundation.org/realtime/preempt_rt_versions
                # https://cateee.net/lkddb/web-lkddb/PREEMPT.html
                self.icon = self.ICON_WARN
                self.moreInfo = self.tr(
                    "RT may be available if compiling this version w/CONFIG_PREEMPT or patching this kernel w/CONFIG_PREEMPT_RT.")

                if "-" not in uname3:
                    if uname3.endswith("-pae"):
                        kernelType = uname3.split("-")[-2].lower()
                        self.result += kernelType.title() + self.tr(" Vanilla (PAE)")
                    else:
                        kernelType = uname3.split("-")[-1].lower()
                        self.result += kernelType.title() + self.tr(" Vanilla")
            else:
                self.icon = self.ICON_ERROR
                self.moreInfo = self.tr("No realtime options for this version of kernel.")

    def get_id(self)->str:
        return 'kernel'

    def tr(self, text):
        return app.translate("CalesonSystemCheck_kernel", text)

calesonSystemChecks = list[CalesonSystemCheck]()

def initSystemChecks():
    if LINUX:
        calesonSystemChecks.append(CalesonSystemCheck_kernel())
        calesonSystemChecks.append(CalesonSystemCheck_audioGroup())


# Additional ALSA Audio options
class ToolBarAlsaAudioDialog(QDialog):
    def __init__(self, parent, customMode):
        QDialog.__init__(self, parent)
        self.ui = ui_caleson_tb_alsa.Ui_Dialog()
        self.ui.setupUi(self)

        self.asoundrcFile = os.path.join(HOME, ".asoundrc")
        self.fCustomMode = customMode

        if customMode:
            asoundrcFd = open(self.asoundrcFile, "r")
            asoundrcRead = asoundrcFd.read().strip()
            asoundrcFd.close()
            self.ui.textBrowser.setPlainText(asoundrcRead)
            self.ui.stackedWidget.setCurrentIndex(0)
            self.ui.buttonBox.setStandardButtons(QDialogButtonBox.Cancel)
        else:
            self.ui.textBrowser.hide()
            self.ui.stackedWidget.setCurrentIndex(1)
            self.adjustSize()

            self.ui.spinBox.setValue(
                GlobalSettings.value("ALSA-Audio/BridgeChannels", 2, type=int))

            if (GlobalSettings.value(
                        "ALSA-Audio/BridgeTool", "alsa_in", type=str)
                    == "zita"):
                self.ui.comboBox.setCurrentIndex(1)
            else:
                self.ui.comboBox.setCurrentIndex(0)

            self.accepted.connect(self.slot_setOptions)

    @pyqtSlot()
    def slot_setOptions(self):
        channels = self.ui.spinBox.value()
        GlobalSettings.setValue("ALSA-Audio/BridgeChannels", channels)
        GlobalSettings.setValue(
            "ALSA-Audio/BridgeTool",
            "zita" if (self.ui.comboBox.currentIndex() == 1) else "alsa_in")

        with open(self.asoundrcFile, "w") as asoundrcFd:
            asoundrcFd.write(
                asoundrc_aloop.replace(
                    "channels 2\n", "channels %i\n" % channels) + "\n")

    def done(self, r):
        QDialog.done(self, r)
        self.close()


# Additional PulseAudio options
class PaBridgeFrame(QFrame):
    def __init__(self, parent, item, edited_signal, bridge_dict: dict):
        QFrame.__init__(self, parent)
        self.ui = ui_pulse_bridge.Ui_Frame()
        self.ui.setupUi(self)
        
        self._parent = parent
        self.item = item
        self._edited_signal = edited_signal
        self.ui.toolButtonRemove.clicked.connect(
            self._remove_clicked)
        
        self.bridge_type = 'source'
        
        if bridge_dict['type'] == 'sink':
            self.bridge_type = 'sink'
            self.ui.toolButtonIcon.setIcon(
                QIcon.fromTheme('audio-volume-medium'))
        
        name = bridge_dict['name']
        if not name:
            if bridge_dict['type'] == 'sink':
                name = "PulseAudio JACK Sink"
            else:
                name = "PulseAudio JACK Source"
        
        self.ui.lineEditName.setText(name)
        self.ui.checkBoxConnect.setChecked(bridge_dict['connected'])
        self.ui.spinBoxChannels.setValue(bridge_dict['channels'])

        self.ui.lineEditName.textEdited.connect(self._edited)
        self.ui.spinBoxChannels.valueChanged.connect(self._edited)
        self.ui.checkBoxConnect.stateChanged.connect(self._edited)
    
    @pyqtSlot()
    def _edited(self, *args):
        self._edited_signal.emit()
    
    @pyqtSlot()
    def _remove_clicked(self):
        self._edited_signal.emit()
        item = self._parent.takeItem(self._parent.row(self.item))
        del item
        del self

    def get_current_dict(self) -> dict:
        bridge_dict = {}
        bridge_dict['type'] = self.bridge_type
        bridge_dict['name'] = self.ui.lineEditName.text()
        bridge_dict['connected'] = self.ui.checkBoxConnect.isChecked()
        bridge_dict['channels'] = self.ui.spinBoxChannels.value()
        return bridge_dict


class PaBridgeItem(QListWidgetItem):
    def __init__(self, parent, edited_signal, bridge_dict: dict):
        QListWidgetItem.__init__(self, parent, QListWidgetItem.UserType + 1)
        self.widget = PaBridgeFrame(parent, self, edited_signal, bridge_dict)
        parent.setItemWidget(self, self.widget)
        self.setSizeHint(QSize(200, 80))
    
    def get_current_dict(self) -> dict:
        return self.widget.get_current_dict()


# Main Window
class CalesonMainW(QMainWindow):
    DBusJackServerStartedCallback = pyqtSignal()
    DBusJackServerStoppedCallback = pyqtSignal()
    DBusJackClientAppearedCallback = pyqtSignal(int, str)
    DBusJackClientDisappearedCallback = pyqtSignal(int)
    DBusA2JBridgeStartedCallback = pyqtSignal()
    DBusA2JBridgeStoppedCallback = pyqtSignal()

    SIGTERM = pyqtSignal()
    SIGUSR1 = pyqtSignal()
    SIGUSR2 = pyqtSignal()
    
    pulse_bridges_edited = pyqtSignal()

    def __init__(self, parent=None):
        QMainWindow.__init__(self, parent)
        self.ui = ui_caleson.Ui_CalesonMainW()
        self.ui.setupUi(self)

        self.settings = QSettings("Caleson", "Caleson")
        self.loadSettings(True)

        self.pix_apply = QIcon(getIcon("dialog-ok-apply", 16)).pixmap(16, 16)
        self.pix_cancel = QIcon(getIcon("dialog-cancel", 16)).pixmap(16, 16)
        self.pix_error = QIcon(getIcon("dialog-error", 16)).pixmap(16, 16)
        self.pix_warning = QIcon(getIcon("dialog-warning", 16)).pixmap(16, 16)

        self.m_lastAlsaIndexType = -2 # invalid

        if jacklib and not jacklib.JACK2:
            self.ui.b_jack_switchmaster.setEnabled(False)

        # -------------------------------------------------------------
        # Set-up GUI (System Information)

        if HAIKU:
            info = get_haiku_information()
        elif LINUX:
            info = get_linux_information()
        elif MACOS:
            info = get_mac_information()
        elif WINDOWS:
            info = get_windows_information()
        else:
            info = ("Unknown", "Unknown")

        self.ui.label_info_os.setText(info[0])
        self.ui.label_info_version.setText(info[1])
        self.ui.label_info_arch.setText(get_architecture())

        # Set-up GUI (System Status)

        self.m_availGovPath = \
            "/sys/devices/system/cpu/cpu0/cpufreq/scaling_available_governors"
        self.m_curGovPath = \
            "/sys/devices/system/cpu/cpu0/cpufreq/scaling_governor"
        self.m_curGovPaths = list[str]()
        self.m_curGovCPUs = list[int]()

        try:
            fBus = dbus.SystemBus(mainloop=gDBus.loop)
            fProxy = fBus.get_object(
                "com.ubuntu.IndicatorCpufreqSelector",
                "/Selector",
                introspect=False)
            haveFreqSelector = True
        except:
            haveFreqSelector = False

        if (haveFreqSelector
                and os.path.exists(self.m_availGovPath)
                and os.path.exists(self.m_curGovPath)):
            self.m_govWatcher = QFileSystemWatcher(self)
            self.m_govWatcher.addPath(self.m_curGovPath)
            self.m_govWatcher.fileChanged.connect(
                self.slot_governorFileChanged)
            QTimer.singleShot(0, self.slot_governorFileChanged)

            availGovFd = open(self.m_availGovPath, "r")
            availGovRead = availGovFd.read().strip()
            availGovFd.close()

            self.m_availGovList = availGovRead.split(" ")
            for availGov in self.m_availGovList:
                self.ui.cb_cpufreq.addItem(availGov)

            for root, dirs, files in os.walk("/sys/devices/system/cpu/"):
                for dir_ in [dir_ for dir_ in dirs if dir_.startswith("cpu")]:
                    if not dir_.replace("cpu", "", 1).isdigit():
                        continue

                    cpuGovPath = os.path.join(
                        root, dir_, "cpufreq", "scaling_governor")

                    if os.path.exists(cpuGovPath):
                        self.m_curGovPaths.append(cpuGovPath)
                        self.m_curGovCPUs.append(
                            int(dir_.replace("cpu", "", 1)))

            self.ui.cb_cpufreq.setCurrentIndex(-1)

        else:
            self.m_govWatcher = None
            self.ui.cb_cpufreq.setEnabled(False)
            self.ui.label_cpufreq.setEnabled(False)

        # -------------------------------------------------------------
        # Set-up GUI (System Checks)

        for check in calesonSystemChecks:
            if check.get_id() == 'kernel':
                self.ui.labelUsedKernel.setText(check.result)
                if check.moreInfo:
                    self.ui.labelUsedKernel.setToolTip(check.moreInfo)
                widgetIcon = self.ui.labelUsedKernelIcon
                
            elif check.get_id() == 'audio_group':
                self.ui.labelUserInAudioGroup.setText(check.result)
                if check.moreInfo:
                    self.ui.labelUserInAudioGroup.setToolTip(check.moreInfo)
                widgetIcon = self.ui.labelUserInAudioGroupIcon

            if check.icon == check.ICON_ERROR:
                widgetIcon.setPixmap(self.pix_error)
            elif check.icon == check.ICON_WARN:
                widgetIcon.setPixmap(self.pix_warning)
            elif check.icon == check.ICON_OK:
                widgetIcon.setPixmap(self.pix_apply)
            else:
                widgetIcon.setPixmap(self.pix_cancel)

        # -------------------------------------------------------------
        # Set-up GUI (JACK Bridges)
        
        self.pulse_bridges_edited.connect(self.slot_PulseAudioBridgeSetEdited)
        self._pulse_check_timer = QTimer()
        self._pulse_check_timer.setInterval(500)
        self._pulse_check_timer.setSingleShot(True)
        self._pulse_check_timer.timeout.connect(
            self.slot_checkPulseAudioBridges)

        if not havePulseAudio:
            #self.toolBox_pulseaudio.setEnabled(False)
            self.ui.label_bridge_pulse.setText(self.tr("PulseAudio is not installed"))
        
        self._pulse_bridge_dicts = pulse2jack_tool.get_existing_modules_in_dicts()
        for bridge_dict in self._pulse_bridge_dicts:
            if bridge_dict['type'] == 'source':
                source_item = PaBridgeItem(self.ui.listWidgetPulseSources,
                                           self.pulse_bridges_edited, bridge_dict)
                self.ui.listWidgetPulseSources.addItem(source_item)
            else:
                sink_item = PaBridgeItem(self.ui.listWidgetPulseSinks,
                                         self.pulse_bridges_edited, bridge_dict)
                self.ui.listWidgetPulseSinks.addItem(sink_item)
        
        # Not available in cxfreeze builds
        if sys.argv[0].endswith("/caleson"):
            # self.ui.groupBox_bridges.setEnabled(False)
            self.ui.cb_jack_autostart.setEnabled(False)

        # -------------------------------------------------------------
        # Set-up GUI (Tweaks)

        self.settings_changed_types = []
        self.ui.frame_tweaks_settings.setVisible(False)

        for i in range(self.ui.tw_tweaks.rowCount()):
            self.ui.tw_tweaks.item(i, 0).setTextAlignment(Qt.AlignCenter)

        self.ui.tw_tweaks.setCurrentCell(0, 0)

        # -------------------------------------------------------------
        # Set-up GUI (Tweaks, Default Applications)

        for desktop in DESKTOP_X_IMAGE:
            if isDesktopFileInstalled(desktop):
                self.ui.cb_app_image.addItem(desktop)

        for desktop in DESKTOP_X_MUSIC:
            if isDesktopFileInstalled(desktop):
                self.ui.cb_app_music.addItem(desktop)

        for desktop in DESKTOP_X_VIDEO:
            if isDesktopFileInstalled(desktop):
                self.ui.cb_app_video.addItem(desktop)

        for desktop in DESKTOP_X_TEXT:
            if isDesktopFileInstalled(desktop):
                self.ui.cb_app_text.addItem(desktop)

        for desktop in DESKTOP_X_BROWSER:
            if isDesktopFileInstalled(desktop):
                self.ui.cb_app_browser.addItem(desktop)

        if self.ui.cb_app_image.count() == 0:
            self.ui.ch_app_image.setEnabled(False)

        if self.ui.cb_app_music.count() == 0:
            self.ui.ch_app_music.setEnabled(False)

        if self.ui.cb_app_video.count() == 0:
            self.ui.ch_app_video.setEnabled(False)

        if self.ui.cb_app_text.count() == 0:
            self.ui.ch_app_text.setEnabled(False)

        if self.ui.cb_app_browser.count() == 0:
            self.ui.ch_app_browser.setEnabled(False)

        mimeappsPath = os.path.join(
            HOME, ".local", "share", "applications", "mimeapps.list")

        if os.path.exists(mimeappsPath):
            fd = open(mimeappsPath, "r")
            mimeappsRead = fd.read()
            fd.close()

            x_image = getXdgProperty(mimeappsRead, "image/bmp")
            x_music = getXdgProperty(mimeappsRead, "audio/wav")
            x_video = getXdgProperty(mimeappsRead, "video/webm")
            x_text = getXdgProperty(mimeappsRead, "text/plain")
            x_browser = getXdgProperty(mimeappsRead, "text/html")

            if x_image and searchAndSetComboBoxValue(self.ui.cb_app_image, x_image):
                self.ui.ch_app_image.setChecked(True)

            if x_music and searchAndSetComboBoxValue(self.ui.cb_app_music, x_music):
                self.ui.ch_app_music.setChecked(True)

            if x_video and searchAndSetComboBoxValue(self.ui.cb_app_video, x_video):
                self.ui.ch_app_video.setChecked(True)

            if x_text and searchAndSetComboBoxValue(self.ui.cb_app_text, x_text):
                self.ui.ch_app_text.setChecked(True)

            if x_browser and searchAndSetComboBoxValue(self.ui.cb_app_browser, x_browser):
                self.ui.ch_app_browser.setChecked(True)

        else: # ~/.local/share/applications/mimeapps.list doesn't exist
            if not os.path.exists(os.path.join(HOME, ".local")):
                os.mkdir(os.path.join(HOME, ".local"))
            elif not os.path.exists(os.path.join(HOME, ".local", "share")):
                os.mkdir(os.path.join(HOME, ".local", "share"))
            elif not os.path.exists(os.path.join(HOME, ".local", "share", "applications")):
                os.mkdir(os.path.join(HOME, ".local", "share", "applications"))

        # -------------------------------------------------------------
        # Set-up GUI (Tweaks, WineASIO)

        if haveWine:
            ins = int(
                getWineAsioKeyValue("Number of inputs", "00000010"), 16)
            outs = int(
                getWineAsioKeyValue("Number of outputs", "00000010"), 16)
            hw = bool(int(
                getWineAsioKeyValue("Connect to hardware", "00000001"), 10))

            autostart = bool(int(
                getWineAsioKeyValue("Autostart server", "00000000"), 10))
            fixed_bsize = bool(int(
                getWineAsioKeyValue("Fixed buffersize", "00000001"), 10))
            prefer_bsize = int(
                getWineAsioKeyValue("Preferred buffersize", "00000400"), 16)

            for bsize in BUFFER_SIZE_LIST:
                self.ui.cb_wineasio_bsizes.addItem(str(bsize))
                if bsize == prefer_bsize:
                    self.ui.cb_wineasio_bsizes.setCurrentIndex(
                        self.ui.cb_wineasio_bsizes.count()-1)

            self.ui.sb_wineasio_ins.setValue(ins)
            self.ui.sb_wineasio_outs.setValue(outs)
            self.ui.cb_wineasio_hw.setChecked(hw)

            self.ui.cb_wineasio_autostart.setChecked(autostart)
            self.ui.cb_wineasio_fixed_bsize.setChecked(fixed_bsize)

        else:
            # No Wine
            self.ui.tw_tweaks.hideRow(2)

        # -------------------------------------------------------------
        # Set-up systray

        self.systray = systray.GlobalSysTray(self, "Caleson", "caleson")

        if haveDBus:
            self.systray.addAction("jack_start", self.tr("Start JACK"))
            self.systray.addAction("jack_stop", self.tr("Stop JACK"))
            self.systray.addAction("jack_configure", self.tr("Configure JACK"))
            self.systray.addSeparator("sep1")

            self.systray.addMenu("alsa", self.tr("ALSA Audio Bridge"))
            self.systray.addMenuAction("alsa", "alsa_start", self.tr("Start"))
            self.systray.addMenuAction("alsa", "alsa_stop", self.tr("Stop"))
            self.systray.addMenu("a2j", self.tr("ALSA MIDI Bridge"))
            self.systray.addMenuAction("a2j", "a2j_start", self.tr("Start"))
            self.systray.addMenuAction("a2j", "a2j_stop", self.tr("Stop"))
            self.systray.addMenu("pulse", self.tr("PulseAudio Bridge"))
            self.systray.addMenuAction("pulse", "pulse_start", self.tr("Start"))
            self.systray.addMenuAction("pulse", "pulse_stop", self.tr("Stop"))
            self.systray.addMenuAction("pulse", "pulse_channels", self.tr("Channels"))

            self.systray.setActionIcon("jack_start", "media-playback-start")
            self.systray.setActionIcon("jack_stop", "media-playback-stop")
            self.systray.setActionIcon("jack_configure", "configure")
            self.systray.setActionIcon("alsa_start", "media-playback-start")
            self.systray.setActionIcon("alsa_stop", "media-playback-stop")
            self.systray.setActionIcon("a2j_start", "media-playback-start")
            self.systray.setActionIcon("a2j_stop", "media-playback-stop")
            self.systray.setActionIcon("pulse_start", "media-playback-start")
            self.systray.setActionIcon("pulse_stop", "media-playback-stop")
            self.systray.setActionIcon("pulse_channels", "audio-card")

            self.systray.connect("jack_start", self.slot_JackServerStart)
            self.systray.connect("jack_stop", self.slot_JackServerStop)
            self.systray.connect("jack_configure", self.slot_JackServerConfigure)
            self.systray.connect("alsa_start", self.slot_AlsaBridgeStart)
            self.systray.connect("alsa_stop", self.slot_AlsaBridgeStop)
            self.systray.connect("a2j_start", self.slot_A2JBridgeStart)
            self.systray.connect("a2j_stop", self.slot_A2JBridgeStop)
            self.systray.connect("pulse_start", self.slot_PulseAudioBridgeStart)
            self.systray.connect("pulse_stop", self.slot_PulseAudioBridgeStop)

        self.systray.addMenu("tools", self.tr("Tools"))
        self.systray.addMenuAction("tools", "app_catarina", "Catarina")
        self.systray.addMenuAction("tools", "app_catia", "Catia")
        self.systray.addMenuSeparator("tools", "tools_sep")
        self.systray.addMenuAction("tools", "app_logs", self.tr("Logs"))
        self.systray.addMenuAction("tools", "app_meter_in", self.tr("Meter (Inputs)"))
        self.systray.addMenuAction("tools", "app_meter_out", self.tr("Meter (Output)"))
        self.systray.addMenuAction("tools", "app_render", self.tr("Render"))
        self.systray.addMenuAction("tools", "app_xy-controller", self.tr("XY-Controller"))
        self.systray.addSeparator("sep2")

        self.systray.connect("app_catarina", self.func_start_catarina)
        self.systray.connect("app_catia", self.func_start_catia)
        self.systray.connect("app_logs", self.func_start_logs)
        self.systray.connect("app_meter_in", self.func_start_jackmeter_in)
        self.systray.connect("app_meter_out", self.func_start_jackmeter)
        self.systray.connect("app_render",  self.func_start_render)
        self.systray.connect("app_xy-controller", self.func_start_xycontroller)

        self.systray.setToolTip("Caleson")
        self.systray.show()

        # -------------------------------------------------------------
        # Set-up connections

        self.ui.b_jack_start.clicked.connect(self.slot_JackServerStart)
        self.ui.b_jack_stop.clicked.connect(self.slot_JackServerStop)
        self.ui.b_jack_restart.clicked.connect(self.slot_JackServerForceRestart)
        self.ui.b_jack_configure.clicked.connect(self.slot_JackServerConfigure)
        self.ui.b_jack_switchmaster.clicked.connect(self.slot_JackServerSwitchMaster)

        self.ui.b_alsa_start.clicked.connect(self.slot_AlsaBridgeStart)
        self.ui.b_alsa_stop.clicked.connect(self.slot_AlsaBridgeStop)
        self.ui.cb_alsa_type.currentIndexChanged[int].connect(self.slot_AlsaBridgeChanged)
        self.ui.tb_alsa_options.clicked.connect(self.slot_AlsaAudioBridgeOptions)

        self.ui.b_a2j_start.clicked.connect(self.slot_A2JBridgeStart)
        self.ui.b_a2j_stop.clicked.connect(self.slot_A2JBridgeStop)
        self.ui.b_pulse_apply.clicked.connect(self.slot_PulseAudioBridgeApply)
        self.ui.b_pulse_start.clicked.connect(self.slot_PulseAudioBridgeStart)
        self.ui.b_pulse_stop.clicked.connect(self.slot_PulseAudioBridgeStop)
        self.ui.pushButtonAddPulseSource.clicked.connect(self.slot_PulseAudioBridgeAddSource)
        self.ui.pushButtonAddPulseSink.clicked.connect(self.slot_PulseAudioBridgeAddSink)

        self.ui.pic_catia.clicked.connect(self.func_start_catia)
        self.ui.pic_logs.clicked.connect(self.func_start_logs)
        self.ui.pic_render.clicked.connect(self.func_start_render)

        self.ui.b_tweaks_apply_now.clicked.connect(self.slot_tweaksApply)

        self.ui.ch_app_image.clicked.connect(self.slot_tweaksSettingsChanged_apps)
        self.ui.cb_app_image.highlighted.connect(self.slot_tweakAppImageHighlighted)
        #self.ui.cb_app_image.currentIndexChanged[int].connect(self.slot_tweakAppImageChanged)
        self.ui.ch_app_music.clicked.connect(self.slot_tweaksSettingsChanged_apps)
        self.ui.cb_app_music.highlighted.connect(self.slot_tweakAppMusicHighlighted)
        self.ui.cb_app_music.currentIndexChanged[int].connect(self.slot_tweakAppMusicChanged)
        self.ui.ch_app_video.clicked.connect(self.slot_tweaksSettingsChanged_apps)
        self.ui.cb_app_video.highlighted.connect(self.slot_tweakAppVideoHighlighted)
        self.ui.cb_app_video.currentIndexChanged[int].connect(self.slot_tweakAppVideoChanged)
        self.ui.ch_app_text.clicked.connect(self.slot_tweaksSettingsChanged_apps)
        self.ui.cb_app_text.highlighted.connect(self.slot_tweakAppTextHighlighted)
        self.ui.cb_app_text.currentIndexChanged[int].connect(self.slot_tweakAppTextChanged)
        self.ui.ch_app_browser.clicked.connect(self.slot_tweaksSettingsChanged_apps)
        self.ui.cb_app_browser.highlighted.connect(self.slot_tweakAppBrowserHighlighted)
        self.ui.cb_app_browser.currentIndexChanged[int].connect(self.slot_tweakAppBrowserChanged)

        self.ui.sb_wineasio_ins.valueChanged.connect(self.slot_tweaksSettingsChanged_wineasio)
        self.ui.sb_wineasio_outs.valueChanged.connect(self.slot_tweaksSettingsChanged_wineasio)
        self.ui.cb_wineasio_hw.clicked.connect(self.slot_tweaksSettingsChanged_wineasio)
        self.ui.cb_wineasio_autostart.clicked.connect(self.slot_tweaksSettingsChanged_wineasio)
        self.ui.cb_wineasio_fixed_bsize.clicked.connect(self.slot_tweaksSettingsChanged_wineasio)
        self.ui.cb_wineasio_bsizes.currentIndexChanged[int].connect(self.slot_tweaksSettingsChanged_wineasio)

        # org.jackaudio.JackControl
        self.DBusJackServerStartedCallback.connect(self.slot_DBusJackServerStartedCallback)
        self.DBusJackServerStoppedCallback.connect(self.slot_DBusJackServerStoppedCallback)

        # org.jackaudio.JackPatchbay
        self.DBusJackClientAppearedCallback.connect(self.slot_DBusJackClientAppearedCallback)
        self.DBusJackClientDisappearedCallback.connect(self.slot_DBusJackClientDisappearedCallback)

        # org.gna.home.a2jmidid.control
        self.DBusA2JBridgeStartedCallback.connect(self.slot_DBusA2JBridgeStartedCallback)
        self.DBusA2JBridgeStoppedCallback.connect(self.slot_DBusA2JBridgeStoppedCallback)
        self.ui.cb_a2j_autoexport.stateChanged[int].connect(self.slot_A2JBridgeExportHW)
        self.ui.cb_a2j_unique_port_names.stateChanged[int].connect(self.slot_A2JBridgeUniquePortNames)

        # -------------------------------------------------------------

        self.m_last_dsp_load = None
        self.m_last_xruns = None
        self.m_last_buffer_size = None

        self.m_timer500 = None
        self.m_timer2000 = self.startTimer(2000)

        self.DBusReconnect()

        if haveDBus:
            gDBus.bus.add_signal_receiver(self.DBusSignalReceiver, destination_keyword='dest', path_keyword='path',
                member_keyword='member', interface_keyword='interface', sender_keyword='sender', )

    def DBusReconnect(self):
        if haveDBus:
            try:
                gDBus.jack = gDBus.bus.get_object("org.jackaudio.service", "/org/jackaudio/Controller")
                gDBus.patchbay = dbus.Interface(gDBus.jack, "org.jackaudio.JackPatchbay")
                jacksettings.initBus(gDBus.bus)
            except:
                gDBus.jack = None
                gDBus.patchbay = None

            try:
                gDBus.a2j = dbus.Interface(
                    gDBus.bus.get_object("org.gna.home.a2jmidid", "/"),
                    "org.gna.home.a2jmidid.control")
            except:
                gDBus.a2j = None

        if gDBus.jack:
            if gDBus.jack.IsStarted():
                # Check for pulseaudio in jack graph
                try:
                    version, groups, conns = gDBus.patchbay.GetGraph(0)
                except:
                    version, groups, conns = (list(), list(), list())

                for group_id, group_name, ports in groups:
                    if group_name == "alsa2jack":
                        global jackClientIdALSA
                        jackClientIdALSA = group_id

                self.jackStarted()

            else:
                self.jackStopped()
                self.ui.label_jack_realtime.setText(self.tr("Yes") if jacksettings.isRealtime() else self.tr("No"))
        else:
            self.jackStopped()
            self.ui.label_jack_status.setText(self.tr("Unavailable"))
            self.ui.label_jack_status_ico.setPixmap(self.pix_error)
            self.ui.label_jack_realtime.setText(self.tr("Unknown"))
            self.ui.label_jack_realtime_ico.setPixmap(self.pix_error)
            self.ui.groupBox_jack.setEnabled(False)
            self.ui.groupBox_jack.setTitle(self.tr("-- jackdbus is not available --"))
            self.ui.b_jack_start.setEnabled(False)
            self.ui.b_jack_stop.setEnabled(False)
            self.ui.b_jack_restart.setEnabled(False)
            self.ui.b_jack_configure.setEnabled(False)
            self.ui.b_jack_switchmaster.setEnabled(False)
            # self.ui.groupBox_bridges.setEnabled(False)

        if gDBus.a2j:
            try:
                started = gDBus.a2j.is_started()
            except:
                started = False

            if started:
                self.a2jStarted()
            else:
                self.a2jStopped()
        else:
            # self.toolBox_alsamidi.setEnabled(False)
            self.ui.cb_a2j_autostart.setChecked(False)
            self.ui.cb_a2j_autoexport.setChecked(False)
            self.ui.cb_a2j_unique_port_names.setChecked(False)
            self.ui.label_bridge_a2j.setText(self.tr("ALSA MIDI Bridge is not installed"))
            self.settings.setValue("A2J/AutoStart", False)

        self.updateSystrayTooltip()

    def DBusSignalReceiver(self, *args, **kwds):
        if kwds['interface'] == "org.freedesktop.DBus" and kwds['path'] == "/org/freedesktop/DBus" and kwds['member'] == "NameOwnerChanged":
            appInterface, appId, newId = args

            if not newId:
                # Something crashed
                if appInterface == "org.jackaudio.service":
                    QTimer.singleShot(0, self.slot_handleCrash_jack)
                elif appInterface == "org.gna.home.a2jmidid":
                    QTimer.singleShot(0, self.slot_handleCrash_a2j)

        elif kwds['interface'] == "org.jackaudio.JackControl":
            if DEBUG: print("org.jackaudio.JackControl", kwds['member'])
            if kwds['member'] == "ServerStarted":
                self.DBusJackServerStartedCallback.emit()
            elif kwds['member'] == "ServerStopped":
                self.DBusJackServerStoppedCallback.emit()

        elif kwds['interface'] == "org.jackaudio.JackPatchbay":
            if gDBus.patchbay and kwds['path'] == gDBus.patchbay.object_path:
                if DEBUG: print("org.jackaudio.JackPatchbay,", kwds['member'])
                if kwds['member'] == "ClientAppeared":
                    self.DBusJackClientAppearedCallback.emit(args[iJackClientId], args[iJackClientName])
                elif kwds['member'] == "ClientDisappeared":
                    self.DBusJackClientDisappearedCallback.emit(args[iJackClientId])

        elif kwds['interface'] == "org.gna.home.a2jmidid.control":
            if DEBUG: print("org.gna.home.a2jmidid.control", kwds['member'])
            if kwds['member'] == "bridge_started":
                self.DBusA2JBridgeStartedCallback.emit()
            elif kwds['member'] == "bridge_stopped":
                self.DBusA2JBridgeStoppedCallback.emit()

    def jackStarted(self):
        self.m_last_dsp_load = gDBus.jack.GetLoad()
        self.m_last_xruns = int(gDBus.jack.GetXruns())
        self.m_last_buffer_size = gDBus.jack.GetBufferSize()

        self.ui.b_jack_start.setEnabled(False)
        self.ui.b_jack_stop.setEnabled(True)
        self.ui.b_jack_switchmaster.setEnabled(True)
        self.systray.setActionEnabled("jack_start", False)
        self.systray.setActionEnabled("jack_stop", True)

        self.ui.label_jack_status.setText(self.tr("Started"))
        self.ui.label_jack_status_ico.setPixmap(self.pix_apply)

        if gDBus.jack.IsRealtime():
            self.ui.label_jack_realtime.setText(self.tr("Yes"))
            self.ui.label_jack_realtime_ico.setPixmap(self.pix_apply)
        else:
            self.ui.label_jack_realtime.setText(self.tr("No"))
            self.ui.label_jack_realtime_ico.setPixmap(self.pix_cancel)

        self.ui.label_jack_dsp.setText("%.2f%%" % self.m_last_dsp_load)
        self.ui.label_jack_xruns.setText(str(self.m_last_xruns))
        self.ui.label_jack_bfsize.setText(self.tr("%i samples") % self.m_last_buffer_size)
        self.ui.label_jack_srate.setText("%i Hz" % gDBus.jack.GetSampleRate())
        self.ui.label_jack_latency.setText("%.1f ms" % gDBus.jack.GetLatency())

        self.m_timer500 = self.startTimer(500)
        self.m_timer2000 = self.startTimer(2000)

        if gDBus.a2j and not gDBus.a2j.is_started():
            portsExported = bool(gDBus.a2j.get_hw_export())
            unique_port_names = not bool(gDBus.a2j.get_disable_port_uniqueness())
            if GlobalSettings.value("A2J/AutoStart", True, type=bool):
                if not portsExported and GlobalSettings.value("A2J/AutoExport", True, type=bool):
                    gDBus.a2j.set_hw_export(True)
                    # portsExported = True
                    
                if not unique_port_names:
                    gDBus.a2j.set_disable_port_uniqueness(True)

                gDBus.a2j.start()
            else:
                self.ui.b_a2j_start.setEnabled(True)
                self.systray.setActionEnabled("a2j_start", True)

        self.checkAlsaAudio()
        self.checkPulseAudio()

    def jackStopped(self):
        if self.m_timer500:
            self.killTimer(self.m_timer500)
            self.m_timer500 = None
        if self.m_timer2000:
            self.killTimer(self.m_timer2000)
            self.m_timer2000 = None

        self.m_last_dsp_load = None
        self.m_last_xruns = None
        self.m_last_buffer_size = None

        self.ui.b_jack_start.setEnabled(True)
        self.ui.b_jack_stop.setEnabled(False)
        self.ui.b_jack_switchmaster.setEnabled(False)

        if haveDBus:
            self.systray.setActionEnabled("jack_start", True)
            self.systray.setActionEnabled("jack_stop", False)

        self.ui.label_jack_status.setText(self.tr("Stopped"))
        self.ui.label_jack_status_ico.setPixmap(self.pix_cancel)

        self.ui.label_jack_dsp.setText("---")
        self.ui.label_jack_xruns.setText("---")
        self.ui.label_jack_bfsize.setText("---")
        self.ui.label_jack_srate.setText("---")
        self.ui.label_jack_latency.setText("---")

        if gDBus.a2j:
            self.ui.b_a2j_start.setEnabled(False)
            self.systray.setActionEnabled("a2j_start", False)

        global jackClientIdALSA
        jackClientIdALSA = -1

        pA_bridge_values.clientIdCapture = -1
        pA_bridge_values.clientIdPlayback = -1

        if haveDBus:
            self.checkAlsaAudio()
            self.checkPulseAudio()

    def a2jStarted(self):
        self.ui.b_a2j_start.setEnabled(False)
        self.ui.b_a2j_stop.setEnabled(True)
        self.systray.setActionEnabled("a2j_start", False)
        self.systray.setActionEnabled("a2j_stop", True)
        if bool(gDBus.a2j.get_hw_export()):
            self.ui.label_bridge_a2j.setText(
                self.tr("ALSA MIDI Bridge is running, ports are exported"))
        else :
            self.ui.label_bridge_a2j.setText(
                self.tr("ALSA MIDI Bridge is running"))

    def a2jStopped(self):
        jackRunning = bool(gDBus.jack and gDBus.jack.IsStarted())
        self.ui.b_a2j_start.setEnabled(jackRunning)
        self.ui.b_a2j_stop.setEnabled(False)
        self.systray.setActionEnabled("a2j_start", jackRunning)
        self.systray.setActionEnabled("a2j_stop", False)
        self.ui.label_bridge_a2j.setText(self.tr("ALSA MIDI Bridge is stopped"))

    def checkAlsaAudio(self):
        asoundrcFile = os.path.join(HOME, ".asoundrc")

        if not os.path.exists(asoundrcFile):
            self.ui.b_alsa_start.setEnabled(False)
            self.ui.b_alsa_stop.setEnabled(False)
            self.ui.cb_alsa_type.setCurrentIndex(iAlsaFileNone)
            self.ui.tb_alsa_options.setEnabled(False)
            self.ui.label_bridge_alsa.setText(self.tr("No bridge in use"))
            self.m_lastAlsaIndexType = -1 # null
            return

        asoundrcFd = open(asoundrcFile, "r")
        asoundrcRead = asoundrcFd.read().strip()
        asoundrcFd.close()

        if asoundrcRead.startswith(asoundrc_aloop_check):
            if isAlsaAudioBridged():
                self.ui.b_alsa_start.setEnabled(False)
                self.ui.b_alsa_stop.setEnabled(True)
                self.systray.setActionEnabled("alsa_start", False)
                self.systray.setActionEnabled("alsa_stop", True)
                self.ui.label_bridge_alsa.setText(
                    self.tr("Using Caleson snd-aloop daemon, started"))
            else:
                try:
                    jackRunning = bool(gDBus.jack and gDBus.jack.IsStarted())
                except:
                    jackRunning = False
                self.ui.b_alsa_start.setEnabled(jackRunning)
                self.ui.b_alsa_stop.setEnabled(False)
                self.systray.setActionEnabled("alsa_start", jackRunning)
                self.systray.setActionEnabled("alsa_stop", False)
                self.ui.label_bridge_alsa.setText(
                    self.tr("Using Caleson snd-aloop daemon, stopped"))

            self.ui.cb_alsa_type.setCurrentIndex(iAlsaFileLoop)
            self.ui.tb_alsa_options.setEnabled(True)

        elif asoundrcRead == asoundrc_jack:
            self.ui.b_alsa_start.setEnabled(False)
            self.ui.b_alsa_stop.setEnabled(False)
            self.systray.setActionEnabled("alsa_start", False)
            self.systray.setActionEnabled("alsa_stop", False)
            self.ui.cb_alsa_type.setCurrentIndex(iAlsaFileJACK)
            self.ui.tb_alsa_options.setEnabled(False)
            self.ui.label_bridge_alsa.setText(
                self.tr("Using JACK plugin bridge (Always on)"))

        elif asoundrcRead == asoundrc_pulse:
            self.ui.b_alsa_start.setEnabled(False)
            self.ui.b_alsa_stop.setEnabled(False)
            self.systray.setActionEnabled("alsa_start", False)
            self.systray.setActionEnabled("alsa_stop", False)
            self.ui.cb_alsa_type.setCurrentIndex(iAlsaFilePulse)
            self.ui.tb_alsa_options.setEnabled(False)
            self.ui.label_bridge_alsa.setText(
                self.tr("Using PulseAudio plugin bridge (Always on)"))

        else:
            self.ui.b_alsa_start.setEnabled(False)
            self.ui.b_alsa_stop.setEnabled(False)
            self.systray.setActionEnabled("alsa_start", False)
            self.systray.setActionEnabled("alsa_stop", False)
            self.ui.cb_alsa_type.addItem(self.tr("Custom"))
            self.ui.cb_alsa_type.setCurrentIndex(iAlsaFileMax)
            self.ui.tb_alsa_options.setEnabled(True)
            self.ui.label_bridge_alsa.setText(
                self.tr("Using custom asoundrc, not managed by Caleson"))

        self.m_lastAlsaIndexType = self.ui.cb_alsa_type.currentIndex()

    def checkPulseAudio(self):
        if not havePulseAudio:
            self.systray.setActionEnabled("pulse_start", False)
            self.systray.setActionEnabled("pulse_stop", False)
            return

        mess = ""

        if isPulseAudioStarted():
            if self._pulse_bridge_dicts:
                self.ui.b_pulse_start.setEnabled(False)
                self.ui.b_pulse_stop.setEnabled(True)
                self.systray.setActionEnabled("pulse_start", False)
                self.systray.setActionEnabled("pulse_stop", True)
                mess = self.tr("PulseAudio is started and bridged to JACK")
            else:
                jackRunning = bool(gDBus.jack and gDBus.jack.IsStarted())
                self.ui.b_pulse_start.setEnabled(jackRunning)
                self.ui.b_pulse_stop.setEnabled(False)
                self.systray.setActionEnabled("pulse_start", jackRunning)
                self.systray.setActionEnabled("pulse_stop", False)
                if jackRunning:
                    mess = self.tr("PulseAudio is started but not bridged")
                else:
                    mess = self.tr("PulseAudio is started but JACK is stopped")
        else:
            jackRunning = bool(gDBus.jack and gDBus.jack.IsStarted())
            self.ui.b_pulse_start.setEnabled(jackRunning)
            self.ui.b_pulse_stop.setEnabled(False)
            self.systray.setActionEnabled("pulse_start", jackRunning)
            self.systray.setActionEnabled("pulse_stop", False)
            if jackRunning:
                mess = self.tr("PulseAudio is not started")
            else:
                mess = self.tr("PulseAudio is not started, nor is JACK")

        self.ui.label_bridge_pulse.setText(mess)

    def setAppDetails(self, desktop):
        appContents = getDesktopFileContents(desktop)
        name = getXdgProperty(appContents, "Name")
        icon = getXdgProperty(appContents, "Icon")
        comment = getXdgProperty(appContents, "Comment")

        if not name:
            name = self.ui.cb_app_image.currentText().replace(".desktop","").title()
        if not icon:
            icon = ""
        if not comment:
           comment = ""

        self.ui.ico_app.setPixmap(getIcon(icon, 48).pixmap(48, 48))
        self.ui.label_app_name.setText(name)
        self.ui.label_app_comment.setText(comment)

    def updateSystrayTooltip(self):
        systrayText = "Caleson\n"
        systrayText += "%s: %s\n" % (self.tr("JACK Status"), self.ui.label_jack_status.text())
        systrayText += "%s: %s\n" % (self.tr("Realtime"), self.ui.label_jack_realtime.text())
        systrayText += "%s: %s\n" % (self.tr("DSP Load"), self.ui.label_jack_dsp.text())
        systrayText += "%s: %s\n" % (self.tr("Xruns"), self.ui.label_jack_xruns.text())
        systrayText += "%s: %s\n" % (self.tr("Buffer Size"), self.ui.label_jack_bfsize.text())
        systrayText += "%s: %s\n" % (self.tr("Sample Rate"), self.ui.label_jack_srate.text())
        systrayText += "%s: %s" % (self.tr("Block Latency"), self.ui.label_jack_latency.text())

        self.systray.setToolTip(systrayText)

    @pyqtSlot()
    def func_start_catarina(self):
        self.func_start_tool("catarina")

    @pyqtSlot()
    def func_start_catia(self):
        self.func_start_tool("catia")

    @pyqtSlot()
    def func_start_logs(self):
        self.func_start_tool("caleson-logs")

    @pyqtSlot()
    def func_start_jackmeter(self):
        self.func_start_tool("caleson-jackmeter")

    @pyqtSlot()
    def func_start_jackmeter_in(self):
        self.func_start_tool("caleson-jackmeter -in")

    @pyqtSlot()
    def func_start_render(self):
        self.func_start_tool("caleson-render")

    @pyqtSlot()
    def func_start_xycontroller(self):
        self.func_start_tool("caleson-xycontroller")

    def func_start_tool(self, tool):
        if sys.argv[0].endswith(".py"):
            if tool == "caleson-logs":
                tool = "logs"
            elif tool == "caleson-render":
                tool = "render"

            stool = tool.split(" ", 1)[0]

            if stool in ("caleson-jackmeter", "caleson-xycontroller"):
                python = ""
                localPath = os.path.join(sys.path[0], "..", "c++", stool.replace("caleson-", ""))

                if os.path.exists(os.path.join(localPath, stool)):
                    base = localPath + os.sep
                else:
                    base = ""

            else:
                python = sys.executable
                tool  += ".py"
                base = sys.argv[0].rsplit("caleson.py", 1)[0]

                if python:
                    python += " "

            cmd = "%s%s%s &" % (python, base, tool)

            print(cmd)
            os.system(cmd)

        elif sys.argv[0].endswith("/caleson"):
            base = sys.argv[0].rsplit("/caleson", 1)[0]
            os.system("%s/%s &" % (base, tool))

        else:
            os.system("%s &" % tool)

    def func_settings_changed(self, stype):
        if stype not in self.settings_changed_types:
            self.settings_changed_types.append(stype)
        self.ui.frame_tweaks_settings.setVisible(True)

    @pyqtSlot()
    def slot_DBusJackServerStartedCallback(self):
        self.jackStarted()

    @pyqtSlot()
    def slot_DBusJackServerStoppedCallback(self):
        self.jackStopped()

    @pyqtSlot(int, str)
    def slot_DBusJackClientAppearedCallback(self, group_id, group_name):
        if group_name == "alsa2jack":
            global jackClientIdALSA
            jackClientIdALSA = group_id
            self.checkAlsaAudio()

        self._pulse_check_timer.start()

    @pyqtSlot(int)
    def slot_DBusJackClientDisappearedCallback(self, group_id):
        global jackClientIdALSA
        if group_id == jackClientIdALSA:
            jackClientIdALSA = -1
            self.checkAlsaAudio()
        
        self._pulse_check_timer.start()

    @pyqtSlot()
    def slot_DBusA2JBridgeStartedCallback(self):
        self.a2jStarted()

    @pyqtSlot()
    def slot_DBusA2JBridgeStoppedCallback(self):
        self.a2jStopped()

    @pyqtSlot()
    def slot_checkPulseAudioBridges(self):
        self._pulse_bridge_dicts = pulse2jack_tool.get_existing_modules_in_dicts()
        self.ui.listWidgetPulseSources.clear()
        self.ui.listWidgetPulseSinks.clear()
        
        for b_dict in self._pulse_bridge_dicts:
            if b_dict['type'] == 'sink':
                sink_item = PaBridgeItem(
                    self.ui.listWidgetPulseSinks, self.pulse_bridges_edited, b_dict)
                self.ui.listWidgetPulseSinks.addItem(sink_item)
            else:
                source_item = PaBridgeItem(
                    self.ui.listWidgetPulseSources, self.pulse_bridges_edited, b_dict)
                self.ui.listWidgetPulseSources.addItem(source_item)
        
        self.ui.b_pulse_apply.setEnabled(False)
        self.checkPulseAudio()

    @pyqtSlot()
    def slot_JackServerStart(self):
        self.saveSettings()
        try:
            gDBus.jack.StartServer()
        except:
            QMessageBox.warning(
                self,
                self.tr("Warning"),
                self.tr("Failed to start JACK, please check the logs for more information."))

    @pyqtSlot()
    def slot_JackServerStop(self):
        if gDBus.a2j and bool(gDBus.a2j.is_started()):
            gDBus.a2j.stop()
        try:
            gDBus.jack.StopServer()
        except:
            QMessageBox.warning(
                self,
                self.tr("Warning"),
                self.tr("Failed to stop JACK, please check the logs for more information."))

    @pyqtSlot()
    def slot_JackServerForceRestart(self):
        if gDBus.jack.IsStarted():
            ask = CustomMessageBox(
                self, QMessageBox.Warning, self.tr("Warning"),
                self.tr("This will force kill all JACK applications!<br>Make sure to save your projects before continue."),
                self.tr("Are you sure you want to force the restart of JACK?"))

            if ask != QMessageBox.Yes:
                return

        if self.m_timer500:
            self.killTimer(self.m_timer500)
            self.m_timer500 = None
        
        if self.m_timer2000:
            self.killTimer(self.m_timer2000)
            self.m_timer2000 = None

        self.saveSettings()
        force_restart.ForceWaitDialog(self).exec_()

    @pyqtSlot()
    def slot_JackServerConfigure(self):
        jacksettingsW = jacksettings.JackSettingsW(self)
        jacksettingsW.exec_()
        del jacksettingsW

    @pyqtSlot()
    def slot_JackServerSwitchMaster(self):
        try:
            gDBus.jack.SwitchMaster()
        except:
            QMessageBox.warning(
                self,
                self.tr("Warning"),
                self.tr("Failed to switch JACK master, please check the logs for more information."))
            return

        self.jackStarted()

    @pyqtSlot()
    def slot_JackClearXruns(self):
        if gDBus.jack:
            gDBus.jack.ResetXruns()

    @pyqtSlot()
    def slot_AlsaBridgeStart(self):
        self.slot_AlsaBridgeStop()
        startAlsaAudioLoopBridge()

    @pyqtSlot()
    def slot_AlsaBridgeStop(self):
        checkFile = "/tmp/.caleson-aloop-daemon.x"
        if os.path.exists(checkFile):
            os.remove(checkFile)

    @pyqtSlot(int)
    def slot_AlsaBridgeChanged(self, index):
        if self.m_lastAlsaIndexType == -2 or self.m_lastAlsaIndexType == index:
            return

        if self.m_lastAlsaIndexType == iAlsaFileMax:
            ask = CustomMessageBox(
                self, 
                QMessageBox.Warning, self.tr("Warning"),
                self.tr(""
                        "You're using a custom ~/.asoundrc file not managed by Caleson.<br/>"
                        "By choosing to use a Caleson ALSA-Audio bridge, <b>the file will be replaced</b>."
                        ""),
                self.tr("Are you sure you want to do this?"))

            if ask == QMessageBox.Yes:
                self.ui.cb_alsa_type.blockSignals(True)
                self.ui.cb_alsa_type.removeItem(iAlsaFileMax)
                self.ui.cb_alsa_type.setCurrentIndex(index)
                self.ui.cb_alsa_type.blockSignals(False)
            else:
                self.ui.cb_alsa_type.blockSignals(True)
                self.ui.cb_alsa_type.setCurrentIndex(iAlsaFileMax)
                self.ui.cb_alsa_type.blockSignals(False)
                return

        asoundrcFile = os.path.join(HOME, ".asoundrc")

        if index == iAlsaFileNone:
            os.remove(asoundrcFile)

        elif index == iAlsaFileLoop:
            asoundrcFd = open(asoundrcFile, "w")
            asoundrcFd.write(asoundrc_aloop+"\n")
            asoundrcFd.close()

        elif index == iAlsaFileJACK:
            asoundrcFd = open(asoundrcFile, "w")
            asoundrcFd.write(asoundrc_jack+"\n")
            asoundrcFd.close()

        elif index == iAlsaFilePulse:
            asoundrcFd = open(asoundrcFile, "w")
            asoundrcFd.write(asoundrc_pulse+"\n")
            asoundrcFd.close()

        else:
            print(self.tr("Caleson::AlsaBridgeChanged(%i) - invalid index") % index)

        self.checkAlsaAudio()

    @pyqtSlot()
    def slot_AlsaAudioBridgeOptions(self):
        ToolBarAlsaAudioDialog(
            self,
            (self.ui.cb_alsa_type.currentIndex() != iAlsaFileLoop)).exec_()

    @pyqtSlot()
    def slot_A2JBridgeStart(self):
        gDBus.a2j.start()

    @pyqtSlot()
    def slot_A2JBridgeStop(self):
        gDBus.a2j.stop()

    @pyqtSlot(int)
    def slot_A2JBridgeExportHW(self, state):
        a2jWasStarted = bool(gDBus.a2j.is_started())

        if a2jWasStarted:
            gDBus.a2j.stop()

        gDBus.a2j.set_hw_export(bool(state))

        if a2jWasStarted:
            gDBus.a2j.start()

    @pyqtSlot(int)
    def slot_A2JBridgeUniquePortNames(self, state: int):
        a2j_was_started = bool(gDBus.a2j.is_started())
        
        if a2j_was_started:
            gDBus.a2j.stop()
            
        gDBus.a2j.set_disable_port_uniqueness(not bool(state))
        
        if a2j_was_started:
            gDBus.a2j.start()

    @pyqtSlot()
    def slot_PulseAudioBridgeApply(self):
        bridge_dicts = []
        for i in range(self.ui.listWidgetPulseSources.count()):
            item = self.ui.listWidgetPulseSources.item(i)
            bridge_dicts.append(item.get_current_dict())
        for i in range(self.ui.listWidgetPulseSinks.count()):
            item = self.ui.listWidgetPulseSinks.item(i)
            bridge_dicts.append(item.get_current_dict())
        
        GlobalSettings.setValue('PulseAudio_bridges', bridge_dicts)
        
        pulse2jack_tool.replace_hotly(bridge_dicts)
        
    @pyqtSlot()
    def slot_PulseAudioBridgeStart(self):
        bridge_dicts = GlobalSettings.value('PulseAudio_bridges', type=list)
        if not bridge_dicts:
            bridge_dicts = [
                {"type": "source",
                "name": "PulseAudio JACK Source",
                "channels": 2,
                "connected": True},
                {"type": "sink",
                "name": "PulseAudio JACK Sink",
                "channels": 2,
                "connected": True}]

        pulse2jack_tool.replace_hotly(bridge_dicts)
    
    @pyqtSlot()
    def slot_PulseAudioBridgeStop(self):
        os.system("pulseaudio -k")

    @pyqtSlot()
    def slot_PulseAudioBridgeSetEdited(self):
        self.ui.b_pulse_apply.setEnabled(True)

    @pyqtSlot()
    def slot_PulseAudioBridgeAddSource(self):
        bridge_name = "PulseAudio JACK Source"
        i = 2
        
        while True:
            for j in range(self.ui.listWidgetPulseSources.count()):
                item = self.ui.listWidgetPulseSources.item(j)
                if item.get_current_dict()['name'] == bridge_name:
                    break
            else:
                break
            
            if bridge_name.endswith(')'):
                bridge_name = "%s%i)" % (bridge_name[:-2], i)
            else:
                bridge_name += ' (%i)' % i
            i += 1
        
        self.ui.listWidgetPulseSources.addItem(
            PaBridgeItem(
                self.ui.listWidgetPulseSources,
                self.pulse_bridges_edited,
                {"type": "source",
                 "name": bridge_name,
                 "channels": 2,
                 "connected": True}))

        self.pulse_bridges_edited.emit()
                
    @pyqtSlot()
    def slot_PulseAudioBridgeAddSink(self):
        bridge_name = "PulseAudio JACK Sink"
        i = 2
        
        while True:
            for j in range(self.ui.listWidgetPulseSinks.count()):
                item = self.ui.listWidgetPulseSinks.item(j)
                if item.get_current_dict()['name'] == bridge_name:
                    break
            else:
                break
            
            if bridge_name.endswith(')'):
                bridge_name = "%s%i)" % (bridge_name[:-2], i)
            else:
                bridge_name += ' (%i)' % i
            i += 1
        
        self.ui.listWidgetPulseSinks.addItem(
            PaBridgeItem(
                self.ui.listWidgetPulseSinks,
                self.pulse_bridges_edited,
                {"type": "sink",
                 "name": bridge_name,
                 "channels": 2,
                 "connected": True}))
        
        self.pulse_bridges_edited.emit()

    @pyqtSlot()
    def slot_handleCrash_jack(self):
        self.DBusReconnect()

    @pyqtSlot()
    def slot_handleCrash_a2j(self):
        pass

    @pyqtSlot(str)
    def slot_changeGovernorMode(self, newMode):
        bus = dbus.SystemBus(mainloop=gDBus.loop)
        #proxy = bus.get_object("org.caleson.CpufreqSelector", "/Selector", introspect=False)
        #print(proxy.hello())
        proxy = bus.get_object(
            "com.ubuntu.IndicatorCpufreqSelector", "/Selector",
            introspect=False)
        proxy.SetGovernor(
            self.m_curGovCPUs, newMode,
            dbus_interface="com.ubuntu.IndicatorCpufreqSelector")

    @pyqtSlot()
    def slot_governorFileChanged(self):
        curGovFd = open(self.m_curGovPath, "r")
        curGovRead = curGovFd.read().strip()
        curGovFd.close()

        customTr = self.tr("Custom")

        if self.ui.cb_cpufreq.currentIndex() == -1:
            # First init
            self.ui.cb_cpufreq.currentIndexChanged[str].connect(
                self.slot_changeGovernorMode)

        self.ui.cb_cpufreq.blockSignals(True)

        if curGovRead in self.m_availGovList:
            self.ui.cb_cpufreq.setCurrentIndex(
                self.m_availGovList.index(curGovRead))

            if customTr in self.m_availGovList:
                self.m_availGovList.remove(customTr)
        else:
            if customTr not in self.m_availGovList:
                self.ui.cb_cpufreq.addItem(customTr)
                self.m_availGovList.append(customTr)

            self.ui.cb_cpufreq.setCurrentIndex(len(self.m_availGovList)-1)

        self.ui.cb_cpufreq.blockSignals(False)

    @pyqtSlot()
    def slot_tweaksApply(self):
        if "plugins" in self.settings_changed_types:
            for p_dict_key, p_dict in self.plugins_dict.items():
                p_dict['paths'].clear()
                
                for i in range(p_dict['widget'].count()):
                    i_path = p_dict['widget'].item(i).text()
                    if i_path:
                        p_dict['paths'].append(i_path)
                
                GlobalSettings.setValue("AudioPlugins/%s_PATH" % p_dict_key,
                                        ':'.join(p_dict['paths']))

        if "apps" in self.settings_changed_types:
            mimeFileContent = ""

            # Fix common mime errors
            mimeFileContent += "application/x-designer=designer-qt4.desktop;\n"
            mimeFileContent += "application/x-ms-dos-executable=wine.desktop;\n"
            mimeFileContent += "audio/x-minipsf=audacious.desktop;\n"
            mimeFileContent += "audio/x-psf=audacious.desktop;\n"

            if self.ui.ch_app_image.isChecked():
                imageApp = self.ui.cb_app_image.currentText().replace("/","-")
                mimeFileContent += "image/bmp=%s;\n" % imageApp
                mimeFileContent += "image/gif=%s;\n" % imageApp
                mimeFileContent += "image/jp2=%s;\n" % imageApp
                mimeFileContent += "image/jpeg=%s;\n" % imageApp
                mimeFileContent += "image/png=%s;\n" % imageApp
                mimeFileContent += "image/svg+xml=%s;\n" % imageApp
                mimeFileContent += "image/svg+xml-compressed=%s;\n" % imageApp
                mimeFileContent += "image/tiff=%s;\n" % imageApp
                mimeFileContent += "image/x-canon-cr2=%s;\n" % imageApp
                mimeFileContent += "image/x-canon-crw=%s;\n" % imageApp
                mimeFileContent += "image/x-eps=%s;\n" % imageApp
                mimeFileContent += "image/x-kodak-dcr=%s;\n" % imageApp
                mimeFileContent += "image/x-kodak-k25=%s;\n" % imageApp
                mimeFileContent += "image/x-kodak-kdc=%s;\n" % imageApp
                mimeFileContent += "image/x-nikon-nef=%s;\n" % imageApp
                mimeFileContent += "image/x-olympus-orf=%s;\n" % imageApp
                mimeFileContent += "image/x-panasonic-raw=%s;\n" % imageApp
                mimeFileContent += "image/x-pcx=%s;\n" % imageApp
                mimeFileContent += "image/x-pentax-pef=%s;\n" % imageApp
                mimeFileContent += "image/x-portable-anymap=%s;\n" % imageApp
                mimeFileContent += "image/x-portable-bitmap=%s;\n" % imageApp
                mimeFileContent += "image/x-portable-graymap=%s;\n" % imageApp
                mimeFileContent += "image/x-portable-pixmap=%s;\n" % imageApp
                mimeFileContent += "image/x-sony-arw=%s;\n" % imageApp
                mimeFileContent += "image/x-sony-sr2=%s;\n" % imageApp
                mimeFileContent += "image/x-sony-srf=%s;\n" % imageApp
                mimeFileContent += "image/x-tga=%s;\n" % imageApp
                mimeFileContent += "image/x-xbitmap=%s;\n" % imageApp
                mimeFileContent += "image/x-xpixmap=%s;\n" % imageApp

            if self.ui.ch_app_music.isChecked():
                musicApp = self.ui.cb_app_music.currentText().replace("/","-")
                mimeFileContent += "application/vnd.apple.mpegurl=%s;\n" % musicApp
                mimeFileContent += "application/xspf+xml=%s;\n" % musicApp
                mimeFileContent += "application/x-smaf=%s;\n" % musicApp
                mimeFileContent += "audio/AMR=%s;\n" % musicApp
                mimeFileContent += "audio/AMR-WB=%s;\n" % musicApp
                mimeFileContent += "audio/aac=%s;\n" % musicApp
                mimeFileContent += "audio/ac3=%s;\n" % musicApp
                mimeFileContent += "audio/basic=%s;\n" % musicApp
                mimeFileContent += "audio/flac=%s;\n" % musicApp
                mimeFileContent += "audio/m3u=%s;\n" % musicApp
                mimeFileContent += "audio/mp2=%s;\n" % musicApp
                mimeFileContent += "audio/mp4=%s;\n" % musicApp
                mimeFileContent += "audio/mpeg=%s;\n" % musicApp
                mimeFileContent += "audio/ogg=%s;\n" % musicApp
                mimeFileContent += "audio/vnd.rn-realaudio=%s;\n" % musicApp
                mimeFileContent += "audio/vorbis=%s;\n" % musicApp
                mimeFileContent += "audio/webm=%s;\n" % musicApp
                mimeFileContent += "audio/wav=%s;\n" % musicApp
                mimeFileContent += "audio/x-adpcm=%s;\n" % musicApp
                mimeFileContent += "audio/x-aifc=%s;\n" % musicApp
                mimeFileContent += "audio/x-aiff=%s;\n" % musicApp
                mimeFileContent += "audio/x-aiffc=%s;\n" % musicApp
                mimeFileContent += "audio/x-ape=%s;\n" % musicApp
                mimeFileContent += "audio/x-cda=%s;\n" % musicApp
                mimeFileContent += "audio/x-flac=%s;\n" % musicApp
                mimeFileContent += "audio/x-flac+ogg=%s;\n" % musicApp
                mimeFileContent += "audio/x-gsm=%s;\n" % musicApp
                mimeFileContent += "audio/x-m4b=%s;\n" % musicApp
                mimeFileContent += "audio/x-matroska=%s;\n" % musicApp
                mimeFileContent += "audio/x-mp2=%s;\n" % musicApp
                mimeFileContent += "audio/x-mpegurl=%s;\n" % musicApp
                mimeFileContent += "audio/x-ms-asx=%s;\n" % musicApp
                mimeFileContent += "audio/x-ms-wma=%s;\n" % musicApp
                mimeFileContent += "audio/x-musepack=%s;\n" % musicApp
                mimeFileContent += "audio/x-ogg=%s;\n" % musicApp
                mimeFileContent += "audio/x-oggflac=%s;\n" % musicApp
                mimeFileContent += "audio/x-pn-realaudio-plugin=%s;\n" % musicApp
                mimeFileContent += "audio/x-riff=%s;\n" % musicApp
                mimeFileContent += "audio/x-scpls=%s;\n" % musicApp
                mimeFileContent += "audio/x-speex=%s;\n" % musicApp
                mimeFileContent += "audio/x-speex+ogg=%s;\n" % musicApp
                mimeFileContent += "audio/x-tta=%s;\n" % musicApp
                mimeFileContent += "audio/x-vorbis+ogg=%s;\n" % musicApp
                mimeFileContent += "audio/x-wav=%s;\n" % musicApp
                mimeFileContent += "audio/x-wavpack=%s;\n" % musicApp

            if self.ui.ch_app_video.isChecked():
                videoApp = self.ui.cb_app_video.currentText().replace("/","-")
                mimeFileContent +="application/mxf=%s;\n" % videoApp
                mimeFileContent +="application/ogg=%s;\n" % videoApp
                mimeFileContent +="application/ram=%s;\n" % videoApp
                mimeFileContent +="application/vnd.ms-asf=%s;\n" % videoApp
                mimeFileContent +="application/vnd.ms-wpl=%s;\n" % videoApp
                mimeFileContent +="application/vnd.rn-realmedia=%s;\n" % videoApp
                mimeFileContent +="application/x-ms-wmp=%s;\n" % videoApp
                mimeFileContent +="application/x-ms-wms=%s;\n" % videoApp
                mimeFileContent +="application/x-netshow-channel=%s;\n" % videoApp
                mimeFileContent +="application/x-ogg=%s;\n" % videoApp
                mimeFileContent +="application/x-quicktime-media-link=%s;\n" % videoApp
                mimeFileContent +="video/3gpp=%s;\n" % videoApp
                mimeFileContent +="video/3gpp2=%s;\n" % videoApp
                mimeFileContent +="video/divx=%s;\n" % videoApp
                mimeFileContent +="video/dv=%s;\n" % videoApp
                mimeFileContent +="video/flv=%s;\n" % videoApp
                mimeFileContent +="video/mp2t=%s;\n" % videoApp
                mimeFileContent +="video/mp4=%s;\n" % videoApp
                mimeFileContent +="video/mpeg=%s;\n" % videoApp
                mimeFileContent +="video/ogg=%s;\n" % videoApp
                mimeFileContent +="video/quicktime=%s;\n" % videoApp
                mimeFileContent +="video/vivo=%s;\n" % videoApp
                mimeFileContent +="video/vnd.rn-realvideo=%s;\n" % videoApp
                mimeFileContent +="video/webm=%s;\n" % videoApp
                mimeFileContent +="video/x-anim=%s;\n" % videoApp
                mimeFileContent +="video/x-flic=%s;\n" % videoApp
                mimeFileContent +="video/x-flv=%s;\n" % videoApp
                mimeFileContent +="video/x-m4v=%s;\n" % videoApp
                mimeFileContent +="video/x-matroska=%s;\n" % videoApp
                mimeFileContent +="video/x-ms-asf=%s;\n" % videoApp
                mimeFileContent +="video/x-ms-wm=%s;\n" % videoApp
                mimeFileContent +="video/x-ms-wmp=%s;\n" % videoApp
                mimeFileContent +="video/x-ms-wmv=%s;\n" % videoApp
                mimeFileContent +="video/x-ms-wvx=%s;\n" % videoApp
                mimeFileContent +="video/x-msvideo=%s;\n" % videoApp
                mimeFileContent +="video/x-nsv=%s;\n" % videoApp
                mimeFileContent +="video/x-ogg=%s;\n" % videoApp
                mimeFileContent +="video/x-ogm=%s;\n" % videoApp
                mimeFileContent +="video/x-ogm+ogg=%s;\n" % videoApp
                mimeFileContent +="video/x-theora=%s;\n" % videoApp
                mimeFileContent +="video/x-theora+ogg=%s;\n" % videoApp
                mimeFileContent +="video/x-wmv=%s;\n" % videoApp

            if self.ui.ch_app_text.isChecked():
                # TODO - more mimetypes
                textApp = self.ui.cb_app_text.currentText().replace("/","-")
                mimeFileContent +="application/rdf+xml=%s;\n" % textApp
                mimeFileContent +="application/xml=%s;\n" % textApp
                mimeFileContent +="application/xml-dtd=%s;\n" % textApp
                mimeFileContent +="application/xml-external-parsed-entity=%s;\n" % textApp
                mimeFileContent +="application/xsd=%s;\n" % textApp
                mimeFileContent +="application/xslt+xml=%s;\n" % textApp
                mimeFileContent +="application/x-trash=%s;\n" % textApp
                mimeFileContent +="application/x-wine-extension-inf=%s;\n" % textApp
                mimeFileContent +="application/x-wine-extension-ini=%s;\n" % textApp
                mimeFileContent +="application/x-zerosize=%s;\n" % textApp
                mimeFileContent +="text/css=%s;\n" % textApp
                mimeFileContent +="text/plain=%s;\n" % textApp
                mimeFileContent +="text/x-authors=%s;\n" % textApp
                mimeFileContent +="text/x-c++-hdr=%s;\n" % textApp
                mimeFileContent +="text/x-c++-src=%s;\n" % textApp
                mimeFileContent +="text/x-changelog=%s;\n" % textApp
                mimeFileContent +="text/x-chdr=%s;\n" % textApp
                mimeFileContent +="text/x-cmake=%s;\n" % textApp
                mimeFileContent +="text/x-copying=%s;\n" % textApp
                mimeFileContent +="text/x-credits=%s;\n" % textApp
                mimeFileContent +="text/x-csharp=%s;\n" % textApp
                mimeFileContent +="text/x-csrc=%s;\n" % textApp
                mimeFileContent +="text/x-install=%s;\n" % textApp
                mimeFileContent +="text/x-log=%s;\n" % textApp
                mimeFileContent +="text/x-lua=%s;\n" % textApp
                mimeFileContent +="text/x-makefile=%s;\n" % textApp
                mimeFileContent +="text/x-ms-regedit=%s;\n" % textApp
                mimeFileContent +="text/x-nfo=%s;\n" % textApp
                mimeFileContent +="text/x-objchdr=%s;\n" % textApp
                mimeFileContent +="text/x-objcsrc=%s;\n" % textApp
                mimeFileContent +="text/x-pascal=%s;\n" % textApp
                mimeFileContent +="text/x-patch=%s;\n" % textApp
                mimeFileContent +="text/x-python=%s;\n" % textApp
                mimeFileContent +="text/x-readme=%s;\n" % textApp
                mimeFileContent +="text/x-vhdl=%s;\n" % textApp

            if self.ui.ch_app_browser.isChecked():
                # TODO - needs something else for default browser
                browserApp = self.ui.cb_app_browser.currentText().replace("/","-")
                mimeFileContent +="application/atom+xml=%s;\n" % browserApp
                mimeFileContent +="application/rss+xml=%s;\n" % browserApp
                mimeFileContent +="application/vnd.mozilla.xul+xml=%s;\n" % browserApp
                mimeFileContent +="application/x-mozilla-bookmarks=%s;\n" % browserApp
                mimeFileContent +="application/x-mswinurl=%s;\n" % browserApp
                mimeFileContent +="application/x-xbel=%s;\n" % browserApp
                mimeFileContent +="application/xhtml+xml=%s;\n" % browserApp
                mimeFileContent +="text/html=%s;\n" % browserApp
                mimeFileContent +="text/opml+xml=%s;\n" % browserApp

            realMimeFileContent ="[Default Applications]\n"
            realMimeFileContent += mimeFileContent
            realMimeFileContent +="\n"
            realMimeFileContent +="[Added Associations]\n"
            realMimeFileContent += mimeFileContent
            realMimeFileContent +="\n"

            local_xdg_defaults = os.path.join(
                HOME, ".local", "share", "applications", "defaults.list")
            local_xdg_mimeapps = os.path.join(
                HOME, ".local", "share", "applications", "mimeapps.list")

            writeFile = open(local_xdg_defaults, "w")
            writeFile.write(realMimeFileContent)
            writeFile.close()

            writeFile = open(local_xdg_mimeapps, "w")
            writeFile.write(realMimeFileContent)
            writeFile.close()

        if "wineasio" in self.settings_changed_types:
            REGFILE = 'REGEDIT4\n'
            REGFILE += '\n'
            REGFILE += '[HKEY_CURRENT_USER\Software\Wine\WineASIO]\n'
            REGFILE += '"Autostart server"=dword:0000000%i\n' % int(
                1 if self.ui.cb_wineasio_autostart.isChecked() else 0)
            REGFILE += '"Connect to hardware"=dword:0000000%i\n' % int(
                1 if self.ui.cb_wineasio_hw.isChecked() else 0)
            REGFILE += '"Fixed buffersize"=dword:0000000%i\n' % int(
                1 if self.ui.cb_wineasio_fixed_bsize.isChecked() else 0)
            REGFILE += '"Number of inputs"=dword:000000%s\n' % smartHex(
                self.ui.sb_wineasio_ins.value(), 2)
            REGFILE += '"Number of outputs"=dword:000000%s\n' % smartHex(
                self.ui.sb_wineasio_outs.value(), 2)
            REGFILE += '"Preferred buffersize"=dword:0000%s\n' % smartHex(
                int(self.ui.cb_wineasio_bsizes.currentText()), 4)

            writeFile = open("/tmp/caleson-wineasio.reg", "w")
            writeFile.write(REGFILE)
            writeFile.close()

            os.system("regedit /tmp/caleson-wineasio.reg")

        self.settings_changed_types = []
        self.ui.frame_tweaks_settings.setVisible(False)

    @pyqtSlot()
    def slot_tweaksSettingsChanged_apps(self):
        self.func_settings_changed("apps")

    @pyqtSlot()
    def slot_tweaksSettingsChanged_wineasio(self):
        self.func_settings_changed("wineasio")

    @pyqtSlot(int)
    def slot_tweakAppImageHighlighted(self, index):
        self.setAppDetails(self.ui.cb_app_image.itemText(index))

    @pyqtSlot(int)
    def slot_tweakAppImageChanged(self, ignored):
        self.setAppDetails(self.ui.cb_app_image.currentText())
        self.func_settings_changed("apps")

    @pyqtSlot(int)
    def slot_tweakAppMusicHighlighted(self, index):
        self.setAppDetails(self.ui.cb_app_music.itemText(index))

    @pyqtSlot(int)
    def slot_tweakAppMusicChanged(self, ignored):
        self.setAppDetails(self.ui.cb_app_music.currentText())
        self.func_settings_changed("apps")

    @pyqtSlot(int)
    def slot_tweakAppVideoHighlighted(self, index):
        self.setAppDetails(self.ui.cb_app_video.itemText(index))

    @pyqtSlot(int)
    def slot_tweakAppVideoChanged(self, ignored):
        self.setAppDetails(self.ui.cb_app_video.currentText())
        self.func_settings_changed("apps")

    @pyqtSlot(int)
    def slot_tweakAppTextHighlighted(self, index):
        self.setAppDetails(self.ui.cb_app_text.itemText(index))

    @pyqtSlot(int)
    def slot_tweakAppTextChanged(self, ignored):
        self.setAppDetails(self.ui.cb_app_text.currentText())
        self.func_settings_changed("apps")

    @pyqtSlot(int)
    def slot_tweakAppBrowserHighlighted(self, index):
        self.setAppDetails(self.ui.cb_app_browser.itemText(index))

    @pyqtSlot(int)
    def slot_tweakAppBrowserChanged(self, ignored):
        self.setAppDetails(self.ui.cb_app_browser.currentText())
        self.func_settings_changed("apps")

    def saveSettings(self):
        self.settings.setValue("Geometry", self.saveGeometry())

        GlobalSettings.setValue(
            "JACK/AutoStart", self.ui.cb_jack_autostart.isChecked())
        GlobalSettings.setValue(
            "ALSA-Audio/BridgeIndexType", self.ui.cb_alsa_type.currentIndex())
        GlobalSettings.setValue(
            "A2J/AutoStart", self.ui.cb_a2j_autostart.isChecked())
        GlobalSettings.setValue(
            "A2J/AutoExport", self.ui.cb_a2j_autoexport.isChecked())
        GlobalSettings.setValue(
            "A2J/UniquePortNames", self.ui.cb_a2j_unique_port_names.isChecked())
        GlobalSettings.setValue(
            "Pulse2JACK/AutoStart",
            (havePulseAudio and self.ui.cb_pulse_autostart.isChecked()))

    def loadSettings(self, geometry):
        if geometry:
            self.restoreGeometry(self.settings.value("Geometry", b""))

        usingAlsaLoop = bool(
            GlobalSettings.value("ALSA-Audio/BridgeIndexType", iAlsaFileNone, type=int)
            == iAlsaFileLoop)

        self.ui.cb_jack_autostart.setChecked(
            GlobalSettings.value("JACK/AutoStart", wantJackStart, type=bool))
        self.ui.cb_a2j_autostart.setChecked(
            GlobalSettings.value("A2J/AutoStart", True, type=bool))
        self.ui.cb_a2j_autoexport.setChecked(
            GlobalSettings.value("A2J/AutoExport", True, type=bool))
        self.ui.cb_a2j_unique_port_names.setChecked(
            GlobalSettings.value("A2J/UniquePortNames", True, type=bool))
        self.ui.cb_pulse_autostart.setChecked(
            GlobalSettings.value("Pulse2JACK/AutoStart", havePulseAudio
                                 and not usingAlsaLoop, type=bool))

    def timerEvent(self, event):
        if event.timerId() == self.m_timer500:
            if gDBus.jack and self.m_last_dsp_load != None:
                next_dsp_load = gDBus.jack.GetLoad()
                next_xruns = int(gDBus.jack.GetXruns())
                needUpdateTip = False

                if self.m_last_dsp_load != next_dsp_load:
                    self.m_last_dsp_load = next_dsp_load
                    self.ui.label_jack_dsp.setText("%.2f%%" % self.m_last_dsp_load)
                    needUpdateTip = True

                if self.m_last_xruns != next_xruns:
                    self.m_last_xruns = next_xruns
                    self.ui.label_jack_xruns.setText(str(self.m_last_xruns))
                    needUpdateTip = True

                if needUpdateTip:
                    self.updateSystrayTooltip()

        elif event.timerId() == self.m_timer2000:
            if gDBus.jack and self.m_last_buffer_size != None:
                next_buffer_size = gDBus.jack.GetBufferSize()

                if self.m_last_buffer_size != next_buffer_size:
                    self.m_last_buffer_size = next_buffer_size
                    self.ui.label_jack_bfsize.setText(
                        self.tr("%i samples") % self.m_last_buffer_size)
                    self.ui.label_jack_latency.setText(
                        "%.1f ms" % gDBus.jack.GetLatency())

            else:
                self.update()

        QMainWindow.timerEvent(self, event)

    def closeEvent(self, event):
        self.saveSettings()
        self.systray.handleQtCloseEvent(event)


#--------------- main ------------------
if __name__ == '__main__':
    # App initialization
    app = QApplication(sys.argv)
    app.setApplicationName("Caleson")
    app.setApplicationVersion(VERSION)
    app.setOrganizationName("Caleson")
    app.setWindowIcon(QIcon(":/scalable/caleson.svg"))
    setup_i18n()

    if haveDBus:
        gDBus.loop = DBusMainLoop(set_as_default=True)
        gDBus.bus = dbus.SessionBus(mainloop=gDBus.loop)

    initSystemChecks()

    # Show GUI
    gui = CalesonMainW()

    # Set-up custom signal handling
    setUpSignals(gui)

    if "--minimized" in app.arguments():
        gui.hide()
        gui.systray.setActionText("show", gui.tr("Restore"))
        app.setQuitOnLastWindowClosed(False)
    else:
        gui.show()

    # Exit properly
    sys.exit(gui.systray.exec_(app))
