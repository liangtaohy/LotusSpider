#-*-coding:utf8-*-
import os
import numpy as np
from PIL import Image

root = './imgs'

image_handle = open('image.csv', 'w')
label_handle = open('label.csv', 'w')

sources = {}

for i in range(62):
    sub_dir = os.path.join(root, str(i))
    for file in os.listdir(sub_dir):
        img = Image.open(os.path.join(sub_dir, file))
        arr = np.array(img)

        arr = arr.reshape((1,360))

        np.savetxt(image_handle, arr.astype(int), fmt='%i', delimiter=',')
        label_handle.write(str(i) + '\n')

image_handle.close()
label_handle.close()