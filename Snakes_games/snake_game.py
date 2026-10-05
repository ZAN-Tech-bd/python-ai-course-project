"""
Snake Game — pygame edition
Arrow keys / WASD to move, P to pause, Enter to start/restart, Esc to quit.
"""

import pygame
import random
import sys
import os
import math

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
CELL = 24
COLS, ROWS = 30, 22
GRID_W, GRID_H = COLS * CELL, ROWS * CELL
HUD_H = 70
WIDTH, HEIGHT = GRID_W, GRID_H + HUD_H

FPS = 60
BASE_SPEED = 8.0          # moves per second at score 0
SPEED_GAIN = 0.18         # extra moves/sec per food eaten
MAX_SPEED = 20.0

HIGHSCORE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "highscore.txt")

# Palette
BG_TOP = (14, 18, 34)
BG_BOTTOM = (28, 16, 46)
GRID_LINE = (255, 255, 255, 10)
PANEL = (18, 22, 40, 210)
TEXT_MAIN = (240, 240, 250)
TEXT_DIM = (150, 155, 180)
ACCENT = (96, 230, 170)
ACCENT2 = (255, 140, 90)
DANGER = (255, 90, 110)

SNAKE_HEAD = (120, 245, 190)
SNAKE_BODY_A = (60, 200, 150)
SNAKE_BODY_B = (35, 150, 120)
FOOD_CORE = (255, 120, 90)
FOOD_GLOW = (255, 170, 90)


def lerp(a, b, t):
    return a + (b - a) * t


def lerp_color(c1, c2, t):
    return tuple(int(lerp(c1[i], c2[i], t)) for i in range(3))


# ---------------------------------------------------------------------------
# Background
# ---------------------------------------------------------------------------
def make_background():
    surf = pygame.Surface((WIDTH, HEIGHT))
    for y in range(HEIGHT):
        t = y / HEIGHT
        surf.fill(lerp_color(BG_TOP, BG_BOTTOM, t), rect=(0, y, WIDTH, 1))
    return surf


def draw_grid(surf, offset_y):
    grid_surf = pygame.Surface((GRID_W, GRID_H), pygame.SRCALPHA)
    for x in range(0, GRID_W + 1, CELL):
        pygame.draw.line(grid_surf, GRID_LINE, (x, 0), (x, GRID_H))
    for y in range(0, GRID_H + 1, CELL):
        pygame.draw.line(grid_surf, GRID_LINE, (0, y), (GRID_W, y))
    surf.blit(grid_surf, (0, offset_y))


# ---------------------------------------------------------------------------
# Game objects
# ---------------------------------------------------------------------------
class Snake:
    def __init__(self):
        cx, cy = COLS // 2, ROWS // 2
        self.body = [(cx - 1, cy), (cx - 2, cy), (cx - 3, cy)]
        self.direction = (1, 0)
        self.pending_dir = (1, 0)
        self.grow_pending = 0

    def head(self):
        return self.body[0]

    def set_direction(self, d):
        # prevent reversing directly into itself
        if (d[0] * -1, d[1] * -1) == self.direction:
            return
        self.pending_dir = d

    def step(self):
        self.direction = self.pending_dir
        hx, hy = self.head()
        dx, dy = self.direction
        new_head = (hx + dx, hy + dy)
        self.body.insert(0, new_head)
        if self.grow_pending > 0:
            self.grow_pending -= 1
        else:
            self.body.pop()

    def grow(self, n=1):
        self.grow_pending += n

    def collides_wall(self):
        x, y = self.head()
        return x < 0 or x >= COLS or y < 0 or y >= ROWS

    def collides_self(self):
        return self.head() in self.body[1:]


def random_food_pos(snake_body):
    while True:
        pos = (random.randrange(COLS), random.randrange(ROWS))
        if pos not in snake_body:
            return pos


# ---------------------------------------------------------------------------
# Drawing helpers
# ---------------------------------------------------------------------------
def cell_rect(cx, cy, offset_y, pad=1):
    return pygame.Rect(cx * CELL + pad, cy * CELL + offset_y + pad, CELL - pad * 2, CELL - pad * 2)


