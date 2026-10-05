"""Ice Cream Catch: ice cream falls from the sky and kids catch it on cones balanced on their heads.

Several kids can play at once - every face the camera sees becomes a player.

Usage:
    python main.py              # play with the default webcam
    python main.py --camera 1   # use a different camera index
"""

import argparse
import math
import os
import random
import time
from functools import lru_cache

import cv2
import numpy as np
from PIL import Image, ImageDraw

from faces import FaceDetector, PlayerTracker
from sprites import FLAVORS, broccoli_sprite, cone_sprite, scoop_sprite, sparkle_sprite
from ui import RAINBOW_RGB, Confetti, blend_bgra, load_font, render_pill, rounded_rect_outline, to_bgra

FRAME_WIDTH, FRAME_HEIGHT = 1280, 720
ROUND_TIME = 60          # seconds per round
COUNTDOWN = 3
TOWER_SIZE = 5           # scoops in a full tower (bonus, then the tower is "eaten")
HOLD_TIME = 1.2          # seconds a head must stay on a button to press it
ITEM_SIZE = 96           # falling scoop size at 1280x720
FALL_SPEED = 170         # px/s at 1280x720, rises during the round
BEST_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "best_score.txt")
CHEERS = ["Yum!", "Tasty!", "Nice catch!", "Wow!", "Super!"]


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
        color = RAINBOW_RGB[i % len(RAINBOW_RGB)]
        if ch.strip():
            i += 1
        d.text((x + 4, stroke + 5), ch, font=font, fill=(0, 0, 0, 70), stroke_width=stroke, stroke_fill=(0, 0, 0, 70))
        d.text((x, stroke), ch, font=font, fill=color, stroke_width=stroke, stroke_fill=(255, 255, 255))
        x += font.getlength(ch)
    return to_bgra(img)


class Item:
    """Something falling from the sky: a scoop (flavor >= 0), a golden scoop (-1) or broccoli."""

    def __init__(self, kind, flavor, x, y, vy, size):
        self.kind, self.flavor = kind, flavor
        self.x0, self.x, self.y, self.vy = x, x, y, vy
        self.size = size
        self.phase = random.uniform(0, 2 * math.pi)
        if kind == "broccoli":
            self.sprite = broccoli_sprite(size)
        else:
            self.sprite = scoop_sprite(flavor, size)

    def update(self, dt, t):
        self.y += self.vy * dt
        self.x = self.x0 + math.sin(t * 1.6 + self.phase) * self.size * 0.3

    def draw(self, frame, t):
        s = self.sprite.shape[0]
        if self.kind == "gold":
            sp = sparkle_sprite(int(s * 1.5))
            blend_bgra(frame, sp, int(self.x - sp.shape[1] / 2), int(self.y - sp.shape[0] / 2),
                       0.6 + 0.4 * math.sin(t * 8))
        blend_bgra(frame, self.sprite, int(self.x - s / 2), int(self.y - s / 2))


class PillButton:
    def __init__(self, label, fill_rgb, action, font_px):
        self.img = render_pill(label, font_px, fill_rgb)
        self.h, self.w = self.img.shape[:2]
        self.action = action
        self.x = self.y = 0

    def overlaps(self, x, y, w, h):
        return x < self.x + self.w and x + w > self.x and y < self.y + self.h and y + h > self.y


