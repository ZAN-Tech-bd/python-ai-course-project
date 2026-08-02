"""
Bike Race — a polished, single-file arcade bike racer built with pygame.

Controls
--------
  LEFT / A        steer left
  RIGHT / D       steer right
  SPACE / LSHIFT  nitro boost (while nitro meter has fuel)
  P / ESC         pause
  ENTER           start / restart

Run:  python bike_race.py
"""

import json
import math
import os
import random
import sys

import pygame

try:
    import numpy as np
    HAVE_NUMPY = True
except ImportError:
    HAVE_NUMPY = False

# ----------------------------------------------------------------------------
# Constants
# ----------------------------------------------------------------------------

WIDTH, HEIGHT = 480, 800
FPS = 60

ROAD_WIDTH = 340
ROAD_LEFT = (WIDTH - ROAD_WIDTH) // 2
ROAD_RIGHT = ROAD_LEFT + ROAD_WIDTH
LANES = 4
LANE_WIDTH = ROAD_WIDTH / LANES

HIGHSCORE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "highscore.json")

# Palette
COL_SKY_TOP = (18, 22, 40)
COL_SKY_BOTTOM = (40, 46, 72)
COL_GRASS_1 = (36, 110, 60)
COL_GRASS_2 = (30, 96, 52)
COL_ROAD = (52, 54, 60)
COL_ROAD_EDGE = (230, 210, 90)
COL_LANE_LINE = (235, 235, 235)
COL_PLAYER = (232, 64, 64)
COL_PLAYER_DARK = (150, 30, 30)
COL_WHITE = (245, 245, 245)
COL_GOLD = (255, 205, 60)
COL_NITRO = (70, 190, 255)
COL_UI_BG = (10, 12, 20)

CAR_COLORS = [
    (66, 133, 244),
    (250, 190, 60),
    (150, 90, 220),
    (60, 190, 140),
    (240, 120, 40),
]

STATE_MENU = "menu"
STATE_PLAYING = "playing"
STATE_PAUSED = "paused"
STATE_GAMEOVER = "gameover"


# ----------------------------------------------------------------------------
# Sound (procedurally synthesized — no external asset files needed)
# ----------------------------------------------------------------------------

class SoundBank:
    def __init__(self):
        self.enabled = HAVE_NUMPY
        self.sounds = {}
        if not self.enabled:
            return
        try:
            pygame.mixer.init(frequency=44100, size=-16, channels=1)
            _, _, actual_channels = pygame.mixer.get_init()
            self.channels = max(1, actual_channels)
        except pygame.error:
            self.enabled = False
            return
        self.sounds["coin"] = self._tone(880, 0.08, fade=0.02, wave="sine", sweep=1600)
        self.sounds["nitro"] = self._tone(220, 0.35, fade=0.05, wave="saw", sweep=760)
        self.sounds["crash"] = self._noise(0.35)
        self.sounds["hit"] = self._tone(140, 0.2, fade=0.05, wave="square", sweep=60)
        self.sounds["click"] = self._tone(600, 0.06, fade=0.01, wave="sine", sweep=600)
        self.sounds["gameover"] = self._tone(300, 0.5, fade=0.1, wave="saw", sweep=60)

    def _tone(self, freq, duration, fade=0.02, wave="sine", sweep=None):
        rate = 44100
        n = int(rate * duration)
        t = np.linspace(0, duration, n, endpoint=False)
        f = freq if sweep is None else np.linspace(freq, sweep, n)
        phase = 2 * np.pi * np.cumsum(f) / rate
        if wave == "sine":
            data = np.sin(phase)
        elif wave == "square":
            data = np.sign(np.sin(phase))
        elif wave == "saw":
            data = 2 * (phase / (2 * np.pi) % 1.0) - 1
        else:
            data = np.sin(phase)
        env = np.ones(n)
        fade_n = max(1, int(rate * fade))
        env[:fade_n] = np.linspace(0, 1, fade_n)
        env[-fade_n:] = np.linspace(1, 0, fade_n)
        data = (data * env * 0.35 * 32767).astype(np.int16)
        return pygame.sndarray.make_sound(self._to_channels(data))

    def _noise(self, duration):
        rate = 44100
        n = int(rate * duration)
        data = np.random.uniform(-1, 1, n)
        env = np.linspace(1, 0, n) ** 1.5
        data = (data * env * 0.4 * 32767).astype(np.int16)
        return pygame.sndarray.make_sound(self._to_channels(data))

    def _to_channels(self, data):
        if self.channels >= 2:
            return np.repeat(data.reshape(-1, 1), self.channels, axis=1)
        return data

    def play(self, name):
        if self.enabled and name in self.sounds:
            self.sounds[name].play()


