#-*-coding:utf8-*-
import logging
from scrapy.utils.log import configure_logging

configure_logging(install_root_handler=False)
logging.basicConfig(
    filename='./spider_log.txt',
    format='%(asctime)s %(levelname)s: %(message)s',
    level=logging.INFO
)