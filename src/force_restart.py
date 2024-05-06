

from enum import Enum
from PyQt5.QtCore import QThread, pyqtSignal, pyqtSlot, Qt
from PyQt5.QtWidgets import QDialog, QMessageBox

import pulse2jack_tool

from shared_caleson import (
    GlobalSettings, sleep, tryCloseJackDBus, getProcList,
    stopAllAudioProcesses, iAlsaFileNone, iAlsaFileLoop, startAlsaAudioLoopBridge)
from shared_canvasjack import gDBus

import ui_caleson_rwait


class Info(Enum):
    DBUS_CLOSE = 0
    STOPPING_AUDIO_PROCESSES = 1
    DBUS_RECONNECT = 2
    WAITING_JACK_DBUS = 3
    START_JACK = 4
    BRIDGING_ALSA_AUDIO = 5
    BRIDGING_A2J = 6
    BRIDGING_PULSEAUDIO = 7


# Wait while JACK restarts
class ForceRestartThread(QThread):
    progressChanged = pyqtSignal(int)
    display_info = pyqtSignal(int)
    action_request = pyqtSignal(object)

    def __init__(self, parent):
        QThread.__init__(self, parent)

        self.m_wasStarted = False
        self.action_request_finished = False
        self.action_return_data = None

    def wasJackStarted(self):
        return self.m_wasStarted

    def startA2J(self):
        ' This function has to be run in main thread '
        started = gDBus.a2j.is_started()
        if (not gDBus.a2j.get_hw_export()
                and GlobalSettings.value("A2J/AutoExport", True, type=bool)):
            if started:
                gDBus.a2j.stop()
                started = False
            gDBus.a2j.set_hw_export(True)
            
        if not started:
            gDBus.a2j.start()

    def _mainThreadAction(self, action, timeout: int) -> bool:
        self.action_request_finished = False
        self.action_request.emit(action)
        
        step_time = 50 # 50 ms
        steps = int(timeout / step_time)
        
        for x in range(steps):
            if self.action_request_finished:
                break
            sleep(step_time * 0.001)
        else:
            return False
        
        return True

    def run(self):
        # Not started yet
        self.m_wasStarted = False
        self.progressChanged.emit(0)
        self.display_info.emit(Info.DBUS_CLOSE.value)

        # Stop JACK safely first, if possible
        self._mainThreadAction(tryCloseJackDBus, 10000)
        dbus_closed = self.action_return_data
        if dbus_closed:
            gDBus.jack = None

        self.progressChanged.emit(20)
        

        # Kill All
        self.display_info.emit(Info.STOPPING_AUDIO_PROCESSES.value)
        stopAllAudioProcesses(False)
        self.progressChanged.emit(30)

        # Connect to jackdbus
        self.display_info.emit(Info.DBUS_RECONNECT.value)
        if not self._mainThreadAction(self.parent().DBusReconnect, 10000):
            return
        
        if not gDBus.jack:
            return

        # Start it
        self.display_info.emit(Info.START_JACK.value)
        self.progressChanged.emit(70)
        if not self._mainThreadAction(gDBus.jack.StartServer, 10000):
            return

        self.progressChanged.emit(90)
                
        # If we made it this far, then JACK is started
        self.m_wasStarted = True

        # Start bridges according to user settings

        # ALSA-Audio
        if (GlobalSettings.value("ALSA-Audio/BridgeIndexType", iAlsaFileNone, type=int)
                == iAlsaFileLoop):
            self.display_info.emit(Info.BRIDGING_ALSA_AUDIO.value)
            startAlsaAudioLoopBridge()
            sleep(0.5)

        self.progressChanged.emit(92)
            
        # ALSA-MIDI
        if GlobalSettings.value("A2J/AutoStart", True, type=bool):
            self.display_info.emit(Info.BRIDGING_A2J.value)
            self._mainThreadAction(self.startA2J, 5000)

        self.progressChanged.emit(96)
        
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
            self.display_info.emit(Info.BRIDGING_PULSEAUDIO.value)
            pulse2jack_tool.replace_hotly(bridge_dicts)

        self.progressChanged.emit(100)


# Force Restart Dialog
class ForceWaitDialog(QDialog):
    def __init__(self, parent):
        QDialog.__init__(self, parent)
        self.ui = ui_caleson_rwait.Ui_Dialog()
        self.ui.setupUi(self)
        self.setWindowFlags(Qt.Dialog|Qt.WindowCloseButtonHint)

        self.rThread = ForceRestartThread(self)
        self.rThread.action_request.connect(self.slot_actionRequest)
        self.rThread.display_info.connect(self.slot_displayInfo)
        self.rThread.start()

        self.rThread.progressChanged.connect(self.progressBar.setValue)
        self.rThread.finished.connect(self.slot_rThreadFinished)

    def DBusReconnect(self):
        self.parent().DBusReconnect()

    def done(self, r):
        QDialog.done(self, r)
        self.close()

    @pyqtSlot()
    def slot_rThreadFinished(self):
        self.close()

        if self.rThread.wasJackStarted():
            QMessageBox.information(
                self, self.tr("Info"), self.tr("JACK was re-started sucessfully"))
        else:
            QMessageBox.critical(
                self, self.tr("Error"), self.tr("Could not start JACK!"))
    
    @pyqtSlot(object)
    def slot_actionRequest(self, action):
        ret = action()
        self.rThread.action_return_data = ret
        self.rThread.action_request_finished = True
        
    @pyqtSlot(int)
    def slot_displayInfo(self, info_int: int):
        info = Info(info_int)

        if info is Info.DBUS_CLOSE:
            text = self.tr("Closing DBus")
        elif info is Info.STOPPING_AUDIO_PROCESSES:
            text = self.tr("Stopping audio processes")
        elif info is Info.DBUS_RECONNECT:
            text = self.tr("Reconnecting to DBus")
        elif info is Info.WAITING_JACK_DBUS:
            text = self.tr("Waiting JACK DBus")
        elif info is Info.START_JACK:
            text = self.tr("Starting JACK")
        elif info is Info.BRIDGING_ALSA_AUDIO:
            text = self.tr("Launching ALSA Audio bridge")
        elif info is Info.BRIDGING_A2J:
            text = self.tr("Launching ALSA MIDI bridge (a2j)")
        elif info is Info.BRIDGING_PULSEAUDIO:
            text = self.tr("Launching PulseAudio bridge")
        else:
            text = ''

        self.ui.labelDisplayAction.setText(text)
            

