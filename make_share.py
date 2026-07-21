"""Regenerate PaintDial share (OG) images to match the existing 1200x630 design."""
import json, os, re, sys, unicodedata
import numpy as np
from PIL import Image, ImageDraw, ImageFont

W, H = 1200, 630
PAPER = (247, 245, 240)
INK = (33, 31, 27)
MUTED = (126, 120, 108)
WHITE = (255, 255, 255)

FR = 'fonts/fraunces.ttf'
AR = 'fonts/archivo.ttf'


def font(path, size, wght=400, opsz=None):
    f = ImageFont.truetype(path, size)
    try:
        vals = []
        for a in f.get_variation_axes():
            n = a['name']
            if n == b'Weight':
                vals.append(wght)
            elif n == b'Optical Size':
                vals.append(opsz if opsz else min(max(size, a['minimum']), a['maximum']))
            elif n == b'Width':
                vals.append(100)
            else:
                vals.append(a['default'])
        f.set_variation_by_axes(vals)
    except Exception:
        pass
    return f


def base_slug(s):
    s = unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode()
    s = s.lower().replace('&', 'and').replace("'", '')
    return re.sub(r'-+', '-', re.sub(r'[^a-z0-9]+', '-', s)).strip('-')


def hex2rgb(h):
    h = h.lstrip('#')
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def ink_for(rgb):
    r, g, b = [v / 255 for v in rgb]
    lum = 0.2126 * r + 0.7152 * g + 0.0722 * b
    return INK if lum > 0.55 else WHITE


def _lin(v):
    v /= 255
    return ((v + 0.055) / 1.055) ** 2.4 if v > 0.04045 else v / 12.92


def rgb2oklab(r, g, b):
    R, G, B = _lin(r), _lin(g), _lin(b)
    l = (0.4122214708 * R + 0.5363325363 * G + 0.0514459929 * B) ** (1 / 3)
    m = (0.2119034982 * R + 0.6806995451 * G + 0.1073969566 * B) ** (1 / 3)
    s = (0.0883024619 * R + 0.2817188376 * G + 0.6299787005 * B) ** (1 / 3)
    return [0.2104542553 * l + 0.7936177850 * m - 0.0040720468 * s,
            1.9779984951 * l - 2.4285922050 * m + 0.4505937099 * s,
            0.0259040371 * l + 0.7827717662 * m - 0.8086757660 * s]


paints =
