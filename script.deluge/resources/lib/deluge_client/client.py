# -*- coding: utf-8 -*-

import base64
import cookielib
import gzip
import itertools
import json
import mimetools
import os
import re
import sys
import time
import urllib
import urllib2
from StringIO import StringIO

import xbmc
import xbmcgui
import xbmcvfs

os.sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__))))

RE = {
    'content-disposition': re.compile('attachment;\sfilename="*([^"\s]+)"|\s')
}


# ################################
#
# HTTP
#
# ################################

class HTTP:
    def __init__(self):
        self._dirname = xbmc.translatePath('special://temp')  # .decode('utf-8').encode('cp1251')
        for subdir in ('xbmcup', sys.argv[0].replace('plugin://', '').replace('/', '')):
            self._dirname = os.path.join(self._dirname, subdir)
            if not xbmcvfs.exists(self._dirname):
                xbmcvfs.mkdir(self._dirname)

    def fetch(self, request, **kwargs):
        self.con, self.fd, self.progress, self.cookies, self.request = None, None, None, None, request

        if not isinstance(self.request, HTTPRequest):
            self.request = HTTPRequest(url=self.request, **kwargs)

        self.response = HTTPResponse(self.request)

        # Debug('XBMCup: HTTP: request: ' + str(self.request))

        try:
            self._opener()
            self._fetch()
        except Exception, e:
            xbmc.log('XBMCup: HTTP: ' + str(e), xbmc.LOGERROR)
            if isinstance(e, urllib2.HTTPError):
                self.response.code = e.code
            self.response.error = e
        else:
            self.response.code = 200

        if self.fd:
            self.fd.close()
            self.fd = None

        if self.con:
            self.con.close()
            self.con = None

        if self.progress:
            self.progress.close()
            self.progress = None

        self.response.time = time.time() - self.response.time

        xbmc.log('XBMCup: HTTP: response: ' + str(self.response), xbmc.LOGDEBUG)

        return self.response

    def _opener(self):

        build = [urllib2.HTTPHandler()]

        if self.request.redirect:
            build.append(urllib2.HTTPRedirectHandler())

        if self.request.proxy_host and self.request.proxy_port:
            build.append(urllib2.ProxyHandler(
                    {self.request.proxy_protocol: self.request.proxy_host + ':' + str(self.request.proxy_port)}))

            if self.request.proxy_username:
                proxy_auth_handler = urllib2.ProxyBasicAuthHandler()
                proxy_auth_handler.add_password('realm', 'uri', self.request.proxy_username,
                                                self.request.proxy_password)
                build.append(proxy_auth_handler)

        if self.request.cookies:
            self.request.cookies = os.path.join(self._dirname, self.request.cookies)
            self.cookies = cookielib.MozillaCookieJar()
            if os.path.isfile(self.request.cookies):
                self.cookies.load(self.request.cookies)
            build.append(urllib2.HTTPCookieProcessor(self.cookies))

        urllib2.install_opener(urllib2.build_opener(*build))

    def _fetch(self):
        params = {} if self.request.params is None else self.request.params

        if self.request.upload:
            boundary, upload = self._upload(self.request.upload, params)
            req = urllib2.Request(self.request.url)
            req.add_data(upload)
        else:

            if self.request.method == 'POST':
                if isinstance(params, dict) or isinstance(params, list):
                    params = urllib.urlencode(params)
                req = urllib2.Request(self.request.url, params)
            else:
                req = urllib2.Request(self.request.url)

        for key, value in self.request.headers.iteritems():
            req.add_header(key, value)

        if self.request.upload:
            req.add_header('Content-type', 'multipart/form-data; boundary=%s'%boundary)
            req.add_header('Content-length', len(upload))

        if self.request.auth_username and self.request.auth_password:
            req.add_header('Authorization', 'Basic %s'%base64.encodestring(
                    ':'.join([self.request.auth_username, self.request.auth_password])).strip())

        # self.con = urllib2.urlopen(req, timeout=self.request.timeout)
        self.con = urllib2.urlopen(req)
        self.response.headers = self._headers(self.con.info())

        if self.request.download:
            self._download()
        else:
            if not self.response.headers.get('content-encoding') == 'gzip':
                self.response.body = self.con.read()
            else:
                buf = StringIO(self.con.read())
                f = gzip.GzipFile(fileobj=buf)
                self.response.body = f.read()

        if self.request.cookies:
            self.cookies.save(self.request.cookies)

    def _download(self):
        fd = open(self.request.download, 'wb')
        if self.request.progress:
            self.progress = xbmcgui.DialogProgress()
            self.progress.create(u'Download')

        bs = 1024*8
        size = -1
        read = 0
        name = None

        if self.request.progress:
            if 'content-length' in self.response.headers:
                size = int(self.response.headers['content-length'])
            if 'content-disposition' in self.response.headers:
                r = RE['content-disposition'].search(self.response.headers['content-disposition'])
                if r:
                    name = urllib.unquote(r.group(1))

        while 1:
            buf = self.con.read(bs)
            if buf == '':
                break
            read += len(buf)
            fd.write(buf)

            if self.request.progress:
                self.progress.update(*self._progress(read, size, name))

        self.response.filename = self.request.download

    def _upload(self, upload, params):
        res = []
        boundary = mimetools.choose_boundary()
        part_boundary = '--' + boundary

        if params:
            for name, value in params.iteritems():
                res.append([part_boundary, 'Content-Disposition: form-data; name="%s"'%name, '', value])

        if isinstance(upload, dict):
            upload = [upload]

        for obj in upload:
            name = obj.get('name')
            filename = obj.get('filename', 'default')
            content_type = obj.get('content-type')
            try:
                body = obj['body'].read()
            except AttributeError:
                body = obj['body']

            if content_type:
                res.append([part_boundary,
                            'Content-Disposition: file; name="%s"; filename="%s"'%(name, urllib.quote(filename)),
                            'Content-Type: %s'%content_type, '', body])
            else:
                res.append([part_boundary,
                            'Content-Disposition: file; name="%s"; filename="%s"'%(name, urllib.quote(filename)), '',
                            body])

        result = list(itertools.chain(*res))
        result.append('--' + boundary + '--')
        result.append('')
        return boundary, '\r\n'.join(result)

    def _headers(self, raw):
        headers = {}
        for line in raw.headers:
            pair = line.split(':', 1)
            if len(pair) == 2:
                tag = pair[0].lower().strip()
                value = pair[1].strip()
                if tag and value:
                    headers[tag] = value
        return headers

    def _progress(self, read, size, name):
        res = []
        if size < 0:
            res.append(1)
        else:
            res.append(int(float(read)/(float(size)/100.0)))
        if name:
            res.append(u'File: ' + name)
        if size != -1:
            res.append(u'Size: ' + self._human(size))
        res.append(u'Load: ' + self._human(read))
        return res

    def _human(self, size):
        human = None
        for h, f in (('KB', 1024), ('MB', 1024*1024), ('GB', 1024*1024*1024), ('TB', 1024*1024*1024*1024)):
            if size/f > 0:
                human = h
                factor = f
            else:
                break
        if human is None:
            return (u'%10.1f %s'%(size, u'byte')).replace(u'.0', u'')
        else:
            return u'%10.2f %s'%(float(size)/float(factor), human)


