#-*-coding:utf8-*-
import requests
import json
import redis
import logging
import random

logger = logging.getLogger(__name__)

client = None

"""
登录后的cookie
"""
LOGIN_COOKIES_QUEUE = "%s:cookies:%s"

"""
需要登录的帐号
"""
USER_ACCOUNTS_QUEUE = "%s:accounts"

"""
登录表单
"""
LOGIN_FORMS_KEY = "%s:form:%s"


def try_get_random_cookie(spider):
    """
    随机获取一个可用的cookie，如果没有，则返回None
    :param spider:
    :return: json | None
    """
    keys = client.keys("%s:cookies:*" % (spider.name))
    if len(keys) > 0:
        elem = random.choice(keys)
        account = elem.split(":")[2]
        return json.loads(client.get(elem), encoding='utf8'), account
    return None, None


def get_cookie(login_url, payload):
    """
    获取登录后的cookie, 默认为POST请求

    :TODO 有的网页需要先请求一个html页面，获取到cookie，然后再试用该cookie登录，这种情况，需要spider自行实现get_cookie方法

    :param login_url:
    :param payload:
    :return:
    """
    s = requests.Session()
    response = s.post(login_url, data=payload)
    cookies = response.cookies.get_dict()
    logger.warning("get Cookie success! form data is " % json.dumps(payload))
    return json.dumps(cookies)


def init_cookie(spider, config):
    """
    初始化cookies, 尝试登录所有的帐号

    :param spider:
    :param config:
    :return:
    """
    redis.Redis(host=config['host'], port=config['port'], db=config['db'], password=config['password'])
    spider_name = spider.name
    login_url = spider.login_url

    while True:
        account = client.lpop(USER_ACCOUNTS_QUEUE % (spider_name))
        if account is not None:
            login_form = client.get(LOGIN_FORMS_KEY % (spider_name, account))
            if hasattr(spider, 'get_cookie'):
                cookie = spider.get_cookie(login_url=login_url, payload=json.loads(login_form, encoding='utf8'))
            else:
                cookie = spider.get_cookie(login_url=login_url, payload=json.loads(login_form, encoding='utf8'))
            client.set(LOGIN_COOKIES_QUEUE % (spider_name, account), cookie)
        else:
            break


def update_cookie(account, spider):
    """
    更新cookie, 避免过期或不可用
    :param account:
    :param spider:
    :return:
    """
    login_form = client.get(LOGIN_FORMS_KEY % (spider.name, account))
    cookie = get_cookie(login_url=spider.login_url, payload=json.loads(login_form, encoding='utf8'))
    client.set(LOGIN_COOKIES_QUEUE % (spider.name, account), cookie)
    return cookie


def remove_cookie(account, spider):
    """
    删除不可用的帐号

    :param account:
    :param spider:
    :return:
    """
    r = client.delete(LOGIN_COOKIES_QUEUE % (spider.name, account))
    if r:
        client.lpush(USER_ACCOUNTS_QUEUE % (spider.name), account)