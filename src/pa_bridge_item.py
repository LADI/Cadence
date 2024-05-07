from PyQt5.QtCore import pyqtSignal, pyqtSlot, QSize
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QListWidget, QListWidgetItem, QFrame

import ui_pulse_bridge


# PulseAudio options Frame
class PaBridgeFrame(QFrame):
    def __init__(self, parent: QListWidget, item: QListWidgetItem,
                 edited_signal: pyqtSignal, bridge_dict: dict):
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
    def __init__(self, parent: QListWidget, edited_signal: pyqtSignal,
                 bridge_dict: dict):
        QListWidgetItem.__init__(self, parent, QListWidgetItem.UserType + 1)
        self.widget = PaBridgeFrame(parent, self, edited_signal, bridge_dict)
        parent.setItemWidget(self, self.widget)
        self.setSizeHint(QSize(200, 80))
    
    def get_current_dict(self) -> dict:
        return self.widget.get_current_dict()