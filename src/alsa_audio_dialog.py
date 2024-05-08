import os

from PyQt5.QtCore import pyqtSlot
from PyQt5.QtWidgets import QDialog, QDialogButtonBox

from asoundrc_strs import ASOUNDRC_ALOOP
from shared import HOME
from shared_caleson import GlobalSettings

import ui_caleson_tb_alsa


class AlsaAudioDialog(QDialog):
    def __init__(self, parent, customMode: bool):
        QDialog.__init__(self, parent)
        self.ui = ui_caleson_tb_alsa.Ui_Dialog()
        self.ui.setupUi(self)

        self.asoundrcFile = os.path.join(HOME, ".asoundrc")
        self.fCustomMode = customMode

        if customMode:
            with open(self.asoundrcFile, "r") as asoundrcFd:
                asoundrcRead = asoundrcFd.read().strip()

            self.ui.textBrowser.setPlainText(asoundrcRead)
            self.ui.stackedWidget.setCurrentIndex(0)
            self.ui.buttonBox.setStandardButtons(QDialogButtonBox.Cancel)
        else:
            self.ui.textBrowser.hide()
            self.ui.stackedWidget.setCurrentIndex(1)
            self.adjustSize()

            self.ui.spinBox.setValue(
                GlobalSettings.value(
                    "ALSA-Audio/BridgeChannels", 2, type=int))

            if (GlobalSettings.value(
                        "ALSA-Audio/BridgeTool", "alsa_in", type=str)
                    == "zita"):
                self.ui.comboBox.setCurrentIndex(1)
            else:
                self.ui.comboBox.setCurrentIndex(0)

            self.accepted.connect(self._slot_set_options)

    @pyqtSlot()
    def _slot_set_options(self):
        channels = self.ui.spinBox.value()
        GlobalSettings.setValue("ALSA-Audio/BridgeChannels", channels)
        GlobalSettings.setValue(
            "ALSA-Audio/BridgeTool",
            "zita" if (self.ui.comboBox.currentIndex() == 1) else "alsa_in")

        with open(self.asoundrcFile, "w") as asoundrcFd:
            asoundrcFd.write(
                ASOUNDRC_ALOOP.replace(
                    "channels 2\n", "channels %i\n" % channels) + "\n")

