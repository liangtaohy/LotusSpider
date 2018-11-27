from setuptools import setup

setup(
    name='lotus-useragent',
    version='1.0.0',
    description='Use a random User-Agent for every request',
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
    packages=[
        'scrapy_fake_useragent',
    ],
    install_requires=[
        'fake-useragent'
    ],
)