"""Food Slice: a kid-friendly fruit-cutting game played by swiping a fingertip in front of the webcam.

Usage:
    python main.py              # play with the default webcam
    python main.py --camera 1   # use a different camera index
"""

import argparse
import math
import os
import random
import time
from collections import deque
from functools import lru_cache

import cv2
import numpy as np
from PIL import Image, ImageDraw

from hand_tracker import HandTracker
from ui import RAINBOW_RGB, Confetti, blend_bgra, load_font, render_pill, rounded_rect_outline, star_points

FRAME_WIDTH, FRAME_HEIGHT = 1280, 720
HOVER_SELECT_TIME = 0.8  # seconds to point at a button before it is pressed
NO_HAND_HINT_DELAY = 1.5  # seconds without a hand before showing "Show me your hand!"
GRAVITY = 1300          # px/s^2 at 1280x720
SLICE_SPEED = 300       # slowest fingertip swipe (px/s at 1280x720) that still cuts
TRAIL_TIME = 0.16       # seconds of fingertip history drawn as the blade
FOOD_SIZE = 130         # sprite diameter at 1280x720
LIVES = 3
COMBO_WINDOW = 0.35     # cuts closer together than this count as one combo
BEST_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "best_score.txt")
CHEERS = ["Yummy!", "Super!", "Wow!", "Nice cut!", "Awesome!", "Great!"]
OUTLINE = (70, 45, 50)


# ---------------------------------------------------------------- sprites
def _to_bgra(img):
    return np.ascontiguousarray(np.array(img)[..., [2, 1, 0, 3]])


class _Pen:
    """Draws on a 2x supersampled square using coordinates in 0..1, for smooth edges after downscaling."""

    def __init__(self, size):
        self.size = size
        self.S = size * 2
        self.img = Image.new("RGBA", (self.S, self.S), (0, 0, 0, 0))
        self.d = ImageDraw.Draw(self.img)
        self.w = max(2, int(self.S * 0.025))

    def p(self, x, y):
        return x * self.S, y * self.S

    def circle(self, cx, cy, r, fill=None, outline=None, width=None):
        S = self.S
        self.d.ellipse([(cx - r) * S, (cy - r) * S, (cx + r) * S, (cy + r) * S], fill=fill, outline=outline,
                       width=self.w if width is None else width)

    def ellipse(self, cx, cy, rx, ry, fill):
        S = self.S
        self.d.ellipse([(cx - rx) * S, (cy - ry) * S, (cx + rx) * S, (cy + ry) * S], fill=fill)

    def blob(self, circles, fill, inset=0.0):
        """Union of circles with a cartoon outline: outline color first, then the fill slightly inside."""
        edge = self.w / self.S
        if inset == 0.0:
            for cx, cy, r in circles:
                self.circle(cx, cy, r, fill=OUTLINE + (255,), width=0)
        for cx, cy, r in circles:
            self.circle(cx, cy, r - edge - inset, fill=fill, width=0)

    def shine(self, cx=0.36, cy=0.32, r=0.08):
        self.ellipse(cx, cy, r, r * 0.65, (255, 255, 255, 110))

    def done(self):
        return _to_bgra(self.img.resize((self.size, self.size), Image.LANCZOS))


def _watermelon(pen, cut):
    if not cut:
        pen.circle(0.5, 0.5, 0.46, fill=(70, 170, 70), outline=OUTLINE)
        for dx in (-0.24, -0.08, 0.08, 0.24):
            hh = math.sqrt(0.43 ** 2 - dx ** 2) * 0.92
            pen.ellipse(0.5 + dx, 0.5, 0.035, hh, (40, 120, 50))
        pen.shine()
        return
    pen.circle(0.5, 0.5, 0.46, fill=(70, 170, 70), outline=OUTLINE)
    pen.circle(0.5, 0.5, 0.40, fill=(235, 250, 220), width=0)
    pen.circle(0.5, 0.5, 0.36, fill=(240, 70, 85), width=0)
    for i in range(8):
        a = math.radians(i * 45 + 20)
        pen.ellipse(0.5 + 0.21 * math.cos(a), 0.5 + 0.21 * math.sin(a), 0.022, 0.035, (40, 30, 30))
    for i in range(4):
        a = math.radians(i * 90 + 45)
        pen.ellipse(0.5 + 0.09 * math.cos(a), 0.5 + 0.09 * math.sin(a), 0.022, 0.035, (40, 30, 30))


