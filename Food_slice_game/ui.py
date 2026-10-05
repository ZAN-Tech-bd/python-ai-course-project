"""Kid-friendly drawing helpers: bubbly fonts, pill-shaped labels, alpha blending and star confetti."""

import math
import random
import time
from functools import lru_cache

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

INK = (40, 50, 90)  # RGB, dark navy used for text
RAINBOW_RGB = [(255, 70, 70), (255, 150, 40), (255, 220, 40), (80, 200, 80),
               (60, 170, 255), (90, 90, 230), (190, 90, 220)]
CONFETTI_BGR = [(50, 50, 240), (0, 150, 255), (0, 230, 255), (60, 200, 60),
                (230, 110, 40), (220, 80, 160), (180, 105, 255)]

FONT_CANDIDATES = [
    "comicbd.ttf",                                                  # Windows
    "/System/Library/Fonts/Supplemental/Comic Sans MS Bold.ttf",    # macOS
    "/usr/share/fonts/truetype/msttcorefonts/comicbd.ttf",          # Linux + MS fonts
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",         # Linux
    "arialbd.ttf",
]


@lru_cache(maxsize=None)
def load_font(size):
    for name in FONT_CANDIDATES:
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default(size=size)


def to_bgra(pil_img):
    return np.ascontiguousarray(np.array(pil_img)[..., [2, 1, 0, 3]])


def text_color_for(fill_rgb):
    luminance = 0.299 * fill_rgb[0] + 0.587 * fill_rgb[1] + 0.114 * fill_rgb[2]
    return INK if luminance > 150 else (255, 255, 255)


def star_points(cx, cy, r_out, rot_deg=-90.0):
    pts = []
    for i in range(10):
        r = r_out if i % 2 == 0 else r_out * 0.45
        a = math.radians(rot_deg + i * 36)
        pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts


def blend_bgra(frame, img, x, y, alpha_scale=1.0):
    """Alpha-blend a BGRA image onto a BGR frame with its top-left at (x, y)."""
    fh, fw = frame.shape[:2]
    ih, iw = img.shape[:2]
    x0, y0 = max(x, 0), max(y, 0)
    x1, y1 = min(x + iw, fw), min(y + ih, fh)
    if x0 >= x1 or y0 >= y1:
        return
    part = img[y0 - y:y1 - y, x0 - x:x1 - x]
    alpha = part[..., 3:4].astype(np.float32) * (alpha_scale / 255.0)
    roi = frame[y0:y1, x0:x1].astype(np.float32)
    frame[y0:y1, x0:x1] = (roi * (1.0 - alpha) + part[..., :3] * alpha).astype(np.uint8)


@lru_cache(maxsize=64)
def render_pill(text, font_px, fill_rgb, text_rgb=None):
    """A rounded 'bubble' with text, returned as a BGRA image."""
    font = load_font(font_px)
    left, top, right, bottom = font.getbbox(text)
    pad_x, pad_y = int(font_px * 0.9), int(font_px * 0.45)
    w, h = right - left + 2 * pad_x, bottom - top + 2 * pad_y
    shadow = max(2, font_px // 10)
    img = Image.new("RGBA", (w + shadow, h + shadow), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([shadow, shadow, w + shadow - 1, h + shadow - 1], radius=h // 2, fill=(0, 0, 0, 60))
    d.rounded_rectangle([0, 0, w - 1, h - 1], radius=h // 2, fill=fill_rgb + (240,),
                        outline=(255, 255, 255, 255), width=max(2, font_px // 9))
    d.text((pad_x - left, pad_y - top), text, font=font, fill=text_rgb or text_color_for(fill_rgb))
    return to_bgra(img)


def rounded_rect_outline(img, x, y, w, h, r, color, thickness):
    r = min(r, w // 2, h // 2)
    for (cx, cy, start) in ((x + r, y + r, 180), (x + w - r, y + r, 270),
                            (x + w - r, y + h - r, 0), (x + r, y + h - r, 90)):
        cv2.ellipse(img, (cx, cy), (r, r), 0, start, start + 90, color, thickness, cv2.LINE_AA)
    cv2.line(img, (x + r, y), (x + w - r, y), color, thickness, cv2.LINE_AA)
    cv2.line(img, (x + r, y + h), (x + w - r, y + h), color, thickness, cv2.LINE_AA)
    cv2.line(img, (x, y + r), (x, y + h - r), color, thickness, cv2.LINE_AA)
    cv2.line(img, (x + w, y + r), (x + w, y + h - r), color, thickness, cv2.LINE_AA)


class Confetti:
    """Falling stars, used to celebrate the end of a round."""

    def __init__(self, scale=1.0):
        self.scale = scale
        self.parts = []
        self.last = time.time()

    def burst(self, width, height, count=70):
        for _ in range(count):
            self.parts.append({
                "x": random.uniform(0, width), "y": random.uniform(-height * 0.4, 0),
                "vx": random.uniform(-60, 60), "vy": random.uniform(180, 380),
                "r": random.uniform(9, 18) * self.scale, "rot": random.uniform(0, 360),
                "spin": random.uniform(-240, 240), "color": random.choice(CONFETTI_BGR),
            })

    def draw(self, frame):
        now = time.time()
        dt = min(now - self.last, 0.05)
        self.last = now
        if not self.parts:
            return
        height = frame.shape[0]
        alive = []
        for p in self.parts:
            p["x"] += p["vx"] * dt
            p["y"] += p["vy"] * dt
            p["rot"] += p["spin"] * dt
            if p["y"] - p["r"] > height:
                continue
            pts = np.array(star_points(p["x"], p["y"], p["r"], p["rot"]), dtype=np.int32)
            cv2.fillPoly(frame, [pts], p["color"], cv2.LINE_AA)
            alive.append(p)
        self.parts = alive
