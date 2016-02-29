# -*- coding: utf-8 -*-
# Copyright (c) 2013 Artem Glebov, Gerónimo Oñativia

import sys

from deluge_client import Deluge

__settings__ = sys.modules["__main__"].__settings__


def get_settings():
    params = {
        'host': __settings__.getSetting('torrent_deluge_host'),
        'port': __settings__.getSetting('torrent_deluge_port'),
        'password': __settings__.getSetting('torrent_deluge_password'),
        'path': __settings__.getSetting('torrent_deluge_path'),
        'stop_all_on_playback': __settings__.getSetting('stop_all_on_playback')
    }
    return params


def get_params():
    params = {
        'host': __settings__.getSetting('torrent_deluge_host'),
        'port': __settings__.getSetting('torrent_deluge_port'),
        'password': __settings__.getSetting('torrent_deluge_password'),
        'path': __settings__.getSetting('torrent_deluge_path'),
    }
    return params


def get_rpc_client():
    params = get_params()
    deluge = Deluge()
    deluge.config(host=params['host'], port=params['port'], login='', password=params['password'], url=params['path'])
    return deluge
