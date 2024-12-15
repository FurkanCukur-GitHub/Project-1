# modules/utils.py
import torch
import numpy as np
from ultralytics.data.augment import LetterBox

def preprocess(img):
    im = LetterBox((640, 640), False)(image=img)
    im = im.transpose((2, 0, 1))[::-1]  # HWC->CHW, BGR->RGB
    im = np.ascontiguousarray(im)
    img = torch.from_numpy(im).to(torch.device('cuda:0'))
    img = img.half()
    img /= 255.0
    if len(img.shape) == 3:
        img = img[None]
    return img
