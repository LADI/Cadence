#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# KDE, App-Indicator or Qt Systray
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

# Imports (Global)

from PyQt5.QtCore import QTimer
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QAction, QMainWindow, QMenu, QSystemTrayIcon


iActNameId = 0
iActWidget = 1
iActParentMenuId = 2
iActFunc = 3

iSepNameId = 0
iSepWidget = 1
iSepParentMenuId = 2

iMenuNameId = 0
iMenuWidget = 1
iMenuParentMenuId = 2

# Get Icon from user theme, using our own as backup (Oxygen)
def getIcon(icon, size=16):
    return QIcon.fromTheme(icon, QIcon(":/%ix%i/%s.png" % (size, size, icon)))

# Global Systray class
class GlobalSysTray(object):
    def __init__(self, parent, name, icon):
        object.__init__(self)

        self._app = None
        self._parent = parent
        self._gtk_running = False
        self._quit_added = False

        self.act_indexes = []
        self.sep_indexes = []
        self.menu_indexes = []

        self.menu = QMenu(parent)
        self.tray = QSystemTrayIcon(getIcon(icon))
        self.tray.setContextMenu(self.menu)
        self.tray.setParent(parent)
        self.tray.activated.connect(self.qt_systray_clicked)

    # -------------------------------------------------------------------------------------------

    def addAction(self, act_name_id, act_name_string, is_check=False):
        act_widget = QAction(act_name_string, self.menu)
        act_widget.setCheckable(is_check)
        self.menu.addAction(act_widget)

        act_obj = [None, None, None, None]
        act_obj[iActNameId] = act_name_id
        act_obj[iActWidget] = act_widget

        self.act_indexes.append(act_obj)

    def addSeparator(self, sep_name_id):
        sep_widget = self.menu.addSeparator()

        sep_obj = [None, None, None]
        sep_obj[iSepNameId] = sep_name_id
        sep_obj[iSepWidget] = sep_widget

        self.sep_indexes.append(sep_obj)

    def addMenu(self, menu_name_id, menu_name_string):
        menu_widget = QMenu(menu_name_string, self.menu)
        self.menu.addMenu(menu_widget)

        menu_obj = [None, None, None]
        menu_obj[iMenuNameId] = menu_name_id
        menu_obj[iMenuWidget] = menu_widget

        self.menu_indexes.append(menu_obj)

    def addMenuAction(self, menu_name_id, act_name_id, act_name_string, is_check=False):
        i = self.get_menu_index(menu_name_id)
        if i < 0: return

        menu_widget = self.menu_indexes[i][iMenuWidget]

        act_widget = QAction(act_name_string, menu_widget)
        act_widget.setCheckable(is_check)
        menu_widget.addAction(act_widget)

        act_obj = [None, None, None, None]
        act_obj[iActNameId] = act_name_id
        act_obj[iActWidget] = act_widget
        act_obj[iActParentMenuId] = menu_name_id

        self.act_indexes.append(act_obj)

    def addMenuSeparator(self, menu_name_id, sep_name_id):
        i = self.get_menu_index(menu_name_id)
        if i < 0: return

        menu_widget = self.menu_indexes[i][iMenuWidget]
        sep_widget = menu_widget.addSeparator()

        sep_obj = [None, None, None]
        sep_obj[iSepNameId] = sep_name_id
        sep_obj[iSepWidget] = sep_widget
        sep_obj[iSepParentMenuId] = menu_name_id

        self.sep_indexes.append(sep_obj)

    # -------------------------------------------------------------------------------------------

    def connect(self, act_name_id, act_func):
        i = self.get_act_index(act_name_id)
        if i < 0: return

        act_widget = self.act_indexes[i][iActWidget]
        act_widget.triggered.connect(act_func)

        self.act_indexes[i][iActFunc] = act_func

    # -------------------------------------------------------------------------------------------

    def setActionEnabled(self, act_name_id, yesno):
        i = self.get_act_index(act_name_id)
        if i < 0: return

        act_widget = self.act_indexes[i][iActWidget]
        act_widget.setEnabled(yesno)

    def setActionIcon(self, act_name_id, icon):
        i = self.get_act_index(act_name_id)
        if i < 0: return

        act_widget = self.act_indexes[i][iActWidget]
        act_widget.setIcon(getIcon(icon))

    def setActionText(self, act_name_id, text):
        i = self.get_act_index(act_name_id)
        if i < 0: return

        act_widget = self.act_indexes[i][iActWidget]
        act_widget.setText(text)

    def setIcon(self, icon):
        self.tray.setIcon(getIcon(icon))

    def setToolTip(self, text):
        self.tray.setToolTip(text)

    def isTrayAvailable(self):
        return QSystemTrayIcon.isSystemTrayAvailable()

    def handleQtCloseEvent(self, event):
        if self.isTrayAvailable() and self._parent.isVisible():
            event.accept()
            self.__hideShowCall()
            return

        self.close()
        QMainWindow.closeEvent(self._parent, event)

    # -------------------------------------------------------------------------------------------

    def show(self):
        if not self._quit_added:
            self._quit_added = True

            self.addSeparator("_quit")
            self.addAction("show", self._parent.tr("Minimize"))
            self.addAction("quit", self._parent.tr("Quit"))
            self.setActionIcon("quit", "application-exit")
            self.connect("show", self.__hideShowCall)
            self.connect("quit", self.__quitCall)

        self.tray.show()

    def hide(self):
        self.tray.hide()

    def close(self):
        self.menu.close()

    def exec_(self, app):
        self._app = app
        return app.exec_()

    # -------------------------------------------------------------------------------------------

    def get_act_index(self, act_name_id):
        for i in range(len(self.act_indexes)):
            if self.act_indexes[i][iActNameId] == act_name_id:
                return i
        else:
            print("systray.py - Failed to get action index for %s" % act_name_id)
            return -1

    def get_sep_index(self, sep_name_id):
        for i in range(len(self.sep_indexes)):
            if self.sep_indexes[i][iSepNameId] == sep_name_id:
                return i
        else:
            print("systray.py - Failed to get separator index for %s" % sep_name_id)
            return -1

    def get_menu_index(self, menu_name_id):
        for i in range(len(self.menu_indexes)):
            if self.menu_indexes[i][iMenuNameId] == menu_name_id:
                return i
        else:
            print("systray.py - Failed to get menu index for %s" % menu_name_id)
            return -1

    # -------------------------------------------------------------------------------------------

    def gtk_call_func(self, gtkmenu, act_name_id):
        i = self.get_act_index(act_name_id)
        if i < 0: return None

        return self.act_indexes[i][iActFunc]

    def qt_systray_clicked(self, reason):
        if reason in (QSystemTrayIcon.DoubleClick, QSystemTrayIcon.Trigger):
            self.__hideShowCall()

    # -------------------------------------------------------------------------------------------

    def __hideShowCall(self):
        if self._parent.isVisible():
            self.setActionText("show", self._parent.tr("Restore"))
            self._parent.hide()

            if self._app:
                self._app.setQuitOnLastWindowClosed(False)

        else:
            self.setActionText("show", self._parent.tr("Minimize"))

            if self._parent.isMaximized():
                self._parent.showMaximized()
            else:
                self._parent.showNormal()

            if self._app:
                self._app.setQuitOnLastWindowClosed(True)

            QTimer.singleShot(500, self.__raiseWindow)

    def __quitCall(self):
        if self._app:
            self._app.setQuitOnLastWindowClosed(True)

        self._parent.hide()
        self._parent.close()

        if self._app:
            self._app.quit()

    def __raiseWindow(self):
        self._parent.activateWindow()
        self._parent.raise_()
