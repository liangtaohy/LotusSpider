"""
Scrapy extension for collecting scraping stats
"""
import pprint
import redis
import json
import logging

from twisted.internet import task

from scrapy.exceptions import NotConfigured
from scrapy import signals

logger = logging.getLogger(__name__)


class RedisStatsCollector(object):

    def __init__(self, crawler):
        self._dump = crawler.settings.getbool('STATS_DUMP')
        config = crawler.settings.get('REDIS_CONFIG')
        self.client = redis.Redis(host=config['host'], port=config['port'], db=config['db'], password=config['password'])
        self._stats = {}

    def get_value(self, key, default=None, spider=None):
        spider_name = spider.name if spider else 'global'
        value = self.client.hget('stats:' + spider_name, key)
        return value if value else default

    def get_stats(self, spider=None):
        try:
            spider_name = spider.name if spider else 'global'
            _stats = json.loads(self.client.hgetall('stats:' + spider_name), encoding='utf-8')
            return _stats
        except:
            return {}

    def set_value(self, key, value, spider=None):
        spider_name = spider.name if spider else 'global'
        self.client.hset('stats:' + spider_name, key, value)

    def set_stats(self, stats, spider=None):
        spider_name = spider.name if spider else 'global'
        self.client.hmset('stats:' + spider_name, stats)

    def inc_value(self, key, count=1, start=0, spider=None):
        spider_name = spider.name if spider else 'global'
        self.client.hsetnx(name='stats:' + spider_name, key=key, value=start)
        if type(count) is int:
            self.client.hincrby(name='stats:' + spider_name, key=key, amount=count)
        elif type(count) is float:
            self.client.hincrbyfloat(name='stats:' + spider_name, key=key, amount=count)

    def max_value(self, key, value, spider=None):
        spider_name = spider.name if spider else 'global'
        v = max(self.get_value(key=key, default=value, spider=spider), value)
        self.client.hset(name='stats:' + spider_name, key=key, value=v)

    def min_value(self, key, value, spider=None):
        spider_name = spider.name if spider else 'global'
        v = min(self.get_value(key=key, default=value, spider=spider), value)
        self.client.hset(name='stats:' + spider_name, key=key, value=v)

    def clear_stats(self, spider=None):
        spider_name = spider.name if spider else 'global'
        self.client.delete(['stats:' + spider_name])

    def open_spider(self, spider):
        pass

    def close_spider(self, spider, reason):
        if self._dump:
            logger.info("Dumping Scrapy stats:\n" + pprint.pformat(self.get_stats(spider=spider)),
                        extra={'spider': spider})
        self._persist_stats(self._stats, spider)

    def _persist_stats(self, stats, spider):
        pass


class SampleStats(object):
    """Sample basic scraping stats periodically"""
    """周期性采样数据"""

    def __init__(self, stats, crawler, interval=60.0):
        self.crawler = crawler
        self.stats = stats
        self.interval = interval
        self.multiplier = 60.0 / self.interval
        self.task = None
        self.threshhold = crawler.settings.getfloat('SAMPLE_STATS_THRESHOLD', 0.5)  # 默认成功响应的阈值为0.5

    @classmethod
    def from_crawler(cls, crawler):
        interval = crawler.settings.getfloat('SAMPLE_STATS_INTERVAL')
        if not interval:
            raise NotConfigured
        o = cls(crawler.stats, crawler, interval)
        crawler.signals.connect(o.spider_opened, signal=signals.spider_opened)
        crawler.signals.connect(o.spider_closed, signal=signals.spider_closed)
        return o

    def spider_opened(self, spider):
        self.pagesprev = 0
        self.itemsprev = 0
        self.request_count_prev = 0
        self.response_count_prev = 0
        self.response_status_count_prev = {'200':0}

        self.task = task.LoopingCall(self.log, spider)
        self.task.start(self.interval)

    def log(self, spider):
        items = self.stats.get_value('item_scraped_count', 0)
        pages = self.stats.get_value('response_received_count', 0)
        irate = (items - self.itemsprev) * self.multiplier
        prate = (pages - self.pagesprev) * self.multiplier
        self.pagesprev, self.itemsprev = pages, items

        requests = self.stats.get_value('downloader/request_count', 0, spider)
        responses = self.stats.get_value('downloader/response_count', 0, spider) - self.response_count_prev
        status_200 = self.stats.get_value('downloader/response_status_count/200', 0, spider) - self.response_status_count_prev['200']

        req_rate = requests - self.request_count_prev
        res_rate = responses - self.response_count_prev
        status_200_rate = status_200 - self.response_status_count_prev['200']

        self.request_count_prev, self.response_count_prev, self.response_status_count_prev['200'] = requests, responses, status_200

        msg = ("Crawled %(pages)d pages (at %(pagerate)d pages/min), "
               "scraped %(items)d items (at %(itemrate)d items/min), "
               "200 response %(status_200_rate)d pages at %(interval)d min")
        log_args = {'pages': pages, 'pagerate': prate,
                    'items': items, 'itemrate': irate, 'status_200_rate': status_200_rate, 'interval': self.interval}
        logger.info(msg, log_args, extra={'spider': spider})

        if status_200_rate / (req_rate + 1.0) <= self.threshhold:
            logger.warning("we will close spider [{0}] 200 is {1}, less than 0.9".format(spider.name, status_200_rate / (req_rate + 1.0)))
            self.crawler.engine.close_spider(spider, 'closespider_lower_response')

    def spider_closed(self, spider, reason):
        if self.task and self.task.running:
            self.task.stop()