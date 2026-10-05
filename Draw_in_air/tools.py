import math
import random
import time
from functools import lru_cache

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

import config

# Colors used to paint the UI with Pillow are RGB(A); colors passed to OpenCV are BGR.
INK = (40, 50, 90)
PANEL_FILL = (255, 255, 255, 215)
TOOL_FILL = (186, 225, 255)
SIZE_FILL = (200, 240, 200)
ACTIONS = [
    ("Undo", "undo", (255, 236, 179)),
    ("Clear", "clear", (255, 205, 210)),
    ("Save", "save", (255, 224, 130)),
    ("3D", "mode3d", (225, 205, 255)),
    ("Exit", "quit", (255, 175, 175)),
]
HELP_PILLS = [
    ("1 finger up = Draw", (255, 182, 193)),
    ("Point at a button & hold = Pick", (173, 216, 255)),
    ("Fist = Rest", (190, 240, 190)),
]
RAINBOW_RGB = [(255, 70, 70), (255, 150, 40), (255, 220, 40), (80, 200, 80),
               (60, 170, 255), (90, 90, 230), (190, 90, 220)]
CONFETTI_BGR = [(50, 50, 240), (0, 150, 255), (0, 230, 255), (60, 200, 60),
                (230, 110, 40), (220, 80, 160), (180, 105, 255)]
SELECTED_BGR = (0, 140, 255)
HOVER_BGR = (255, 0, 220)

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


def bgr_to_rgb(color):
    return color[2], color[1], color[0]


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


def _to_bgra(pil_img):
    return np.ascontiguousarray(np.array(pil_img)[..., [2, 1, 0, 3]])


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
    return _to_bgra(img)