def _orange(pen, cut):
    pen.circle(0.5, 0.53, 0.43, fill=(255, 150, 30), outline=OUTLINE)
    if not cut:
        for x, y in ((0.35, 0.6), (0.6, 0.42), (0.65, 0.7), (0.45, 0.78), (0.72, 0.55), (0.3, 0.45)):
            pen.circle(x, y, 0.018, fill=(255, 185, 90), width=0)
        pen.ellipse(0.62, 0.1, 0.11, 0.05, (80, 170, 60))
        pen.shine(0.36, 0.38)
        return
    pen.circle(0.5, 0.53, 0.38, fill=(255, 240, 200), width=0)
    S = pen.S
    box = [(0.5 - 0.34) * S, (0.53 - 0.34) * S, (0.5 + 0.34) * S, (0.53 + 0.34) * S]
    for i in range(8):
        pen.d.pieslice(box, i * 45 + 4, (i + 1) * 45 - 4, fill=(255, 175, 50))
    pen.circle(0.5, 0.53, 0.04, fill=(255, 240, 200), width=0)


def _apple(pen, cut):
    body = [(0.38, 0.56, 0.32), (0.62, 0.56, 0.32)]
    pen.blob(body, (230, 40, 55))
    pen.d.line([pen.p(0.5, 0.3), pen.p(0.54, 0.1)], fill=(110, 70, 40), width=pen.w * 2)
    if not cut:
        pen.d.polygon([pen.p(0.54, 0.18), pen.p(0.68, 0.07), pen.p(0.78, 0.1), pen.p(0.64, 0.2)],
                      fill=(80, 180, 60), outline=OUTLINE)
        pen.shine(0.3, 0.45)
        return
    pen.blob([(0.38, 0.57, 0.27), (0.62, 0.57, 0.27)], (255, 240, 200), inset=0.0001)
    pen.ellipse(0.46, 0.57, 0.025, 0.045, (110, 60, 30))
    pen.ellipse(0.54, 0.57, 0.025, 0.045, (110, 60, 30))


def _kiwi(pen, cut):
    pen.circle(0.5, 0.5, 0.42, fill=(150, 105, 60), outline=OUTLINE)
    if not cut:
        rnd = random.Random(7)
        for _ in range(26):
            a, rr = rnd.uniform(0, 2 * math.pi), rnd.uniform(0, 0.36)
            pen.circle(0.5 + rr * math.cos(a), 0.5 + rr * math.sin(a), 0.012, fill=(115, 80, 45), width=0)
        pen.shine()
        return
    pen.circle(0.5, 0.5, 0.37, fill=(130, 205, 60), width=0)
    pen.circle(0.5, 0.5, 0.15, fill=(240, 248, 205), width=0)
    for i in range(14):
        a = math.radians(i * 360 / 14)
        pen.ellipse(0.5 + 0.22 * math.cos(a), 0.5 + 0.22 * math.sin(a), 0.016, 0.016, (30, 30, 30))


def _donut(pen, cut):
    pen.circle(0.5, 0.5, 0.45, fill=(215, 160, 90), outline=OUTLINE)
    pen.circle(0.5, 0.48, 0.38, fill=(255, 120, 185), width=0)
    rnd = random.Random(3)
    colors = [(255, 255, 255), (80, 200, 255), (255, 220, 40), (120, 220, 120), (180, 120, 255)]
    for _ in range(18):
        a, rr = rnd.uniform(0, 2 * math.pi), rnd.uniform(0.2, 0.33)
        x, y = 0.5 + rr * math.cos(a), 0.48 + rr * math.sin(a)
        t = rnd.uniform(0, math.pi)
        pen.d.line([pen.p(x - 0.03 * math.cos(t), y - 0.03 * math.sin(t)),
                    pen.p(x + 0.03 * math.cos(t), y + 0.03 * math.sin(t))], fill=rnd.choice(colors), width=pen.w)
    pen.circle(0.5, 0.5, 0.13, fill=(0, 0, 0, 0), outline=OUTLINE)


