#-*-coding:utf8-*-
import requests
import time
import sys
import os
import re
from urlparse import urlparse
from twisted.web.client import getPage, defer
from twisted.internet import reactor
from twisted.web import client

"""
"""
#SQUID_CONF_ORIGINAL = "/etc/squid/squid.conf.original"
#SQUID_CONF = "/etc/squid/squid.conf"
SQUID_CONF_ORIGINAL = "squid.conf.original"
SQUID_CONF = "squid.conf"

"""
配置config语句
"""
PEER_CONF = "cache_peer %s parent %s 0 no-query weighted-round-robin weight=%d connect-fail-limit=1 allow-miss max-conn=5 connect-timeout=10\n"

"""
SPEED_TEST_URL = "https://www.baidu.com/img/bd_logo1.png?where=super"
"""

def restartSquid():
    # os.system('systemctl start squid')
    os.system('squid -k reconfigure')
    print 'done'


def addSquidConf(proxys):
    with open(SQUID_CONF_ORIGINAL, 'r') as f:
        squid_conf = f.readlines()
        squid_conf.append('\n# Cache peer config\n')
        for proxy in proxys:
            ip = proxy['proxy'][7:].strip().split(':')
            weight = int(10 / proxy['speed']) + 1  # set weight
            squid_conf.append(PEER_CONF % (ip[0], ip[1], weight))
        with open(SQUID_CONF, 'w') as n:
            n.writelines(squid_conf)
            n.close()
        f.close()


class HttpStatusChecker(client.HTTPClientFactory):
    def __init__(self, url, proxy=None, headers=None, timeout=2):
        client.HTTPClientFactory.__init__(self, url=url, headers=headers)
        self.status = None
        self.header_time = None
        self.start_time = time.time()
        self.timeout = timeout
        self.proxy = proxy
        self.deferred.addCallback(lambda data : (data, self.status, self.proxy, self.response_headers, self.start_time, self.header_time))

    def gotHeaders(self, headers):
        self.header_time = time.time()
        return client.HTTPClientFactory.gotHeaders(self, headers)
    """
    def startedConnecting(self, connector):
        print 'started connecting'
        self.start_time = time.time()
    """

    def buildProtocol(self, addr):
        p = client.HTTPClientFactory.buildProtocol(self, addr)
        print 'connected'
        self.start_time = time.time()
        return p


def checkStatus(url, proxy=None, contextFactory=None, *args, **kwargs):
    x = url
    if proxy is not None:
        x = proxy
    s = urlparse(x)
    scheme, netloc, path = s.scheme, s.netloc, s.path
    if ':' not in netloc:
        netloc = netloc + ":80"
    host, port = netloc.split(':')
    port = int(port)
    factory = HttpStatusChecker(url, proxy=proxy, *args, **kwargs)
    if scheme == 'https':
        from twisted.internet import ssl
        if contextFactory is None:
            contextFactory = ssl.ClientContextFactory()
        reactor.connectSSL(host, port, factory, contextFactory)
    else:
        reactor.connectTCP(host, port, factory)
    return factory.deferred

"""
s = requests.session()
r = s.get('http://d.jghttp.golangapi.com/getip?num=35&type=1&pro=&city=0&yys=0&port=1&pack=3654&ts=0&ys=0&cs=0&lb=1&sb=0&pb=45&mr=1&regions=')
with open('golangapi_50_ip.txt', 'w') as f:
    f.write(r.content)
    f.close()
"""


availables = []


def all_done(arg):
    reactor.stop()


def callback(result):
    global availables
    _, status, proxy, _, start_time, end_time = result
    if end_time - start_time < 10:
        availables.append({'proxy': proxy, 'speed': end_time - start_time})
    print status, proxy, end_time - start_time


def errback(failure):
    sys.stderr.write(str(failure))


if __name__ == '__main__':
    while True:
        res = requests.get("http://www.89ip.cn/tqdl.html?api=1&num=500&port=&address=&isp=")
        proxies = []

        # add new proxy into proxy list
        for proxy in re.findall("([0-9\.:]{10,})", res.content):
            proxies.append('http://' + proxy)

        # merge old available proxy into proxy list
        for item in availables:
            proxies.append(item['proxy'])

        # clean availables
        availables = []

        proxies = list(set(proxies))
        r = requests.session()

        tasks = []

        url = "http://www.lawsdata.com/"

        deferred_list = []
        if True:
            for proxy in proxies:
                for i in range(0,1):
                    deferred = checkStatus(url=url, proxy=proxy, timeout=10)
                    deferred.addCallback(callback)  # 请求返回后的回调函数
                    deferred.addErrback(errback)
                    deferred_list.append(deferred)  # 把所有的请求加到列表里，后面要检测
            dlist = defer.DeferredList(deferred_list)  # 检测所有的请求
            dlist.addBoth(all_done)  # 检测到所有请求都执行完，执行的方法
            reactor.run()
            print availables

        addSquidConf(availables)
        time.sleep(60)
