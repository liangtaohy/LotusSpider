import os
import re
from image_tools import *

root = 'imgs'

tmp = 'tmp'

source_images_root = '/Users/xlegal/work/images'

charmap = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"

if not os.path.exists(root):
    os.mkdir(root)

if not os.path.exists(tmp):
    os.mkdir(tmp)

for i in range(62):
    if not os.path.exists(os.path.join(root, str(i))):
        os.mkdir(os.path.join(root, str(i)))

i = 1
for file in os.listdir(source_images_root):
    file_name, ext = file.split('.')
    match = re.search('([0-9]+)_([0-9a-zA-Z]{4})\.gif', file)
    if match and match.groups():
        id = match.group(2)
        p = os.path.join(source_images_root, file)
        t = os.path.join(tmp, 'bin_' + file_name + '.jpg')
        l = binary_image(p)
        l = slide_by_window(l)
        save_to(l, t)

        img = Image.open(t)

        j = 0
        for chop in crop_image(img):
            index = charmap.index(id[j])
            save_to(chop, os.path.join(os.path.join(root, str(index)), str(i) + '.jpg'))
            j += 1
            i += 1