def _strawberry(pen, cut):
    body = [(0.33, 0.4, 0.22), (0.67, 0.4, 0.22), (0.5, 0.55, 0.3), (0.5, 0.72, 0.18)]
    pen.blob(body, (235, 50, 70))
    if cut:
        pen.blob([(0.36, 0.42, 0.16), (0.64, 0.42, 0.16), (0.5, 0.56, 0.23), (0.5, 0.7, 0.12)],
                 (255, 150, 165), inset=0.0001)
        pen.ellipse(0.5, 0.52, 0.08, 0.17, (255, 215, 220))
    else:
        for x, y in ((0.32, 0.42), (0.5, 0.42), (0.68, 0.42), (0.4, 0.57), (0.6, 0.57), (0.5, 0.72),
                     (0.28, 0.32), (0.72, 0.32)):
            pen.ellipse(x, y, 0.015, 0.024, (255, 230, 120))
        pen.shine(0.3, 0.35, 0.06)
    pen.d.polygon(star_points(0.5 * pen.S, 0.2 * pen.S, 0.17 * pen.S), fill=(70, 175, 60), outline=OUTLINE)


def _bomb(pen, _cut):
    pen.d.line([pen.p(0.5, 0.17), pen.p(0.58, 0.08), pen.p(0.68, 0.1)], fill=(150, 110, 70), width=pen.w * 2)
    pen.d.polygon(star_points(0.72 * pen.S, 0.09 * pen.S, 0.08 * pen.S), fill=(255, 210, 40))
    pen.d.rectangle([*pen.p(0.42, 0.14), *pen.p(0.58, 0.24)], fill=(120, 120, 140), outline=OUTLINE, width=pen.w)
    pen.circle(0.5, 0.58, 0.38, fill=(45, 45, 60), outline=(20, 20, 25))
    pen.shine(0.36, 0.44, 0.09)


# name, draw function, juice color (BGR)
FOODS = [
    ("watermelon", _watermelon, (85, 70, 240)),
    ("orange", _orange, (30, 150, 255)),
    ("apple", _apple, (170, 225, 255)),
    ("kiwi", _kiwi, (60, 205, 130)),
    ("donut", _donut, (185, 120, 255)),
    ("strawberry", _strawberry, (90, 60, 235)),
]