class IceCreamCatch:
    def __init__(self, camera_index=0):
        self.cap = cv2.VideoCapture(camera_index)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)
        ok, frame = self.cap.read()
        if not ok:
            raise RuntimeError("Could not access the webcam.")
        self.height, self.width = frame.shape[:2]
        self.s = min(self.width / 1280, self.height / 720)

        self.detector = FaceDetector()
        self.tracker = PlayerTracker()
        self.confetti = Confetti(self.s)
        self.tint = np.full((self.height, self.width, 3), (240, 230, 255), dtype=np.uint8)

        # big and in the middle, where a kid's face naturally is
        play = PillButton("Play!", (140, 220, 120), "play", self.S(64))
        again = PillButton("Play again!", (140, 220, 120), "play", self.S(56))
        play.x, play.y = (self.width - play.w) // 2, int(self.height * 0.56)
        again.x, again.y = (self.width - again.w) // 2, int(self.height * 0.72)
        exit_btn = PillButton("Exit", (255, 175, 175), "exit", self.S(26))
        exit_btn.x, exit_btn.y = self.width - exit_btn.w - self.S(20), self.S(16)
        self.buttons = {"start": [play, exit_btn], "over": [again, exit_btn], "countdown": [], "play": []}

        self.best = self._load_best()
        self.state = "start"
        self.running = True
        self.items = []
        self.debris = []
        self.popups = []
        self.next_spawn = time.time() + 1.0
        self.state_start = time.time()
        self.round_start = time.time()
        self.hover_button, self.hover_start, self.hover_seen = None, 0.0, 0.0
        self.last_face_time = time.time()
        self.last_time = time.time()
        self.results = []

    def S(self, v):
        return int(round(v * self.s))

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

    # ---------- cone + stack geometry for one player ----------
    def _geometry(self, p):
        cone_w = max(self.S(50), p.w * 0.8)
        cone_h = cone_w * 1.15
        scoop_d = cone_w * 1.05
        head_top = p.y - p.h * 0.18  # face boxes start around the eyebrows
        cone_top = head_top - cone_h * 0.95
        return cone_w, cone_h, scoop_d, cone_top

    def _scoop_center(self, p, i, t):
        cone_w, _cone_h, scoop_d, cone_top = self._geometry(p)
        wobble = math.sin(t * 3 + p.slot) * i * self.S(3)
        return p.cx + wobble, cone_top - scoop_d * 0.12 - i * scoop_d * 0.55

    def _catch_point(self, p, t):
        _cone_w, _h, scoop_d, cone_top = self._geometry(p)
        if not p.stack:
            return p.cx, cone_top
        x, y = self._scoop_center(p, len(p.stack) - 1, t)
        return x, y - scoop_d * 0.35

    # ---------- game flow ----------
    def _press(self, action):
        if action == "play":
            self.tracker.reset_scores()
            self.items, self.debris = [], []
            self.state, self.state_start = "countdown", time.time()
        elif action == "exit":
            self.running = False

    def _start_round(self):
        self.state = "play"
        self.round_start = self.state_start = time.time()
        self.tracker.keep_time = 20.0  # keep a kid's score if they step away for a bit during the round
        self.tracker.reset_scores()
        self.next_spawn = time.time() + 0.3
        self._popup("Go!", self.width / 2, self.height * 0.45, (140, 220, 120), big=True)

    def _end_round(self):
        self.state, self.state_start = "over", time.time()
        self.tracker.keep_time = 3.0
        self.results = sorted(self.tracker.players, key=lambda p: -p.score)
        self.results = [(p.name, p.color, p.score) for p in self.results]
        self.new_best = False
        if self.results and self.results[0][2] > self.best:
            self.best = self.results[0][2]
            self.new_best = True
            self._save_best()
        if self.results and self.results[0][2] > 0:
            self.confetti.burst(self.width, self.height)
        self.items = []

    def _spawn(self, players):
        now = time.time()
        playing = self.state == "play"
        elapsed = now - self.round_start if playing else 0
        size = self.S(ITEM_SIZE)
        x = random.uniform(self.width * 0.08, self.width * 0.92)
        # aim some items above a player so everyone gets a fair chance
        if players and random.random() < 0.6:
            x = random.choice(players).cx + random.uniform(-1, 1) * self.width * 0.15
            x = min(max(x, self.width * 0.05), self.width * 0.95)
        speed = (FALL_SPEED + elapsed * 2.0) * self.s * random.uniform(0.85, 1.2)
        roll = random.random()
        if playing and elapsed > 10 and roll < 0.15:
            item = Item("broccoli", 0, x, -size, speed * 1.1, size)
        elif playing and roll > 0.94:
            item = Item("gold", -1, x, -size, speed * 1.2, size)
        else:
            item = Item("scoop", random.randrange(len(FLAVORS)), x, -size, speed, size)
        self.items.append(item)
        crowd = math.sqrt(max(1, len(players)))
        interval = (max(0.45, 1.2 - elapsed * 0.01) if playing else 1.6) / crowd
        self.next_spawn = now + interval * random.uniform(0.8, 1.2)

    def _check_catches(self, players, t):
        for item in list(self.items):
            for p in players:
                cone_w, _h, scoop_d, _top = self._geometry(p)
                cx, cy = self._catch_point(p, t)
                if abs(item.x - cx) < cone_w * 0.55 + item.size * 0.2 and abs(item.y - cy) < scoop_d * 0.4:
                    self.items.remove(item)
                    self._caught(p, item, t)
                    break

    def _caught(self, p, item, t):
        playing = self.state == "play"
        x, y = self._catch_point(p, t)
        if item.kind == "broccoli":
            self._drop_stack(p, t)
            self._popup("Yuck! Broccoli!", x, y - self.S(40), (190, 240, 190), big=True)
            return
        p.stack.append(item.flavor)
        if playing:
            points = 3 if item.kind == "gold" else 1
            p.score += points
            if item.kind == "gold":
                self._popup("Golden! +3", x, y - self.S(30), (255, 224, 130), big=True)
            else:
                self._popup("+1", x, y - self.S(30), p.color)
        if len(p.stack) >= TOWER_SIZE:
            if playing:
                p.score += TOWER_SIZE
                self._popup(f"{p.name}: Tower! +{TOWER_SIZE}", self.width / 2, self.height * 0.3, p.color, big=True)
            self.confetti.burst(self.width, self.height, count=30)
            p.stack = []
        elif playing and random.random() < 0.15:
            self._popup(random.choice(CHEERS), x, y - self.S(80), (255, 255, 255))

    def _drop_stack(self, p, t):
        _cone_w, _h, scoop_d, _top = self._geometry(p)
        for i, flavor in enumerate(p.stack):
            x, y = self._scoop_center(p, i, t)
            self.debris.append([scoop_sprite(flavor, scoop_d), x, y, random.uniform(-200, 200) * self.s,
                                random.uniform(-300, -100) * self.s])
        p.stack = []

    def _popup(self, text, x, y, fill_rgb, big=False):
        img = render_pill(text, max(12, self.S(40 if big else 28)), tuple(fill_rgb))
        self.popups.append((img, x, y, time.time()))

    def _update_hover(self, players):
        now = time.time()
        btn = None
        for p in players:
            # any part of the face touching the button counts
            btn = next((b for b in self.buttons[self.state] if b.overlaps(p.x, p.y, p.w, p.h)), None)
            if btn:
                break
        if btn is None:
            if self.hover_button is not None and now - self.hover_seen > 0.3:
                self.hover_button = None
            return
        self.hover_seen = now
        if btn is not self.hover_button:
            self.hover_button, self.hover_start = btn, now
        elif now - self.hover_start >= HOLD_TIME:
            self.hover_button = None
            self._press(btn.action)

    # ---------- drawing ----------
    def _center(self, frame, img, y, alpha=1.0):
        blend_bgra(frame, img, (self.width - img.shape[1]) // 2, int(y), alpha)

    def _draw_player(self, frame, p, t):
        cone_w, cone_h, scoop_d, cone_top = self._geometry(p)
        cone = cone_sprite(cone_w)
        blend_bgra(frame, cone, int(p.cx - cone.shape[1] / 2), int(cone_top))
        for i, flavor in enumerate(p.stack):
            x, y = self._scoop_center(p, i, t)
            sp = scoop_sprite(flavor, scoop_d)
            blend_bgra(frame, sp, int(x - sp.shape[1] / 2), int(y - sp.shape[0] / 2))
        label = f"{p.name}  {p.score}" if self.state in ("play", "over") else p.name
        tag = render_pill(label, max(12, self.S(26)), p.color)
        blend_bgra(frame, tag, int(p.cx - tag.shape[1] / 2), int(p.y + p.h + self.S(12)))

    def _draw_items(self, frame, dt, t):
        for item in self.items:
            item.draw(frame, t)
        alive = []
        for d in self.debris:
            d[4] += 1300 * self.s * dt
            d[1] += d[3] * dt
            d[2] += d[4] * dt
            if d[2] < self.height + 100:
                blend_bgra(frame, d[0], int(d[1] - d[0].shape[1] / 2), int(d[2] - d[0].shape[0] / 2))
                alive.append(d)
        self.debris = alive

    def _draw_popups(self, frame):
        now = time.time()
        alive = []
        for img, x, y, t0 in self.popups:
            age = now - t0
            if age > 1.0:
                continue
            h, w = img.shape[:2]
            fade = min(1.0, (1.0 - age) / 0.3)
            blend_bgra(frame, img, int(x - w / 2), int(y - h / 2 - age * self.S(60)), fade)
            alive.append((img, x, y, t0))
        self.popups = alive

    def _draw_buttons(self, frame):
        for b in self.buttons[self.state]:
            blend_bgra(frame, b.img, b.x, b.y)
            if b is self.hover_button:
                progress = min(1.0, (time.time() - self.hover_start) / HOLD_TIME)
                pad = self.S(6)
                rounded_rect_outline(frame, b.x - pad, b.y - pad, b.w + 2 * pad, b.h + 2 * pad, b.h // 2 + pad,
                                     (0, 140, 255), max(3, self.S(5)))
                y = b.y + b.h + self.S(10)
                x0, x1 = b.x + b.h // 2, b.x + b.w - b.h // 2
                cv2.line(frame, (x0, y), (x1, y), (255, 255, 255), max(4, self.S(10)), cv2.LINE_AA)
                cv2.line(frame, (x0, y), (x0 + int((x1 - x0) * progress), y), (255, 0, 220), max(4, self.S(10)),
                         cv2.LINE_AA)

    def _draw_screen(self, frame, players, now):
        if self.state == "start":
            self._center(frame, rainbow_title("Ice Cream Catch!", self.S(96)), self.height * 0.04)
            self._center(frame, render_pill("Catch the ice cream with your head!", max(14, self.S(32)),
                                            (255, 255, 255)), self.height * 0.25)
            tips = render_pill("Watch out for broccoli!   Up to 6 friends can play!", max(12, self.S(24)),
                               (255, 236, 179))
            self._center(frame, tips, self.height * 0.35)
            b = self.buttons["start"][0]
            hint = render_pill("Put your head on Play! and hold still", max(12, self.S(24)), (173, 216, 255))
            self._center(frame, hint, b.y + b.h + self.S(30))
        elif self.state == "countdown":
            left = COUNTDOWN - (now - self.state_start)
            if left <= 0:
                self._start_round()
            else:
                num = rainbow_title(str(int(math.ceil(left))), self.S(220))
                self._center(frame, num, (self.height - num.shape[0]) / 2)
        elif self.state == "play":
            left = max(0, ROUND_TIME - (now - self.round_start))
            fill = (255, 175, 175) if left <= 10 else (255, 255, 255)
            timer = render_pill(f"Time {int(left) // 60}:{int(left) % 60:02d}", max(14, self.S(34)), fill)
            pulse = 0.75 + 0.25 * math.sin(now * 8) if left <= 10 else 1.0
            self._center(frame, timer, self.S(14), pulse)
            y = self.S(14)
            for p in sorted(self.tracker.players, key=lambda q: -q.score):
                tag = render_pill(f"{p.name} {p.score}", max(12, self.S(22)), p.color)
                blend_bgra(frame, tag, self.S(16), y, 1.0 if p.active else 0.5)
                y += tag.shape[0] + self.S(6)
            if left <= 0:
                self._end_round()
        elif self.state == "over":
            if not self.results:
                title = "Nobody played!"
            elif len(self.results) > 1 and self.results[0][2] == self.results[1][2]:
                title = "It's a tie!"
            else:
                title = f"{self.results[0][0]} wins!"
            self._center(frame, rainbow_title(title, self.S(90)), self.height * 0.04)
            y = self.height * 0.21
            for rank, (name, color, score) in enumerate(self.results[:6], start=1):
                tag = render_pill(f"{rank}. {name}  {score} point{'s' if score != 1 else ''}",
                                  max(12, self.S(26)), color)
                self._center(frame, tag, y)
                y += tag.shape[0] + self.S(6)
            best = "New best score!" if self.new_best else f"Best ever: {self.best}"
            self._center(frame, render_pill(best, max(12, self.S(24)), (255, 224, 130)), self.height * 0.9)

        if not players and now - self.last_face_time > 1.5:
            hint = render_pill("Step in front of the camera!", max(14, self.S(40)), (255, 255, 255))
            self._center(frame, hint, self.height * 0.44 + self.S(8) * math.sin(now * 4))

    # ---------- main loop ----------
    def run(self):
        window = "Ice Cream Catch"
        cv2.namedWindow(window)

        while self.running:
            ok, frame = self.cap.read()
            if not ok:
                break
            frame = cv2.flip(frame, 1)
            now = time.time()
            dt = min(now - self.last_time, 0.05)
            self.last_time = now

            self.tracker.update(self.detector.detect(frame))
            players = self.tracker.active_players()
            if players:
                self.last_face_time = now

            if self.state in ("start", "play") and now >= self.next_spawn:
                self._spawn(players)
            for item in self.items:
                item.update(dt, now)
            self.items = [i for i in self.items if i.y < self.height + i.size]
            if self.state in ("start", "play"):
                self._check_catches(players, now)
            self._update_hover(players)

            if self.state in ("start", "over"):
                frame = cv2.addWeighted(frame, 0.6, self.tint, 0.4, 0)
            for p in players:
                self._draw_player(frame, p, now)
            self._draw_items(frame, dt, now)
            self._draw_screen(frame, players, now)
            self._draw_buttons(frame)
            self._draw_popups(frame)
            self.confetti.draw(frame)

            cv2.imshow(window, frame)
            key = cv2.waitKey(1) & 0xFF
            if key in (ord('q'), 27):
                self.running = False
            elif key == ord(' ') and self.state in ("start", "over"):
                self._press("play")

        self.cap.release()
        cv2.destroyWindow(window)
        self.detector.close()


def main():
    parser = argparse.ArgumentParser(description="Ice Cream Catch - catch falling ice cream on your head.")
    parser.add_argument("--camera", type=int, default=0, help="webcam index (default: 0)")
    args = parser.parse_args()
    IceCreamCatch(args.camera).run()


if __name__ == "__main__":
    main()
