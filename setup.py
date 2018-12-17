#-*-coding:utf8-*-
from setuptools import setup, find_packages, __version__ as setuptools_version

setup(
    name='lotus-spider',
    version='1.0.0',
    description='lotus spider',
    keywords='scrapy proxy user-agent web-scraping',
    license='New BSD License',
    author="Liang Tao",
    author_email='liangtaohy@gmail.com',
    url='https://github.com/liangtaohy/LotusSpider.git',
    classifiers=[
        'Development Status :: 5 - Production',
        'Framework :: Scrapy',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Programming Language :: Python',
        'Topic :: Internet :: WWW/HTTP',
    ],
    packages=find_packages(exclude=('captcha', 'captcha.*'))
)