# ----------------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------------

def lane_center_x(lane_index):
    return ROAD_LEFT + LANE_WIDTH * (lane_index + 0.5)


def clamp(v, lo, hi):
    return max(lo, min(hi, v))


def lerp(a, b, t):
    return a + (b - a) * t


def rounded_rect(surf, rect, color, radius=8):
    pygame.draw.rect(surf, color, rect, border_radius=radius)


# ----------------------------------------------------------------------------
# Particles
# ----------------------------------------------------------------------------

class Particle:
    __slots__ = ("x", "y", "vx", "vy", "life", "max_life", "color", "size", "gravity")

    def __init__(self, x, y, vx, vy, life, color, size, gravity=0.0):
        self.x, self.y = x, y
        self.vx, self.vy = vx, vy
        self.life = self.max_life = life
        self.color = color
        self.size = size
        self.gravity = gravity

    def update(self, dt):
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.vy += self.gravity * dt
        self.life -= dt
        return self.life > 0

    def draw(self, surf):
        t = clamp(self.life / self.max_life, 0, 1)
        alpha = int(255 * t)
        size = max(1, self.size * t)
        s = pygame.Surface((size * 2, size * 2), pygame.SRCALPHA)
        pygame.draw.circle(s, (*self.color, alpha), (size, size), size)
        surf.blit(s, (self.x - size, self.y - size))


class ParticleSystem:
    def __init__(self):
        self.particles = []

    def burst(self, x, y, color, count=16, speed=140, life=0.6, size=4, gravity=0.0, spread=math.tau):
        for _ in range(count):
            ang = random.uniform(0, spread) - spread / 2 - math.pi / 2
            spd = random.uniform(speed * 0.3, speed)
            vx, vy = math.cos(ang) * spd, math.sin(ang) * spd
            self.particles.append(Particle(x, y, vx, vy, random.uniform(life * 0.5, life), color,
                                            random.uniform(size * 0.5, size), gravity))

    def exhaust(self, x, y, color=(200, 210, 230)):
        vx = random.uniform(-20, 20)
        vy = random.uniform(60, 120)
        self.particles.append(Particle(x, y, vx, vy, random.uniform(0.25, 0.45), color,
                                        random.uniform(3, 6)))

    def update(self, dt):
        self.particles = [p for p in self.particles if p.update(dt)]

    def draw(self, surf):
        for p in self.particles:
            p.draw(surf)


# ----------------------------------------------------------------------------
# Road (scrolling background)
# ----------------------------------------------------------------------------

