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

"""
被封禁的账号
"""
ACCOUNT_BAN_KEY = "%s:account:ban:%s"


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


def get_cookie(spider, payload):
    """
    获取登录后的cookie, 默认为POST请求

    :TODO 有的网页需要先请求一个html页面，获取到cookie，然后再用该cookie登录，这种情况，需要spider自行实现get_cookie方法

    :param login_url:
    :param payload:
    :return:
    """

    s = requests.Session()
    response = s.post(spider.login_url, data=payload)
    cookies = response.cookies.get_dict()
    logger.warning("get Cookie success! form data is %s" % json.dumps(payload))
    return json.dumps(cookies)


def enqueue_account(spider_name, account, form, redis_client):
    """
    account入队，同时把表单也入队
    :param spider_name:
    :param account:
    :param form:
    :param redis_client:
    :return:
    """
    if not redis_client.get(LOGIN_FORMS_KEY % (spider_name, account)):
        redis_client.lpush(USER_ACCOUNTS_QUEUE % (spider_name), account)
        redis_client.set(LOGIN_FORMS_KEY % (spider_name, account), json.dumps(form, encoding='utf8'))


def get_account_form(spider_name, account):
    """
    获取指定账号的登录表单
    :param spider_name:
    :param account:
    :return:
    """
    return client.get(LOGIN_FORMS_KEY % (spider_name, account))


def init_cookie(spider, config):
    """
    初始化cookies, 尝试登录所有的帐号

    :param spider:
    :param config:
    :return:
    """
    client = redis.Redis(host=config['host'], port=config['port'], db=config['db'], password=config['password'])
    spider_name = spider.name

    accounts = client.lrange(USER_ACCOUNTS_QUEUE % (spider_name), 0, -1)
    for account in accounts:
        if account is not None or len(account) > 0:
            banned_times = client.get(ACCOUNT_BAN_KEY % (spider.name, account))
            if banned_times is not None and int(banned_times) > 0:
                continue
            if cookie_exists(account, spider):
                continue

            login_form = client.get(LOGIN_FORMS_KEY % (spider_name, account))

            if hasattr(spider, 'get_cookie'):
                cookie = spider.get_cookie(spider=spider, payload=json.loads(login_form, encoding='utf8'))
            else:
                raise NotImplementedError
            client.set(LOGIN_COOKIES_QUEUE % (spider_name, account), cookie)


def cookie_exists(account, spider):
    if client.get(LOGIN_COOKIES_QUEUE % (spider.name, account)):
        return True
    else:
        return False


def update_cookie(account, spider):
    """
    更新cookie, 避免过期或不可用
    :param account:
    :param spider:
    :return:
    """
    login_form = client.get(LOGIN_FORMS_KEY % (spider.name, account))

    if hasattr(spider, 'get_cookie'):
        cookie = get_cookie(spider=spider, payload=json.loads(login_form, encoding='utf8'))
    else:
        raise NotImplementedError

    client.set(LOGIN_COOKIES_QUEUE % (spider.name, account), cookie)
    return cookie


def account_banned(account, retry_times, spider):
    """
    帐号被封禁，重用时间设为retry_times * 60 * 10，即retry_times个10分钟后才可以尝试重用该账号
    :param account:
    :param retry_times:
    :param spider:
    :return:
    """
    client.delete(LOGIN_COOKIES_QUEUE % (spider.name, account))
    client.incr(ACCOUNT_BAN_KEY % (spider.name, account))
    client.expire(ACCOUNT_BAN_KEY % (spider.name, account), retry_times * 60 * 10)


def remove_cookie(account, spider):
    """
    删除不可用的帐号

    :param account:
    :param spider:
    :return:
    """
    client.delete(LOGIN_COOKIES_QUEUE % (spider.name, account))


