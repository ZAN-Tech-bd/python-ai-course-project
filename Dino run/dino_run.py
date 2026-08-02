import json
import math
import os
import random
import sys

import pygame

WIDTH, HEIGHT = 1000, 350
GROUND_Y = 290
FPS = 60

GRAVITY = 2600.0
JUMP_VELOCITY = -880.0
JUMP_CUT_MULT = 0.45
FAST_FALL_BONUS = 1700.0

START_SPEED = 340.0
MAX_SPEED = 820.0
SPEED_ACCEL = 3.2

DINO_X = 110
HIGHSCORE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "highscore.json")

STATE_START, STATE_PLAYING, STATE_PAUSED, STATE_GAMEOVER = range(4)


def lerp(a, b, t):
    return a + (b - a) * t


def lerp_color(c1, c2, t):
    return tuple(int(lerp(a, b, t)) for a, b in zip(c1, c2))


def clamp(v, lo, hi):
    return max(lo, min(hi, v))


class Palette:
    DAY_SKY_TOP = (135, 206, 250)
    DAY_SKY_BOTTOM = (224, 246, 255)
    NIGHT_SKY_TOP = (10, 12, 40)
    NIGHT_SKY_BOTTOM = (35, 35, 70)

    DAY_HILL = (168, 202, 148)
    NIGHT_HILL = (25, 28, 48)

    DAY_GROUND = (86, 60, 40)
    NIGHT_GROUND = (30, 28, 45)

    DAY_CLOUD = (255, 255, 255)
    NIGHT_CLOUD = (90, 95, 130)

    DAY_UI = (60, 60, 60)
    NIGHT_UI = (230, 230, 240)