class Road:
    def __init__(self):
        self.scroll = 0.0
        self.dash_h = 46
        self.dash_gap = 34
        self.tree_period = 130
        self.trees_l = [random.uniform(0, 1) for _ in range(20)]
        self.trees_r = [random.uniform(0, 1) for _ in range(20)]

    def update(self, dt, speed):
        self.scroll = (self.scroll + speed * dt) % (self.dash_h + self.dash_gap)

    def draw(self, surf):
        # sky/grass gradient background
        for y in range(0, HEIGHT, 4):
            t = y / HEIGHT
            col = (
                int(lerp(COL_SKY_TOP[0], COL_SKY_BOTTOM[0], t)),
                int(lerp(COL_SKY_TOP[1], COL_SKY_BOTTOM[1], t)),
                int(lerp(COL_SKY_TOP[2], COL_SKY_BOTTOM[2], t)),
            )
            pygame.draw.rect(surf, col, (0, y, WIDTH, 4))

        # grass with subtle scrolling stripes
        grass_scroll = self.scroll * 1.4
        stripe_h = 60
        for side_rect in [(0, 0, ROAD_LEFT, HEIGHT), (ROAD_RIGHT, 0, WIDTH - ROAD_RIGHT, HEIGHT)]:
            surf.fill((0, 0, 0), side_rect)  # reset (avoid bleed) - will paint stripes
        for i, y in enumerate(range(-stripe_h, HEIGHT + stripe_h, stripe_h)):
            yy = y + grass_scroll % stripe_h
            color = COL_GRASS_1 if i % 2 == 0 else COL_GRASS_2
            pygame.draw.rect(surf, color, (0, yy, ROAD_LEFT, stripe_h))
            pygame.draw.rect(surf, color, (ROAD_RIGHT, yy, WIDTH - ROAD_RIGHT, stripe_h))

        # trees (parallax dots) on both margins
        for i, phase in enumerate(self.trees_l):
            y = (phase * self.tree_period + self.scroll * 1.4) % (HEIGHT + self.tree_period) - self.tree_period
            x = 22 + (i % 3) * 18
            pygame.draw.circle(surf, (18, 70, 34), (x, int(y)), 12)
            pygame.draw.circle(surf, (24, 88, 42), (x, int(y) - 4), 9)
        for i, phase in enumerate(self.trees_r):
            y = (phase * self.tree_period + self.scroll * 1.4) % (HEIGHT + self.tree_period) - self.tree_period
            x = WIDTH - 22 - (i % 3) * 18
            pygame.draw.circle(surf, (18, 70, 34), (x, int(y)), 12)
            pygame.draw.circle(surf, (24, 88, 42), (x, int(y) - 4), 9)

        # road surface with soft shading
        pygame.draw.rect(surf, COL_ROAD, (ROAD_LEFT, 0, ROAD_WIDTH, HEIGHT))
        shade = pygame.Surface((ROAD_WIDTH, HEIGHT), pygame.SRCALPHA)
        pygame.draw.rect(shade, (255, 255, 255, 10), (0, 0, ROAD_WIDTH // 2, HEIGHT))
        surf.blit(shade, (ROAD_LEFT, 0))

        # road edges (rumble strip)
        edge_w = 8
        pygame.draw.rect(surf, COL_ROAD_EDGE, (ROAD_LEFT - edge_w, 0, edge_w, HEIGHT))
        pygame.draw.rect(surf, COL_ROAD_EDGE, (ROAD_RIGHT, 0, edge_w, HEIGHT))

        # lane dashes
        for lane in range(1, LANES):
            x = ROAD_LEFT + lane * LANE_WIDTH
            y = -self.dash_h + self.scroll
            while y < HEIGHT:
                pygame.draw.rect(surf, COL_LANE_LINE, (x - 3, y, 6, self.dash_h), border_radius=3)
                y += self.dash_h + self.dash_gap


# ----------------------------------------------------------------------------
# Entities
# ----------------------------------------------------------------------------

class Bike:
    WIDTH, HEIGHT = 40, 68

    def __init__(self):
        self.lane_pos = (LANES - 1) / 2  # fractional lane index
        self.x = lane_center_x(self.lane_pos)
        self.y = HEIGHT - 140
        self.vx = 0.0
        self.tilt = 0.0
        self.invuln = 0.0
        self.wheelie = 0.0

    def rect(self):
        return pygame.Rect(int(self.x - self.WIDTH / 2), int(self.y - self.HEIGHT / 2), self.WIDTH, self.HEIGHT)

    def update(self, dt, steer, nitro_active):
        target_vx = steer * 300
        self.vx = lerp(self.vx, target_vx, min(1, dt * 10))
        self.x += self.vx * dt
        min_x = ROAD_LEFT + self.WIDTH / 2 + 4
        max_x = ROAD_RIGHT - self.WIDTH / 2 - 4
        self.x = clamp(self.x, min_x, max_x)
        if self.x in (min_x, max_x):
            self.vx = 0
        self.tilt = lerp(self.tilt, clamp(-self.vx * 0.08, -22, 22), min(1, dt * 12))
        self.wheelie = lerp(self.wheelie, 10 if nitro_active else 0, min(1, dt * 8))
        if self.invuln > 0:
            self.invuln -= dt

    def draw(self, surf, nitro_active):
        blink = self.invuln > 0 and int(self.invuln * 10) % 2 == 0
        if blink:
            return
        cx, cy = self.x, self.y
        body = pygame.Surface((90, 110), pygame.SRCALPHA)
        bx, by = 45, 55 + self.wheelie * 0.5

        shadow = pygame.Surface((70, 24), pygame.SRCALPHA)
        pygame.draw.ellipse(shadow, (0, 0, 0, 90), shadow.get_rect())
        surf.blit(shadow, (cx - 35, cy + 30))

        # wheels
        pygame.draw.circle(body, (25, 25, 28), (bx, by + 38 - self.wheelie), 13)
        pygame.draw.circle(body, (25, 25, 28), (bx, by - 38), 13)
        pygame.draw.circle(body, (90, 90, 96), (bx, by + 38 - self.wheelie), 6)
        pygame.draw.circle(body, (90, 90, 96), (bx, by - 38), 6)

        # frame / body
        pygame.draw.polygon(body, COL_PLAYER_DARK, [
            (bx - 10, by + 30 - self.wheelie), (bx + 10, by + 30 - self.wheelie),
            (bx + 14, by - 25), (bx - 14, by - 25),
        ])
        pygame.draw.polygon(body, COL_PLAYER, [
            (bx - 12, by + 10), (bx + 12, by + 10),
            (bx + 16, by - 30), (bx - 16, by - 30),
        ])
        pygame.draw.rect(body, COL_PLAYER, (bx - 8, by - 42, 16, 18), border_radius=6)
        # windshield / headlight
        pygame.draw.polygon(body, (230, 240, 250), [(bx - 8, by - 40), (bx + 8, by - 40), (bx, by - 50)])
        pygame.draw.circle(body, COL_GOLD, (bx, by - 44), 4)
        # rider
        pygame.draw.circle(body, (30, 30, 34), (bx, by - 8), 10)
        pygame.draw.rect(body, (40, 40, 46), (bx - 9, by - 2, 18, 22), border_radius=6)

        if nitro_active:
            flame_h = random.uniform(18, 30)
            pygame.draw.polygon(body, (255, 160, 40), [
                (bx - 8, by + 30 - self.wheelie), (bx + 8, by + 30 - self.wheelie), (bx, by + 30 - self.wheelie + flame_h)
            ])
            pygame.draw.polygon(body, (255, 230, 120), [
                (bx - 4, by + 30 - self.wheelie), (bx + 4, by + 30 - self.wheelie), (bx, by + 30 - self.wheelie + flame_h * 0.6)
            ])

        rotated = pygame.transform.rotate(body, self.tilt)
        rect = rotated.get_rect(center=(cx, cy))
        surf.blit(rotated, rect)


class Car:
    def __init__(self, lane, y, speed_mult=1.0):
        self.lane = lane
        self.x = lane_center_x(lane)
        self.y = y
        self.w = random.choice([44, 50])
        self.h = int(self.w * 1.7)
        self.color = random.choice(CAR_COLORS)
        self.speed_mult = speed_mult

    def rect(self):
        return pygame.Rect(int(self.x - self.w / 2), int(self.y - self.h / 2), self.w, self.h)

    def update(self, dt, world_speed):
        self.y += world_speed * self.speed_mult * dt

    def draw(self, surf):
        r = self.rect()
        shadow = pygame.Surface((self.w + 10, 20), pygame.SRCALPHA)
        pygame.draw.ellipse(shadow, (0, 0, 0, 90), shadow.get_rect())
        surf.blit(shadow, (r.centerx - shadow.get_width() // 2, r.bottom - 12))

        dark = tuple(max(0, c - 60) for c in self.color)
        rounded_rect(surf, r, self.color, radius=10)
        rounded_rect(surf, (r.x + 4, r.y + r.h * 0.15, r.w - 8, r.h * 0.32), dark, radius=8)
        # headlights/taillights
        pygame.draw.circle(surf, (255, 235, 150), (r.x + 8, r.bottom - 8), 4)
        pygame.draw.circle(surf, (255, 235, 150), (r.right - 8, r.bottom - 8), 4)
        pygame.draw.circle(surf, (230, 60, 60), (r.x + 8, r.y + 8), 4)
        pygame.draw.circle(surf, (230, 60, 60), (r.right - 8, r.y + 8), 4)


class Coin:
    def __init__(self, lane, y):
        self.lane = lane
        self.x = lane_center_x(lane)
        self.y = y
        self.r = 12
        self.t = random.uniform(0, math.tau)
        self.collected = False

    def rect(self):
        return pygame.Rect(int(self.x - self.r), int(self.y - self.r), self.r * 2, self.r * 2)

    def update(self, dt, world_speed):
        self.y += world_speed * dt
        self.t += dt * 6

    def draw(self, surf):
        scale = abs(math.cos(self.t))
        w = max(2, int(self.r * 2 * scale))
        rect = pygame.Rect(0, 0, w, self.r * 2)
        rect.center = (int(self.x), int(self.y))
        pygame.draw.ellipse(surf, COL_GOLD, rect)
        pygame.draw.ellipse(surf, (200, 150, 20), rect, 2)


class NitroPickup:
    def __init__(self, lane, y):
        self.lane = lane
        self.x = lane_center_x(lane)
        self.y = y
        self.r = 14
        self.t = random.uniform(0, math.tau)

    def rect(self):
        return pygame.Rect(int(self.x - self.r), int(self.y - self.r), self.r * 2, self.r * 2)

    def update(self, dt, world_speed):
        self.y += world_speed * dt
        self.t += dt * 4

    def draw(self, surf):
        bob = math.sin(self.t) * 4
        pts = [(self.x, self.y - 16 + bob), (self.x - 9, self.y + 2 + bob), (self.x - 2, self.y + 2 + bob),
               (self.x - 6, self.y + 16 + bob), (self.x + 9, self.y - 4 + bob), (self.x + 1, self.y - 4 + bob)]
        pygame.draw.polygon(surf, COL_NITRO, pts)
        pygame.draw.polygon(surf, (255, 255, 255), pts, 1)


# ----------------------------------------------------------------------------
# Game
# ----------------------------------------------------------------------------

class Game:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("Bike Race")
        self.clock = pygame.time.Clock()
        self.sounds = SoundBank()

        self.font_big = pygame.font.SysFont("arialblack", 46)
        self.font_mid = pygame.font.SysFont("arial", 26, bold=True)
        self.font_small = pygame.font.SysFont("arial", 18, bold=True)

        self.high_score = self.load_high_score()
        self.state = STATE_MENU
        self.reset()

    # ---------------- persistence ----------------
    def load_high_score(self):
        try:
            with open(HIGHSCORE_FILE) as f:
                return json.load(f).get("high_score", 0)
        except (FileNotFoundError, json.JSONDecodeError, ValueError):
            return 0

    def save_high_score(self):
        try:
            with open(HIGHSCORE_FILE, "w") as f:
                json.dump({"high_score": self.high_score}, f)
        except OSError:
            pass

    # ---------------- lifecycle ----------------
    def reset(self):
        self.road = Road()
        self.bike = Bike()
        self.particles = ParticleSystem()
        self.cars = []
        self.coins = []
        self.nitro_pickups = []
        self.world_speed = 220.0
        self.base_speed = 220.0
        self.max_speed = 620.0
        self.distance = 0.0
        self.score = 0
        self.lives = 3
        self.nitro_meter = 40.0
        self.nitro_max = 100.0
        self.nitro_active = False
        self.spawn_timer = 0.0
        self.coin_timer = 0.0
        self.nitro_spawn_timer = 6.0
        self.shake = 0.0
        self.combo = 0
        self.combo_timer = 0.0
        self.flash = 0.0
        self.game_time = 0.0

    def start(self):
        self.reset()
        self.state = STATE_PLAYING
        self.sounds.play("click")

    # ---------------- spawning ----------------
    def spawn_wave(self):
        difficulty = clamp(self.distance / 4000, 0, 1)
        gap = lerp(1.35, 0.55, difficulty)
        self.spawn_timer = gap + random.uniform(-0.15, 0.15)

        pattern = random.random()
        occupied = set()
        if pattern < 0.55:
            lane = random.randrange(LANES)
            occupied.add(lane)
            self.cars.append(Car(lane, -80, speed_mult=random.uniform(0.55, 0.8)))
        elif pattern < 0.85:
            lanes = random.sample(range(LANES), 2)
            for i, lane in enumerate(lanes):
                occupied.add(lane)
                self.cars.append(Car(lane, -80 - i * 90, speed_mult=random.uniform(0.5, 0.75)))
        else:
            lanes = random.sample(range(LANES), min(3, LANES))
            for i, lane in enumerate(lanes):
                occupied.add(lane)
                self.cars.append(Car(lane, -80 - i * 70, speed_mult=random.uniform(0.45, 0.7)))

        free_lanes = [l for l in range(LANES) if l not in occupied]
        if free_lanes and random.random() < 0.7:
            self.coins.append(Coin(random.choice(free_lanes), -60))

    def spawn_coin_row(self):
        self.coin_timer = random.uniform(1.6, 2.6)
        lane = random.randrange(LANES)
        if random.random() < 0.4:
            for dy in range(3):
                self.coins.append(Coin(lane, -60 - dy * 40))
        else:
            self.coins.append(Coin(lane, -60))

    # ---------------- update ----------------
    def update(self, dt):
        keys = pygame.key.get_pressed()
        if self.state == STATE_PLAYING:
            steer = 0
            if keys[pygame.K_LEFT] or keys[pygame.K_a]:
                steer -= 1
            if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
                steer += 1

            want_nitro = (keys[pygame.K_SPACE] or keys[pygame.K_LSHIFT]) and self.nitro_meter > 0
            if want_nitro and not self.nitro_active:
                self.sounds.play("nitro")
            self.nitro_active = want_nitro
            if self.nitro_active:
                self.nitro_meter = clamp(self.nitro_meter - dt * 34, 0, self.nitro_max)
            else:
                self.nitro_meter = clamp(self.nitro_meter + dt * 6, 0, self.nitro_max)

            self.game_time += dt
            difficulty = clamp(self.distance / 5000, 0, 1)
            self.base_speed = lerp(220, self.max_speed, difficulty)
            target_speed = self.base_speed * (1.7 if self.nitro_active else 1.0)
            self.world_speed = lerp(self.world_speed, target_speed, min(1, dt * 3))

            self.distance += self.world_speed * dt
            self.score += self.world_speed * dt * (0.05 if not self.nitro_active else 0.1)

            self.bike.update(dt, steer, self.nitro_active)
            self.road.update(dt, self.world_speed)

            if random.random() < dt * 22:
                side = -1 if random.random() < 0.5 else 1
                self.particles.exhaust(self.bike.x + side * 14, self.bike.y + 32)

            self.spawn_timer -= dt
            if self.spawn_timer <= 0:
                self.spawn_wave()
            self.coin_timer -= dt
            if self.coin_timer <= 0:
                self.spawn_coin_row()
            self.nitro_spawn_timer -= dt
            if self.nitro_spawn_timer <= 0:
                self.nitro_spawn_timer = random.uniform(9, 15)
                self.nitro_pickups.append(NitroPickup(random.randrange(LANES), -60))

            for c in self.cars:
                c.update(dt, self.world_speed)
            for c in self.coins:
                c.update(dt, self.world_speed)
            for n in self.nitro_pickups:
                n.update(dt, self.world_speed)

            self.cars = [c for c in self.cars if c.y - c.h < HEIGHT + 60]
            self.coins = [c for c in self.coins if not c.collected and c.y < HEIGHT + 40]
            self.nitro_pickups = [n for n in self.nitro_pickups if n.y < HEIGHT + 40]

            self.check_collisions()

            if self.combo_timer > 0:
                self.combo_timer -= dt
                if self.combo_timer <= 0:
                    self.combo = 0

        self.particles.update(dt)
        if self.shake > 0:
            self.shake = max(0, self.shake - dt * 20)
        if self.flash > 0:
            self.flash = max(0, self.flash - dt * 2)

    def check_collisions(self):
        brect = self.bike.rect().inflate(-10, -14)
        for c in self.coins:
            if not c.collected and brect.colliderect(c.rect()):
                c.collected = True
                self.combo += 1
                self.combo_timer = 1.4
                self.score += 25 * max(1, self.combo * 0.5)
                self.particles.burst(c.x, c.y, COL_GOLD, count=14, speed=160, size=3)
                self.sounds.play("coin")

        for n in self.nitro_pickups[:]:
            if brect.colliderect(n.rect()):
                self.nitro_pickups.remove(n)
                self.nitro_meter = clamp(self.nitro_meter + 45, 0, self.nitro_max)
                self.particles.burst(n.x, n.y, COL_NITRO, count=20, speed=180, size=4)
                self.sounds.play("nitro")

        if self.bike.invuln <= 0:
            for c in self.cars:
                if brect.colliderect(c.rect()):
                    self.on_crash(c)
                    break

    def on_crash(self, car):
        self.lives -= 1
        self.shake = 14
        self.flash = 1.0
        self.particles.burst(self.bike.x, self.bike.y, (255, 120, 40), count=34, speed=260, size=5, gravity=180)
        self.particles.burst(self.bike.x, self.bike.y, (90, 90, 90), count=18, speed=150, size=6, gravity=260)
        if car in self.cars:
            self.cars.remove(car)
        if self.lives <= 0:
            self.sounds.play("crash")
            self.end_game()
        else:
            self.sounds.play("hit")
            self.bike.invuln = 2.0

    def end_game(self):
        self.state = STATE_GAMEOVER
        self.high_score = max(self.high_score, int(self.score))
        self.save_high_score()
        self.sounds.play("gameover")

    # ---------------- drawing ----------------
    def draw(self):
        surf = self.screen
        offset = (0, 0)
        if self.shake > 0:
            offset = (random.uniform(-self.shake, self.shake), random.uniform(-self.shake, self.shake))

        world = pygame.Surface((WIDTH, HEIGHT))
        self.road.draw(world)

        for c in self.coins:
            c.draw(world)
        for n in self.nitro_pickups:
            n.draw(world)
        for c in self.cars:
            c.draw(world)

        self.particles.draw(world)

        if self.state in (STATE_PLAYING, STATE_PAUSED):
            self.bike.draw(world, self.nitro_active)

        if self.nitro_active:
            speed_lines = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            for _ in range(6):
                x = random.uniform(ROAD_LEFT, ROAD_RIGHT)
                y = random.uniform(0, HEIGHT)
                pygame.draw.line(speed_lines, (255, 255, 255, 40), (x, y), (x, y + 40), 2)
            world.blit(speed_lines, (0, 0))

        surf.blit(world, offset)

        if self.flash > 0:
            fl = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            fl.fill((255, 60, 40, int(90 * self.flash)))
            surf.blit(fl, (0, 0))

        self.draw_hud(surf)

        if self.state == STATE_MENU:
            self.draw_menu(surf)
        elif self.state == STATE_PAUSED:
            self.draw_pause(surf)
        elif self.state == STATE_GAMEOVER:
            self.draw_gameover(surf)

        pygame.display.flip()

    def draw_text_shadow(self, surf, text, font, color, pos, center=False, shadow=(0, 0, 0)):
        img_s = font.render(text, True, shadow)
        img = font.render(text, True, color)
        r = img.get_rect()
        if center:
            r.center = pos
        else:
            r.topleft = pos
        surf.blit(img_s, (r.x + 2, r.y + 2))
        surf.blit(img, r)
        return r

    def draw_hud(self, surf):
        if self.state == STATE_MENU:
            return
        # top bar
        bar = pygame.Surface((WIDTH, 78), pygame.SRCALPHA)
        bar.fill((10, 12, 20, 150))
        surf.blit(bar, (0, 0))

        self.draw_text_shadow(surf, f"{int(self.score)}", self.font_mid, COL_WHITE, (16, 10))
        self.draw_text_shadow(surf, "SCORE", self.font_small, (200, 200, 210), (16, 40))

        hi_img = self.font_small.render(f"HI {self.high_score}", True, COL_GOLD)
        surf.blit(hi_img, (WIDTH - 16 - hi_img.get_width(), 12))

        # lives (hearts)
        for i in range(3):
            cx = WIDTH - 24 - i * 26
            cy = 46
            color = COL_PLAYER if i < self.lives else (70, 70, 76)
            self.draw_heart(surf, cx, cy, 9, color)

        # nitro meter
        meter_w, meter_h = 150, 14
        mx, my = WIDTH // 2 - meter_w // 2, 54
        pygame.draw.rect(surf, (30, 30, 36), (mx, my, meter_w, meter_h), border_radius=7)
        fill_w = int(meter_w * self.nitro_meter / self.nitro_max)
        color = COL_NITRO if not self.nitro_active else (255, 210, 90)
        if fill_w > 0:
            pygame.draw.rect(surf, color, (mx, my, fill_w, meter_h), border_radius=7)
        pygame.draw.rect(surf, (255, 255, 255), (mx, my, meter_w, meter_h), 2, border_radius=7)
        label = self.font_small.render("NITRO", True, (230, 230, 240))
        surf.blit(label, (mx + meter_w // 2 - label.get_width() // 2, my - 18))

        if self.combo > 1:
            combo_img = self.font_mid.render(f"x{self.combo} COMBO!", True, COL_GOLD)
            surf.blit(combo_img, (WIDTH // 2 - combo_img.get_width() // 2, 84))

    def draw_heart(self, surf, x, y, s, color):
        pygame.draw.circle(surf, color, (x - s // 2, y - s // 3), s // 2)
        pygame.draw.circle(surf, color, (x + s // 2, y - s // 3), s // 2)
        pygame.draw.polygon(surf, color, [(x - s, y - s // 4), (x + s, y - s // 4), (x, y + s)])

    def draw_menu(self, surf):
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((5, 6, 12, 165))
        surf.blit(overlay, (0, 0))

        pulse = (math.sin(pygame.time.get_ticks() / 300) + 1) / 2
        title_color = (
            int(lerp(COL_PLAYER[0], COL_GOLD[0], pulse)),
            int(lerp(COL_PLAYER[1], COL_GOLD[1], pulse)),
            int(lerp(COL_PLAYER[2], COL_GOLD[2], pulse)),
        )
        self.draw_text_shadow(surf, "BIKE RACE", self.font_big, title_color, (WIDTH // 2, HEIGHT // 2 - 160), center=True)

        tmp_bike = Bike()
        tmp_bike.x, tmp_bike.y = WIDTH // 2, HEIGHT // 2 - 60
        tmp_bike.tilt = math.sin(pygame.time.get_ticks() / 500) * 8
        tmp_bike.draw(surf, False)

        lines = [
            "ARROWS / A D  —  steer",
            "SPACE / SHIFT  —  nitro boost",
            "P  —  pause",
            "",
            "Dodge traffic, grab coins,",
            "chase the high score!",
        ]
        y = HEIGHT // 2 + 30
        for line in lines:
            if line:
                self.draw_text_shadow(surf, line, self.font_small, (225, 225, 235), (WIDTH // 2, y), center=True)
            y += 26

        if int(pygame.time.get_ticks() / 500) % 2 == 0:
            self.draw_text_shadow(surf, "PRESS ENTER TO START", self.font_mid, COL_WHITE,
                                   (WIDTH // 2, HEIGHT - 110), center=True)

        self.draw_text_shadow(surf, f"HIGH SCORE: {self.high_score}", self.font_small, COL_GOLD,
                               (WIDTH // 2, HEIGHT - 60), center=True)

    def draw_pause(self, surf):
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((5, 6, 12, 165))
        surf.blit(overlay, (0, 0))
        self.draw_text_shadow(surf, "PAUSED", self.font_big, COL_WHITE, (WIDTH // 2, HEIGHT // 2 - 40), center=True)
        self.draw_text_shadow(surf, "PRESS P TO RESUME", self.font_mid, (210, 210, 220),
                               (WIDTH // 2, HEIGHT // 2 + 20), center=True)

    def draw_gameover(self, surf):
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((10, 5, 8, 185))
        surf.blit(overlay, (0, 0))
        self.draw_text_shadow(surf, "CRASHED!", self.font_big, COL_PLAYER, (WIDTH // 2, HEIGHT // 2 - 140), center=True)
        self.draw_text_shadow(surf, f"SCORE: {int(self.score)}", self.font_mid, COL_WHITE,
                               (WIDTH // 2, HEIGHT // 2 - 60), center=True)
        is_new = int(self.score) >= self.high_score and self.score > 0
        hs_color = COL_GOLD if not is_new else (120, 255, 150)
        hs_text = f"HIGH SCORE: {self.high_score}" + ("  NEW!" if is_new else "")
        self.draw_text_shadow(surf, hs_text, self.font_mid, hs_color, (WIDTH // 2, HEIGHT // 2 - 10), center=True)

        if int(pygame.time.get_ticks() / 500) % 2 == 0:
            self.draw_text_shadow(surf, "PRESS ENTER TO RETRY", self.font_mid, COL_WHITE,
                                   (WIDTH // 2, HEIGHT // 2 + 80), center=True)

    # ---------------- input / loop ----------------
    def handle_event(self, event):
        if event.type == pygame.QUIT:
            self.quit()
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_RETURN:
                if self.state in (STATE_MENU, STATE_GAMEOVER):
                    self.start()
            elif event.key in (pygame.K_p, pygame.K_ESCAPE):
                if self.state == STATE_PLAYING:
                    self.state = STATE_PAUSED
                    self.sounds.play("click")
                elif self.state == STATE_PAUSED:
                    self.state = STATE_PLAYING
                    self.sounds.play("click")

    def quit(self):
        pygame.quit()
        sys.exit(0)

    def run(self):
        while True:
            dt = self.clock.tick(FPS) / 1000.0
            dt = min(dt, 1 / 30)
            for event in pygame.event.get():
                self.handle_event(event)
            self.update(dt)
            self.draw()


def main():
    Game().run()


if __name__ == "__main__":
    main()
