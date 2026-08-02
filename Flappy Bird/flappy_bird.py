"""Flappy Bird — pygame edition."""

import math
import random
import sys
from pathlib import Path

import pygame

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
WIDTH, HEIGHT = 480, 720
FPS = 60
GROUND_HEIGHT = 120

GRAVITY = 1500.0          # px/s^2
FLAP_VELOCITY = -430.0    # px/s
MAX_FALL_SPEED = 700.0

PIPE_SPEED = 180.0        # px/s
PIPE_GAP = 190
PIPE_WIDTH = 78
PIPE_SPACING = 260

BIRD_X = WIDTH * 0.3
BIRD_RADIUS = 18

HIGH_SCORE_FILE = Path(__file__).with_name("highscore.txt")

# Palette
SKY_TOP = (78, 192, 233)
SKY_BOTTOM = (178, 232, 244)
GROUND_TOP = (222, 216, 149)
GROUND_BOTTOM = (150, 105, 55)
PIPE_GREEN = (86, 189, 86)
PIPE_GREEN_DARK = (58, 145, 58)
PIPE_GREEN_LIGHT = (140, 224, 130)
WHITE = (255, 255, 255)
BLACK = (20, 20, 20)
GOLD = (255, 205, 60)


def clamp(v, lo, hi):
    return max(lo, min(hi, v))


def lerp_color(c1, c2, t):
    return tuple(int(a + (b - a) * t) for a, b in zip(c1, c2))


# ---------------------------------------------------------------------------
# Background: parallax clouds & hills
# ---------------------------------------------------------------------------
class Cloud:
    def __init__(self, x, y, scale, speed):
        self.x = x
        self.y = y
        self.scale = scale
        self.speed = speed

    def update(self, dt):
        self.x -= self.speed * dt
        if self.x < -120 * self.scale:
            self.x = WIDTH + random.randint(20, 100)
            self.y = random.randint(40, 220)

    def draw(self, surf):
        s = self.scale
        cx, cy = int(self.x), int(self.y)
        color = (255, 255, 255, 235)
        cloud_surf = pygame.Surface((160 * s, 70 * s), pygame.SRCALPHA)
        for dx, dy, r in [(30, 35, 26), (60, 20, 32), (95, 32, 26), (60, 45, 30)]:
            pygame.draw.circle(cloud_surf, color, (int(dx * s), int(dy * s)), int(r * s))
        surf.blit(cloud_surf, (cx, cy))


class Hill:
    def __init__(self, base_y, amp, freq, speed, color, phase=0.0):
        self.base_y = base_y
        self.amp = amp
        self.freq = freq
        self.speed = speed
        self.color = color
        self.offset = phase

    def update(self, dt):
        self.offset += self.speed * dt

    def draw(self, surf):
        points = [(0, HEIGHT - GROUND_HEIGHT + 40)]
        for x in range(0, WIDTH + 20, 20):
            y = self.base_y + math.sin((x + self.offset) * self.freq) * self.amp
            points.append((x, y))
        points.append((WIDTH, HEIGHT - GROUND_HEIGHT + 40))
        pygame.draw.polygon(surf, self.color, points)


# ---------------------------------------------------------------------------
# Particles
# ---------------------------------------------------------------------------
class Particle:
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
        self.vy += 500 * dt
        self.life -= dt
        return self.life > 0

    def draw(self, surf):
        t = clamp(self.life / self.max_life, 0, 1)
        r = max(1, int(self.radius * t))
        alpha = int(255 * t)
        s = pygame.Surface((r * 2 + 2, r * 2 + 2), pygame.SRCALPHA)
        pygame.draw.circle(s, (*self.color, alpha), (r + 1, r + 1), r)
        surf.blit(s, (self.x - r, self.y - r))


