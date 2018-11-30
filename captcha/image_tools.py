#-*-coding:utf8-*-
import sys
import os
import numpy as np
import scipy.misc
import requests
from StringIO import StringIO
from PIL import Image
from softmax_regression import *


def bin_table(threshold=250):
    table = []
    for i in range(256):
        if i <= threshold:
            table.append(0)
        else:
            table.append(1)
    return table

def binary_image(image):
    L = image.convert('L')
    L = L.point(bin_table(), '1')
    return L

def binary_image_from_file(file):
    I = Image.open(file)
    L = I.convert('L')
    L = L.point(bin_table(), '1')
    return L


def slide_by_window(image, window=(2,2)):
    image = np.array(image)

    row, column = image.shape
    w_r, w_c = window

    for i in range(row - w_r + 1):
        for j in range(1, column - w_c + 1):
            if i == 0:
                if image[0][j] == False:
                    image[0][j] = True
            if image[i][j] == False:
                v = int(image[i + 1][j]) + int(image[i][j + 1]) + int(image[i+1][j+1])
                v += int(image[i - 1][j]) + int(image[i][j - 1]) + int(image[i-1][j-1]) + int(image[i-1][j+1]) + int(image[i+1][j-1])
                if v == 8:
                    image[i][j] = True

    for j in range(column):
        if image[row - 1][j] == False:
            image[row - 1][j] = True

    x = np.ndarray(image.shape)
    for i in range(row):
        for j in range(column):
            if image[i][j]:
                x[i][j] = 255
            else:
                x[i][j] = 0
    return x


def crop_image(img):
    img_list = []
    for i in range(4):
        x = i * 25
        y = 0
        img_list.append(img.crop((x, y, x + 12, y + 30)))
    return img_list


def save_to(image, file):
    scipy.misc.imsave(file, image)


def get_image_from_url(url):
    """
    从Url中加载数据，并返回Image对象

    :param url:
    :return:
    """
    response = requests.get(url)
    return Image.open(StringIO(response.content))

if __name__ == "__main__":
    """l = binary_image('/Users/xlegal/work/images/7232_PUsx.gif')
    l = slide_by_window(l)
    save_to(l, 'outfile.png')

    img = Image.open('outfile.jpg')"""

    img = get_image_from_url('https://www.jufaanli.com/home/Server/identitycode?0.8454335617089259')
    l = binary_image(img)
    l = slide_by_window(l)
    save_to(l, 'outfile.jpg')

    img = Image.open('outfile.jpg')

    i = 0
    for chop in crop_image(img):
        save_to(chop, str(i) + '.jpg')
        i += 1