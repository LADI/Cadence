#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Imports (Global)
import dbus
import sys
from PyQt5.QtCore import QCoreApplication

# Imports (Custom Stuff)
import pulse2jack_tool
from shared_cadence import *

# Cadence Global Settings
GlobalSettings = QSettings("Cadence", "GlobalSettings")

# DBus
class dBus(object):
    __slots__ = [
      'bus',
      'a2j',
      'jack'
    ]
DBus = dBus()

def forceReset():
    # Kill all audio processes
    stopAllAudioProcesses()

    # Remove configs
    configFiles = (
        # Cadence GlobalSettings
        os.path.join(HOME, ".asoundrc"),
        # ALSA settings
        os.path.join(HOME, ".config", "Cadence", "GlobalSettings.conf"),
        # JACK2 settings
        os.path.join(HOME, ".config", "jack", "conf.xml"),
        # JACK1 settings
        os.path.join(HOME, ".config", "jack", "conf-jack1.xml")
    )

    for config in configFiles:
        if os.path.exists(config):
            os.remove(config)

# Start JACK, A2J and Pulse, according to user settings
def startSession(systemStarted, secondSystemStartAttempt):
    # Check if JACK is set to auto-start
    if systemStarted and not GlobalSettings.value("JACK/AutoStart", wantJackStart, type=bool):
        print("JACK is set to NOT auto-start on login")
        return True

    # Called via autostart desktop file
    if systemStarted and secondSystemStartAttempt:
        tmp_bus  = dbus.SessionBus()
        tmp_jack = tmp_bus.get_object("org.jackaudio.service", "/org/jackaudio/Controller")
        started  = bool(tmp_jack.IsStarted())

        # Cleanup
        del tmp_bus, tmp_jack

        # If already started, do nothing
        if started:
            return True

    # Kill all audio processes first
    stopAllAudioProcesses()

    # Connect to DBus
    DBus.bus  = dbus.SessionBus()
    DBus.jack = DBus.bus.get_object("org.jackaudio.service", "/org/jackaudio/Controller")
    
    try:
        DBus.a2j = dbus.Interface(DBus.bus.get_object("org.gna.home.a2jmidid", "/"), "org.gna.home.a2jmidid.control")
    except:
        DBus.a2j = None

    
    try:
        startJack()
    except dbus.exceptions.DBusException as e:
        sys.stderr.write(str(e) + '\n')
        sys.stderr.write('First attempt to start JACK failed, retry one time\n')
        # with some configs, it is possible that jack start failed this firt time
        # but perfectly works the second time
        # So, startJack failed, but we try one more time.
        startJack()

    if not bool(DBus.jack.IsStarted()):
        print("JACK Failed to Start")
        return False

    # Start bridges according to user settings

    # ALSA-Audio
    if GlobalSettings.value("ALSA-Audio/BridgeIndexType", iAlsaFileNone, type=int) == iAlsaFileLoop:
        startAlsaAudioLoopBridge()
        sleep(0.5)

    # ALSA-MIDI
    if GlobalSettings.value("A2J/AutoStart", True, type=bool) and DBus.a2j and not bool(DBus.a2j.is_started()):
        a2jExportHW = GlobalSettings.value("A2J/ExportHW", True, type=bool)
        DBus.a2j.set_hw_export(a2jExportHW)
        DBus.a2j.start()

    # PulseAudio
    if GlobalSettings.value("Pulse2JACK/AutoStart", True, type=bool):
        bridge_dicts = GlobalSettings.value("PulseAudio_bridges", type=list)
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

    print("JACK Started Successfully")
    return True

def startJack():
    if not bool(DBus.jack.IsStarted()):
        DBus.jack.StartServer()

def print_plugin_path(plugin_type: str):
    if plugin_type not in DEFAULT_PLUGIN_PATH.keys():
        return
    
    plugin_path = GlobalSettings.value(
        "AudioPlugins/%s_PATH" % plugin_type,
        DEFAULT_PLUGIN_PATH[plugin_type],
        type=str)
    
    if plugin_path != DEFAULT_PLUGIN_PATH[plugin_type]:
        path_list = plugin_path.split(':')
        def_list = DEFAULT_PLUGIN_PATH[plugin_type].split(':')
        for path in def_list:
            if path not in path_list:
                path_list.append(path)
        
        plugin_path = ':'.join(path_list)

    print(plugin_path)

def printArguments():
    print("\t-s|--start  \tStart session")
    print("\t   --reset  \tForce-reset all JACK daemons and settings (disables auto-start at login)")
    print("")
    print("\t-h|--help   \tShow this help message")
    print("\t-v|--version\tShow version")

def printError(cmd):
    print("Invalid arguments")
    print("Run '%s -h' for help" % (cmd))

def printHelp(cmd):
    print("Usage: %s [cmd]" % (cmd))
    printArguments()

def printVersion():
    print("Cadence version %s" % (VERSION))
    print("Developed by falkTX and the rest of the KXStudio Team")

#--------------- main ------------------
if __name__ == '__main__':
    # App initialization
    app = QCoreApplication(sys.argv)
    app.setApplicationName("Cadence")
    app.setApplicationVersion(VERSION)
    app.setOrganizationName("Cadence")

    # Check arguments
    cmd = sys.argv[0]

    if len(app.arguments()) == 1:
        printHelp(cmd)
    elif len(app.arguments()) == 2:
        arg = app.arguments()[1]
        if (arg.startswith('--print') and arg.endswith('_PATH')
                and arg[7:-5] in DEFAULT_PLUGIN_PATH.keys()):
            print_plugin_path(arg[7:-5])
        elif arg == "--reset":
            forceReset()
        elif arg in ("--system-start", "--system-start-desktop"):
            sys.exit(0 if startSession(True, arg == "--system-start-desktop") else 1)
        elif arg in ("-s", "--s", "-start", "--start"):
            sys.exit(0 if startSession(False, False) else 1)
        elif arg in ("-h", "--h", "-help", "--help"):
            printHelp(cmd)
        elif arg in ("-v", "--v", "-version", "--version"):
            printVersion()
        else:
            printError(cmd)
    else:
        printError(cmd)

    # Exit
    sys.exit(0)