def draw_snake(surf, snake, offset_y):
    n = len(snake.body)
    for i, (cx, cy) in enumerate(reversed(snake.body)):
        idx = n - 1 - i
        t = idx / max(1, n - 1)
        color = lerp_color(SNAKE_BODY_A, SNAKE_BODY_B, t)
        rect = cell_rect(cx, cy, offset_y, pad=2)
        radius = 9
        pygame.draw.rect(surf, color, rect, border_radius=radius)

    # head, drawn on top with eyes
    hx, hy = snake.head()
    rect = cell_rect(hx, hy, offset_y, pad=1)
    pygame.draw.rect(surf, SNAKE_HEAD, rect, border_radius=10)

    dx, dy = snake.direction
    eye_off = CELL * 0.22
    cx_px, cy_px = rect.center
    perp = (-dy, dx)
    for s in (-1, 1):
        ex = cx_px + dx * eye_off + perp[0] * eye_off * s
        ey = cy_px + dy * eye_off + perp[1] * eye_off * s
        pygame.draw.circle(surf, (20, 30, 30), (int(ex), int(ey)), 2)


def draw_food(surf, pos, offset_y, pulse):
    cx = pos[0] * CELL + CELL // 2
    cy = pos[1] * CELL + offset_y + CELL // 2
    glow_r = int(CELL * (0.9 + 0.25 * pulse))
    glow_surf = pygame.Surface((glow_r * 2, glow_r * 2), pygame.SRCALPHA)
    for r in range(glow_r, 0, -2):
        alpha = int(60 * (1 - r / glow_r))
        pygame.draw.circle(glow_surf, (*FOOD_GLOW, alpha), (glow_r, glow_r), r)
    surf.blit(glow_surf, (cx - glow_r, cy - glow_r), special_flags=pygame.BLEND_RGBA_ADD)
    core_r = int(CELL * 0.34)
    pygame.draw.circle(surf, FOOD_CORE, (cx, cy), core_r)
    pygame.draw.circle(surf, (255, 220, 200), (cx - core_r // 3, cy - core_r // 3), max(2, core_r // 3))


def draw_panel(surf, rect, color=PANEL, radius=14):
    panel = pygame.Surface(rect.size, pygame.SRCALPHA)
    pygame.draw.rect(panel, color, panel.get_rect(), border_radius=radius)
    surf.blit(panel, rect.topleft)


def text(surf, s, font, color, center=None, topleft=None):
    img = font.render(s, True, color)
    r = img.get_rect()
    if center:
        r.center = center
    if topleft:
        r.topleft = topleft
    surf.blit(img, r)
    return r


# ---------------------------------------------------------------------------
# High score
# ---------------------------------------------------------------------------
def load_highscore():
    try:
        with open(HIGHSCORE_FILE, "r") as f:
            return int(f.read().strip())
    except Exception:
        return 0


def save_highscore(v):
    try:
        with open(HIGHSCORE_FILE, "w") as f:
            f.write(str(v))
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    pygame.init()
    pygame.display.set_caption("Snake")
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    clock = pygame.time.Clock()

    font_big = pygame.font.SysFont("Segoe UI", 56, bold=True)
    font_mid = pygame.font.SysFont("Segoe UI", 28, bold=True)
    font_small = pygame.font.SysFont("Segoe UI", 20)
    font_score = pygame.font.SysFont("Segoe UI", 26, bold=True)

    background = make_background()
    highscore = load_highscore()

    STATE_START, STATE_PLAY, STATE_PAUSE, STATE_OVER = range(4)
    state = STATE_START

    snake = Snake()
    food = random_food_pos(snake.body)
    score = 0
    move_timer = 0.0
    pulse_t = 0.0
    shake = 0.0

    def reset():
        nonlocal snake, food, score, move_timer
        snake = Snake()
        food = random_food_pos(snake.body)
        score = 0
        move_timer = 0.0

    running = True
    while running:
        dt = clock.tick(FPS) / 1000.0
        pulse_t += dt * 3.0

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key in (pygame.K_UP, pygame.K_w):
                    if state == STATE_PLAY:
                        snake.set_direction((0, -1))
                    elif state in (STATE_START, STATE_OVER):
                        pass
                elif event.key in (pygame.K_DOWN, pygame.K_s):
                    if state == STATE_PLAY:
                        snake.set_direction((0, 1))
                elif event.key in (pygame.K_LEFT, pygame.K_a):
                    if state == STATE_PLAY:
                        snake.set_direction((-1, 0))
                elif event.key in (pygame.K_RIGHT, pygame.K_d):
                    if state == STATE_PLAY:
                        snake.set_direction((1, 0))
                elif event.key == pygame.K_p:
                    if state == STATE_PLAY:
                        state = STATE_PAUSE
                    elif state == STATE_PAUSE:
                        state = STATE_PLAY
                elif event.key == pygame.K_RETURN:
                    if state in (STATE_START, STATE_OVER):
                        reset()
                        state = STATE_PLAY

        if state == STATE_PLAY:
            speed = min(MAX_SPEED, BASE_SPEED + score * SPEED_GAIN)
            move_timer += dt
            step_time = 1.0 / speed
            if move_timer >= step_time:
                move_timer -= step_time
                snake.step()
                if snake.collides_wall() or snake.collides_self():
                    state = STATE_OVER
                    shake = 12.0
                    if score > highscore:
                        highscore = score
                        save_highscore(highscore)
                elif snake.head() == food:
                    snake.grow(1)
                    score += 1
                    food = random_food_pos(snake.body)
                    if score > highscore:
                        highscore = score

        if shake > 0:
            shake = max(0.0, shake - dt * 40)

        # ---------------- draw ----------------
        screen.blit(background, (0, 0))

        offset_y = HUD_H
        ox = random.uniform(-1, 1) * shake
        oy = random.uniform(-1, 1) * shake

        grid_surf = pygame.Surface((GRID_W, GRID_H), pygame.SRCALPHA)
        pygame.draw.rect(grid_surf, (255, 255, 255, 8), grid_surf.get_rect())
        draw_grid(grid_surf, 0)
        draw_food(grid_surf, food, 0, (math.sin(pulse_t) + 1) / 2)
        draw_snake(grid_surf, snake, 0)
        screen.blit(grid_surf, (ox, offset_y + oy))

        # HUD panel
        draw_panel(screen, pygame.Rect(0, 0, WIDTH, HUD_H), color=(15, 18, 34, 235), radius=0)
        text(screen, "SCORE", font_small, TEXT_DIM, topleft=(24, 10))
        text(screen, str(score), font_score, ACCENT, topleft=(24, 30))
        hs_r = text(screen, "BEST", font_small, TEXT_DIM, topleft=(WIDTH - 140, 10))
        text(screen, str(highscore), font_score, ACCENT2, topleft=(WIDTH - 140, 30))
        text(screen, "SNAKE", font_mid, TEXT_MAIN, center=(WIDTH // 2, 34))
        pygame.draw.line(screen, (255, 255, 255, 30), (0, HUD_H), (WIDTH, HUD_H), 2)

        if state == STATE_START:
            overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            overlay.fill((10, 12, 24, 165))
            screen.blit(overlay, (0, 0))
            text(screen, "SNAKE", font_big, ACCENT, center=(WIDTH // 2, HEIGHT // 2 - 70))
            text(screen, "Press ENTER to start", font_mid, TEXT_MAIN, center=(WIDTH // 2, HEIGHT // 2))
            text(screen, "Arrows / WASD to move   •   P to pause   •   Esc to quit",
                 font_small, TEXT_DIM, center=(WIDTH // 2, HEIGHT // 2 + 44))

        elif state == STATE_PAUSE:
            overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            overlay.fill((10, 12, 24, 165))
            screen.blit(overlay, (0, 0))
            text(screen, "PAUSED", font_big, TEXT_MAIN, center=(WIDTH // 2, HEIGHT // 2 - 20))
            text(screen, "Press P to resume", font_mid, TEXT_DIM, center=(WIDTH // 2, HEIGHT // 2 + 30))

        elif state == STATE_OVER:
            overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            overlay.fill((10, 12, 24, 180))
            screen.blit(overlay, (0, 0))
            text(screen, "GAME OVER", font_big, DANGER, center=(WIDTH // 2, HEIGHT // 2 - 80))
            text(screen, f"Score: {score}", font_mid, TEXT_MAIN, center=(WIDTH // 2, HEIGHT // 2 - 26))
            text(screen, f"Best: {highscore}", font_mid, ACCENT2, center=(WIDTH // 2, HEIGHT // 2 + 10))
            text(screen, "Press ENTER to play again", font_small, TEXT_DIM,
                 center=(WIDTH // 2, HEIGHT // 2 + 54))

        pygame.display.flip()

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