# ---------------------------------------------------------------------------
# Bird
# ---------------------------------------------------------------------------
class Bird:
    def __init__(self):
        self.reset()

    def reset(self):
        self.x = BIRD_X
        self.y = HEIGHT / 2
        self.vy = 0.0
        self.angle = 0.0
        self.flap_timer = 0.0
        self.wing_phase = 0.0
        self.alive = True

    def flap(self):
        self.vy = FLAP_VELOCITY
        self.flap_timer = 0.15

    def update(self, dt, particles):
        self.vy = clamp(self.vy + GRAVITY * dt, -1e9, MAX_FALL_SPEED)
        self.y += self.vy * dt

        target_angle = clamp(-self.vy * 0.07, -30, 90)
        self.angle += (target_angle - self.angle) * clamp(dt * 10, 0, 1)

        self.wing_phase += dt * (16 if self.flap_timer > 0 else 7)
        self.flap_timer = max(0.0, self.flap_timer - dt)

        if random.random() < 0.5:
            particles.append(Particle(
                self.x - BIRD_RADIUS * 0.8, self.y,
                -random.uniform(20, 60), random.uniform(-20, 20),
                0.4, (255, 255, 255), 4))

    def rect(self):
        return pygame.Rect(self.x - BIRD_RADIUS, self.y - BIRD_RADIUS,
                            BIRD_RADIUS * 2, BIRD_RADIUS * 2)

    def draw(self, surf):
        bx, by = int(self.x), int(self.y)
        bird_surf = pygame.Surface((70, 70), pygame.SRCALPHA)
        cx, cy = 35, 35

        wing_offset = math.sin(self.wing_phase) * 10
        wing_pts = [
            (cx - 6, cy + 2),
            (cx - 22, cy + 6 + wing_offset),
            (cx - 8, cy + 14),
        ]
        pygame.draw.polygon(bird_surf, (220, 160, 30), wing_pts)

        pygame.draw.circle(bird_surf, GOLD, (cx, cy), BIRD_RADIUS)
        pygame.draw.circle(bird_surf, (255, 230, 140), (cx - 4, cy - 6), BIRD_RADIUS - 8)

        pygame.draw.circle(bird_surf, WHITE, (cx + 8, cy - 6), 7)
        pygame.draw.circle(bird_surf, BLACK, (cx + 10, cy - 6), 3)

        beak_pts = [(cx + 15, cy - 2), (cx + 30, cy + 2), (cx + 15, cy + 7)]
        pygame.draw.polygon(bird_surf, (255, 140, 30), beak_pts)
        pygame.draw.polygon(bird_surf, (220, 100, 20), beak_pts, 1)

        pygame.draw.polygon(bird_surf, (220, 160, 30), wing_pts, 0)
        pygame.draw.line(bird_surf, (190, 130, 20),
                          (cx - 6, cy + 2), (cx - 20, cy + 4 + wing_offset), 2)

        rotated = pygame.transform.rotate(bird_surf, -self.angle)
        rect = rotated.get_rect(center=(bx, by))
        surf.blit(rotated, rect)


