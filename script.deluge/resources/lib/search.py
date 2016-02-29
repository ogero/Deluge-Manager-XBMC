# -*- coding: utf-8 -*-
# Copyright (c) 2016 Correl J. Roush, Gerónimo Oñativia

import re
import socket
import sys
from urllib import quote, quote_plus, urlencode
from urllib2 import urlopen, Request, URLError, HTTPError
from urllib import pathname2url
from StringIO import StringIO
import gzip
from BeautifulSoup import BeautifulSoup, BeautifulStoneSoup

socket.setdefaulttimeout(15)

USER_AGENT = 'Mozilla/5.0 (Windows NT 6.3; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/48.0.2564.116 Safari/537.36'


def fetch_url(url):
    data = None
    req = Request(url)
    req.add_header('Accept-encoding', 'gzip')
    req.add_header('User-Agent', USER_AGENT)
    response = urlopen(req)
    if response.info().get('content-encoding') == 'gzip':
        buf = StringIO(response.read())
        f = gzip.GzipFile(fileobj=buf)
        data = f.read()
    else:
        data = response.read()
    return data


class Search:
    def __init__(self):
        return NotImplemented

    def search(terms):
        return NotImplemented


class Kickass(Search):
    def __init__(self):
        self.search_uri = 'https://kat.cr/usearch/%s/?field=seeders&sorder=desc&rss=1'

    def search(self, terms):
        torrents = []
        url = self.search_uri%pathname2url(terms)
        soup = BeautifulStoneSoup(fetch_url(url))
        for item in soup.findAll('item'):
            torrents.append({
                'url': item.enclosure['url'],
                'name': item.title.text,
                'seeds': int(item.find('torrent:seeds').text),
                'leechers': int(item.find('torrent:peers').text),
            })
        return torrents


class EZTV(Search):
    def __init__(self):
        self.uri_prefix = 'https://eztv.ch/'
        self.search_uri = self.uri_prefix+'search/%s'

    def search(self, terms):
        torrents = []
        url = self.search_uri%pathname2url(terms)
        print(url)
        soup = BeautifulStoneSoup(fetch_url(url))
        for (c, item) in enumerate(soup.findAll('a', {'class': 'magnet'})):
            if c == 30: break
            info = item.findPrevious('a')
            item_soup = BeautifulStoneSoup(fetch_url(self.uri_prefix + info['href']))
            sp = item_soup.findAll('span', {'class': re.compile('^stat_')})
            if sp:
                sp = [int(i.text.replace(',', '')) for i in sp]
            else:
                sp = [0, 0]
            torrents.append({
                'url': item['href'],
                'name': info.text,
                'seeds': sp[0],
                'leechers': sp[1]
            })
        return torrents


class TPB(Search):
    def __init__(self):
        self.search_uris = ['https://thepiratebay.se/search/%s/',
                            'https://pirateproxy.net/search/%s/']

    def search(self, terms):
        torrents = []
        data = None
        for url in [u%pathname2url(terms) for u in self.search_uris]:
            data = fetch_url(url)
            if data is not None:
                break
        if not data:
            raise Exception('Out of pirate bay proxies')
        soup = BeautifulSoup(data)
        for details in soup.findAll('a', {'class': 'detLink'}):
            name = details.text
            url = details.findNext('a', {'href': re.compile('^magnet:')})['href']
            td = details.findNext('td')
            seeds = int(td.text)
            td = td.findNext('td')
            leechers = int(td.text)
            torrents.append({
                'url': url,
                'name': name,
                'seeds': seeds,
                'leechers': leechers,
            })
        return torrents


class L337x(Search):
    def __init__(self):
        self.uri_prefix = 'http://1337x.to'
        self.search_uri = self.uri_prefix + '/sort-search/%s/seeders/desc/1/'

    def search(self, terms):
        torrents = []
        url = self.search_uri%pathname2url(terms)
        soup = BeautifulStoneSoup(fetch_url(url))
        for details in soup.findAll('a', {'href': re.compile('^/torrent/')}):
            div = details.findNext('div')
            seeds = int(div.text)
            div = div.findNext('div')
            soup_link = BeautifulStoneSoup(fetch_url(self.uri_prefix + details['href']))
            link = soup_link.find('a', {'href': re.compile('^magnet:')})
            if not link:
                continue
            torrents.append({
                'url': link['href'],
                'name': details.text,
                'seeds': seeds,
                'leechers': int(div.text),
            })
        return torrents


class YTS(Search):
    def __init__(self):
        self.search_uri = 'http://yts.to/rss/%s/all/all/0'

    def search(self, terms):
        torrents = []
        url = self.search_uri%pathname2url(terms)
        soup = BeautifulStoneSoup(fetch_url(url))
        for item in soup.findAll('item'):
            item_quality = item.link.text.rpartition('_')[2]
            item_soup = BeautifulStoneSoup(fetch_url(item.link.text))
            qualities = [s.text.strip() for s in
                         item_soup.findAll('span', {'class': re.compile('^tech-quality')})]
            q_index = qualities.index(item_quality)
            span = item_soup.findAll('span', {'title': 'Peers and Seeds'})[q_index]
            ps_pos = len(span.parent.contents) - 1
            ps = span.parent.contents[ps_pos].split('/')
            torrents.append({
                'url': item.enclosure['url'],
                'name': item.title.text,
                'seeds': int(ps[1]),
                'leechers': int(ps[0])
            })
        return torrents


class Lime(Search):
    def __init__(self):
        self.search_uri = 'https://www.limetorrents.cc/searchrss/%s/'

    def search(self, terms):
        torrents = []
        url = self.search_uri%pathname2url(terms)
        soup = BeautifulStoneSoup(fetch_url(url))
        for item in soup.findAll('item'):
            (seeds, leechers) = re.findall('Seeds: (\d+) , Leechers (\d+)', item.description.text)[0]
            torrents.append({
                'url': item.enclosure['url'],
                'name': item.title.text,
                'seeds': int(seeds),
                'leechers': int(leechers)
            })
        return torrents


if __name__ == '__main__':
    sites = [Kickass(), TPB(), EZTV(), L337x(), YTS(), Lime()]
    terms = 'transmission'
    if len(sys.argv) > 1:
        terms = sys.argv[1]
    print 'Searching for "' + terms + '"'
    for site in sites:
        print site.__class__.__name__.center(79, '=')
        torrents = site.search(terms)
        print 'Total found = ' + str(len(torrents))
        for counter, file in enumerate(torrents):
            print '[{:3},{:3}] {:33} "{:33}"'.format(file['seeds'], file['leechers'],
                                                     file['name'].encode('ascii', 'replace')[:33],
                                                     file['url'][:33])
            if counter == 9: break
