#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Common/Shared code related to the Settings dialog
# Copyright (C) 2010-2018 Filipe Coelho <falktx@falktx.com>
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


from shared import HOME

# ------------------------------------------------------------------------------------------------------------
# Global variables

# Tab indexes
TAB_INDEX_MAIN = 0
TAB_INDEX_CANVAS = 1
TAB_INDEX_NONE = 2

# PatchCanvas defines
CANVAS_ANTIALIASING_SMALL = 1
CANVAS_EYECANDY_SMALL = 1

# Internal defaults
global SETTINGS_DEFAULT_PROJECT_FOLDER
SETTINGS_DEFAULT_PROJECT_FOLDER = HOME

# ------------------------------------------------------------------------------------------------------------
# Change internal defaults

def setDefaultProjectFolder(folder):
    global SETTINGS_DEFAULT_PROJECT_FOLDER
    SETTINGS_DEFAULT_PROJECT_FOLDER = folder