class HTTPRequest:
    def __init__(self, url, method='GET', headers=None, cookies=None, params=None, upload=None, download=None,
                 progress=False, auth_username=None, auth_password=None, proxy_protocol='http', proxy_host=None,
                 proxy_port=None, proxy_username=None, proxy_password='', timeout=20.0, redirect=True, gzip=False):
        if headers is None:
            headers = {}

        self.url = url
        self.method = method
        self.headers = headers

        self.cookies = cookies

        self.params = params

        self.upload = upload
        self.download = download
        self.progress = progress

        self.auth_username = auth_username
        self.auth_password = auth_password

        self.proxy_protocol = proxy_protocol
        self.proxy_host = proxy_host
        self.proxy_port = proxy_port
        self.proxy_username = proxy_username
        self.proxy_password = proxy_password

        self.timeout = timeout

        self.redirect = redirect

        self.gzip = gzip

    def __repr__(self):
        return '%s(%s)'%(self.__class__.__name__, ','.join('%s=%r'%i for i in self.__dict__.iteritems()))


class HTTPResponse:
    def __init__(self, request):
        self.request = request
        self.code = None
        self.headers = {}
        self.error = None
        self.body = None
        self.filename = None
        self.time = time.time()

    def __repr__(self):
        args = ','.join('%s=%r'%i for i in self.__dict__.iteritems() if i[0] != 'body')
        if self.body:
            args += ',body=<data>'
        else:
            args += ',body=None'
        return '%s(%s)'%(self.__class__.__name__, args)


