#-*-coding:utf8-*-

import json
import logging
import os
import random
import re
import base64
import redis
from scrapy import signals
from authcookies import *
from scrapy.utils.python import to_native_str

logger = logging.getLogger(__name__)

"""
DOWNLOADER_MIDDLEWARES = {
    'scrapy.downloadermiddlewares.useragent.UserAgentMiddleware': None,
    'scrapy_fake_useragent.middleware.RandomUserAgentMiddleware': 400,
}
"""
class RandomUserAgentMiddleware(object):
    def __init__(self, crawler):
        super(RandomUserAgentMiddleware, self).__init__()
        self.ua_list = crawler.settings.get('UER_AGENT_LIST', None)
        self.ua_type = crawler.settings.get("UER_AGENT_TYPE", 'static')
        if not self.ua_list:
            self.user_agent = crawler.settings.get('USER_AGENT')

    @classmethod
    def from_crawler(cls, crawler):
        return cls(crawler)

    def process_request(self, request, spider):
        ua = ''
        if self.ua_type == 'static':
            ua = self.user_agent
            request.headers.setdefault('User-Agent', self.user_agent)
        elif self.ua_type == 'random':
            ua = random.choice(self.ua_list)
            request.headers.setdefault('User-Agent', ua)
        elif self.ua_type == 'per_user':
            if 'user' in request.meta.keys():
                ua = self.ua_list[request.meta['user']]
                request.headers.setdefault('User-Agent', self.ua_list[request.meta['user_id']])
            else:
                ua = self.user_agent
                request.headers.setdefault('User-Agent', self.user_agent)
        logger.info("set default User-Agent to " + ua)


class Mode:
    RANDOMIZE_PROXY_EVERY_REQUESTS, RANDOMIZE_PROXY_ONCE, SET_CUSTOM_PROXY, POLL_PROXY_EVERY_REQUESTS, STICKY_PROXY_EVERY_SESSION_ID = range(5)


class CookieMiddleware(object):
    def __init__(self, settings, crawler):
        self.debug = settings.getbool('COOKIES_DEBUG', False)
        self.enabled = True
        if self.enabled is True:
            init_cookie(crawler.spider, settings.get('ACCOUNT_CONFIG'))

    @classmethod
    def from_crawler(cls, crawler):
        return cls(crawler.settings, crawler)

    def process_request(self, request, spider):
        if self.enabled is True:

            if 'auto_login' in request.meta and request.meta['auto_login'] is True:

                if 'login_type' in request.meta and request.meta['login_type'] == 'random':
                    cookie, account = try_get_random_cookie(spider=spider)
                else:
                    cookie, account = poll_cookie(spider=spider)

                if cookie is not None:
                    # FIXME need to fix, not work
                    request.cookies = cookie
                    s = ''
                    for key in cookie:
                        s = key + '=' + cookie[key] + ';'
                    request.headers['Cookie'] = s
                    request.meta['account'] = account
            self._debug_cookie(request, spider)

    def _debug_cookie(self, request, spider):
        if self.debug:
            cl = [to_native_str(c, errors='replace')
                  for c in request.headers.getlist('Cookie')]
            if cl:
                cookies = "\n".join("Cookie: {}\n".format(c) for c in cl)
                msg = "Sending cookies to: {}\n{}".format(request, cookies)
                logger.debug(msg, extra={'spider': spider})


class CookieBannedMiddleware(object):
    def __init__(self, settings, crawler):
        self.cookie_max_retry_times = settings.getint('COOKIE_RETRY_TIMES', default=3)
        self.priority_adjust = settings.getint('COOKIE_RETRY_PRIORITY_ADJUST', default=-1)
        self.enabled = settings.getbool('COOKIES_ENABLED', False)
        self.debug = settings.getbool('COOKIES_DEBUG', False)

    @classmethod
    def from_crawler(cls, crawler):
        return cls(crawler.settings, crawler)

    def process_response(self, request, response, spider):
        """
        如果账号被封禁，则随机更换一个账号
        :param request:
        :param response:
        :param spider:
        :return:
        """
        print 'CookieBannedMiddleware.process_response', response.body
        if self.enabled and hasattr(spider, 'account_banned') and 'auto_login' in request.meta:
            banned = spider.account_banned(response)
            if banned is True:
                retries = request.meta.get('cookie_retry_times', 0) + 1
                account_banned(account=request.meta['account'], retry_times=retries, spider=spider)
                max_retry_times = request.meta.get('cookie_max_retry_times', self.cookie_max_retry_times)
                if retries < max_retry_times:
                    if 'login_type' in request.meta.keys() and request.meta['login_type'] == 'random':
                        cookie, account = try_get_random_cookie(spider=spider)
                    else:
                        cookie, account = poll_cookie(spider=spider)
                    if cookie is not None:
                        retryreq = request.copy()
                        retryreq.cookies = cookie
                        retryreq.meta['cookie_retry_times'] = retries
                        retryreq.dont_filter = True
                        retryreq.priority = request.priority + self.priority_adjust
                        return retryreq
        else:
            logger.debug("method account_banned is not defined, skip CookieBannedMiddleware")
        return response


