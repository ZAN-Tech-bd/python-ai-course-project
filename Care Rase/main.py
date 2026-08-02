"""
Care Rase - a good-looking, interactive car racing game built with pygame.

Controls:
    LEFT / A        - steer left
    RIGHT / D       - steer right
    UP / W          - accelerate
    DOWN / S        - brake
    SPACE / SHIFT   - nitro boost (while gauge has fuel)
    P / ESC         - pause
    ENTER           - confirm menu / restart after game over
"""

import json
import math
import os
import random
import sys

import pygame

# --------------------------------------------------------------------------- #
# Setup & constants
# --------------------------------------------------------------------------- #

pygame.init()

WIDTH, HEIGHT = 900, 720
FPS = 60

ROAD_WIDTH = 480
ROAD_LEFT = (WIDTH - ROAD_WIDTH) // 2
ROAD_RIGHT = ROAD_LEFT + ROAD_WIDTH
LANE_COUNT = 3
LANE_WIDTH = ROAD_WIDTH // LANE_COUNT

HIGH_SCORE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "highscore.json")

# Colors
NIGHT_SKY_TOP = (18, 22, 42)
NIGHT_SKY_BOTTOM = (40, 34, 62)
GRASS_DARK = (24, 82, 42)
GRASS_LIGHT = (30, 96, 50)
ROAD_COLOR = (46, 46, 54)
ROAD_EDGE = (230, 210, 60)
LANE_LINE = (235, 235, 235)
WHITE = (255, 255, 255)
BLACK = (10, 10, 10)
RED = (220, 60, 60)
GOLD = (255, 205, 60)
CYAN = (80, 220, 235)
SHADOW = (0, 0, 0)

CAR_COLORS = [
    (220, 60, 60),
    (60, 120, 220),
    (240, 170, 40),
    (150, 90, 220),
    (60, 190, 120),
    (230, 230, 230),
]

PLAYER_COLOR = (235, 60, 90)

screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Care Rase")
clock = pygame.time.Clock()

FONT_BIG = pygame.font.SysFont("arialblack", 64)
FONT_MED = pygame.font.SysFont("arial", 34, bold=True)
FONT_SMALL = pygame.font.SysFont("arial", 22, bold=True)
FONT_TINY = pygame.font.SysFont("arial", 16)


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #

def clamp(v, lo, hi):
    return max(lo, min(hi, v))


def lerp(a, b, t):
    return a + (b - a) * t


def vertical_gradient(surface, top_color, bottom_color):
    h = surface.get_height()
    for y in range(h):
        t = y / h
        color = (
            int(lerp(top_color[0], bottom_color[0], t)),
            int(lerp(top_color[1], bottom_color[1], t)),
            int(lerp(top_color[2], bottom_color[2], t)),
        )
        pygame.draw.line(surface, color, (0, y), (surface.get_width(), y))


def load_high_score():
    try:
        with open(HIGH_SCORE_FILE, "r") as f:
            return json.load(f).get("high_score", 0)
    except (FileNotFoundError, json.JSONDecodeError):
        return 0


def save_high_score(score):
    try:
        with open(HIGH_SCORE_FILE, "w") as f:
            json.dump({"high_score": score}, f)
    except OSError:
        pass


def lane_center_x(lane_index):
    return ROAD_LEFT + LANE_WIDTH * lane_index + LANE_WIDTH // 2


def draw_text_centered(surf, text, font, color, cx, cy, shadow=True):
    if shadow:
        shadow_surf = font.render(text, True, BLACK)
        rect = shadow_surf.get_rect(center=(cx + 3, cy + 3))
        surf.blit(shadow_surf, rect)
    render = font.render(text, True, color)
    rect = render.get_rect(center=(cx, cy))
    surf.blit(render, rect)


# --------------------------------------------------------------------------- #
# Visual effects
# --------------------------------------------------------------------------- #