class Deluge:
    def config(self, login, password, host, port, url):
        self.login = login
        self.password = password

        self.url = 'http://' + host
        if port:
            self.url += ':' + str(port)
        self.url += url
        # log(str(self.url))
        self.http = HTTP()

    def get_info(self):
        obj = self.action({"method": "web.update_ui",
                           "params": [[], {}], "id": 1})
        return obj

    def list(self):
        obj = self.get_info()
        if obj is None or obj is False:
            return False

        res = []
        if len(obj['result'].get('torrents')) > 0:
            for k in obj['result'].get('torrents').keys():
                r = obj['result']['torrents'][k]
                add = {
                    'id': str(k),
                    'status': self.get_status(r['state']),
                    'name': r['name'],
                    'size': r['total_wanted'],
                    'progress': round(r['progress'], 2),
                    'download': r['total_done'],
                    'upload': r['total_uploaded'],
                    'upspeed': r['upload_payload_rate'],
                    'downspeed': r['download_payload_rate'],
                    'ratio': round(r['ratio'], 2),
                    'eta': r['eta'],
                    'peer': r['total_peers'],
                    'seed': r['num_seeds'],
                    'leech': r['num_peers'],
                    'add': r['time_added'],
                    'dir': r['save_path']
                }
                if len(r['files']) > 1: add['dir'] = os.path.join(r['save_path'], r['name'])
                res.append(add)
        return res

    def listdirs(self):
        obj = self.action({"method": "core.get_config", "params": [], "id": 5})
        if obj is None:
            return False

        try:
            res = [obj['result'].get('download_location')]
        except:
            res = [None]
        return res, res

    def listfiles(self, id):
        obj = self.get_info()
        i = 0
        if obj is None or obj is False:
            return None

        res = []
        obj = obj['result']['torrents'][id]
        # print str(obj)
        if len(obj['files']) == 1:
            strip_path = None
        else:
            strip_path = obj['name']

        for x in obj['files']:
            if x['size'] >= 1024*1024*1024:
                size = str(x['size']/(1024*1024*1024)) + 'GB'
            elif x['size'] >= 1024*1024:
                size = str(x['size']/(1024*1024)) + 'MB'
            elif x['size'] >= 1024:
                size = str(x['size']/1024) + 'KB'
            else:
                size = str(x['size']) + 'B'
            if strip_path:
                path = x['path'].lstrip(strip_path).lstrip('/')
            else:
                path = x['path']

            if x.get('progress'):
                percent = int(x['progress']*100)
            elif obj.get('file_progress') and len(obj['file_progress']) >= i:
                percent = int(obj['file_progress'][i]*100)
            else:
                percent = 0

            i += 1
            res.append([path, percent, x['index'], size])

        return res

    def get_prio(self, id):
        obj = self.get_info()
        if obj is None:
            return None
        res = obj['result']['torrents'][id]['file_priorities']
        return res

    def add(self, torrent, dirname):
        torrentFile = os.path.join(self.http._dirname, 'deluge.torrent')
        if self.action({'method': 'core.add_torrent_file',
                        'params': [torrentFile,
                                   base64.b64encode(torrent), {"download_path": dirname}], "id": 3}) is None:
            return None
        return True

    def add_url(self, torrent, dirname):
        if re.match("^magnet\:.+$", torrent):
            if self.action({'method': 'core.add_torrent_magnet', 'params': [torrent,
                                                                            {'download_path': dirname}],
                            "id": 3}) is None:
                return None
        else:
            if self.action({"method": "core.add_torrent_url", "params": [torrent, {'download_path': dirname}],
                            "id": 3}) is None:
                return None
        return True

    def setprio(self, id, ind):
        i = -1
        prios = self.get_prio(id)

        for p in prios:
            i = i + 1
            if p == 1:
                prios.pop(i)
                prios.insert(i, 0)

        prios.pop(int(ind))
        prios.insert(int(ind), 7)

        if self.action({"method": "core.set_torrent_file_priorities", "params": [id, prios], "id": 6}) is None:
            return None

        return True

    def setprio_simple(self, id, prio, ind):
        prios = self.get_prio(id)

        if ind != None:
            prios.pop(int(ind))
            if prio == '3':
                prios.insert(int(ind), 7)
            elif prio == '0':
                prios.insert(int(ind), 0)

        if self.action({"method": "core.set_torrent_file_priorities", "params": [id, prios], "id": 6}) is None:
            return None
        return True

    def setprio_simple_multi(self, menu):
        id = menu[0][0]
        prios = self.get_prio(id)

        for hash, action, ind in menu:
            prios.pop(int(ind))
            if action == '3':
                prios.insert(int(ind), 7)
            elif action == '0':
                prios.insert(int(ind), 0)

        if self.action({"method": "core.set_torrent_file_priorities", "params": [id, prios], "id": 6}) is None:
            return None

    def action(self, request):
        cookie = self.get_auth()
        if not cookie:
            return None

        try:
            jsobj = json.dumps(request)
        except:
            return None
        else:
            response = self.http.fetch(self.url + '/json', method='POST', params=jsobj,
                                       headers={'X-Requested-With': 'XMLHttpRequest', 'Cookie': cookie,
                                                'Content-Type': 'application/json; charset=UTF-8'})

            if response.error:
                return None

            else:
                try:
                    obj = json.loads(response.body)
                except:
                    return None
                else:
                    return obj

    def action_simple(self, action, id):
        actions = {'start': {"method": "core.resume_torrent", "params": [[id]], "id": 4},
                   'stop': {"method": "core.pause_torrent", "params": [[id]], "id": 4},
                   'remove': {"method": "core.remove_torrent", "params": [id, False], "id": 4},
                   'removedata': {"method": "core.remove_torrent", "params": [id, True], "id": 4}}
        obj = self.action(actions[action])
        return True if obj else None

    def get_auth(self):
        params = json.dumps({"method": "auth.login", "params": [self.password], "id": 0})
        response = self.http.fetch(self.url + '/json', method='POST', params=params, gzip=True,
                                   headers={'X-Requested-With': 'XMLHttpRequest',
                                            'Content-Type': 'application/json; charset=UTF-8'})
        if response.error:
            return None

        auth = json.loads(response.body)
        if auth["result"] == False:
            return False
        else:
            r = re.compile('_session_id=([^;]+);').search(response.headers.get('set-cookie', ''))
            if r:
                cookie = r.group(1).strip()
                return '_session_id=' + cookie

    def get_status(self, code):
        mapping = {
            'Queued': 'stopped',
            'Error': 'stopped',
            'Checking': 'checking',
            'Paused': 'seed_pending',
            'Downloading': 'downloading',
            'Active': 'seed_pending',
            'Seeding': 'seeding'
        }
        return mapping[code]