# ---------------------------------------------------------------------------
# Pipes
# ---------------------------------------------------------------------------
class PipePair:
    def __init__(self, x):
        self.x = x
        margin = 90
        self.gap_y = random.randint(margin + PIPE_GAP // 2,
                                     HEIGHT - GROUND_HEIGHT - margin - PIPE_GAP // 2)
        self.scored = False
        self.passed_glow = 0.0

    @property
    def top_height(self):
        return self.gap_y - PIPE_GAP // 2

    @property
    def bottom_y(self):
        return self.gap_y + PIPE_GAP // 2

    def update(self, dt):
        self.x -= PIPE_SPEED * dt

    def off_screen(self):
        return self.x < -PIPE_WIDTH

    def rects(self):
        top = pygame.Rect(self.x, 0, PIPE_WIDTH, self.top_height)
        bottom = pygame.Rect(self.x, self.bottom_y, PIPE_WIDTH,
                              HEIGHT - GROUND_HEIGHT - self.bottom_y)
        return top, bottom

    def _draw_pipe(self, surf, x, y, w, h, flipped):
        if h <= 0:
            return
        body = pygame.Rect(x, y, w, h)
        pygame.draw.rect(surf, PIPE_GREEN, body)
        pygame.draw.rect(surf, PIPE_GREEN_LIGHT, (x + 4, y, 10, h))
        pygame.draw.rect(surf, PIPE_GREEN_DARK, (x + w - 10, y, 10, h))
        pygame.draw.rect(surf, PIPE_GREEN_DARK, body, 2)

        cap_h = 30
        cap_y = y + h - cap_h if flipped else y
        cap = pygame.Rect(x - 6, cap_y, w + 12, cap_h)
        pygame.draw.rect(surf, PIPE_GREEN, cap)
        pygame.draw.rect(surf, PIPE_GREEN_LIGHT, (x - 6 + 4, cap_y, 10, cap_h))
        pygame.draw.rect(surf, PIPE_GREEN_DARK, (x - 6 + w + 12 - 14, cap_y, 10, cap_h))
        pygame.draw.rect(surf, PIPE_GREEN_DARK, cap, 2)

    def draw(self, surf):
        self._draw_pipe(surf, self.x, 0, PIPE_WIDTH, self.top_height, flipped=True)
        self._draw_pipe(surf, self.x, self.bottom_y, PIPE_WIDTH,
                         HEIGHT - GROUND_HEIGHT - self.bottom_y, flipped=False)


# ---------------------------------------------------------------------------
# Game
# ---------------------------------------------------------------------------
class Game:
    STATE_MENU = "menu"
    STATE_PLAY = "play"
    STATE_DEAD = "dead"

    def __init__(self):
        pygame.init()
        pygame.display.set_caption("Flappy Bird")
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        self.clock = pygame.time.Clock()

        self.font_big = pygame.font.SysFont("arialblack,arial", 54)
        self.font_med = pygame.font.SysFont("arialblack,arial", 30)
        self.font_small = pygame.font.SysFont("arial", 20)

        self.high_score = self._load_high_score()
        self.ground_scroll = 0.0
        self.flash = 0.0
        self.shake = 0.0
        self.bg_pulse = 0.0

        self.clouds = [Cloud(random.randint(0, WIDTH), random.randint(30, 200),
                              random.uniform(0.7, 1.4), random.uniform(8, 20))
                        for _ in range(5)]
        self.hills_far = Hill(HEIGHT - GROUND_HEIGHT - 10, 10, 0.02, 12,
                               (120, 200, 150))
        self.hills_near = Hill(HEIGHT - GROUND_HEIGHT + 20, 16, 0.015, 25,
                                (90, 175, 120))

        self.reset()

    def _load_high_score(self):
        try:
            return int(HIGH_SCORE_FILE.read_text().strip())
        except Exception:
            return 0

    def _save_high_score(self):
        try:
            HIGH_SCORE_FILE.write_text(str(self.high_score))
        except Exception:
            pass

    def reset(self):
        self.bird = Bird()
        self.pipes = [PipePair(WIDTH + 200 + i * PIPE_SPACING) for i in range(3)]
        self.particles = []
        self.score = 0
        self.state = Game.STATE_MENU
        self.death_timer = 0.0
        self.flap_bounce = 0.0

    # ------------------------------------------------------------------
    def spawn_burst(self, x, y, color, n=18, speed=220):
        for _ in range(n):
            ang = random.uniform(0, math.tau)
            spd = random.uniform(speed * 0.3, speed)
            self.particles.append(Particle(
                x, y, math.cos(ang) * spd, math.sin(ang) * spd,
                random.uniform(0.4, 0.9), color, random.randint(3, 6)))

    def handle_flap(self):
        if self.state == Game.STATE_MENU:
            self.state = Game.STATE_PLAY
            self.bird.flap()
        elif self.state == Game.STATE_PLAY:
            self.bird.flap()
            self.flap_bounce = 1.0
        elif self.state == Game.STATE_DEAD:
            if self.death_timer > 0.4:
                self.reset()

    def update(self, dt):
        self.ground_scroll -= PIPE_SPEED * dt
        self.ground_scroll %= 48
        self.bg_pulse += dt

        for c in self.clouds:
            c.update(dt * (0.4 if self.state != Game.STATE_PLAY else 1.0))
        self.hills_far.update(dt if self.state == Game.STATE_PLAY else dt * 0.3)
        self.hills_near.update(dt if self.state == Game.STATE_PLAY else dt * 0.3)

        self.particles = [p for p in self.particles if p.update(dt)]
        self.flash = max(0.0, self.flash - dt * 3)
        self.shake = max(0.0, self.shake - dt * 6)
        self.flap_bounce = max(0.0, self.flap_bounce - dt * 4)

        if self.state == Game.STATE_MENU:
            self.bird.y = HEIGHT / 2 + math.sin(self.bg_pulse * 2.5) * 12
            self.bird.angle = math.sin(self.bg_pulse * 2.5) * 8
            self.bird.wing_phase += dt * 7
            return

        if self.state == Game.STATE_DEAD:
            self.death_timer += dt
            if self.bird.y < HEIGHT - GROUND_HEIGHT - BIRD_RADIUS:
                self.bird.update(dt, [])
            else:
                self.bird.y = HEIGHT - GROUND_HEIGHT - BIRD_RADIUS
                self.bird.vy = 0
                self.bird.angle = 90
            return

        # STATE_PLAY
        self.bird.update(dt, self.particles)

        for pipe in self.pipes:
            pipe.update(dt)
        if self.pipes and self.pipes[0].off_screen():
            self.pipes.pop(0)
            self.pipes.append(PipePair(self.pipes[-1].x + PIPE_SPACING))

        bird_rect = self.bird.rect()
        for pipe in self.pipes:
            if not pipe.scored and pipe.x + PIPE_WIDTH < self.bird.x:
                pipe.scored = True
                self.score += 1
                self.spawn_burst(self.bird.x, self.bird.y, GOLD, n=14, speed=140)
            top, bottom = pipe.rects()
            if bird_rect.colliderect(top) or bird_rect.colliderect(bottom):
                self._die()

        if self.bird.y - BIRD_RADIUS < 0:
            self.bird.y = BIRD_RADIUS
            self.bird.vy = 0
        if self.bird.y + BIRD_RADIUS > HEIGHT - GROUND_HEIGHT:
            self._die()

    def _die(self):
        if self.state != Game.STATE_PLAY:
            return
        self.state = Game.STATE_DEAD
        self.death_timer = 0.0
        self.flash = 1.0
        self.shake = 1.0
        self.spawn_burst(self.bird.x, self.bird.y, (255, 90, 90), n=26, speed=260)
        if self.score > self.high_score:
            self.high_score = self.score
            self._save_high_score()

    # ------------------------------------------------------------------
    def draw_background(self, surf):
        for y in range(HEIGHT):
            t = y / HEIGHT
            color = lerp_color(SKY_TOP, SKY_BOTTOM, t)
            pygame.draw.line(surf, color, (0, y), (WIDTH, y))

        for c in self.clouds:
            c.draw(surf)

        self.hills_far.draw(surf)
        self.hills_near.draw(surf)

    def draw_ground(self, surf):
        rect = pygame.Rect(0, HEIGHT - GROUND_HEIGHT, WIDTH, GROUND_HEIGHT)
        for y in range(rect.top, rect.bottom):
            t = (y - rect.top) / GROUND_HEIGHT
            pygame.draw.line(surf, lerp_color(GROUND_TOP, GROUND_BOTTOM, t),
                              (0, y), (WIDTH, y))
        pygame.draw.rect(surf, (90, 60, 30), (0, HEIGHT - GROUND_HEIGHT, WIDTH, 6))

        stripe_w = 24
        x = -int(self.ground_scroll)
        while x < WIDTH:
            pygame.draw.polygon(surf, (110, 80, 40), [
                (x, HEIGHT - GROUND_HEIGHT + 6),
                (x + stripe_w / 2, HEIGHT - GROUND_HEIGHT + 16),
                (x + stripe_w, HEIGHT - GROUND_HEIGHT + 6),
            ])
            x += stripe_w

    def draw_score(self, surf, value, y, big=True):
        font = self.font_big if big else self.font_med
        text = font.render(str(value), True, WHITE)
        outline = font.render(str(value), True, BLACK)
        x = WIDTH / 2 - text.get_width() / 2
        for ox, oy in [(-3, 0), (3, 0), (0, -3), (0, 3), (-2, -2), (2, 2), (-2, 2), (2, -2)]:
            surf.blit(outline, (x + ox, y + oy))
        surf.blit(text, (x, y))

    def draw_panel(self, surf, cx, cy, w, h, title, lines):
        panel = pygame.Rect(0, 0, w, h)
        panel.center = (cx, cy)
        shadow = panel.copy()
        shadow.move_ip(0, 8)
        s = pygame.Surface((w, h), pygame.SRCALPHA)
        pygame.draw.rect(s, (0, 0, 0, 90), s.get_rect(), border_radius=18)
        surf.blit(s, shadow)

        pygame.draw.rect(surf, (250, 230, 170), panel, border_radius=18)
        pygame.draw.rect(surf, (200, 150, 70), panel, 5, border_radius=18)

        t = self.font_med.render(title, True, (120, 70, 20))
        surf.blit(t, (cx - t.get_width() / 2, panel.top + 18))

        for i, (label, value) in enumerate(lines):
            ly = panel.top + 70 + i * 34
            lab = self.font_small.render(label, True, (110, 80, 40))
            val = self.font_small.render(str(value), True, (60, 40, 10))
            surf.blit(lab, (panel.left + 24, ly))
            surf.blit(val, (panel.right - 24 - val.get_width(), ly))

    def draw(self):
        surf = self.screen
        offset = (0, 0)
        if self.shake > 0:
            offset = (random.uniform(-1, 1) * self.shake * 8,
                      random.uniform(-1, 1) * self.shake * 8)

        world = pygame.Surface((WIDTH, HEIGHT))
        self.draw_background(world)

        if self.state != Game.STATE_MENU:
            for pipe in self.pipes:
                pipe.draw(world)

        for p in self.particles:
            p.draw(world)

        self.draw_ground(world)

        scale = 1.0 + self.flap_bounce * 0.08
        if abs(scale - 1.0) > 0.001 and self.state == Game.STATE_PLAY:
            bx, by = self.bird.x, self.bird.y
            bird_layer = pygame.Surface((100, 100), pygame.SRCALPHA)
            temp_bird = self.bird
            saved_x, saved_y = temp_bird.x, temp_bird.y
            temp_bird.x, temp_bird.y = 50, 50
            temp_bird.draw(bird_layer)
            temp_bird.x, temp_bird.y = saved_x, saved_y
            scaled = pygame.transform.rotozoom(bird_layer, 0, scale)
            rect = scaled.get_rect(center=(bx, by))
            world.blit(scaled, rect)
        else:
            self.bird.draw(world)

        if self.state == Game.STATE_MENU:
            title = self.font_big.render("Flappy Bird", True, WHITE)
            title_o = self.font_big.render("Flappy Bird", True, (255, 140, 20))
            tx = WIDTH / 2 - title.get_width() / 2
            ty = 140 + math.sin(self.bg_pulse * 2) * 4
            world.blit(title_o, (tx + 3, ty + 3))
            world.blit(title, (tx, ty))

            hint_alpha = int(180 + 75 * math.sin(self.bg_pulse * 4))
            hint = self.font_small.render("Click / Space / Up to flap", True, WHITE)
            hs = pygame.Surface(hint.get_size(), pygame.SRCALPHA)
            hs.blit(hint, (0, 0))
            hs.set_alpha(hint_alpha)
            world.blit(hs, (WIDTH / 2 - hint.get_width() / 2, HEIGHT / 2 + 110))

            self.draw_panel(world, WIDTH / 2, HEIGHT - GROUND_HEIGHT - 90, 220, 70,
                             "Best", [("Score", self.high_score)])

        elif self.state == Game.STATE_PLAY:
            self.draw_score(world, self.score, 40)

        elif self.state == Game.STATE_DEAD:
            self.draw_score(world, self.score, 40)
            if self.death_timer > 0.3:
                new_best = self.score >= self.high_score and self.score > 0
                self.draw_panel(world, WIDTH / 2, HEIGHT / 2 - 40, 280, 170,
                                 "Game Over",
                                 [("Score", self.score), ("Best", self.high_score)])
                if new_best:
                    pop = 1 + 0.15 * math.sin(self.bg_pulse * 8)
                    badge = self.font_small.render("NEW BEST!", True, (255, 140, 0))
                    badge = pygame.transform.rotozoom(badge, 0, pop)
                    world.blit(badge, (WIDTH / 2 - badge.get_width() / 2, HEIGHT / 2 - 40 + 68))
                hint = self.font_small.render("Click / Space to retry", True, (255, 255, 255))
                world.blit(hint, (WIDTH / 2 - hint.get_width() / 2, HEIGHT / 2 + 130))

        if self.flash > 0:
            fs = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            fs.fill((255, 255, 255, int(self.flash * 160)))
            world.blit(fs, (0, 0))

        surf.fill((0, 0, 0))
        surf.blit(world, offset)
        pygame.display.flip()

    # ------------------------------------------------------------------
    def run(self):
        while True:
            dt = self.clock.tick(FPS) / 1000.0
            dt = min(dt, 1 / 30)

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                if event.type == pygame.KEYDOWN:
                    if event.key in (pygame.K_SPACE, pygame.K_UP, pygame.K_w):
                        self.handle_flap()
                    if event.key == pygame.K_ESCAPE:
                        pygame.quit()
                        sys.exit()
                if event.type == pygame.MOUSEBUTTONDOWN:
                    self.handle_flap()

            self.update(dt)
            self.draw()


if __name__ == "__main__":
    Game().run()
