# -*- coding: utf-8 -*-
# Copyright (c) 2010 Correl J. Roush, Gerónimo Oñativia

import base64
import os
import sys
import threading

import common
import search
import json
import xbmc
import xbmcgui
from basictypes.bytes import Bytes

_ = sys.modules["__main__"].__language__
__settings__ = sys.modules["__main__"].__settings__
BASE_ADDON_PATH = sys.modules["__main__"].BASE_ADDON_PATH

KEY_BUTTON_BACK = 275
KEY_KEYBOARD_ESC = 61467
KEY_MENU_ID = 92

EXIT_SCRIPT = (6, 10, 247, 275, 61467, 216, 257, 61448,)
CANCEL_DIALOG = EXIT_SCRIPT + (216, 257, 61448,)

UPDATE_INTERVAL = float(__settings__.getSetting('gui_refresh_interval'))

STATUS_ICONS = {'seed_pending': 'status_paused.png',
                'seeding': 'status_done.png',
                'fake_done': 'status_done.png',
                'downloading': 'status_downloading.png'}

PLAY_REQUESTED = False


class TransmissionGUI(xbmcgui.WindowXMLDialog):
    def __init__(self, strXMLname, strFallbackPath, strDefaultName, bforeFallback=0):
        self.listItems = {}
        self.torrents = {}
        self.timer = None

    @staticmethod
    def set_settings(params):
        __settings__.setSetting('torrent_deluge_host', params['host'])
        __settings__.setSetting('torrent_deluge_port', params['port'])
        __settings__.setSetting('torrent_deluge_password', params['password'])
        __settings__.setSetting('torrent_deluge_path', params['path'])

    def onInit(self):
        if not len(__settings__.getSetting('download_path')):
            self.close()
            if xbmcgui.Dialog().yesno(_(32002), _(32903), _(32003)):
                __settings__.openSettings()
                return False
        p = xbmcgui.DialogProgress()
        p.create(_(32000), _(32001))  # 'Deluge', 'Connecting to Deluge'
        self.deluge = common.get_rpc_client()
        info = self.deluge.get_info()
        if (not info or info['result']['connected'] is not True):
            xbmc.log(json.dumps(info), xbmc.LOGDEBUG)
            p.close()
            self.close()
            message = _(32901)  # Unable to connect
            if xbmcgui.Dialog().yesno(_(32002), message, _(32003)):
                __settings__.openSettings()
            del p
            return False
        self.updateTorrents()
        p.close()
        del p
        self.timer = threading.Timer(UPDATE_INTERVAL, self.updateTorrents)
        self.timer.start()

    def updateTorrents(self):
        torrents = self.deluge.list()
        if torrents:
            self.torrents = torrents
            list = self.getControl(120)
            keys = []
            for torrent in self.torrents:
                keys.append(torrent['id'])
                statusline = "Down: %(down)s %(pct).2f%% %(dspeed)s/s | Up: %(up)s %(uspeed)s/s | Ratio: %(ratio).2f"% \
                             {'down': Bytes.format(torrent['download']), 'pct': torrent['progress'], \
                              'dspeed': Bytes.format(torrent['downspeed']), 'up': Bytes.format(torrent['upload']),
                              'uspeed': Bytes.format(torrent['upspeed']), 'ratio': torrent['ratio']}
                if torrent['progress'] == 100: torrent['status'] = 'fake_done'
                if torrent['id'] not in self.listItems:
                    # Create a new list item
                    l = xbmcgui.ListItem(label=torrent['name'], label2=statusline)
                    self.listItems[torrent['id']] = l
                    list.addItem(l)
                else:
                    # Update existing list item
                    l = self.listItems[torrent['id']]
                l.setLabel(torrent['name'])
                l.setLabel2(statusline)
                l.setProperty('TorrentID', str(torrent['id']))
                l.setProperty('TorrentStatusIcon', STATUS_ICONS.get(torrent['status'], 'status_paused.png'))
                l.setProperty('TorrentProgress', "%3d%%"%torrent['progress'])

            removed = [id for id in self.listItems.keys() if id not in keys]
            if len(removed) > 0:
                # Clear torrents from the list that have been removed
                for id in removed:
                    del self.listItems[id]
                list.reset()
                for id in self.listItems:
                    list.addItem(self.listItems[id])
            list.setEnabled(bool(self.torrents))

        # Update again, after an interval, but only if the timer has not been cancelled
        if self.timer:
            self.timer = threading.Timer(UPDATE_INTERVAL, self.updateTorrents)
            self.timer.start()

    def onClick(self, controlID):
        list = self.getControl(120)
        if (controlID == 111):
            # Add torrent
            engines = [
                (_(32200), None),
                (_(32204), search.Kickass),
                (_(32208), search.EZTV),
                (_(32202), search.TPB),
                (_(32205), search.L337x),
                (_(32206), search.YTS),
                (_(32207), search.Lime),
            ]
            selected = xbmcgui.Dialog().select(_(32000), [i[0] for i in engines])
            if selected < 0:
                return
            engine = engines[selected][1]
            if not engine:
                filename = xbmcgui.Dialog().input(_(32000), '', xbmcgui.INPUT_ALPHANUM)
                if (len(filename)):
                    self.deluge.add_url(filename, __settings__.getSetting('download_path'))
            else:
                kb = xbmc.Keyboard(__settings__.getSetting('last_search'), engines[selected][0])
                kb.doModal()
                if not kb.isConfirmed():
                    return
                terms = kb.getText()
                __settings__.setSetting('last_search', terms)
                p = xbmcgui.DialogProgress()
                p.create(_(32000), _(32290))
                try:
                    results = engine().search(terms)
                except:
                    p.close()
                    xbmcgui.Dialog().ok(_(32000), _(32292))
                    return
                p.close()
                del p
                if not results:
                    xbmcgui.Dialog().ok(_(32000), _(32291))
                    return
                selected = xbmcgui.Dialog().select(_(32000),
                                                   ['[S:%d L:%d] %s'%(t['seeds'], t['leechers'], t['name']) for t in
                                                    results])
                if selected < 0:
                    return
                try:
                    self.deluge.add_url(results[selected]['url'], __settings__.getSetting('download_path'))
                except:
                    xbmcgui.Dialog().ok(_(32000), _(32293))
                    return
        if (controlID == 112):
            # Remove selected torrent
            item = list.getSelectedItem()
            if item and xbmcgui.Dialog().yesno(_(32000), 'Remove \'%s\'?'%item.getLabel()):
                remove_data = xbmcgui.Dialog().yesno(_(32000), 'Remove data as well?')
                if remove_data:
                    self.deluge.action_simple('removedata', item.getProperty('TorrentID'))
                else:
                    self.deluge.action_simple('remove', item.getProperty('TorrentID'))
        if (controlID == 113):
            # Stop selected torrent
            item = list.getSelectedItem()
            if item:
                self.deluge.action_simple('stop', item.getProperty('TorrentID'))
        if (controlID == 114):
            # Start selected torrent
            item = list.getSelectedItem()
            if item:
                self.deluge.action_simple('start', item.getProperty('TorrentID'))
        if (controlID == 115):
            # Stop all torrents
            for torrent in self.torrents:
                self.deluge.action_simple('stop', torrent['id'])
        if (controlID == 116):
            # Start all torrents
            for torrent in self.torrents:
                self.deluge.action_simple('start', torrent['id'])
        if (controlID == 118):
            # Settings button
            prev_settings = common.get_settings()
            __settings__.openSettings()
            p = xbmcgui.DialogProgress()
            p.create(_(32000), _(32001))  # 'Transmission', 'Connecting to Transmission'
            try:
                self.deluge = common.get_rpc_client()
                self.updateTorrents()
                p.close()
            except:
                p.close()
                xbmcgui.Dialog().ok(_(32002), _(32901))
                # restore settings
                self.set_settings(prev_settings)
                try:
                    self.deluge = common.get_rpc_client()
                except err:
                    xbmcgui.Dialog().ok(_(32002), _(32901))
                    self.close()
            del p
        if (controlID == 120):
            global PLAY_REQUESTED
            # A torrent was chosen, show details
            item = list.getSelectedItem()
            w = TorrentInfoGUI("script-Deluge-details.xml", __settings__.getAddonInfo('path'), "Default")
            w.setTorrent(self.deluge, item.getProperty('TorrentID'))
            w.doModal()
            del w
            if PLAY_REQUESTED:
                PLAY_REQUESTED = False
                self.close()
        if (controlID == 117):
            # Exit button
            self.close()

    def onFocus(self, controlID):
        # if controlID == 111 and xbmc.Player().isPlaying():
        #     xbmc.executebuiltin(
        #             "Notification(%s,%s,1500,%s)"%(_(32000), _(32005), BASE_ADDON_PATH + "/notification.png"))
        #     self.close()
        pass

    def onAction(self, action):
        if (action.getButtonCode() in CANCEL_DIALOG) or (action.getId() == KEY_MENU_ID):
            self.close()

    def close(self):
        if self.timer:
            self.timer.cancel()
            self.timer.join()
        self.listItems.clear()
        self.getControl(120).reset()
        super(TransmissionGUI, self).close()


