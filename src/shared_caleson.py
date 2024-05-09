#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Common/Shared code for Caleson
# Copyright (C) 2012-2018 Filipe Coelho <falktx@falktx.com>
# Copyright (C) 2023-2024 Houston4444 <picotmathieu@gmail.com>
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
from enum import Enum
import logging
import os
import time

from PyQt5.QtCore import QProcess, QSettings

# Imports (Custom Stuff)
from shared import Platform, platform_


_logger = logging.getLogger(__name__)


class AlsaFile(Enum):
    INVALID = -2
    NULL = -1
    NONE = 0
    LOOP = 1
    JACK = 2
    PULSE = 3
    MAX = 4


GlobalSettings = QSettings("Caleson", "GlobalSettings")

# KXStudio Check
wantJackStart = os.path.exists(
    "/usr/share/kxstudio/config/config/Caleson/GlobalSettings.conf")

# Get Process list
def getProcList() -> list[str]:
    retProcs = list[str]()

    if platform_ in (Platform.LINUX, Platform.MACOS):
        process = QProcess()
        process.start("ps", ["-u", str(os.getuid())])
        process.waitForFinished()

        processDump = process.readAllStandardOutput().split("\n")

        for i in range(len(processDump)):
            if (i == 0):
                continue

            dumpTest = str(
                processDump[i], encoding="utf-8").rsplit(":", 1)[-1].split(" ")
            if len(dumpTest) > 1 and dumpTest[1]:
                retProcs.append(dumpTest[1])

    else:
        _logger.error("getProcList() - Not supported in this system")

    return retProcs

# Start ALSA-Audio Bridge, reading its settings
def startAlsaAudioLoopBridge():
    channels = GlobalSettings.value(
        "ALSA-Audio/BridgeChannels", 2, type=int)
    useZita = bool(
        GlobalSettings.value(
            "ALSA-Audio/BridgeTool", "alsa_in", type=str)
        == "zita")

    os.system(
        "caleson-aloop-daemon --channels=%i %s &" % (
            channels, "--zita" if useZita else ""))

# Stop all audio processes, used for force-restart
def waitProcsEnd(procs, tries):
    for x in range(tries):
        procsList = getProcList()
        for proc in procs:
            if proc in procsList:
                break
            else:
                time.sleep(0.1)
        else:
            break

# Cleanly close the jack dbus service
def tryCloseJackDBus() -> bool:
    try:
        import dbus
        bus = dbus.SessionBus()
        jack = bus.get_object(
            "org.jackaudio.service", "/org/jackaudio/Controller")
        jack.Exit()
    except:
        _logger.error("tryCloseJackDBus() failed")
        return False
    
    return True

# Stop all audio processes, used for force-restart
def stopAllAudioProcesses(tryCloseJack = True):
    if tryCloseJack:
        tryCloseJackDBus()

    if platform_ not in (Platform.HAIKU, Platform.LINUX, Platform.MACOS):
        _logger.error(
            "stopAllAudioProcesses() - Not supported in this system")
        return

    process = QProcess()

    # Tell pulse2jack script to create files, prevents pulseaudio respawn
    process.start("caleson-pulse2jack", ["--dummy"])
    process.waitForFinished()

    procsTerm = ["a2j", "a2jmidid", "artsd", "jackd",
                 "jackdmp", "knotify4", "jmcore"]
    procsKill = ["jackdbus", "pulseaudio"]
    tries = 20

    process.start("killall", procsTerm)
    process.waitForFinished()
    waitProcsEnd(procsTerm, tries)

    process.start("killall", ["-KILL"] + procsKill)
    process.waitForFinished()
    waitProcsEnd(procsKill, tries)