def rounded_rect_outline(img, x, y, w, h, r, color, thickness):
    r = min(r, w // 2, h // 2)
    for (cx, cy, start) in ((x + r, y + r, 180), (x + w - r, y + r, 270),
                            (x + w - r, y + h - r, 0), (x + r, y + h - r, 90)):
        cv2.ellipse(img, (cx, cy), (r, r), 0, start, start + 90, color, thickness, cv2.LINE_AA)
    cv2.line(img, (x + r, y), (x + w - r, y), color, thickness, cv2.LINE_AA)
    cv2.line(img, (x + r, y + h), (x + w - r, y + h), color, thickness, cv2.LINE_AA)
    cv2.line(img, (x, y + r), (x, y + h - r), color, thickness, cv2.LINE_AA)
    cv2.line(img, (x + w, y + r), (x + w, y + h - r), color, thickness, cv2.LINE_AA)


def draw_icon(d, kind, cx, cy, r):
    """Draw a simple cartoon icon centred at (cx, cy) with half-size r."""
    lw = max(2, round(r * 0.16))

    def diag(u, v):  # axis running from bottom-left to top-right
        return (cx + (u * 0.707 + v * 0.707) * r, cy + (-u * 0.707 + v * 0.707) * r)

    if kind == "pen":
        d.polygon([diag(-0.5, -0.3), diag(0.75, -0.3), diag(0.75, 0.3), diag(-0.5, 0.3)],
                  fill=(255, 200, 40), outline=INK, width=lw)
        d.polygon([diag(0.75, -0.3), diag(1.05, -0.3), diag(1.05, 0.3), diag(0.75, 0.3)],
                  fill=(255, 140, 170), outline=INK, width=lw)
        d.polygon([diag(-1.05, 0), diag(-0.5, -0.3), diag(-0.5, 0.3)],
                  fill=(245, 215, 175), outline=INK, width=lw)
        d.polygon([diag(-1.05, 0), diag(-0.85, -0.11), diag(-0.85, 0.11)], fill=INK)
    elif kind == "line":
        a, b = (cx - r, cy + 0.7 * r), (cx + r, cy - 0.7 * r)
        d.line([a, b], fill=INK, width=lw + 2)
        for px, py in (a, b):
            d.ellipse([px - 0.22 * r, py - 0.22 * r, px + 0.22 * r, py + 0.22 * r], fill=(255, 110, 140))
    elif kind == "rectangle":
        d.rounded_rectangle([cx - r, cy - 0.75 * r, cx + r, cy + 0.75 * r], radius=int(0.2 * r),
                            fill=(255, 255, 255), outline=INK, width=lw)
    elif kind == "circle":
        d.ellipse([cx - 0.85 * r, cy - 0.85 * r, cx + 0.85 * r, cy + 0.85 * r],
                  fill=(255, 255, 255), outline=INK, width=lw)
    elif kind == "eraser":
        d.polygon([diag(-0.95, -0.42), diag(-0.05, -0.42), diag(-0.05, 0.42), diag(-0.95, 0.42)],
                  fill=(255, 140, 170), outline=INK, width=lw)
        d.polygon([diag(-0.05, -0.42), diag(0.95, -0.42), diag(0.95, 0.42), diag(-0.05, 0.42)],
                  fill=(140, 200, 255), outline=INK, width=lw)
    elif kind == "undo":
        cy2 = cy + 0.15 * r
        d.arc([cx - 0.75 * r, cy2 - 0.75 * r, cx + 0.75 * r, cy2 + 0.75 * r], 180, 360, fill=INK, width=lw + 1)
        ax = cx - 0.75 * r
        d.polygon([(ax - 0.4 * r, cy2), (ax + 0.4 * r, cy2), (ax, cy2 + 0.55 * r)], fill=INK)
    elif kind == "clear":
        d.polygon([(cx - 0.6 * r, cy - 0.4 * r), (cx + 0.6 * r, cy - 0.4 * r),
                   (cx + 0.45 * r, cy + 0.95 * r), (cx - 0.45 * r, cy + 0.95 * r)],
                  fill=(210, 225, 240), outline=INK, width=lw)
        d.rounded_rectangle([cx - 0.85 * r, cy - 0.72 * r, cx + 0.85 * r, cy - 0.45 * r],
                            radius=int(0.1 * r), fill=(210, 225, 240), outline=INK, width=lw)
        d.rectangle([cx - 0.25 * r, cy - 0.95 * r, cx + 0.25 * r, cy - 0.72 * r], outline=INK, width=lw)
        for dx in (-0.22, 0.22):
            d.line([(cx + dx * r, cy - 0.15 * r), (cx + dx * r, cy + 0.7 * r)], fill=INK, width=max(1, lw - 1))
    elif kind == "save":
        d.polygon(star_points(cx, cy + 0.05 * r, 1.05 * r), fill=(255, 200, 0), outline=INK, width=lw)
    elif kind == "mode3d":
        x0, y0, side, off = cx - 0.8 * r, cy - 0.3 * r, 1.1 * r, 0.45 * r
        d.rectangle([x0 + off, y0 - off, x0 + off + side, y0 - off + side], outline=INK, width=lw)
        for px, py in ((x0, y0), (x0 + side, y0), (x0, y0 + side), (x0 + side, y0 + side)):
            d.line([(px, py), (px + off, py - off)], fill=INK, width=lw)
        d.rectangle([x0, y0, x0 + side, y0 + side], fill=(200, 170, 255), outline=INK, width=lw)
    elif kind == "quit":
        d.rounded_rectangle([cx - 0.6 * r, cy - 0.95 * r, cx + 0.6 * r, cy + 0.95 * r], radius=int(0.15 * r),
                            fill=(205, 140, 90), outline=INK, width=lw)
        d.ellipse([cx + 0.2 * r, cy - 0.05 * r, cx + 0.42 * r, cy + 0.17 * r], fill=(255, 220, 80))


class Button:
    def __init__(self, x, y, w, h, label, action, fill=None, round_shape=False):
        self.x, self.y, self.w, self.h = x, y, w, h
        self.label = label
        self.action = action  # (kind, value) e.g. ("color", (0,0,255)) / ("tool", "pen") / ("action", "clear")
        self.fill = fill
        self.round_shape = round_shape

    def contains(self, px, py):
        return self.x <= px <= self.x + self.w and self.y <= py <= self.y + self.h

    def center(self):
        return self.x + self.w // 2, self.y + self.h // 2


class ToolBar:
    """Kid-friendly UI: tool buttons on top, paint colors down the left, gesture help at the bottom."""

    def __init__(self, frame_width, frame_height):
        self.width, self.frame_height = frame_width, frame_height
        self.s = min(frame_width / 1280, frame_height / 720)
        self.top_h = self.S(112)
        self.left_w = self.S(86)
        self.bottom_y = frame_height - self.S(54)
        self.buttons = []
        self._layout()
        self.layers = self._prepare_layers(self._render_static())

    def S(self, v):
        return int(round(v * self.s))

    def _layout(self):
        size, gap, group_gap = self.S(80), self.S(10), self.S(26)
        groups = [
            [(label, ("tool", tool), TOOL_FILL) for label, tool in config.TOOLS],
            [(name, ("brush", b), SIZE_FILL) for name, b in zip(config.BRUSH_NAMES, config.BRUSH_SIZES)],
            [(label, ("action", value), fill) for label, value, fill in ACTIONS],
        ]
        count = sum(len(g) for g in groups)
        total = count * size + (count - len(groups)) * gap + (len(groups) - 1) * group_gap
        x, y = (self.width - total) // 2, self.S(12)
        for group in groups:
            for label, action, fill in group:
                self.buttons.append(Button(x, y, size, size, label, action, fill))
                x += size + gap
            x += group_gap - gap

        d, gap = self.S(52), self.S(6)
        x, y = (self.left_w - d) // 2, self.S(126)
        for name, color in config.COLORS:
            self.buttons.append(Button(x, y, d, d, name, ("color", color), color, round_shape=True))
            y += d + gap
        self.colors_bottom = y - gap

    def _render_static(self):
        S = self.S
        img = Image.new("RGBA", (self.width, self.frame_height), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)

        d.rounded_rectangle([S(6), -S(40), self.width - S(6), self.top_h - S(4)], radius=S(26), fill=PANEL_FILL)
        d.rounded_rectangle([S(4), S(116), self.left_w - S(4), self.colors_bottom + S(10)],
                            radius=S(26), fill=PANEL_FILL)

        label_font = load_font(max(10, S(15)))
        for b in self.buttons:
            kind = b.action[0]
            sh = S(3)
            if b.round_shape:
                d.ellipse([b.x + sh, b.y + sh, b.x + b.w + sh, b.y + b.h + sh], fill=(0, 0, 0, 45))
                box = [b.x, b.y, b.x + b.w, b.y + b.h]
                if b.action[1] == config.RAINBOW:
                    step = 360 / len(RAINBOW_RGB)
                    for i, c in enumerate(RAINBOW_RGB):
                        d.pieslice(box, -90 + i * step, -90 + (i + 1) * step, fill=c)
                    d.ellipse(box, outline=(255, 255, 255), width=S(4))
                else:
                    rgb = bgr_to_rgb(b.fill)
                    outline = (190, 195, 210) if rgb == (255, 255, 255) else (255, 255, 255)
                    d.ellipse(box, fill=rgb, outline=outline, width=S(4))
                continue

            d.rounded_rectangle([b.x + sh, b.y + sh, b.x + b.w + sh, b.y + b.h + sh], radius=S(22), fill=(0, 0, 0, 45))
            d.rounded_rectangle([b.x, b.y, b.x + b.w, b.y + b.h], radius=S(22), fill=b.fill,
                                outline=(255, 255, 255), width=S(3))
            cx, icon_cy = b.x + b.w / 2, b.y + S(32)
            if kind == "brush":
                rr = b.action[1] / 2 * self.s * 1.15
                d.ellipse([cx - rr, icon_cy - rr, cx + rr, icon_cy + rr], fill=INK)
            else:
                draw_icon(d, b.action[1], cx, icon_cy, S(19))
            d.text((cx, b.y + b.h - S(13)), b.label, font=label_font, fill=INK, anchor="mm")

        # gesture help along the bottom
        pill_font = max(10, S(20))
        pills = [render_pill(text, pill_font, fill) for text, fill in HELP_PILLS]
        gap = S(14)
        total = sum(p.shape[1] for p in pills) + gap * (len(pills) - 1)
        x = (self.width - total) // 2
        out = _to_bgra(img)
        for p in pills:
            y = self.bottom_y + (self.frame_height - self.bottom_y - p.shape[0]) // 2
            _paste_bgra(out, p, x, y)
            x += p.shape[1] + gap
        return out

    def _prepare_layers(self, overlay):
        """Split the static overlay into its visible boxes with pre-multiplied colors, so each frame is cheap."""
        regions = [
            (0, 0, self.width, self.top_h),
            (0, self.top_h, self.left_w, self.bottom_y),
            (0, self.bottom_y, self.width, self.frame_height),
        ]
        layers = []
        for x0, y0, x1, y1 in regions:
            part = overlay[y0:y1, x0:x1]
            ys, xs = np.nonzero(part[..., 3])
            if len(ys) == 0:
                continue
            bx0, bx1, by0, by1 = xs.min(), xs.max() + 1, ys.min(), ys.max() + 1
            crop = part[by0:by1, bx0:bx1].astype(np.float32)
            alpha = crop[..., 3:4] / 255.0
            layers.append(((slice(y0 + by0, y0 + by1), slice(x0 + bx0, x0 + bx1)),
                           np.ascontiguousarray(np.repeat(1.0 - alpha, 3, axis=2)),
                           np.ascontiguousarray(crop[..., :3] * alpha)))
        return layers

    def is_ui_area(self, px, py):
        return py < self.top_h or py >= self.bottom_y or (px < self.left_w and py < self.colors_bottom + self.S(14))

    def hit_test(self, px, py):
        for b in self.buttons:
            if b.contains(px, py):
                return b
        return None

    def draw(self, frame, active_color, active_tool, active_brush, hover_button=None, hover_progress=0.0):
        for region, inv_alpha, premult in self.layers:
            roi = frame[region].astype(np.float32)
            frame[region] = cv2.add(cv2.multiply(roi, inv_alpha), premult).astype(np.uint8)

        thick = max(3, self.S(5))
        for b in self.buttons:
            kind, value = b.action
            active = ((kind == "color" and value == active_color) or
                      (kind == "tool" and value == active_tool) or
                      (kind == "brush" and value == active_brush))
            if active:
                if b.round_shape:
                    cx, cy = b.center()
                    cv2.circle(frame, (cx, cy), b.w // 2 + self.S(6), SELECTED_BGR, thick, cv2.LINE_AA)
                else:
                    pad = self.S(5)
                    rounded_rect_outline(frame, b.x - pad, b.y - pad, b.w + 2 * pad, b.h + 2 * pad,
                                         self.S(26), SELECTED_BGR, thick)

            if hover_button is b and hover_progress > 0:
                cx, cy = b.center()
                radius = int(b.w * (0.72 if b.round_shape else 0.62))
                cv2.circle(frame, (cx, cy), radius, (255, 255, 255), thick + 4, cv2.LINE_AA)
                angle = int(360 * min(hover_progress, 1.0))
                cv2.ellipse(frame, (cx, cy), (radius, radius), -90, 0, angle, HOVER_BGR, thick + 2, cv2.LINE_AA)

        return frame


def _paste_bgra(dst, src, x, y):
    """Composite a BGRA image onto a BGRA image (both straight alpha)."""
    h, w = src.shape[:2]
    region = dst[y:y + h, x:x + w]
    a = src[..., 3:4].astype(np.float32) / 255.0
    region[..., :3] = (src[..., :3] * a + region[..., :3] * (1 - a)).astype(np.uint8)
    region[..., 3] = np.maximum(region[..., 3], src[..., 3])


class Confetti:
    """Falling stars, used to celebrate a saved picture."""

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