def make_beep(freq, duration, volume=0.4, wave="sine", sweep_to=None):
    try:
        import numpy as np
    except ImportError:
        return None
    sr = 44100
    n = int(sr * duration)
    t = np.linspace(0, duration, n, False)
    if sweep_to is not None:
        f = np.linspace(freq, sweep_to, n)
        phase = 2 * np.pi * np.cumsum(f) / sr
    else:
        phase = 2 * np.pi * freq * t
    if wave == "square":
        tone = np.sign(np.sin(phase))
    else:
        tone = np.sin(phase)
    envelope = np.ones(n)
    fade = max(1, n // 12)
    envelope[:fade] = np.linspace(0, 1, fade)
    envelope[-fade:] = np.linspace(1, 0, fade)
    tone = tone * envelope * volume
    stereo = np.repeat((tone * 32767).astype(np.int16).reshape(-1, 1), 2, axis=1)
    stereo = np.ascontiguousarray(stereo)
    return pygame.sndarray.make_sound(stereo)


class SoundBank:
    def __init__(self):
        self.enabled = False
        self.jump = self.point = self.hit = self.duck = None
        try:
            pygame.mixer.pre_init(44100, -16, 2, 256)
            pygame.mixer.init()
            self.jump = make_beep(520, 0.11, 0.35, sweep_to=880)
            self.point = make_beep(900, 0.08, 0.3)
            self.hit = make_beep(160, 0.25, 0.45, wave="square", sweep_to=60)
            self.duck = make_beep(300, 0.05, 0.2)
            self.enabled = self.jump is not None
        except Exception:
            self.enabled = False

    def play(self, name):
        if not self.enabled:
            return
        snd = getattr(self, name, None)
        if snd is not None:
            snd.play()


class HighScore:
    def __init__(self):
        self.value = 0
        self.load()

    def load(self):
        try:
            with open(HIGHSCORE_FILE, "r") as f:
                self.value = int(json.load(f).get("high_score", 0))
        except Exception:
            self.value = 0

    def save(self):
        try:
            with open(HIGHSCORE_FILE, "w") as f:
                json.dump({"high_score": self.value}, f)
        except Exception:
            pass


class Particle:
    __slots__ = ("x", "y", "vx", "vy", "life", "max_life", "size", "color")

    def __init__(self, x, y, vx, vy, life, size, color):
        self.x, self.y, self.vx, self.vy = x, y, vx, vy
        self.life = self.max_life = life
        self.size = size
        self.color = color

    def update(self, dt):
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.vy += 900 * dt
        self.life -= dt
        return self.life > 0

    def draw(self, surf, shake):
        t = clamp(self.life / self.max_life, 0, 1)
        alpha = int(255 * t)
        s = max(1, int(self.size * t))
        surface = pygame.Surface((s * 2, s * 2), pygame.SRCALPHA)
        pygame.draw.circle(surface, (*self.color, alpha), (s, s), s)
        surf.blit(surface, (self.x - s + shake[0], self.y - s + shake[1]))


class ParticleSystem:
    def __init__(self):
        self.particles = []

    def dust(self, x, y):
        for _ in range(2):
            self.particles.append(Particle(
                x + random.uniform(-4, 4), y,
                random.uniform(-60, -10), random.uniform(-40, -10),
                random.uniform(0.25, 0.45), random.uniform(3, 5), (200, 190, 170)))

    def burst(self, x, y, color, count=26):
        for _ in range(count):
            ang = random.uniform(0, math.tau)
            speed = random.uniform(80, 320)
            self.particles.append(Particle(
                x, y, math.cos(ang) * speed, math.sin(ang) * speed - 100,
                random.uniform(0.4, 0.8), random.uniform(3, 7), color))

    def confetti(self, x, y):
        colors = [(255, 90, 90), (255, 200, 60), (90, 200, 255), (120, 220, 120), (220, 120, 255)]
        for _ in range(3):
            self.particles.append(Particle(
                x + random.uniform(-30, 30), y,
                random.uniform(-40, 40), random.uniform(-260, -160),
                random.uniform(0.9, 1.6), random.uniform(3, 5), random.choice(colors)))

    def update(self, dt):
        self.particles = [p for p in self.particles if p.update(dt)]

    def draw(self, surf, shake):
        for p in self.particles:
            p.draw(surf, shake)


class Dino:
    WIDTH_RUN, HEIGHT_RUN = 46, 54
    WIDTH_DUCK, HEIGHT_DUCK = 64, 32

    def __init__(self, sounds: SoundBank):
        self.sounds = sounds
        self.reset()

    def reset(self):
        self.y = GROUND_Y - self.HEIGHT_RUN
        self.vel_y = 0.0
        self.on_ground = True
        self.ducking = False
        self.leg_phase = 0.0
        self.blink_timer = random.uniform(2, 5)
        self.blinking = False
        self.jump_held = False
        self.squash = 1.0

    @property
    def height(self):
        return self.HEIGHT_DUCK if self.ducking else self.HEIGHT_RUN

    @property
    def width(self):
        return self.WIDTH_DUCK if self.ducking else self.WIDTH_RUN

    def rect(self):
        w, h = self.width, self.height
        inset_x, inset_y = w * 0.22, h * 0.14
        return pygame.Rect(DINO_X + inset_x, self.y + inset_y, w - inset_x * 2, h - inset_y * 1.6)

    def jump(self):
        if self.on_ground:
            self.vel_y = JUMP_VELOCITY
            self.on_ground = False
            self.jump_held = True
            self.ducking = False
            self.squash = 1.35
            self.sounds.play("jump")

    def cut_jump(self):
        if not self.on_ground and self.vel_y < 0 and self.jump_held:
            self.vel_y *= JUMP_CUT_MULT
            self.jump_held = False

    def set_duck(self, held, particles):
        if held and self.on_ground:
            if not self.ducking:
                self.ducking = True
        elif not held:
            self.ducking = False
        self.fast_fall = held and not self.on_ground

    def update(self, dt, speed, particles):
        base_y = GROUND_Y - self.height
        if self.on_ground:
            self.leg_phase += dt * (7 + speed * 0.018)
            if int(self.leg_phase * 2) % 2 == 0 and random.random() < 0.6:
                particles.dust(DINO_X + 6, GROUND_Y - 2)
        else:
            fall_bonus = FAST_FALL_BONUS if getattr(self, "fast_fall", False) else 0
            self.vel_y += (GRAVITY + fall_bonus) * dt
            self.y += self.vel_y * dt
            if self.y >= base_y:
                self.y = base_y
                if not self.on_ground:
                    particles.dust(DINO_X + 10, GROUND_Y - 2)
                    particles.dust(DINO_X - 6, GROUND_Y - 2)
                self.on_ground = True
                self.vel_y = 0
                self.squash = 1.3
            self.y = min(self.y, base_y)
        if self.on_ground:
            self.y = base_y

        self.squash = lerp(self.squash, 1.0, min(1, dt * 10))

        self.blink_timer -= dt
        if self.blink_timer <= 0:
            self.blinking = not self.blinking
            self.blink_timer = random.uniform(0.08, 0.15) if self.blinking else random.uniform(2, 5)

    def draw(self, surf, shake, ui_light):
        x = DINO_X + shake[0]
        y = self.y + shake[1]
        body_color = (86, 175, 110)
        belly_color = (170, 225, 175)
        dark = (46, 110, 65)

        if self.ducking:
            self._draw_duck(surf, x, y, body_color, belly_color, dark)
        elif not self.on_ground:
            self._draw_jump(surf, x, y, body_color, belly_color, dark)
        else:
            self._draw_run(surf, x, y, body_color, belly_color, dark)

    def _eye(self, surf, cx, cy, blinking):
        if blinking:
            pygame.draw.line(surf, (30, 30, 30), (cx - 4, cy), (cx + 4, cy), 2)
        else:
            pygame.draw.circle(surf, (255, 255, 255), (cx, cy), 5)
            pygame.draw.circle(surf, (25, 25, 25), (cx + 1, cy), 2)

    def _draw_run(self, surf, x, y, body_color, belly_color, dark):
        w, h = self.WIDTH_RUN, self.HEIGHT_RUN
        sq = self.squash
        cx, cy = x + w * 0.42, y + h * 0.55
        bw, bh = w * 0.62 * (2 - sq), h * 0.62 * sq

        leg_off1 = math.sin(self.leg_phase) * 9
        leg_off2 = math.sin(self.leg_phase + math.pi) * 9
        for off, lift in ((leg_off1, 0), (leg_off2, 0)):
            lx = x + w * 0.32 + off * 0.3
            ly_len = 20 + max(0, -off)
            pygame.draw.rect(surf, dark, (lx, y + h - 6, 10, ly_len - 6 + max(0, off * 0.2)), border_radius=3)

        pygame.draw.polygon(surf, body_color, [
            (x + w * 0.05, y + h * 0.62), (x + w * 0.28, y + h * 0.42), (x + w * 0.28, y + h * 0.72)])

        body_rect = pygame.Rect(0, 0, bw, bh)
        body_rect.center = (cx, cy)
        pygame.draw.ellipse(surf, body_color, body_rect)
        belly_rect = pygame.Rect(0, 0, bw * 0.7, bh * 0.55)
        belly_rect.center = (cx + 2, cy + bh * 0.18)
        pygame.draw.ellipse(surf, belly_color, belly_rect)

        head_r = w * 0.30
        head_cx, head_cy = x + w * 0.78, y + h * 0.30
        pygame.draw.circle(surf, body_color, (int(head_cx), int(head_cy)), int(head_r))
        snout = pygame.Rect(0, 0, head_r * 1.3, head_r * 0.9)
        snout.midleft = (head_cx - 2, head_cy + head_r * 0.25)
        pygame.draw.ellipse(surf, body_color, snout)
        pygame.draw.circle(surf, dark, (int(head_cx + head_r * 1.1), int(head_cy + head_r * 0.45)), 2)

        arm_x, arm_y = x + w * 0.5, y + h * 0.62
        pygame.draw.line(surf, dark, (arm_x, arm_y), (arm_x + 10, arm_y + 8), 5)

        self._eye(surf, int(head_cx + 4), int(head_cy - 3), self.blinking)

    def _draw_jump(self, surf, x, y, body_color, belly_color, dark):
        w, h = self.WIDTH_RUN, self.HEIGHT_RUN
        sq = self.squash
        cx, cy = x + w * 0.42, y + h * 0.5
        bw, bh = w * 0.64 * (2 - sq), h * 0.66 * sq

        pygame.draw.rect(surf, dark, (x + w * 0.28, y + h - 16, 11, 16), border_radius=3)
        pygame.draw.rect(surf, dark, (x + w * 0.5, y + h - 20, 11, 20), border_radius=3)

        pygame.draw.polygon(surf, body_color, [
            (x + w * 0.02, y + h * 0.55), (x + w * 0.26, y + h * 0.32), (x + w * 0.26, y + h * 0.66)])

        body_rect = pygame.Rect(0, 0, bw, bh)
        body_rect.center = (cx, cy)
        pygame.draw.ellipse(surf, body_color, body_rect)
        belly_rect = pygame.Rect(0, 0, bw * 0.7, bh * 0.5)
        belly_rect.center = (cx + 2, cy + bh * 0.2)
        pygame.draw.ellipse(surf, belly_color, belly_rect)

        head_r = w * 0.30
        head_cx, head_cy = x + w * 0.8, y + h * 0.22
        pygame.draw.circle(surf, body_color, (int(head_cx), int(head_cy)), int(head_r))
        snout = pygame.Rect(0, 0, head_r * 1.3, head_r * 0.9)
        snout.midleft = (head_cx - 2, head_cy + head_r * 0.2)
        pygame.draw.ellipse(surf, body_color, snout)
        self._eye(surf, int(head_cx + 4), int(head_cy - 4), False)

    def _draw_duck(self, surf, x, y, body_color, belly_color, dark):
        w, h = self.WIDTH_DUCK, self.HEIGHT_DUCK
        cx, cy = x + w * 0.4, y + h * 0.55
        bw, bh = w * 0.75, h * 0.7

        leg_off = math.sin(self.leg_phase * 1.6) * 6
        for i, off in enumerate((leg_off, -leg_off)):
            lx = x + w * 0.28 + i * 14 + off * 0.2
            pygame.draw.rect(surf, dark, (lx, y + h - 5, 9, 10), border_radius=2)

        body_rect = pygame.Rect(0, 0, bw, bh)
        body_rect.center = (cx, cy)
        pygame.draw.ellipse(surf, body_color, body_rect)
        belly_rect = pygame.Rect(0, 0, bw * 0.6, bh * 0.5)
        belly_rect.center = (cx, cy + bh * 0.2)
        pygame.draw.ellipse(surf, belly_color, belly_rect)

        head_r = w * 0.20
        head_cx, head_cy = x + w * 0.86, y + h * 0.38
        pygame.draw.circle(surf, body_color, (int(head_cx), int(head_cy)), int(head_r))
        snout = pygame.Rect(0, 0, head_r * 1.5, head_r * 0.8)
        snout.midleft = (head_cx, head_cy + head_r * 0.15)
        pygame.draw.ellipse(surf, body_color, snout)
        self._eye(surf, int(head_cx + 2), int(head_cy - 3), self.blinking)

        pygame.draw.polygon(surf, body_color, [
            (x, y + h * 0.5), (x + w * 0.22, y + h * 0.3), (x + w * 0.22, y + h * 0.68)])


class Cactus:
    def __init__(self, x, speed):
        self.kind = random.choice(["small", "small", "medium", "cluster", "tall"])
        self.x = float(x)
        if self.kind == "small":
            self.w, self.h = 26, 46
        elif self.kind == "medium":
            self.w, self.h = 34, 58
        elif self.kind == "tall":
            self.w, self.h = 22, 72
        else:
            self.w, self.h = 56, 46
        self.passed = False

    def update(self, dt, speed):
        self.x -= speed * dt

    def offscreen(self):
        return self.x + self.w < -20

    def rect(self):
        return pygame.Rect(self.x + self.w * 0.15, GROUND_Y - self.h + self.h * 0.1,
                            self.w * 0.7, self.h * 0.85)

    def draw(self, surf, shake, dark_mode):
        color = (60, 110, 70) if not dark_mode else (35, 55, 60)
        highlight = (90, 150, 100) if not dark_mode else (55, 80, 90)
        x = self.x + shake[0]
        base_y = GROUND_Y + shake[1]

        def trunk(px, py, w, h):
            r = pygame.Rect(px, py - h, w, h)
            pygame.draw.rect(surf, color, r, border_radius=int(w * 0.4))
            pygame.draw.rect(surf, highlight, (px + w * 0.2, py - h + 4, w * 0.25, h - 8), border_radius=3)

        if self.kind == "cluster":
            trunk(x, base_y, 16, 34)
            trunk(x + 18, base_y, 20, 46)
            trunk(x + 38, base_y, 16, 30)
        else:
            trunk(x + self.w * 0.3, base_y, self.w * 0.4, self.h)
            arm_y = base_y - self.h * 0.55
            pygame.draw.rect(surf, color, (x, arm_y - 18, self.w * 0.35, 14), border_radius=6)
            pygame.draw.rect(surf, color, (x + self.w * 0.55, arm_y - 26, self.w * 0.35, 14), border_radius=6)


class Bird:
    LANES = [GROUND_Y - 40, GROUND_Y - 95, GROUND_Y - 150]

    def __init__(self, x):
        self.x = float(x)
        self.y = random.choice(self.LANES)
        self.wing_phase = random.uniform(0, math.tau)
        self.w, self.h = 46, 34

    def update(self, dt, speed):
        self.x -= speed * dt
        self.wing_phase += dt * 12

    def offscreen(self):
        return self.x + self.w < -20

    def rect(self):
        return pygame.Rect(self.x + 6, self.y + 8, self.w - 12, self.h - 16)

    def draw(self, surf, shake, dark_mode):
        color = (70, 70, 90) if not dark_mode else (200, 200, 215)
        x = self.x + shake[0]
        y = self.y + shake[1]
        wing = math.sin(self.wing_phase) * 16

        cx, cy = x + self.w * 0.5, y + self.h * 0.5
        pygame.draw.ellipse(surf, color, (cx - 14, cy - 7, 28, 14))
        pygame.draw.polygon(surf, color, [(cx + 12, cy - 3), (cx + 22, cy), (cx + 12, cy + 3)])
        pygame.draw.polygon(surf, color, [(cx - 2, cy), (cx - 20, cy - wing), (cx - 4, cy - 4)])
        pygame.draw.polygon(surf, color, [(cx - 2, cy), (cx - 20, cy + wing), (cx - 4, cy + 4)])


class Cloud:
    def __init__(self, x, y, scale):
        self.x, self.y, self.scale = x, y, scale

    def update(self, dt, speed):
        self.x -= speed * 0.35 * dt

    def draw(self, surf, shake, color):
        x, y = self.x + shake[0] * 0.3, self.y + shake[1] * 0.3
        s = self.scale
        surface = pygame.Surface((90 * s, 40 * s), pygame.SRCALPHA)
        c = (*color, 210)
        pygame.draw.ellipse(surface, c, (0, 14 * s, 60 * s, 20 * s))
        pygame.draw.ellipse(surface, c, (18 * s, 2 * s, 45 * s, 28 * s))
        pygame.draw.ellipse(surface, c, (40 * s, 12 * s, 50 * s, 22 * s))
        surf.blit(surface, (x, y))


class Hill:
    def __init__(self, x, height, width):
        self.x, self.height, self.width = x, height, width

    def update(self, dt, speed):
        self.x -= speed * 0.55 * dt

    def draw(self, surf, shake, color):
        x = self.x + shake[0] * 0.5
        points = [(x, GROUND_Y)]
        steps = 10
        for i in range(steps + 1):
            t = i / steps
            px = x + t * self.width
            py = GROUND_Y - math.sin(t * math.pi) * self.height
            points.append((px, py))
        points.append((x + self.width, GROUND_Y))
        pygame.draw.polygon(surf, color, points)


class Star:
    def __init__(self):
        self.x = random.uniform(0, WIDTH)
        self.y = random.uniform(10, GROUND_Y - 120)
        self.phase = random.uniform(0, math.tau)
        self.size = random.choice([1, 1, 2])

    def draw(self, surf, t, alpha_mult):
        twinkle = (math.sin(t * 3 + self.phase) + 1) / 2
        alpha = int((90 + twinkle * 165) * alpha_mult)
        if alpha <= 0:
            return
        s = pygame.Surface((self.size * 2 + 2, self.size * 2 + 2), pygame.SRCALPHA)
        pygame.draw.circle(s, (255, 255, 255, alpha), (self.size + 1, self.size + 1), self.size)
        surf.blit(s, (self.x, self.y))


class Game:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("Dino Run")
        self.clock = pygame.time.Clock()
        self.sounds = SoundBank()
        self.highscore = HighScore()

        font_path = pygame.font.match_font("consolas,couriernew,monospace") or None
        self.font_big = pygame.font.Font(font_path, 46)
        self.font_med = pygame.font.Font(font_path, 24)
        self.font_small = pygame.font.Font(font_path, 18)

        self.particles = ParticleSystem()
        self.stars = [Star() for _ in range(60)]
        self.clouds = [Cloud(random.uniform(0, WIDTH), random.uniform(20, 120), random.uniform(0.7, 1.3))
                       for _ in range(4)]
        self.hills = [Hill(i * 260, random.uniform(30, 60), 260) for i in range(-1, 5)]

        self.next_cloud_timer = 0
        self.shake_timer = 0.0
        self.shake_mag = 0.0
        self.time_elapsed = 0.0

        self.new_game()
        self.state = STATE_START

    def new_game(self):
        self.dino = Dino(self.sounds)
        self.obstacles = []
        self.speed = START_SPEED
        self.score = 0.0
        self.spawn_timer = 1.2
        self.play_time = 0.0
        self.milestone = 0
        self.beat_highscore = False
        self.shake_timer = 0.0

    def spawn_obstacle(self):
        min_gap = lerp(260, 380, clamp(self.speed / MAX_SPEED, 0, 1))
        gap = random.uniform(min_gap, min_gap + 220)
        self.spawn_timer = gap / self.speed
        x = WIDTH + 40
        if self.play_time > 8 and random.random() < 0.32:
            self.obstacles.append(Bird(x))
        else:
            self.obstacles.append(Cactus(x, self.speed))

    def trigger_shake(self, mag, dur):
        self.shake_mag = mag
        self.shake_timer = dur

    def handle_input_down(self, key):
        if key in (pygame.K_ESCAPE,):
            pygame.quit()
            sys.exit(0)

        if self.state == STATE_START:
            if key in (pygame.K_SPACE, pygame.K_UP):
                self.state = STATE_PLAYING
                self.dino.jump()
        elif self.state == STATE_PLAYING:
            if key in (pygame.K_SPACE, pygame.K_UP):
                self.dino.jump()
            elif key == pygame.K_DOWN:
                self.dino.set_duck(True, self.particles)
            elif key == pygame.K_p:
                self.state = STATE_PAUSED
        elif self.state == STATE_PAUSED:
            if key == pygame.K_p:
                self.state = STATE_PLAYING
        elif self.state == STATE_GAMEOVER:
            if key in (pygame.K_SPACE, pygame.K_UP):
                self.new_game()
                self.state = STATE_PLAYING
                self.dino.jump()

    def handle_input_up(self, key):
        if key in (pygame.K_SPACE, pygame.K_UP):
            self.dino.cut_jump()
        elif key == pygame.K_DOWN:
            self.dino.set_duck(False, self.particles)

    def update(self, dt):
        self.time_elapsed += dt
        for star in self.stars:
            pass

        if self.shake_timer > 0:
            self.shake_timer -= dt

        if self.state != STATE_PLAYING:
            for c in self.clouds:
                c.update(dt, 60)
            return

        self.play_time += dt
        self.speed = min(MAX_SPEED, self.speed + SPEED_ACCEL * dt)
        self.score += self.speed * dt * 0.045

        self.dino.update(dt, self.speed, self.particles)

        self.spawn_timer -= dt
        if self.spawn_timer <= 0:
            self.spawn_obstacle()

        dino_rect = self.dino.rect()
        for ob in self.obstacles:
            ob.update(dt, self.speed)
            if ob.rect().colliderect(dino_rect):
                self.crash()
                break
        self.obstacles = [o for o in self.obstacles if not o.offscreen()]

        for c in self.clouds:
            c.update(dt, self.speed)
        if any(c.x < -100 for c in self.clouds):
            self.clouds = [c for c in self.clouds if c.x > -100]
            self.clouds.append(Cloud(WIDTH + random.uniform(0, 100), random.uniform(20, 120),
                                      random.uniform(0.7, 1.3)))

        for h in self.hills:
            h.update(dt, self.speed)
        if any(h.x + h.width < 0 for h in self.hills):
            self.hills = [h for h in self.hills if h.x + h.width > 0]
            max_x = max((h.x for h in self.hills), default=0)
            self.hills.append(Hill(max_x + 260, random.uniform(30, 60), 260))

        new_milestone = int(self.score) // 100
        if new_milestone > self.milestone:
            self.milestone = new_milestone
            self.sounds.play("point")

        if int(self.score) > self.highscore.value and not self.beat_highscore:
            self.beat_highscore = True

        self.particles.update(dt)

    def crash(self):
        self.state = STATE_GAMEOVER
        self.sounds.play("hit")
        self.trigger_shake(10, 0.35)
        cx = DINO_X + self.dino.width // 2
        cy = int(self.dino.y + self.dino.height // 2)
        self.particles.burst(cx, cy, (200, 90, 70))
        if int(self.score) > self.highscore.value:
            self.highscore.value = int(self.score)
            self.highscore.save()

    def sky_brightness(self):
        cycle = 50.0
        t = (self.time_elapsed % cycle) / cycle
        return (math.sin(t * math.tau - math.pi / 2) + 1) / 2

    def get_shake_offset(self):
        if self.shake_timer > 0:
            f = self.shake_timer / 0.35
            return (random.uniform(-1, 1) * self.shake_mag * f, random.uniform(-1, 1) * self.shake_mag * f)
        return (0, 0)

    def draw_background(self, brightness, shake):
        top = lerp_color(Palette.NIGHT_SKY_TOP, Palette.DAY_SKY_TOP, brightness)
        bottom = lerp_color(Palette.NIGHT_SKY_BOTTOM, Palette.DAY_SKY_BOTTOM, brightness)
        for i in range(HEIGHT):
            t = i / HEIGHT
            color = lerp_color(top, bottom, t)
            pygame.draw.line(self.screen, color, (0, i), (WIDTH, i))

        dark_mode = brightness < 0.5
        for star in self.stars:
            star.draw(self.screen, self.time_elapsed, clamp(1 - brightness * 2, 0, 1))

        cycle = 50.0
        tt = (self.time_elapsed % cycle) / cycle
        body_x = tt * (WIDTH + 100) - 50
        body_y = 60 + math.sin(tt * math.pi) * -40 + 60
        if brightness > 0.5:
            glow = pygame.Surface((140, 140), pygame.SRCALPHA)
            pygame.draw.circle(glow, (255, 235, 150, 60), (70, 70), 70)
            self.screen.blit(glow, (body_x - 70 + shake[0] * 0.2, body_y - 70 + shake[1] * 0.2))
            pygame.draw.circle(self.screen, (255, 246, 190), (int(body_x), int(body_y)), 26)
        else:
            pygame.draw.circle(self.screen, (230, 230, 245), (int(body_x), int(body_y)), 22)
            pygame.draw.circle(self.screen, lerp_color(Palette.NIGHT_SKY_TOP, Palette.NIGHT_SKY_BOTTOM, 0.5),
                                (int(body_x + 9), int(body_y - 5)), 20)

        hill_color = lerp_color(Palette.NIGHT_HILL, Palette.DAY_HILL, brightness)
        for h in self.hills:
            h.draw(self.screen, shake, hill_color)

        cloud_color = lerp_color(Palette.NIGHT_CLOUD, Palette.DAY_CLOUD, brightness)
        for c in self.clouds:
            c.draw(self.screen, shake, cloud_color)

        return dark_mode

    def draw_ground(self, brightness, shake):
        ground_color = lerp_color(Palette.NIGHT_GROUND, Palette.DAY_GROUND, brightness)
        pygame.draw.rect(self.screen, ground_color, (0, GROUND_Y + shake[1], WIDTH, HEIGHT - GROUND_Y))
        line_color = lerp_color((10, 10, 20), (60, 40, 25), brightness)
        pygame.draw.line(self.screen, line_color, (0, GROUND_Y + shake[1]), (WIDTH, GROUND_Y + shake[1]), 3)

        offset = int(self.time_elapsed * self.speed) % 40 if self.state == STATE_PLAYING else 0
        for i in range(-1, WIDTH // 40 + 2):
            x = i * 40 - offset + shake[0]
            pygame.draw.line(self.screen, line_color, (x, GROUND_Y + 10 + shake[1]), (x + 18, GROUND_Y + 10 + shake[1]), 2)

    def draw_hud(self, brightness):
        ui_color = lerp_color(Palette.NIGHT_UI, Palette.DAY_UI, brightness)
        score_text = f"{int(self.score):05d}"
        hi_text = f"HI {int(self.highscore.value):05d}"
        surf1 = self.font_med.render(hi_text, True, ui_color)
        surf2 = self.font_med.render(score_text, True, ui_color)
        self.screen.blit(surf1, (WIDTH - surf2.get_width() - surf1.get_width() - 40, 16))
        self.screen.blit(surf2, (WIDTH - surf2.get_width() - 16, 16))

    def draw_center_text(self, lines, y_start, colors=None):
        for i, line in enumerate(lines):
            font = self.font_big if i == 0 else self.font_med
            color = (colors[i] if colors else (30, 30, 30))
            surf = font.render(line, True, color)
            self.screen.blit(surf, (WIDTH // 2 - surf.get_width() // 2, y_start + i * 40))

    def draw(self):
        brightness = self.sky_brightness()
        shake = self.get_shake_offset()
        dark_mode = self.draw_background(brightness, shake)
        self.draw_ground(brightness, shake)

        for ob in self.obstacles:
            ob.draw(self.screen, shake, dark_mode)

        self.dino.draw(self.screen, shake, brightness > 0.5)
        self.particles.draw(self.screen, shake)
        self.draw_hud(brightness)

        ui_color = lerp_color(Palette.NIGHT_UI, Palette.DAY_UI, brightness)

        if self.state == STATE_START:
            self.draw_center_text(["DINO RUN", "Press SPACE or ^ to start",
                                    "v duck    ESC quit    P pause"], 70,
                                   [ui_color, ui_color, ui_color])
        elif self.state == STATE_PAUSED:
            overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 90))
            self.screen.blit(overlay, (0, 0))
            self.draw_center_text(["PAUSED", "Press P to resume"], 110, [(255, 255, 255), (230, 230, 230)])
        elif self.state == STATE_GAMEOVER:
            lines = ["GAME OVER", f"Score {int(self.score):05d}   Best {int(self.highscore.value):05d}",
                     "Press SPACE to restart"]
            colors = [ui_color, ui_color, ui_color]
            if self.beat_highscore:
                lines.insert(1, "NEW HIGH SCORE!")
                colors.insert(1, (230, 170, 30))
                if random.random() < 0.3:
                    self.particles.confetti(WIDTH // 2, 60)
            self.draw_center_text(lines, 60, colors)

        pygame.display.flip()

    def run(self):
        running = True
        while running:
            dt = self.clock.tick(FPS) / 1000.0
            dt = min(dt, 0.05)
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    self.handle_input_down(event.key)
                elif event.type == pygame.KEYUP:
                    self.handle_input_up(event.key)

            self.update(dt)
            self.draw()

        self.highscore.save()
        pygame.quit()


def main():
    Game().run()


if __name__ == "__main__":
    main()
