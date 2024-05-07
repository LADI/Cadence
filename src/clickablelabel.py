#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Clickable Label, a custom Qt widget
# Copyright (C) 2011-2018 Filipe Coelho <falktx@falktx.com>
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

# ------------------------------------------------------------------------------------------------------------
# Imports (Global)

from PyQt5.QtCore import pyqtSignal, pyqtSlot, Qt, QTimer
from PyQt5.QtWidgets import QLabel, QListWidget

# ------------------------------------------------------------------------------------------------------------
# Widget Class

class ClickableLabel(QLabel):
    clicked = pyqtSignal()

    def __init__(self, parent):
        QLabel.__init__(self, parent)

        self.setCursor(Qt.PointingHandCursor)

    def mousePressEvent(self, event):
        self.clicked.emit()

        # Use busy cursor for 2 secs
        self.setCursor(Qt.WaitCursor)
        QTimer.singleShot(2000, self.slot_setNormalCursor)

        QLabel.mousePressEvent(self, event)

    @pyqtSlot()
    def slot_setNormalCursor(self):
        self.setCursor(Qt.PointingHandCursor)


class DropSenderListWidget(QListWidget):
    drop_event = pyqtSignal()
    
    def __init__(self, parent):
        QListWidget.__init__(self, parent)
    
    def dropEvent(self, event):
        QListWidget.dropEvent(self, event)
        self.drop_event.emit()