class Particle:
    __slots__ = ("x", "y", "vx", "vy", "life", "max_life", "color", "radius")

    def __init__(self, x, y, vx, vy, life, color, radius):
        self.x, self.y = x, y
        self.vx, self.vy = vx, vy
        self.life = life
        self.max_life = life
        self.color = color
        self.radius = radius

    def update(self, dt):
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.vy += 40 * dt
        self.life -= dt
        return self.life > 0

    def draw(self, surf):
        t = clamp(self.life / self.max_life, 0, 1)
        r = max(1, int(self.radius * t))
        alpha = int(255 * t)
        s = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
        pygame.draw.circle(s, (*self.color, alpha), (r, r), r)
        surf.blit(s, (self.x - r, self.y - r))


class ParticleSystem:
    def __init__(self):
        self.particles = []

    def emit_smoke(self, x, y):
        self.particles.append(Particle(
            x + random.uniform(-4, 4), y + random.uniform(-2, 2),
            random.uniform(-10, 10), random.uniform(20, 50),
            random.uniform(0.35, 0.6), (120, 120, 130), random.randint(4, 8)))

    def emit_boost(self, x, y):
        self.particles.append(Particle(
            x + random.uniform(-6, 6), y,
            random.uniform(-20, 20), random.uniform(140, 220),
            random.uniform(0.25, 0.4),
            random.choice([(255, 150, 40), (255, 210, 60), (255, 90, 30)]),
            random.randint(4, 9)))

    def emit_explosion(self, x, y):
        for _ in range(45):
            angle = random.uniform(0, math.tau)
            speed = random.uniform(60, 320)
            self.particles.append(Particle(
                x, y, math.cos(angle) * speed, math.sin(angle) * speed,
                random.uniform(0.4, 0.9),
                random.choice([(255, 120, 30), (255, 200, 40), (200, 40, 20), (90, 90, 90)]),
                random.randint(3, 10)))

    def emit_sparkle(self, x, y):
        for _ in range(14):
            angle = random.uniform(0, math.tau)
            speed = random.uniform(30, 140)
            self.particles.append(Particle(
                x, y, math.cos(angle) * speed, math.sin(angle) * speed,
                random.uniform(0.3, 0.5), GOLD, random.randint(2, 5)))

    def update(self, dt):
        self.particles = [p for p in self.particles if p.update(dt)]

    def draw(self, surf):
        for p in self.particles:
            p.draw(surf)


class ScreenShake:
    def __init__(self):
        self.strength = 0.0

    def kick(self, amount):
        self.strength = max(self.strength, amount)

    def update(self, dt):
        self.strength = max(0.0, self.strength - dt * 40)

    def offset(self):
        if self.strength <= 0:
            return 0, 0
        return (random.uniform(-1, 1) * self.strength, random.uniform(-1, 1) * self.strength)


# --------------------------------------------------------------------------- #
# Car drawing (procedural, no image assets required)
# --------------------------------------------------------------------------- #