class RandomProxy(object):
    def __init__(self, settings):
        self.mode = settings.get('PROXY_MODE')
        self.proxy_list = settings.get('PROXY_LIST')
        self.chosen_proxy = ''
        self.next_proxy_index = 0
        self.proxy_size = 0

        if self.mode == Mode.RANDOMIZE_PROXY_EVERY_REQUESTS or self.mode == Mode.RANDOMIZE_PROXY_ONCE or self.mode == Mode.POLL_PROXY_EVERY_REQUESTS or self.mode == Mode.STICKY_PROXY_EVERY_SESSION_ID:
            if self.proxy_list is None:
                raise KeyError('PROXY_LIST setting is missing')
            self.proxies = {}
            fin = open(self.proxy_list)
            try:
                for line in fin.readlines():
                    parts = re.match('(\w+://)([^:]+?:[^@]+?@)?(.+)', line.strip())
                    if not parts:
                        continue

                    # Cut trailing @
                    if parts.group(2):
                        user_pass = parts.group(2)[:-1]
                    else:
                        user_pass = ''

                    self.proxies[parts.group(1) + parts.group(3)] = user_pass
            finally:
                fin.close()
            self.proxy_size = len(self.proxies)
            if self.mode == Mode.RANDOMIZE_PROXY_ONCE:
                self.chosen_proxy = random.choice(list(self.proxies.keys()))
        elif self.mode == Mode.SET_CUSTOM_PROXY:
            custom_proxy = settings.get('CUSTOM_PROXY')
            self.proxies = {}
            parts = re.match('(\w+://)([^:]+?:[^@]+?@)?(.+)', custom_proxy.strip())
            if not parts:
                raise ValueError('CUSTOM_PROXY is not well formatted')

            if parts.group(2):
                user_pass = parts.group(2)[:-1]
            else:
                user_pass = ''

            self.proxies[parts.group(1) + parts.group(3)] = user_pass
            self.chosen_proxy = parts.group(1) + parts.group(3)

        if self.mode == Mode.STICKY_PROXY_EVERY_SESSION_ID:
            config = settings.get('REDIS_CONFIG', None)
            db = settings.get('PROXY_STICKY_DB', None)
            if db is None or config is None:
                raise KeyError('PROXY_STICKY_DB OR REDIS_CONFIG is missing')
            self.client = redis.Redis(host=config['host'], port=config['port'], db=db, password=config['password'])
            self.sticky_time = config['STICKY_TIME']

    @classmethod
    def from_crawler(cls, crawler):
        return cls(crawler.settings)

    def process_request(self, request, spider):
        # Don't overwrite with a random one (server-side state for IP)
        if 'proxy' in request.meta:
            if 'exception' in request.meta and request.meta["exception"] is False:
                return
        request.meta["exception"] = False
        if len(self.proxies) == 0:
            raise ValueError('All proxies are unusable, cannot proceed')

        if self.mode == Mode.RANDOMIZE_PROXY_EVERY_REQUESTS:
            proxy_address = random.choice(list(self.proxies.keys()))
        elif self.mode == Mode.POLL_PROXY_EVERY_REQUESTS:
            id = (self.next_proxy_index) % self.proxy_size
            proxy_address = list(self.proxies.keys())[id]
            self.next_proxy_index = (self.next_proxy_index + 1) % self.proxy_size
        elif self.mode == Mode.STICKY_PROXY_EVERY_SESSION_ID:  # session sticky
            """
            提供代理粘滞功能
            一个session或帐号可能需要绑定一个固定的IP，而不是随机切换IP
            """
            session_id = request.meta['account'] if 'account' in request.meta else None
            if session_id is None:
                raise ValueError('key account is missing for sticky proxy')
            key = 'sticky:proxy:%s' % (session_id)
            if self.client.exists(key):
                proxy_address = self.client.get(key)
            else:
                self.next_proxy_index = (self.next_proxy_index + 1) % self.proxy_size
                proxy_address = list(self.proxies.keys())[self.next_proxy_index]
                self.client.set(key, proxy_address)
                self.client.expire(key, self.sticky_time)
        else:
            proxy_address = self.chosen_proxy

        proxy_user_pass = self.proxies[proxy_address]

        logger.info("set proxy {0} with account {1}".format(proxy_address, request.meta['account'] if 'account' in request.meta else 'default'))
        request.meta['proxy'] = proxy_address
        if proxy_user_pass:
            basic_auth = 'Basic ' + base64.b64encode(proxy_user_pass.encode()).decode()
            request.headers['Proxy-Authorization'] = basic_auth
        else:
            logger.debug('Proxy user pass not found')
            logger.debug('Using proxy <%s>, %d proxies left' % (
                proxy_address, len(self.proxies)))

    def process_exception(self, request, exception, spider):
        if 'proxy' not in request.meta:
            return
        if self.mode == Mode.RANDOMIZE_PROXY_EVERY_REQUESTS or self.mode == Mode.RANDOMIZE_PROXY_ONCE:
            proxy = request.meta['proxy']
            try:
                del self.proxies[proxy]
            except KeyError:
                pass
            request.meta["exception"] = True
            if self.mode == Mode.RANDOMIZE_PROXY_ONCE:
                self.chosen_proxy = random.choice(list(self.proxies.keys()))
            logger.info('Removing failed proxy <%s>, %d proxies left' % (
                proxy, len(self.proxies)))