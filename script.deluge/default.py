# -*- coding: utf-8 -*-
# Copyright (c) 2016 Correl J. Roush, Gerónimo Oñativia

import os
import sys
import xbmc
import xbmcaddon

__script_id__ = 'script.deluge'
__settings__ = xbmcaddon.Addon(id=__script_id__)
__language__ = __settings__.getLocalizedString

BASE_ADDON_PATH = xbmc.translatePath(__settings__.getAddonInfo('path'))
BASE_RESOURCE_PATH = xbmc.translatePath(os.path.join(__settings__.getAddonInfo('path'), 'resources', 'lib'))
sys.path.append(BASE_RESOURCE_PATH)

KEY_BUTTON_BACK = 275
KEY_KEYBOARD_ESC = 61467

if __name__ == '__main__':
    from gui import TransmissionGUI

    w = TransmissionGUI("script-Deluge-main.xml", __settings__.getAddonInfo('path'), "Default")
    w.doModal()
    del w