if __name__ == '__main__':
    UER_AGENT_LIST = [
        "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.1 "
        "(KHTML, like Gecko) Chrome/22.0.1207.1 Safari/537.1",
        "Mozilla/5.0 (X11; CrOS i686 2268.111.0) AppleWebKit/536.11 "
        "(KHTML, like Gecko) Chrome/20.0.1132.57 Safari/536.11",
        "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/536.6 "
        "(KHTML, like Gecko) Chrome/20.0.1092.0 Safari/536.6",
        "Mozilla/5.0 (Windows NT 6.2) AppleWebKit/536.6 "
        "(KHTML, like Gecko) Chrome/20.0.1090.0 Safari/536.6",
        "Mozilla/5.0 (Windows NT 6.2; WOW64) AppleWebKit/537.1 "
        "(KHTML, like Gecko) Chrome/19.77.34.5 Safari/537.1",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/536.5 "
        "(KHTML, like Gecko) Chrome/19.0.1084.9 Safari/536.5",
        "Mozilla/5.0 (Windows NT 6.0) AppleWebKit/536.5 "
        "(KHTML, like Gecko) Chrome/19.0.1084.36 Safari/536.5",
        "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/536.3 "
        "(KHTML, like Gecko) Chrome/19.0.1063.0 Safari/536.3",
        "Mozilla/5.0 (Windows NT 5.1) AppleWebKit/536.3 "
        "(KHTML, like Gecko) Chrome/19.0.1063.0 Safari/536.3",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_8_0) AppleWebKit/536.3 "
        "(KHTML, like Gecko) Chrome/19.0.1063.0 Safari/536.3",
        "Mozilla/5.0 (Windows NT 6.2) AppleWebKit/536.3 "
        "(KHTML, like Gecko) Chrome/19.0.1062.0 Safari/536.3",
        "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/536.3 "
        "(KHTML, like Gecko) Chrome/19.0.1062.0 Safari/536.3",
        "Mozilla/5.0 (Windows NT 6.2) AppleWebKit/536.3 "
        "(KHTML, like Gecko) Chrome/19.0.1061.1 Safari/536.3",
        "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/536.3 "
        "(KHTML, like Gecko) Chrome/19.0.1061.1 Safari/536.3",
        "Mozilla/5.0 (Windows NT 6.1) AppleWebKit/536.3 "
        "(KHTML, like Gecko) Chrome/19.0.1061.1 Safari/536.3",
        "Mozilla/5.0 (Windows NT 6.2) AppleWebKit/536.3 "
        "(KHTML, like Gecko) Chrome/19.0.1061.0 Safari/536.3",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/535.24 "
        "(KHTML, like Gecko) Chrome/19.0.1055.1 Safari/535.24",
        "Mozilla/5.0 (Windows NT 6.2; WOW64) AppleWebKit/535.24 "
        "(KHTML, like Gecko) Chrome/19.0.1055.1 Safari/535.24",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/70.0.3538.77 Safari/537.36"
    ]

    PROXY = "http://60.205.169.24:9988"

    class Spider(object):
        name = 'test_spider'

        def get_cookie(self, spider, payload):
            session = requests.Session()
            proxies = {
                'http': PROXY,
            }

            headers = {'user-agent': random.choice(UER_AGENT_LIST)}

            r = session.get("http://www.lawsdata.com/", headers=headers, proxies=proxies)
            if r.status_code == 200:
                r = session.get("http://www.lawsdata.com/template/index/login-e51b5f65b6.html", headers=headers, proxies=proxies)
                url = "http://www.lawsdata.com/login"

                headers.update({
                    'X-Requested-With': 'XMLHttpRequest',
                    'referer': "http://www.lawsdata.com/template/index/login-e51b5f65b6.html"
                })

                payload = {
                    'mobile': '15102223207',
                    'password': 'asdf1234',
                    'rememberMe': 'false'
                }

                r = session.post(url, headers=headers, proxies=proxies, data=payload)

                if r.status_code == 200:
                    cookies = session.cookies.get_dict()
                    print 'login cookies:', cookies
                    logger.warning("get Cookie success! form data is %s" % json.dumps(cookies))
                    return json.dumps(cookies)
            return None

    spider = Spider()

    config = {
        'host': '127.0.0.1',
        'port': 6379,
        'password': 'foobared',
        'db': 1
    }

    account = '15102223207'

    login_form = {
        'mobile': '15102223207',
        'password': 'asdf1234',
        'rememberMe': 'false'
    }

    client = redis.Redis(host=config['host'], port=config['port'], db=config['db'], password=config['password'])
    client.set(LOGIN_FORMS_KEY % (spider.name, account), json.dumps(login_form))
    client.lpush(USER_ACCOUNTS_QUEUE % (spider.name), account)

    init_cookie(spider=spider, config=config)
    cookie, account = try_get_random_cookie(spider=spider)

    print cookie
    print account