def draw_car(surf, cx, cy, color, width=52, height=92, tilt=0, headlights=True, taillights=False):
    car_surf = pygame.Surface((width + 40, height + 40), pygame.SRCALPHA)
    ox, oy = (width + 40) // 2, (height + 40) // 2

    # shadow
    shadow_surf = pygame.Surface((width + 40, height + 40), pygame.SRCALPHA)
    pygame.draw.ellipse(shadow_surf, (0, 0, 0, 90), (ox - width / 2 + 6, oy - height / 2 + 14, width, height))
    surf.blit(shadow_surf, (cx - ox + 4, cy - oy + 10))

    body_rect = pygame.Rect(ox - width / 2, oy - height / 2, width, height)
    dark = tuple(clamp(c - 60, 0, 255) for c in color)
    light = tuple(clamp(c + 45, 0, 255) for c in color)

    pygame.draw.rect(car_surf, dark, body_rect, border_radius=18)
    inner = body_rect.inflate(-6, -6)
    pygame.draw.rect(car_surf, color, inner, border_radius=16)

    highlight = pygame.Rect(inner.x + 4, inner.y + 4, inner.width - 8, inner.height * 0.35)
    pygame.draw.rect(car_surf, light, highlight, border_radius=12)

    windshield = pygame.Rect(ox - width * 0.32, oy - height * 0.30, width * 0.64, height * 0.22)
    pygame.draw.rect(car_surf, (40, 60, 90), windshield, border_radius=6)
    rear_window = pygame.Rect(ox - width * 0.30, oy + height * 0.06, width * 0.60, height * 0.18)
    pygame.draw.rect(car_surf, (40, 60, 90), rear_window, border_radius=6)

    stripe = pygame.Rect(ox - 4, oy - height / 2 + 4, 8, height - 8)
    pygame.draw.rect(car_surf, light, stripe, border_radius=4)

    wheel_w, wheel_h = 10, 22
    for wx in (ox - width / 2 - wheel_w / 2 + 2, ox + width / 2 - wheel_w / 2 - 2):
        for wy in (oy - height / 2 + 14, oy + height / 2 - 14 - wheel_h):
            pygame.draw.rect(car_surf, (15, 15, 15), (wx, wy, wheel_w, wheel_h), border_radius=4)

    if headlights:
        for lx in (ox - width * 0.30, ox + width * 0.30 - 8):
            pygame.draw.rect(car_surf, (255, 250, 200), (lx, oy - height / 2 + 2, 8, 6), border_radius=2)
    if taillights:
        for lx in (ox - width * 0.30, ox + width * 0.30 - 8):
            pygame.draw.rect(car_surf, (255, 60, 60), (lx, oy + height / 2 - 8, 8, 6), border_radius=2)

    if tilt:
        car_surf = pygame.transform.rotate(car_surf, tilt)

    rect = car_surf.get_rect(center=(cx, cy))
    surf.blit(car_surf, rect)


# --------------------------------------------------------------------------- #
# Entities
# --------------------------------------------------------------------------- #

class Player:
    WIDTH, HEIGHT = 52, 92

    def __init__(self):
        self.lane_pos = 1.0  # fractional lane index 0..LANE_COUNT-1
        self.x = lane_center_x(1)
        self.y = HEIGHT_GROUND
        self.vx = 0.0
        self.speed = 260.0
        self.min_speed = 150.0
        self.max_speed = 560.0
        self.tilt = 0.0
        self.nitro = 100.0
        self.nitro_active = False
        self.invincible_timer = 0.0
        self.alive = True

    @property
    def rect(self):
        return pygame.Rect(self.x - self.WIDTH * 0.38, self.y - self.HEIGHT * 0.42,
                            self.WIDTH * 0.76, self.HEIGHT * 0.84)

    def update(self, dt, keys, particles):
        steer = 0
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            steer -= 1
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            steer += 1

        target_vx = steer * 340
        self.vx = lerp(self.vx, target_vx, clamp(dt * 8, 0, 1))
        self.x += self.vx * dt
        self.x = clamp(self.x, ROAD_LEFT + self.WIDTH * 0.55, ROAD_RIGHT - self.WIDTH * 0.55)

        self.tilt = lerp(self.tilt, -self.vx * 0.045, clamp(dt * 10, 0, 1))

        accelerate = keys[pygame.K_UP] or keys[pygame.K_w]
        brake = keys[pygame.K_DOWN] or keys[pygame.K_s]
        if accelerate:
            self.speed += 260 * dt
        elif brake:
            self.speed -= 340 * dt
        else:
            self.speed += (self.min_speed + 120 - self.speed) * dt * 0.6

        want_boost = (keys[pygame.K_SPACE] or keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT])
        self.nitro_active = want_boost and self.nitro > 0
        if self.nitro_active:
            self.speed += 520 * dt
            self.nitro -= 55 * dt
            particles.emit_boost(self.x - math.sin(math.radians(self.tilt)) * 10,
                                  self.y + self.HEIGHT * 0.42)
        else:
            self.nitro = min(100.0, self.nitro + 8 * dt)

        self.speed = clamp(self.speed, self.min_speed, self.max_speed)

        if self.invincible_timer > 0:
            self.invincible_timer -= dt

        if random.random() < dt * 18:
            particles.emit_smoke(self.x - 14 * math.copysign(1, self.tilt + 0.001),
                                  self.y + self.HEIGHT * 0.40)

    def draw(self, surf):
        if self.invincible_timer > 0 and int(self.invincible_timer * 12) % 2 == 0:
            return
        draw_car(surf, self.x, self.y, PLAYER_COLOR, self.WIDTH, self.HEIGHT, tilt=self.tilt,
                 headlights=True, taillights=self.speed < self.min_speed + 40)


