#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Common/Shared code for Cadence
# Copyright (C) 2012-2018 Filipe Coelho <falktx@falktx.com>
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
from time import sleep

from PyQt5.QtCore import QProcess, QSettings

# Imports (Custom Stuff)

from shared import (HOME, HAIKU, LINUX, MACOS)

# ------------------------------------------------------------------------------------------------------------
# Default Plugin PATHs

def get_default_path(plugin_format: str) -> list:
    return ':'.join(['%s/.%s' % (HOME, plugin_format),
                     '/usr/local/lib/%s' % plugin_format,
                     '/usr/lib/%s' % plugin_format])

DEFAULT_PLUGIN_PATH = {
    'LADSPA': get_default_path('ladspa'),
    'DSSI': get_default_path('dssi'),
    'LV2': get_default_path('lv2'),
    'VST': get_default_path('vst'),
    'VST3': get_default_path('vst3'),
    'LXVST': get_default_path('lxvst')}

# ------------------------------------------------------------------------------------------------------------
# ALSA file-type indexes

iAlsaFileNone = 0
iAlsaFileLoop = 1
iAlsaFileJACK = 2
iAlsaFilePulse = 3
iAlsaFileMax = 4

# ------------------------------------------------------------------------------------------------------------
# Global Settings

GlobalSettings = QSettings("Cadence", "GlobalSettings")

# ------------------------------------------------------------------------------------------------------------
# KXStudio Check

wantJackStart = os.path.exists("/usr/share/kxstudio/config/config/Cadence/GlobalSettings.conf")

# ------------------------------------------------------------------------------------------------------------
# Get Process list

def getProcList():
    retProcs = []

    if HAIKU or LINUX or MACOS:
        process = QProcess()
        process.start("ps", ["-u", str(os.getuid())])
        process.waitForFinished()

        processDump = process.readAllStandardOutput().split("\n")

        for i in range(len(processDump)):
            if (i == 0): continue
            dumpTest = str(processDump[i], encoding="utf-8").rsplit(":", 1)[-1].split(" ")
            if len(dumpTest) > 1 and dumpTest[1]:
                retProcs.append(dumpTest[1])

    else:
        print("getProcList() - Not supported in this system")

    return retProcs

# ------------------------------------------------------------------------------------------------------------
# Start ALSA-Audio Bridge, reading its settings

def startAlsaAudioLoopBridge():
    channels = GlobalSettings.value("ALSA-Audio/BridgeChannels", 2, type=int)
    useZita = bool(GlobalSettings.value("ALSA-Audio/BridgeTool", "alsa_in", type=str) == "zita")

    os.system("cadence-aloop-daemon --channels=%i %s &" % (channels, "--zita" if useZita else ""))

# ------------------------------------------------------------------------------------------------------------
# Stop all audio processes, used for force-restart

def waitProcsEnd(procs, tries):
    for x in range(tries):
        procsList = getProcList()
        for proc in procs:
            if proc in procsList:
                break
            else:
                sleep(0.1)
        else:
            break

# ------------------------------------------------------------------------------------------------------------
# Cleanly close the jack dbus service

def tryCloseJackDBus() -> bool:
    try:
        import dbus
        bus = dbus.SessionBus()
        jack = bus.get_object("org.jackaudio.service", "/org/jackaudio/Controller")
        jack.Exit()
    except:
        print("tryCloseJackDBus() failed")
        return False
    
    return True

# ------------------------------------------------------------------------------------------------------------
# Stop all audio processes, used for force-restart

def stopAllAudioProcesses(tryCloseJack = True):
    if tryCloseJack:
        tryCloseJackDBus()

    if not (HAIKU or LINUX or MACOS):
        print("stopAllAudioProcesses() - Not supported in this system")
        return

    process = QProcess()

    # Tell pulse2jack script to create files, prevents pulseaudio respawn
    process.start("cadence-pulse2jack", ["--dummy"])
    process.waitForFinished()

    procsTerm = ["a2j", "a2jmidid", "artsd", "jackd", "jackdmp", "knotify4", "jmcore"]
    procsKill = ["jackdbus", "pulseaudio"]
    tries = 20

    process.start("killall", procsTerm)
    process.waitForFinished()
    waitProcsEnd(procsTerm, tries)

    process.start("killall", ["-KILL"] + procsKill)
    process.waitForFinished()
    waitProcsEnd(procsKill, tries)
