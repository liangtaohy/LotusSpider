import os
import requests
import numpy as np
from PIL import Image
import matplotlib.pyplot as plt


def downloads_pic(pic_path, pic_name):
    url = 'https://www.jufaanli.com/home/Server/identitycode?0.7052675594065716'
    res = requests.get(url, stream=True)
    if not os.path.exists(pic_path):
        os.mkdir(pic_path)

    with open(os.path.join(pic_path, pic_name+'.gif'), 'wb') as f:
        for chunk in res.iter_content(chunk_size=1024):
            if chunk:  # filter out keep-alive new chunks
                f.write(chunk)
                f.flush()
        f.close()


for i in range(2445,10001 - 2444):
    downloads_pic('images', str(i))