class TrafficCar:
    WIDTH, HEIGHT = 50, 88

    def __init__(self, lane, y, speed, color, kind="car"):
        self.lane = lane
        self.x = lane_center_x(lane)
        self.y = y
        self.speed = speed
        self.color = color
        self.kind = kind
        self.scored = False

    @property
    def rect(self):
        return pygame.Rect(self.x - self.WIDTH * 0.38, self.y - self.HEIGHT * 0.42,
                            self.WIDTH * 0.76, self.HEIGHT * 0.84)

    def update(self, dt, world_speed):
        self.y += (world_speed - self.speed) * dt

    def draw(self, surf):
        draw_car(surf, self.x, self.y, self.color, self.WIDTH, self.HEIGHT, taillights=True)


class Coin:
    def __init__(self, lane, y):
        self.x = lane_center_x(lane)
        self.y = y
        self.collected = False
        self.spin = random.uniform(0, math.tau)

    @property
    def rect(self):
        return pygame.Rect(self.x - 14, self.y - 14, 28, 28)

    def update(self, dt, world_speed):
        self.y += world_speed * dt
        self.spin += dt * 6

    def draw(self, surf):
        w = max(2, int(10 * abs(math.cos(self.spin))) + 4)
        pygame.draw.ellipse(surf, (255, 215, 60), (self.x - w, self.y - 14, w * 2, 28))
        pygame.draw.ellipse(surf, (255, 240, 150), (self.x - w + 3, self.y - 10, max(1, w - 3) * 2, 20), 2)


# --------------------------------------------------------------------------- #
# Background scenery
# --------------------------------------------------------------------------- #

class Scenery:
    def __init__(self):
        self.items = []
        for i in range(14):
            self.items.append(self._make(random.uniform(0, HEIGHT)))

    def _make(self, y):
        side = random.choice(["left", "right"])
        margin = random.uniform(20, 140)
        x = ROAD_LEFT - margin if side == "left" else ROAD_RIGHT + margin
        kind = random.choice(["tree", "tree", "bush", "lamp"])
        return {"x": x, "y": y, "kind": kind, "scale": random.uniform(0.8, 1.3)}

    def update(self, dt, world_speed):
        for item in self.items:
            item["y"] += world_speed * dt * 1.05
            if item["y"] > HEIGHT + 60:
                item["y"] = -60
                item.update(self._make(-60))

    def draw(self, surf):
        for item in self.items:
            x, y, kind, scale = item["x"], item["y"], item["kind"], item["scale"]
            if kind == "tree":
                pygame.draw.rect(surf, (90, 60, 35), (x - 4 * scale, y, 8 * scale, 26 * scale))
                pygame.draw.circle(surf, (24, 90, 40), (int(x), int(y - 10 * scale)), int(24 * scale))
                pygame.draw.circle(surf, (34, 110, 50), (int(x - 6 * scale), int(y - 18 * scale)), int(16 * scale))
            elif kind == "bush":
                pygame.draw.circle(surf, (30, 100, 45), (int(x), int(y)), int(14 * scale))
                pygame.draw.circle(surf, (40, 120, 55), (int(x + 8 * scale), int(y + 3 * scale)), int(10 * scale))
            elif kind == "lamp":
                pygame.draw.rect(surf, (60, 60, 65), (x - 2, y - 40 * scale, 4, 40 * scale))
                pygame.draw.circle(surf, (255, 235, 150), (int(x), int(y - 40 * scale)), int(6 * scale))


HEIGHT_GROUND = HEIGHT - 130


# --------------------------------------------------------------------------- #
# Game
# --------------------------------------------------------------------------- #

MENU, PLAYING, PAUSED, GAME_OVER = range(4)