class TorrentInfoGUI(xbmcgui.WindowXMLDialog):
    def __init__(self, strXMLname, strFallbackPath, strDefaultName, bforeFallback=0):
        global PLAY_REQUESTED
        PLAY_REQUESTED = False
        self.deluge = None
        self.torrent_id = None
        self.torrent = None
        self.list = {}
        self.timer = None

    def setTorrent(self, deluge, t_id):
        self.listItems = {}
        self.deluge = deluge
        self.torrent_id = t_id
        self.timer = threading.Timer(UPDATE_INTERVAL, self.updateTorrent)
        self.timer.start()

    def updateTorrent(self):
        pbar = self.getControl(219)
        list = self.getControl(220)
        labelName = self.getControl(1)
        labelDownload = self.getControl(2)
        labelUpload = self.getControl(5)
        labelETA = self.getControl(4)
        labelProgress = self.getControl(11)
        torrents = self.deluge.list()
        if torrents is not False:
            for torrent in torrents:
                if torrent['id'] == self.torrent_id: break
            self.torrent = torrent
            labelName.setLabel(torrent['name'])
            download_line = "Done %(down)s (%(pct).2f%%) | Speed %(dspeed)s/s"% \
                            {'down': Bytes.format(torrent['download']), 'pct': torrent['progress'],
                             'dspeed': Bytes.format(torrent['downspeed'])}
            labelDownload.setLabel(download_line)
            upload_line = "Sent %(up)s | Speed %(uspeed)s/s | Ratio: %(ratio).2f"% \
                          {'up': Bytes.format(torrent['upload']), 'uspeed': Bytes.format(torrent['upspeed']),
                           'ratio': torrent['ratio']}
            labelUpload.setLabel(upload_line)
            if torrent['status'] is 'downloading':
                eta_line = "%(eta)s"%{'eta': self.formatEta(int(torrent['eta']))}
            else:
                eta_line = "inf."
            labelETA.setLabel(eta_line)
            labelProgress.setLabel('%3d%%'%(torrent['progress']))
            pbar.setPercent(torrent['progress'])
            files = self.deluge.listfiles(self.torrent_id)  # [[path, percent, x['index'], size],...]
            if files is not None:
                for file in files:
                    if file[2] not in self.listItems.keys():
                        # Create a new list item
                        l = xbmcgui.ListItem(label=file[0])
                        list.addItem(l)
                        self.listItems[file[2]] = l
                    else:
                        # Update existing list item
                        l = self.listItems[file[2]]
                    l.setProperty('Progress', '[%3d%% of %s]'%(file[1], file[3]))

        # Update again, after an interval
        self.timer = threading.Timer(UPDATE_INTERVAL, self.updateTorrent)
        self.timer.start()

    def onInit(self):
        self.updateTorrent()

    def close(self):
        if self.timer:
            self.timer.cancel()
            self.timer.join()
        self.listItems.clear()
        self.getControl(220).reset()
        super(TorrentInfoGUI, self).close()

    def onAction(self, action):
        if (action.getButtonCode() in CANCEL_DIALOG) or (action.getId() == KEY_MENU_ID):
            self.close()
            pass

    def onClick(self, controlID):
        global PLAY_REQUESTED
        if controlID == 111:
            self.close()
        if controlID == 220:
            item = self.getControl(220).getSelectedItem()
            xbmc.executebuiltin("Notification(%s,%s,1500,%s)"%(
                _(32000), _(32004) + item.getLabel(), BASE_ADDON_PATH + "/notification.png"))
            playlist = xbmc.PlayList(xbmc.PLAYLIST_VIDEO)
            playlist.clear()
            playlist.add(os.path.join(self.torrent['dir'], item.getLabel()))
            xbmc.Player().play(playlist)
            PLAY_REQUESTED = True
            self.close()

    def onFocus(self, controlID):
        pass

    def formatEta(self, eta, granularity=2):
        intervals = (
            ('weeks', 604800),  # 60 * 60 * 24 * 7
            ('days', 86400),  # 60 * 60 * 24
            ('hours', 3600),  # 60 * 60
            ('minutes', 60),
            ('seconds', 1),
        )
        result = []
        for name, count in intervals:
            value = eta//count
            if value:
                eta -= value*count
                if value == 1:
                    name = name.rstrip('s')
                result.append("{} {}".format(value, name))
        return ', '.join(result[:granularity])
