#-*-coding:utf8-*-
import logging
import random

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
        if self.ua_type == 'static':
            request.headers.setdefault('User-Agent', self.user_agent)
        elif self.ua_type == 'random':
            request.headers.setdefault('User-Agent', random.choice(self.ua_list))
        elif self.ua_type == 'per_user':
            if 'user_id' in request.meta.keys():
                request.headers.setdefault('User-Agent', self.ua_list[request.meta['user_id']])
            else:
                request.headers.setdefault('User-Agent', self.user_agent)