class Game:
    def __init__(self):
        self.state = MENU
        self.high_score = load_high_score()
        self.reset()
        self.road_scroll = 0.0
        self.scenery = Scenery()
        self.particles = ParticleSystem()
        self.shake = ScreenShake()
        self.title_pulse = 0.0

    def reset(self):
        self.player = Player()
        self.traffic = []
        self.coins = []
        self.spawn_timer = 0.0
        self.coin_timer = 1.5
        self.distance = 0.0
        self.score = 0
        self.difficulty = 1.0
        self.elapsed = 0.0
        self.lane_cooldowns = [0.0] * LANE_COUNT
        self.particles = ParticleSystem() if hasattr(self, "particles") else ParticleSystem()
        self.shake = ScreenShake() if hasattr(self, "shake") else ScreenShake()

    # ---- spawning ------------------------------------------------------ #

    def spawn_traffic(self):
        lane = random.randint(0, LANE_COUNT - 1)
        if self.lane_cooldowns[lane] > 0:
            return
        speed = random.uniform(90, 200) * (0.9 + self.difficulty * 0.1)
        color = random.choice(CAR_COLORS)
        self.traffic.append(TrafficCar(lane, -120, speed, color))
        self.lane_cooldowns[lane] = random.uniform(0.5, 1.1)

    def spawn_coin(self):
        lane = random.randint(0, LANE_COUNT - 1)
        self.coins.append(Coin(lane, -40))

    # ---- update ---------------------------------------------------------- #

    def update(self, dt, keys):
        self.title_pulse += dt

        if self.state != PLAYING:
            return

        self.elapsed += dt
        self.difficulty = 1.0 + self.elapsed / 25.0

        self.player.update(dt, keys, self.particles)
        world_speed = self.player.speed

        self.road_scroll = (self.road_scroll + world_speed * dt) % 80
        self.distance += world_speed * dt
        self.score = int(self.distance / 10)

        self.scenery.update(dt, world_speed)

        for i in range(LANE_COUNT):
            self.lane_cooldowns[i] = max(0.0, self.lane_cooldowns[i] - dt)

        self.spawn_timer -= dt
        if self.spawn_timer <= 0:
            self.spawn_traffic()
            self.spawn_timer = clamp(random.uniform(0.5, 1.1) / self.difficulty, 0.28, 1.1)

        self.coin_timer -= dt
        if self.coin_timer <= 0:
            self.spawn_coin()
            self.coin_timer = random.uniform(1.0, 2.0)

        for car in self.traffic:
            car.update(dt, world_speed)
        self.traffic = [c for c in self.traffic if c.y < HEIGHT + 150]

        for coin in self.coins:
            coin.update(dt, world_speed)
        self.coins = [c for c in self.coins if c.y < HEIGHT + 60 and not c.collected]

        self.particles.update(dt)
        self.shake.update(dt)

        self._handle_collisions()

    def _handle_collisions(self):
        player_rect = self.player.rect

        if self.player.invincible_timer <= 0:
            for car in self.traffic:
                if player_rect.colliderect(car.rect):
                    self._crash()
                    return

        for coin in self.coins:
            if not coin.collected and player_rect.colliderect(coin.rect):
                coin.collected = True
                self.score += 25
                self.player.nitro = min(100.0, self.player.nitro + 18)
                self.particles.emit_sparkle(coin.x, coin.y)

    def _crash(self):
        self.particles.emit_explosion(self.player.x, self.player.y)
        self.shake.kick(18)
        self.state = GAME_OVER
        self.player.alive = False
        if self.score > self.high_score:
            self.high_score = self.score
            save_high_score(self.high_score)

    # ---- drawing ----------------------------------------------------------- #

    def draw(self, surf):
        vertical_gradient(surf, NIGHT_SKY_TOP, NIGHT_SKY_BOTTOM)

        ox, oy = self.shake.offset()
        world = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)

        self._draw_road(world)
        self.scenery.draw(world)

        for coin in self.coins:
            coin.draw(world)

        entities = list(self.traffic)
        entities.sort(key=lambda c: c.y)
        for car in entities:
            car.draw(world)

        self.particles.draw(world)

        if self.player.alive:
            self.player.draw(world)

        surf.blit(world, (ox, oy))

        self._draw_hud(surf)

        if self.state == MENU:
            self._draw_menu(surf)
        elif self.state == PAUSED:
            self._draw_pause(surf)
        elif self.state == GAME_OVER:
            self._draw_game_over(surf)

    def _draw_road(self, surf):
        pygame.draw.rect(surf, GRASS_DARK, (0, 0, ROAD_LEFT, HEIGHT))
        pygame.draw.rect(surf, GRASS_DARK, (ROAD_RIGHT, 0, WIDTH - ROAD_RIGHT, HEIGHT))
        for y in range(-80, HEIGHT + 80, 40):
            yy = (y + self.road_scroll * 0.5) % (HEIGHT + 80) - 80
            pygame.draw.rect(surf, GRASS_LIGHT, (0, yy, ROAD_LEFT, 20))
            pygame.draw.rect(surf, GRASS_LIGHT, (ROAD_RIGHT, yy, WIDTH - ROAD_RIGHT, 20))

        pygame.draw.rect(surf, ROAD_COLOR, (ROAD_LEFT, 0, ROAD_WIDTH, HEIGHT))

        pygame.draw.rect(surf, ROAD_EDGE, (ROAD_LEFT - 6, 0, 6, HEIGHT))
        pygame.draw.rect(surf, ROAD_EDGE, (ROAD_RIGHT, 0, 6, HEIGHT))

        for lane in range(1, LANE_COUNT):
            x = ROAD_LEFT + lane * LANE_WIDTH
            for y in range(-80, HEIGHT + 80, 60):
                yy = (y + self.road_scroll) % (HEIGHT + 80) - 80
                pygame.draw.rect(surf, LANE_LINE, (x - 3, yy, 6, 34), border_radius=3)

    def _draw_hud(self, surf):
        panel = pygame.Surface((260, 96), pygame.SRCALPHA)
        pygame.draw.rect(panel, (0, 0, 0, 120), (0, 0, 260, 96), border_radius=14)
        surf.blit(panel, (16, 16))

        score_text = FONT_SMALL.render(f"Score: {self.score}", True, WHITE)
        surf.blit(score_text, (30, 24))
        hs_text = FONT_TINY.render(f"Best: {self.high_score}", True, (200, 200, 210))
        surf.blit(hs_text, (30, 54))

        speed_pct = clamp((self.player.speed - self.player.min_speed) /
                           (self.player.max_speed - self.player.min_speed), 0, 1)
        bar_x, bar_y, bar_w, bar_h = 30, 76, 200, 12
        pygame.draw.rect(surf, (60, 60, 70), (bar_x, bar_y, bar_w, bar_h), border_radius=6)
        pygame.draw.rect(surf, CYAN, (bar_x, bar_y, bar_w * speed_pct, bar_h), border_radius=6)

        nitro_panel = pygame.Surface((260, 54), pygame.SRCALPHA)
        pygame.draw.rect(nitro_panel, (0, 0, 0, 120), (0, 0, 260, 54), border_radius=14)
        surf.blit(nitro_panel, (WIDTH - 276, 16))
        label = FONT_TINY.render("NITRO", True, (255, 210, 120))
        surf.blit(label, (WIDTH - 260, 22))
        nx, ny, nw, nh = WIDTH - 260, 42, 220, 14
        pygame.draw.rect(surf, (60, 60, 70), (nx, ny, nw, nh), border_radius=7)
        color = (255, 160, 40) if self.player.nitro_active else GOLD
        pygame.draw.rect(surf, color, (nx, ny, nw * (self.player.nitro / 100), nh), border_radius=7)

    def _draw_menu(self, surf):
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 140))
        surf.blit(overlay, (0, 0))

        pulse = 1 + 0.03 * math.sin(self.title_pulse * 2)
        title_font = pygame.font.SysFont("arialblack", int(70 * pulse))
        title = title_font.render("CARE RASE", True, GOLD)
        rect = title.get_rect(center=(WIDTH / 2, HEIGHT / 2 - 160))
        shadow = title_font.render("CARE RASE", True, BLACK)
        surf.blit(shadow, rect.move(4, 4))
        surf.blit(title, rect)

        draw_text_centered(surf, "Dodge traffic. Grab coins. Beat your best.",
                            FONT_SMALL, WHITE, WIDTH / 2, HEIGHT / 2 - 90)

        draw_car(surf, WIDTH / 2, HEIGHT / 2 - 10, PLAYER_COLOR, 60, 104)

        blink = int(self.title_pulse * 2) % 2 == 0
        if blink:
            draw_text_centered(surf, "PRESS ENTER TO START", FONT_MED, CYAN, WIDTH / 2, HEIGHT / 2 + 110)

        controls = [
            "ARROWS / WASD  -  steer, accelerate, brake",
            "SPACE / SHIFT  -  nitro boost",
            "P  -  pause",
        ]
        for i, line in enumerate(controls):
            draw_text_centered(surf, line, FONT_TINY, (210, 210, 220), WIDTH / 2, HEIGHT / 2 + 160 + i * 26)

        draw_text_centered(surf, f"Best Score: {self.high_score}", FONT_SMALL, GOLD, WIDTH / 2, HEIGHT / 2 + 260)

    def _draw_pause(self, surf):
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 160))
        surf.blit(overlay, (0, 0))
        draw_text_centered(surf, "PAUSED", FONT_BIG, WHITE, WIDTH / 2, HEIGHT / 2 - 30)
        draw_text_centered(surf, "Press P to resume", FONT_MED, CYAN, WIDTH / 2, HEIGHT / 2 + 40)

    def _draw_game_over(self, surf):
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 170))
        surf.blit(overlay, (0, 0))

        draw_text_centered(surf, "CRASHED!", FONT_BIG, RED, WIDTH / 2, HEIGHT / 2 - 120)
        draw_text_centered(surf, f"Score: {self.score}", FONT_MED, WHITE, WIDTH / 2, HEIGHT / 2 - 40)

        if self.score >= self.high_score and self.score > 0:
            draw_text_centered(surf, "NEW BEST!", FONT_MED, GOLD, WIDTH / 2, HEIGHT / 2 + 6)
        else:
            draw_text_centered(surf, f"Best: {self.high_score}", FONT_SMALL, (200, 200, 210), WIDTH / 2, HEIGHT / 2 + 6)

        blink = int(self.title_pulse * 2) % 2 == 0
        if blink:
            draw_text_centered(surf, "PRESS ENTER TO RETRY", FONT_MED, CYAN, WIDTH / 2, HEIGHT / 2 + 90)
        draw_text_centered(surf, "ESC for menu", FONT_TINY, (200, 200, 210), WIDTH / 2, HEIGHT / 2 + 140)

    # ---- input handling -------------------------------------------------- #

    def handle_keydown(self, key):
        if self.state == MENU and key in (pygame.K_RETURN, pygame.K_SPACE):
            self.reset()
            self.state = PLAYING
        elif self.state == PLAYING and key in (pygame.K_p, pygame.K_ESCAPE):
            self.state = PAUSED
        elif self.state == PAUSED and key in (pygame.K_p, pygame.K_ESCAPE):
            self.state = PLAYING
        elif self.state == GAME_OVER and key == pygame.K_RETURN:
            self.reset()
            self.state = PLAYING
        elif self.state == GAME_OVER and key == pygame.K_ESCAPE:
            self.state = MENU


# --------------------------------------------------------------------------- #
# Main loop
# --------------------------------------------------------------------------- #

def main():
    game = Game()
    running = True
    while running:
        dt = clock.tick(FPS) / 1000.0
        dt = min(dt, 1 / 30)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_q and (pygame.key.get_mods() & pygame.KMOD_CTRL):
                    running = False
                game.handle_keydown(event.key)

        keys = pygame.key.get_pressed()
        game.update(dt, keys)
        game.draw(screen)

        pygame.display.flip()

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
