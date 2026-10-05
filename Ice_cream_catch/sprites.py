"""Cartoon ice cream sprites, drawn with Pillow at 2x and downscaled for smooth edges."""

import math
from functools import lru_cache

from PIL import Image, ImageChops, ImageDraw

from ui import star_points, to_bgra

OUTLINE = (90, 55, 50)

# name, scoop color (RGB)
FLAVORS = [
    ("Strawberry", (255, 150, 185)),
    ("Vanilla", (255, 243, 205)),
    ("Chocolate", (150, 90, 60)),
    ("Mint", (150, 232, 195)),
    ("Blueberry", (150, 165, 255)),
    ("Mango", (255, 195, 70)),
]
GOLD = (255, 205, 40)


class _Pen:
    def __init__(self, size):
        self.size = size
        self.S = size * 2
        self.img = Image.new("RGBA", (self.S, self.S), (0, 0, 0, 0))
        self.d = ImageDraw.Draw(self.img)
        self.w = max(2, int(self.S * 0.03))

    def p(self, x, y):
        return x * self.S, y * self.S

    def circle(self, cx, cy, r, fill):
        S = self.S
        self.d.ellipse([(cx - r) * S, (cy - r) * S, (cx + r) * S, (cy + r) * S], fill=fill)

    def blob(self, circles, fill):
        """Union of circles with a cartoon outline."""
        edge = self.w / self.S
        for cx, cy, r in circles:
            self.circle(cx, cy, r, OUTLINE + (255,))
        for cx, cy, r in circles:
            self.circle(cx, cy, r - edge, fill)

    def done(self, width=None, height=None):
        return to_bgra(self.img.resize((width or self.size, height or self.size), Image.LANCZOS))


SCOOP_SHAPE = [(0.5, 0.44, 0.38), (0.22, 0.66, 0.13), (0.42, 0.72, 0.13), (0.62, 0.72, 0.13), (0.8, 0.64, 0.12)]


def _bucket(size):
    return max(8, int(round(size / 6.0)) * 6)


@lru_cache(maxsize=256)
def _scoop(flavor, size):
    pen = _Pen(size)
    color = GOLD if flavor < 0 else FLAVORS[flavor][1]
    pen.blob(SCOOP_SHAPE, color)
    pen.circle(0.37, 0.3, 0.07, (255, 255, 255, 130))
    if flavor >= 0 and FLAVORS[flavor][0] == "Mint":
        for x, y in ((0.55, 0.35), (0.4, 0.55), (0.66, 0.55), (0.3, 0.42), (0.52, 0.62)):
            pen.circle(x, y, 0.025, (70, 45, 35))
    elif flavor >= 0 and FLAVORS[flavor][0] == "Vanilla":
        for i, (x, y) in enumerate(((0.55, 0.3), (0.38, 0.52), (0.65, 0.5), (0.5, 0.62), (0.3, 0.4))):
            c = [(255, 90, 120), (80, 180, 255), (120, 210, 90), (255, 200, 50), (190, 110, 230)][i]
            pen.d.line([pen.p(x - 0.03, y), pen.p(x + 0.03, y - 0.02)], fill=c, width=pen.w)
    if flavor < 0:
        pen.d.polygon(star_points(0.5 * pen.S, 0.44 * pen.S, 0.17 * pen.S), fill=(255, 250, 220))
    else:
        pen.circle(0.5, 0.08, 0.075, OUTLINE + (255,))  # cherry on top
        pen.circle(0.5, 0.08, 0.06, (230, 30, 50))
    return pen.done()


def scoop_sprite(flavor, size):
    """flavor = index into FLAVORS, or -1 for the golden scoop."""
    return _scoop(flavor, _bucket(size))


@lru_cache(maxsize=64)
def _cone(width):
    height = int(width * 1.15)
    pen = _Pen(width)
    S = pen.S
    tri = [pen.p(0.08, 0.04), pen.p(0.92, 0.04), pen.p(0.5, 0.98)]
    pen.d.polygon(tri, fill=OUTLINE)
    inner = [pen.p(0.13, 0.06), pen.p(0.87, 0.06), pen.p(0.5, 0.93)]
    pen.d.polygon(inner, fill=(235, 175, 95))
    # waffle lines, clipped to the cone
    lines = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    ld = ImageDraw.Draw(lines)
    for i in range(-6, 10):
        off = i * 0.14
        ld.line([pen.p(off, 0), pen.p(off + 1, 1)], fill=(200, 135, 65), width=pen.w)
        ld.line([pen.p(off + 1, 0), pen.p(off, 1)], fill=(200, 135, 65), width=pen.w)
    mask = Image.new("L", (S, S), 0)
    ImageDraw.Draw(mask).polygon(inner, fill=255)
    pen.img.paste(lines, (0, 0), ImageChops.multiply(lines.getchannel("A"), mask))
    pen.d.rectangle([*pen.p(0.06, 0.0), *pen.p(0.94, 0.1)], fill=(215, 150, 75), outline=OUTLINE, width=pen.w)
    return pen.done(width, height)


def cone_sprite(width):
    return _cone(_bucket(width))


@lru_cache(maxsize=16)
def _broccoli(size):
    pen = _Pen(size)
    pen.d.polygon([pen.p(0.38, 0.5), pen.p(0.62, 0.5), pen.p(0.58, 0.95), pen.p(0.42, 0.95)],
                  fill=(165, 210, 110), outline=OUTLINE, width=pen.w)
    pen.blob([(0.28, 0.42, 0.18), (0.5, 0.3, 0.22), (0.72, 0.42, 0.18), (0.38, 0.5, 0.14), (0.62, 0.5, 0.14)],
             (70, 160, 70))
    for x, y in ((0.4, 0.25), (0.6, 0.3), (0.3, 0.42), (0.7, 0.45), (0.5, 0.45)):
        pen.circle(x, y, 0.035, (50, 125, 55))
    # a grumpy face
    pen.circle(0.43, 0.38, 0.03, (40, 40, 40))
    pen.circle(0.57, 0.38, 0.03, (40, 40, 40))
    pen.d.arc([*pen.p(0.42, 0.45), *pen.p(0.58, 0.55)], 200, 340, fill=(40, 40, 40), width=pen.w)
    return pen.done()


def broccoli_sprite(size):
    return _broccoli(_bucket(size))


@lru_cache(maxsize=4)
def sparkle_sprite(size):
    pen = _Pen(size)
    for i in range(6):
        a = math.radians(i * 60)
        pen.d.polygon(star_points((0.5 + 0.38 * math.cos(a)) * pen.S, (0.5 + 0.38 * math.sin(a)) * pen.S,
                                  0.09 * pen.S), fill=(255, 240, 120))
    return pen.done()