@lru_cache(maxsize=None)
def food_sprites(index, size):
    """Returns (whole, left_half, right_half) BGRA sprites; halves keep the full square so they rotate in place."""
    _name, draw, _juice = FOODS[index]
    whole = _Pen(size)
    draw(whole, False)
    cut = _Pen(size)
    draw(cut, True)
    cut_img = cut.done()
    left, right = cut_img.copy(), cut_img.copy()
    left[:, size // 2:, 3] = 0
    right[:, :size // 2, 3] = 0
    return whole.done(), left, right


@lru_cache(maxsize=None)
def bomb_sprite(size):
    pen = _Pen(size)
    _bomb(pen, False)
    return pen.done()


@lru_cache(maxsize=None)
def heart_sprite(size, full):
    pen = _Pen(size)
    fill = (255, 70, 100) if full else (210, 210, 220)
    pen.blob([(0.32, 0.38, 0.22), (0.68, 0.38, 0.22)], fill)
    pen.d.polygon([pen.p(0.13, 0.45), pen.p(0.87, 0.45), pen.p(0.5, 0.9)], fill=OUTLINE + (255,))
    pen.d.polygon([pen.p(0.17, 0.46), pen.p(0.83, 0.46), pen.p(0.5, 0.84)], fill=fill)
    if full:
        pen.shine(0.3, 0.3, 0.06)
    return pen.done()


@lru_cache(maxsize=16)
def rainbow_title(text, px):
    """Big bubbly title, each letter a different rainbow color with a white outline."""
    font = load_font(px)
    stroke = max(3, px // 12)
    width = int(sum(font.getlength(ch) for ch in text)) + 2 * stroke + 8
    height = int(px * 1.4) + 2 * stroke
    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    x, i = stroke + 4, 0
    for ch in text:
        if ch.strip():
            color = RAINBOW_RGB[i % len(RAINBOW_RGB)]
            i += 1
        else:
            color = (0, 0, 0)
        d.text((x + 4, stroke + 5), ch, font=font, fill=(0, 0, 0, 70), stroke_width=stroke, stroke_fill=(0, 0, 0, 70))
        d.text((x, stroke), ch, font=font, fill=color, stroke_width=stroke, stroke_fill=(255, 255, 255))
        x += font.getlength(ch)
    return _to_bgra(img)


def rotate_sprite(img, angle):
    h, w = img.shape[:2]
    m = cv2.getRotationMatrix2D((w / 2, h / 2), angle, 1.0)
    return cv2.warpAffine(img, m, (w, h), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT,
                          borderValue=(0, 0, 0, 0))


def seg_point_distance(ax, ay, bx, by, px, py):
    dx, dy = bx - ax, by - ay
    length_sq = dx * dx + dy * dy
    t = 0.0 if length_sq == 0 else max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / length_sq))
    return math.hypot(ax + t * dx - px, ay + t * dy - py)


# ---------------------------------------------------------------- game objects
class Flyer:
    """Anything thrown through the air: whole food, a cut half, or a bomb."""

    def __init__(self, sprite, x, y, vx, vy, spin, kind, food_index=-1):
        self.sprite = sprite
        self.x, self.y, self.vx, self.vy = x, y, vx, vy
        self.angle, self.spin = random.uniform(0, 360), spin
        self.kind = kind  # "food", "half", "bomb"
        self.food_index = food_index
        self.radius = sprite.shape[0] * 0.42

    def update(self, dt, gravity):
        self.vy += gravity * dt
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.angle += self.spin * dt

    def draw(self, frame):
        img = rotate_sprite(self.sprite, self.angle)
        size = img.shape[0]
        blend_bgra(frame, img, int(self.x - size / 2), int(self.y - size / 2))


class PillButton:
    def __init__(self, label, fill_rgb, action, font_px):
        self.img = render_pill(label, font_px, fill_rgb)
        self.h, self.w = self.img.shape[:2]
        self.action = action
        self.x = self.y = 0

    def contains(self, px, py):
        return self.x <= px <= self.x + self.w and self.y <= py <= self.y + self.h


# ---------------------------------------------------------------- game
class FoodSliceGame:
    def __init__(self, camera_index=0):
        self.cap = cv2.VideoCapture(camera_index)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)
        ok, frame = self.cap.read()
        if not ok:
            raise RuntimeError("Could not access the webcam.")
        self.height, self.width = frame.shape[:2]
        self.s = min(self.width / 1280, self.height / 720)
        self.tracker = HandTracker(max_hands=1)
        self.confetti = Confetti(self.s)

        self.food_size = self.S(FOOD_SIZE)
        self.gravity = GRAVITY * self.s
        self.tint = np.full((self.height, self.width, 3), (235, 225, 255), dtype=np.uint8)

        btn_px = max(14, self.S(34))
        self.screen_buttons = {
            "start": [PillButton("Play!", (140, 220, 120), "play", self.S(44)),
                      PillButton("Exit", (255, 175, 175), "exit", btn_px)],
            "over": [PillButton("Play again!", (140, 220, 120), "play", self.S(44)),
                     PillButton("Exit", (255, 175, 175), "exit", btn_px)],
            "play": [PillButton("Stop", (255, 205, 210), "stop", max(12, self.S(26)))],
        }
        self._layout_buttons()

        self.best = self._load_best()
        self.state = "start"
        self.running = True
        self._reset_round()

        self.trail = deque()
        self.hover_button = None
        self.hover_start = 0.0
        self.hover_seen = 0.0
        self.last_hand_time = time.time()
        self.last_time = time.time()

    def S(self, v):
        return int(round(v * self.s))

    def _layout_buttons(self):
        for state in ("start", "over"):
            row = self.screen_buttons[state]
            gap = self.S(30)
            total = sum(b.w for b in row) + gap * (len(row) - 1)
            x = (self.width - total) // 2
            y = int(self.height * 0.72)
            for b in row:
                b.x, b.y = x, y + (row[0].h - b.h) // 2
                x += b.w + gap
        stop = self.screen_buttons["play"][0]
        stop.x, stop.y = self.width - stop.w - self.S(20), self.S(18)

    def _load_best(self):
        try:
            with open(BEST_FILE) as f:
                return int(f.read().strip() or 0)
        except (OSError, ValueError):
            return 0

    def _save_best(self):
        try:
            with open(BEST_FILE, "w") as f:
                f.write(str(self.best))
        except OSError:
            pass

    def _reset_round(self):
        self.flyers = []
        self.particles = []
        self.popups = []
        self.score = 0
        self.lives = LIVES
        self.round_start = time.time()
        self.next_spawn = time.time() + 0.6
        self.combo = 0
        self.last_cut_time = 0.0
        self.flash_until = 0.0
        self.over_at = None
        self.new_best = False

    # ---------- spawning ----------
    def _spawn_wave(self):
        now = time.time()
        playing = self.state == "play"
        elapsed = now - self.round_start
        count = 1 if not playing else random.choice([1, 1, 2, 2, 3] if elapsed > 20 else [1, 1, 2])
        bomb_slot = random.randrange(count) if playing and elapsed > 8 and random.random() < 0.3 else -1
        for i in range(count):
            x = random.uniform(self.width * 0.2, self.width * 0.8)
            y = self.height + self.food_size * 0.6
            peak = random.uniform(self.height * 0.15, self.height * 0.45)
            vy = -math.sqrt(2 * self.gravity * (y - peak))
            vx = (self.width / 2 - x) * random.uniform(0.3, 0.8) + random.uniform(-80, 80) * self.s
            spin = random.uniform(-160, 160)
            if i == bomb_slot:
                self.flyers.append(Flyer(bomb_sprite(self.food_size), x, y, vx, vy, spin, "bomb"))
            else:
                idx = random.randrange(len(FOODS))
                whole = food_sprites(idx, self.food_size)[0]
                self.flyers.append(Flyer(whole, x, y, vx, vy, spin, "food", idx))
        if playing:
            interval = max(0.75, 1.5 - elapsed * 0.012)
        else:
            interval = 1.6
        self.next_spawn = now + interval * random.uniform(0.8, 1.2)

    # ---------- cutting ----------
    def _cut_food(self, f, swipe_dx, swipe_dy):
        now = time.time()
        _whole, left, right = food_sprites(f.food_index, self.food_size)
        # halves fly apart sideways to the swipe direction
        length = math.hypot(swipe_dx, swipe_dy) or 1.0
        nx, ny = -swipe_dy / length, swipe_dx / length
        push = 220 * self.s
        for img, sign in ((left, -1), (right, 1)):
            half = Flyer(img, f.x, f.y, f.vx + sign * nx * push, f.vy + sign * ny * push - 120 * self.s,
                         f.spin + sign * 200, "half")
            half.angle = f.angle
            self.flyers.append(half)
        self._splash(f.x, f.y, FOODS[f.food_index][2], 22)

        if self.state != "play":
            return
        self.combo = self.combo + 1 if now - self.last_cut_time < COMBO_WINDOW else 1
        self.last_cut_time = now
        self.score += 1
        self._popup("+1", f.x, f.y, (255, 236, 179))
        if self.combo >= 3:
            self.score += 1
            self._popup(f"Combo x{self.combo}!", self.width / 2, self.height * 0.32, (255, 182, 193), big=True)
        elif random.random() < 0.18:
            self._popup(random.choice(CHEERS), f.x, f.y - self.food_size * 0.6, (190, 240, 190))

    def _hit_bomb(self, b):
        self._splash(b.x, b.y, (0, 140, 255), 40, speed=650)
        self._splash(b.x, b.y, (60, 60, 60), 20, speed=400)
        self.flash_until = time.time() + 0.25
        if self.state == "play":
            self.lives -= 1
            self._popup("Oh no! A bomb!", self.width / 2, self.height * 0.32, (255, 175, 175), big=True)
            if self.lives <= 0 and self.over_at is None:
                self.over_at = time.time() + 1.0

    def _splash(self, x, y, color, count, speed=450):
        for _ in range(count):
            a = random.uniform(0, 2 * math.pi)
            v = random.uniform(0.3, 1.0) * speed * self.s
            self.particles.append([x, y, v * math.cos(a), v * math.sin(a) - 150 * self.s,
                                   random.uniform(4, 11) * self.s, color, time.time()])

    def _popup(self, text, x, y, fill_rgb, big=False):
        img = render_pill(text, max(12, self.S(40 if big else 28)), fill_rgb)
        self.popups.append((img, x, y, time.time()))

    def _check_cuts(self):
        if len(self.trail) < 2:
            return
        (ax, ay, at), (bx, by, bt) = self.trail[-2], self.trail[-1]
        dt = max(bt - at, 1e-3)
        if math.hypot(bx - ax, by - ay) / dt < SLICE_SPEED * self.s:
            return
        for f in list(self.flyers):
            if f.kind == "half":
                continue
            if seg_point_distance(ax, ay, bx, by, f.x, f.y) < f.radius:
                self.flyers.remove(f)
                if f.kind == "food":
                    self._cut_food(f, bx - ax, by - ay)
                else:
                    self._hit_bomb(f)

    # ---------- buttons ----------
    def _update_hover(self, tip):
        now = time.time()
        btn = None
        if tip is not None:
            btn = next((b for b in self.screen_buttons[self.state] if b.contains(*tip)), None)
        if btn is None:
            if self.hover_button is not None and now - self.hover_seen > 0.3:
                self.hover_button = None
            return
        self.hover_seen = now
        if btn is not self.hover_button:
            self.hover_button, self.hover_start = btn, now
        elif now - self.hover_start >= HOVER_SELECT_TIME:
            self.hover_button = None
            self._press(btn.action)

    def _press(self, action):
        if action == "play":
            self._reset_round()
            self.state = "play"
            self._popup("Go!", self.width / 2, self.height * 0.4, (140, 220, 120), big=True)
        elif action == "stop":
            self._game_over()
        elif action == "exit":
            self.running = False

    def _game_over(self):
        self.state = "over"
        self.over_at = None
        self.flyers = [f for f in self.flyers if f.kind == "half"]
        if self.score > self.best:
            self.best = self.score
            self.new_best = self.score > 0
            self._save_best()
        if self.score > 0:
            self.confetti.burst(self.width, self.height)

    # ---------- drawing ----------
    def _draw_trail(self, frame):
        pts = list(self.trail)
        n = len(pts)
        for i in range(1, n):
            k = i / n
            a = (int(pts[i - 1][0]), int(pts[i - 1][1]))
            b = (int(pts[i][0]), int(pts[i][1]))
            cv2.line(frame, a, b, (255, 220, 120), max(2, int(self.S(22) * k)), cv2.LINE_AA)
            cv2.line(frame, a, b, (255, 255, 255), max(1, int(self.S(10) * k)), cv2.LINE_AA)

    def _draw_particles(self, frame, dt):
        now = time.time()
        alive = []
        for p in self.particles:
            p[3] += self.gravity * dt
            p[0] += p[2] * dt
            p[1] += p[3] * dt
            life = now - p[6]
            if life > 0.9 or p[1] > self.height + 20:
                continue
            r = max(1, int(p[4] * (1 - life / 0.9)))
            cv2.circle(frame, (int(p[0]), int(p[1])), r, p[5], -1, cv2.LINE_AA)
            alive.append(p)
        self.particles = alive

    def _draw_popups(self, frame):
        now = time.time()
        alive = []
        for img, x, y, t0 in self.popups:
            age = now - t0
            if age > 0.9:
                continue
            h, w = img.shape[:2]
            fade = min(1.0, (0.9 - age) / 0.3)
            blend_bgra(frame, img, int(x - w / 2), int(y - h / 2 - age * self.S(70)), fade)
            alive.append((img, x, y, t0))
        self.popups = alive

    def _draw_buttons(self, frame):
        for b in self.screen_buttons[self.state]:
            blend_bgra(frame, b.img, b.x, b.y)
            if b is self.hover_button:
                progress = min(1.0, (time.time() - self.hover_start) / HOVER_SELECT_TIME)
                pad = self.S(6)
                rounded_rect_outline(frame, b.x - pad, b.y - pad, b.w + 2 * pad, b.h + 2 * pad, b.h // 2 + pad,
                                     (0, 140, 255), max(3, self.S(5)))
                bar_y = b.y + b.h + self.S(8)
                cv2.line(frame, (b.x + b.h // 2, bar_y), (b.x + b.w - b.h // 2, bar_y), (255, 255, 255),
                         max(4, self.S(10)), cv2.LINE_AA)
                if progress > 0:
                    end = b.x + b.h // 2 + int((b.w - b.h) * progress)
                    cv2.line(frame, (b.x + b.h // 2, bar_y), (end, bar_y), (255, 0, 220), max(4, self.S(10)),
                             cv2.LINE_AA)

    def _center(self, frame, img, y):
        blend_bgra(frame, img, (self.width - img.shape[1]) // 2, int(y))

    def _draw_hud(self, frame):
        score = render_pill(f"Score: {self.score}", max(14, self.S(34)), (255, 236, 179))
        blend_bgra(frame, score, self.S(20), self.S(16))
        hs = self.S(54)
        stop = self.screen_buttons["play"][0]
        x = stop.x - self.S(20) - LIVES * (hs + self.S(6))
        for i in range(LIVES):
            blend_bgra(frame, heart_sprite(hs, i < self.lives), x + i * (hs + self.S(6)), self.S(16))

    def _draw_screen_text(self, frame):
        if self.state == "start":
            self._center(frame, rainbow_title("Food Slice!", self.S(110)), self.height * 0.1)
            self._center(frame, render_pill("Swipe your finger to cut the food!", max(14, self.S(32)),
                                            (255, 255, 255)), self.height * 0.36)
            tip = render_pill("Don't cut the bombs!", max(12, self.S(26)), (255, 205, 210))
            bomb = bomb_sprite(self.S(64))
            total = bomb.shape[1] + self.S(10) + tip.shape[1]
            x = (self.width - total) // 2
            y = int(self.height * 0.5)
            blend_bgra(frame, bomb, x, y)
            blend_bgra(frame, tip, x + bomb.shape[1] + self.S(10), y + (bomb.shape[0] - tip.shape[0]) // 2)
        elif self.state == "over":
            self._center(frame, rainbow_title("Great job!", self.S(100)), self.height * 0.1)
            self._center(frame, render_pill(f"You cut {self.score} foods!", max(14, self.S(44)), (255, 236, 179)),
                         self.height * 0.36)
            best = "New best score!" if self.new_best else f"Best: {self.best}"
            self._center(frame, render_pill(best, max(12, self.S(28)),
                                            (255, 224, 130) if self.new_best else (255, 255, 255)),
                         self.height * 0.52)

    def _draw_cursor(self, frame, tip):
        r = self.S(14)
        cv2.circle(frame, tip, r, (255, 255, 255), -1, cv2.LINE_AA)
        cv2.circle(frame, tip, r, (255, 0, 220), max(2, self.S(4)), cv2.LINE_AA)

    # ---------- main loop ----------
    def run(self):
        window = "Food Slice"
        cv2.namedWindow(window)

        while self.running:
            ok, frame = self.cap.read()
            if not ok:
                break
            frame = cv2.flip(frame, 1)
            now = time.time()
            dt = min(now - self.last_time, 0.05)
            self.last_time = now

            self.tracker.process(frame)
            points = self.tracker.get_landmark_list(frame)
            tip = None
            if points:
                self.last_hand_time = now
                tip = points[8][:2]
                self.trail.append((tip[0], tip[1], now))
            else:
                self.trail.clear()
            while self.trail and now - self.trail[0][2] > TRAIL_TIME:
                self.trail.popleft()

            if self.state != "over" and now >= self.next_spawn:
                self._spawn_wave()
            for f in self.flyers:
                f.update(dt, self.gravity)
            self.flyers = [f for f in self.flyers if f.y < self.height + self.food_size or f.vy < 0]
            self._check_cuts()
            self._update_hover(tip)
            if self.over_at is not None and now >= self.over_at:
                self._game_over()

            if self.state != "play":
                frame = cv2.addWeighted(frame, 0.6, self.tint, 0.4, 0)
            for f in self.flyers:
                f.draw(frame)
            self._draw_particles(frame, dt)
            if now < self.flash_until:
                frame = cv2.addWeighted(frame, 0.4, np.full_like(frame, 255), 0.6, 0)

            self._draw_screen_text(frame)
            if self.state == "play":
                self._draw_hud(frame)
            self._draw_buttons(frame)
            self._draw_popups(frame)
            self.confetti.draw(frame)
            self._draw_trail(frame)
            if tip:
                self._draw_cursor(frame, tip)
            elif now - self.last_hand_time > NO_HAND_HINT_DELAY:
                hint = render_pill("Show me your hand!", max(14, self.S(40)), (255, 255, 255))
                bob = int(self.S(8) * math.sin(now * 4))
                self._center(frame, hint, self.height * 0.82 + bob)

            cv2.imshow(window, frame)
            key = cv2.waitKey(1) & 0xFF
            if key in (ord('q'), 27):
                self.running = False
            elif key == ord(' ') and self.state != "play":
                self._press("play")

        self.cap.release()
        cv2.destroyWindow(window)
        self.tracker.close()


def main():
    parser = argparse.ArgumentParser(description="Food Slice - cut flying food with your finger.")
    parser.add_argument("--camera", type=int, default=0, help="webcam index (default: 0)")
    args = parser.parse_args()
    FoodSliceGame(args.camera).run()


if __name__ == "__main__":
    main()
