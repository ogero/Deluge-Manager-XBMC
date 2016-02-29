Deluge Manager for XBMC
=================

A client for the popular [Deluge](http://deluge-torrent.org/) bittorrent application for [XBMC](http://xbmc.org/).  
Based on [Transmission-XBMC](https://github.com/correl/Transmission-XBMC) XBMC Addon by Correl J. Roush.  

Features
--------

Currently, Deluge Manager supports viewing, adding, removing, starting, stopping torrents and launching videos if torrent client is in local host.  
More advanced features may be added in future releases.  

### Screenshot
![Screenshot](https://raw.githubusercontent.com/ogero/Deluge-Manager-XBMC/master/deluge-manager.png)

Installation
------------

This script was developed on XBMC 16 (Jarvis) but should work on XBMC 13 (Gotham) or higher.

This script can be installed via the addon manager within XBMC. Attempting to install it manually may not work, as it requires the simplejson library which is automatically installed by the addon manager.

If your deluge web-ui is running on a machine other than localhost, using a port other than 8112, or requires authentication, you will have to change the plugin settings before running it.

License
-------

Deluge-Manager is licensed under the terms of the [MIT license](http://www.opensource.org/licenses/mit-license.html).
