// Food Slice game logic and rendering. Port of FoodSliceGame in main.py.
// The canvas is always 1280x720 internally; CSS scales it to fit the window.

import { Confetti, choice, rainbowTitle, rand, renderPill, rgb, roundRectPath } from "./ui.js";
import { FOODS, bombSprite, foodSprites, heartSprite } from "./sprites.js";

export const W = 1280, H = 720;
const HOVER_SELECT_TIME = 0.8;   // seconds to point at a button before it is pressed
const NO_HAND_HINT_DELAY = 1.5;  // seconds without a hand before showing "Show me your hand!"
const GRAVITY = 1300;            // px/s^2
const SLICE_SPEED = 300;         // slowest fingertip swipe (px/s) that still cuts
const TRAIL_TIME = 0.16;         // seconds of fingertip history drawn as the blade
const FOOD_SIZE = 130;
const LIVES = 3;
const COMBO_WINDOW = 0.35;
const MOUSE_TIMEOUT = 1.5;       // mouse/touch counts as the "finger" for this long after it moves
const MAX_SAMPLE_GAP = 0.35;     // longest gap between two fingertip samples that still forms a cut
const BEST_KEY = "foodslice.best";
const CHEERS = ["Yummy!", "Super!", "Wow!", "Nice cut!", "Awesome!", "Great!"];

const now = () => performance.now() / 1000;

function segPointDistance(ax, ay, bx, by, px, py) {
  const dx = bx - ax, dy = by - ay;
  const lenSq = dx * dx + dy * dy;
  const t = lenSq === 0 ? 0 : Math.max(0, Math.min(1, ((px - ax) * dx + (py - ay) * dy) / lenSq));
  return Math.hypot(ax + t * dx - px, ay + t * dy - py);
}

/** Anything thrown through the air: whole food, a cut half, or a bomb. */
class Flyer {
  constructor(sprite, x, y, vx, vy, spin, kind, foodIndex = -1) {
    Object.assign(this, { sprite, x, y, vx, vy, spin, kind, foodIndex });
    this.angle = rand(0, 360);
    this.radius = sprite.width * 0.42;
  }

  update(dt) {
    this.vy += GRAVITY * dt;
    this.x += this.vx * dt;
    this.y += this.vy * dt;
    this.angle += this.spin * dt;
  }

  draw(ctx) {
    const s = this.sprite.width;
    ctx.save();
    ctx.translate(this.x, this.y);
    ctx.rotate(-this.angle * Math.PI / 180);
    ctx.drawImage(this.sprite, -s / 2, -s / 2);
    ctx.restore();
  }
}

class PillButton {
  constructor(label, fill, action, px) {
    this.img = renderPill(label, px, fill);
    this.w = this.img.width;
    this.h = this.img.height;
    this.action = action;
    this.x = this.y = 0;
  }
  contains(px, py) {
    return px >= this.x && px <= this.x + this.w && py >= this.y && py <= this.y + this.h;
  }
}

export class FoodSliceGame {
  /**
   * @param canvas  the 1280x720 game canvas
   * @param tracker HandTracker, or null to play with mouse/touch only
   * @param onExit  called when the Exit button is chosen
   */
  constructor(canvas, tracker, onExit) {
    this.canvas = canvas;
    this.ctx = canvas.getContext("2d");
    this.tracker = tracker;
    this.onExit = onExit;
    this.confetti = new Confetti();

    this.screenButtons = {
      start: [new PillButton("Play!", [140, 220, 120], "play", 44),
              new PillButton("Exit", [255, 175, 175], "exit", 34)],
      over: [new PillButton("Play again!", [140, 220, 120], "play", 44),
             new PillButton("Exit", [255, 175, 175], "exit", 34)],
      play: [new PillButton("Stop", [255, 205, 210], "stop", 26)],
    };
    this.layoutButtons();

    this.best = this.loadBest();
    this.state = "start";
    this.resetRound();

    this.trail = [];
    this.hoverButton = null;
    this.hoverStart = 0;
    this.hoverSeen = 0;
    this.lastHandTime = now();
    this.lastTime = now();
    this.mouse = null;       // {x, y, t} last mouse/touch position
    this.mouseSamples = [];  // mouse/touch samples since the last frame
    this.lastSample = null;  // last fingertip sample [x, y, t], used to cut along the swipe

    this.bindInput();
  }

  // ---------- setup ----------
  layoutButtons() {
    for (const state of ["start", "over"]) {
      const row = this.screenButtons[state];
      const gap = 30;
      const total = row.reduce((s, b) => s + b.w, 0) + gap * (row.length - 1);
      let x = Math.floor((W - total) / 2);
      const y = Math.floor(H * 0.72);
      for (const b of row) {
        b.x = x;
        b.y = y + Math.floor((row[0].h - b.h) / 2);
        x += b.w + gap;
      }
    }
    const stop = this.screenButtons.play[0];
    stop.x = W - stop.w - 20;
    stop.y = 18;
  }

  loadBest() {
    try {
      return parseInt(localStorage.getItem(BEST_KEY) || "0", 10) || 0;
    } catch {
      return 0;
    }
  }

  saveBest() {
    try { localStorage.setItem(BEST_KEY, String(this.best)); } catch { /* storage unavailable */ }
  }

  resetRound() {
    this.flyers = [];
    this.particles = [];
    this.popups = [];
    this.score = 0;
    this.lives = LIVES;
    this.roundStart = now();
    this.nextSpawn = now() + 0.6;
    this.combo = 0;
    this.lastCutTime = 0;
    this.flashUntil = 0;
    this.overAt = null;
    this.newBest = false;
  }

  bindInput() {
    const toCanvas = (e) => {
      const r = this.canvas.getBoundingClientRect();
      return { x: (e.clientX - r.left) * (W / r.width), y: (e.clientY - r.top) * (H / r.height) };
    };
    this.canvas.addEventListener("pointermove", (e) => {
      // use every coalesced event so fast swipes still cut even when the game runs at low fps
      const events = e.getCoalescedEvents?.().length ? e.getCoalescedEvents() : [e];
      const t = now();
      for (const ev of events) {
        const p = toCanvas(ev);
        this.mouseSamples.push([p.x, p.y, t]);
      }
      const p = toCanvas(e);
      this.mouse = { x: p.x, y: p.y, t };
    });
    this.canvas.addEventListener("pointerdown", (e) => {
      const p = toCanvas(e);
      this.mouse = { x: p.x, y: p.y, t: now() };
      // a click presses a button right away (pointing and holding also works)
      const btn = this.screenButtons[this.state].find((b) => b.contains(p.x, p.y));
      if (btn) this.press(btn.action);
    });
    this.canvas.addEventListener("pointerleave", () => { this.mouse = null; });

    window.addEventListener("keydown", (e) => {
      if (e.key === " " && this.state !== "play") { e.preventDefault(); this.press("play"); }
      else if ((e.key === "q" || e.key === "Q") && this.state === "play") this.press("stop");
    });
  }

  // ---------- spawning ----------
  spawnWave() {
    const t = now();
    const playing = this.state === "play";
    const elapsed = t - this.roundStart;
    const count = !playing ? 1 : choice(elapsed > 20 ? [1, 1, 2, 2, 3] : [1, 1, 2]);
    const bombSlot = playing && elapsed > 8 && Math.random() < 0.3 ? Math.floor(Math.random() * count) : -1;
    for (let i = 0; i < count; i++) {
      const x = rand(W * 0.2, W * 0.8);
      const y = H + FOOD_SIZE * 0.6;
      const peak = rand(H * 0.15, H * 0.45);
      const vy = -Math.sqrt(2 * GRAVITY * (y - peak));
      const vx = (W / 2 - x) * rand(0.3, 0.8) + rand(-80, 80);
      const spin = rand(-160, 160);
      if (i === bombSlot) {
        this.flyers.push(new Flyer(bombSprite(FOOD_SIZE), x, y, vx, vy, spin, "bomb"));
      } else {
        const idx = Math.floor(Math.random() * FOODS.length);
        this.flyers.push(new Flyer(foodSprites(idx, FOOD_SIZE)[0], x, y, vx, vy, spin, "food", idx));
      }
    }
    const interval = playing ? Math.max(0.75, 1.5 - elapsed * 0.012) : 1.6;
    this.nextSpawn = t + interval * rand(0.8, 1.2);
  }

  // ---------- cutting ----------
  cutFood(f, swipeDx, swipeDy) {
    const t = now();
    const [, left, right] = foodSprites(f.foodIndex, FOOD_SIZE);
    // halves fly apart sideways to the swipe direction
    const len = Math.hypot(swipeDx, swipeDy) || 1;
    const nx = -swipeDy / len, ny = swipeDx / len;
    const push = 220;
    for (const [img, sign] of [[left, -1], [right, 1]]) {
      const half = new Flyer(img, f.x, f.y, f.vx + sign * nx * push, f.vy + sign * ny * push - 120,
                             f.spin + sign * 200, "half");
      half.angle = f.angle;
      this.flyers.push(half);
    }
    this.splash(f.x, f.y, FOODS[f.foodIndex][2], 22);

    if (this.state !== "play") return;
    this.combo = t - this.lastCutTime < COMBO_WINDOW ? this.combo + 1 : 1;
    this.lastCutTime = t;
    this.score += 1;
    this.popup("+1", f.x, f.y, [255, 236, 179]);
    if (this.combo >= 3) {
      this.score += 1;
      this.popup(`Combo x${this.combo}!`, W / 2, H * 0.32, [255, 182, 193], true);
    } else if (Math.random() < 0.18) {
      this.popup(choice(CHEERS), f.x, f.y - FOOD_SIZE * 0.6, [190, 240, 190]);
    }
  }

  hitBomb(b) {
    this.splash(b.x, b.y, [255, 140, 0], 40, 650);
    this.splash(b.x, b.y, [60, 60, 60], 20, 400);
    this.flashUntil = now() + 0.25;
    if (this.state === "play") {
      this.lives -= 1;
      this.popup("Oh no! A bomb!", W / 2, H * 0.32, [255, 175, 175], true);
      if (this.lives <= 0 && this.overAt === null) this.overAt = now() + 1.0;
    }
  }

  splash(x, y, color, count, speed = 450) {
    const t = now();
    for (let i = 0; i < count; i++) {
      const a = rand(0, Math.PI * 2);
      const v = rand(0.3, 1.0) * speed;
      this.particles.push({ x, y, vx: v * Math.cos(a), vy: v * Math.sin(a) - 150, r: rand(4, 11), color, t0: t });
    }
  }

  popup(text, x, y, fill, big = false) {
    this.popups.push({ img: renderPill(text, big ? 40 : 28, fill), x, y, t0: now() });
  }

  /** Record one fingertip/mouse sample: draws into the blade trail and cuts along the segment from the last one. */
  addSample(x, y, t) {
    const prev = this.lastSample;
    // Connect to the previous sample even on slow PCs (low fps), but not after the hand vanished for a while.
    if (prev && t - prev[2] <= MAX_SAMPLE_GAP) this.checkCut(prev, [x, y, t]);
    this.lastSample = [x, y, t];
    this.trail.push([x, y, t]);
  }

  checkCut([ax, ay, at], [bx, by, bt]) {
    const dt = Math.max(bt - at, 1e-3);
    if (Math.hypot(bx - ax, by - ay) / dt < SLICE_SPEED) return;
    for (const f of [...this.flyers]) {
      if (f.kind === "half") continue;
      if (segPointDistance(ax, ay, bx, by, f.x, f.y) < f.radius) {
        this.flyers.splice(this.flyers.indexOf(f), 1);
        if (f.kind === "food") this.cutFood(f, bx - ax, by - ay);
        else this.hitBomb(f);
      }
    }
  }

  // ---------- buttons ----------
  updateHover(tip) {
    const t = now();
    const btn = tip ? this.screenButtons[this.state].find((b) => b.contains(tip.x, tip.y)) : null;
    if (!btn) {
      if (this.hoverButton && t - this.hoverSeen > 0.3) this.hoverButton = null;
      return;
    }
    this.hoverSeen = t;
    if (btn !== this.hoverButton) {
      this.hoverButton = btn;
      this.hoverStart = t;
    } else if (t - this.hoverStart >= HOVER_SELECT_TIME) {
      this.hoverButton = null;
      this.press(btn.action);
    }
  }

  press(action) {
    if (action === "play") {
      this.resetRound();
      this.state = "play";
      this.popup("Go!", W / 2, H * 0.4, [140, 220, 120], true);
    } else if (action === "stop") {
      this.gameOver();
    } else if (action === "exit") {
      this.onExit?.();
    }
  }

  gameOver() {
    this.state = "over";
    this.overAt = null;
    this.flyers = this.flyers.filter((f) => f.kind === "half");
    if (this.score > this.best) {
      this.best = this.score;
      this.newBest = this.score > 0;
      this.saveBest();
    }
    if (this.score > 0) this.confetti.burst(W, H);
  }

  // ---------- input ----------
  /** Where the "finger" is this frame: tracked fingertip first, otherwise a recently moved mouse/touch. */
  readTip(t) {
    const hand = this.tracker?.detect(t * 1000);
    if (hand && this.videoRect) {
      const { dx, dy, dw, dh } = this.videoRect;
      return { x: W - (dx + hand.x * dw), y: dy + hand.y * dh, source: "hand" }; // mirrored like a selfie
    }
    if (this.mouse && t - this.mouse.t < MOUSE_TIMEOUT) return { x: this.mouse.x, y: this.mouse.y, source: "mouse" };
    return null;
  }

  // ---------- drawing ----------
  drawBackground(ctx) {
    const video = this.tracker?.video;
    if (this.tracker?.ready && video.videoWidth) {
      const vw = video.videoWidth, vh = video.videoHeight;
      const scale = Math.max(W / vw, H / vh);
      const dw = vw * scale, dh = vh * scale;
      this.videoRect = { dx: (W - dw) / 2, dy: (H - dh) / 2, dw, dh };
      ctx.save();
      ctx.translate(W, 0);
      ctx.scale(-1, 1);
      ctx.drawImage(video, this.videoRect.dx, this.videoRect.dy, dw, dh);
      ctx.restore();
    } else {
      this.videoRect = null;
      const g = ctx.createLinearGradient(0, 0, 0, H);
      g.addColorStop(0, "#bfe6ff");
      g.addColorStop(1, "#ffe3ef");
      ctx.fillStyle = g;
      ctx.fillRect(0, 0, W, H);
    }
  }

  drawTrail(ctx) {
    const pts = this.trail, n = pts.length;
    ctx.lineCap = "round";
    for (let i = 1; i < n; i++) {
      const k = i / n;
      ctx.beginPath();
      ctx.moveTo(pts[i - 1][0], pts[i - 1][1]);
      ctx.lineTo(pts[i][0], pts[i][1]);
      ctx.strokeStyle = rgb([120, 220, 255]);
      ctx.lineWidth = Math.max(2, 22 * k);
      ctx.stroke();
      ctx.strokeStyle = "#fff";
      ctx.lineWidth = Math.max(1, 10 * k);
      ctx.stroke();
    }
  }

  drawParticles(ctx, dt) {
    const t = now();
    const alive = [];
    for (const p of this.particles) {
      p.vy += GRAVITY * dt;
      p.x += p.vx * dt;
      p.y += p.vy * dt;
      const life = t - p.t0;
      if (life > 0.9 || p.y > H + 20) continue;
      const r = Math.max(1, p.r * (1 - life / 0.9));
      ctx.beginPath();
      ctx.arc(p.x, p.y, r, 0, Math.PI * 2);
      ctx.fillStyle = rgb(p.color);
      ctx.fill();
      alive.push(p);
    }
    this.particles = alive;
  }

  drawPopups(ctx) {
    const t = now();
    this.popups = this.popups.filter((p) => t - p.t0 <= 0.9);
    for (const p of this.popups) {
      const age = t - p.t0;
      ctx.globalAlpha = Math.min(1, (0.9 - age) / 0.3);
      ctx.drawImage(p.img, p.x - p.img.width / 2, p.y - p.img.height / 2 - age * 70);
    }
    ctx.globalAlpha = 1;
  }

  drawButtons(ctx) {
    for (const b of this.screenButtons[this.state]) {
      ctx.drawImage(b.img, b.x, b.y);
      if (b !== this.hoverButton) continue;
      const progress = Math.min(1, (now() - this.hoverStart) / HOVER_SELECT_TIME);
      const pad = 6;
      roundRectPath(ctx, b.x - pad, b.y - pad, b.w + 2 * pad, b.h + 2 * pad, b.h / 2 + pad);
      ctx.strokeStyle = rgb([255, 140, 0]);
      ctx.lineWidth = 5;
      ctx.stroke();
      const barY = b.y + b.h + 8;
      const x0 = b.x + b.h / 2, x1 = b.x + b.w - b.h / 2;
      ctx.lineCap = "round";
      ctx.lineWidth = 10;
      ctx.beginPath();
      ctx.moveTo(x0, barY);
      ctx.lineTo(x1, barY);
      ctx.strokeStyle = "#fff";
      ctx.stroke();
      if (progress > 0) {
        ctx.beginPath();
        ctx.moveTo(x0, barY);
        ctx.lineTo(x0 + (x1 - x0) * progress, barY);
        ctx.strokeStyle = rgb([220, 0, 255]);
        ctx.stroke();
      }
    }
  }

  center(ctx, img, y) {
    ctx.drawImage(img, Math.floor((W - img.width) / 2), Math.floor(y));
  }

  drawHud(ctx) {
    ctx.drawImage(renderPill(`Score: ${this.score}`, 34, [255, 236, 179]), 20, 16);
    const hs = 54;
    const stop = this.screenButtons.play[0];
    const x = stop.x - 20 - LIVES * (hs + 6);
    for (let i = 0; i < LIVES; i++) ctx.drawImage(heartSprite(hs, i < this.lives), x + i * (hs + 6), 16);
  }

  drawScreenText(ctx) {
    if (this.state === "start") {
      this.center(ctx, rainbowTitle("Food Slice!", 110), H * 0.1);
      const how = this.tracker ? "Swipe your finger to cut the food!" : "Swipe the mouse to cut the food!";
      this.center(ctx, renderPill(how, 32, [255, 255, 255]), H * 0.36);
      const tip = renderPill("Don't cut the bombs!", 26, [255, 205, 210]);
      const bomb = bombSprite(64);
      const total = bomb.width + 10 + tip.width;
      const x = Math.floor((W - total) / 2), y = Math.floor(H * 0.5);
      ctx.drawImage(bomb, x, y);
      ctx.drawImage(tip, x + bomb.width + 10, y + Math.floor((bomb.height - tip.height) / 2));
    } else if (this.state === "over") {
      this.center(ctx, rainbowTitle("Great job!", 100), H * 0.1);
      this.center(ctx, renderPill(`You cut ${this.score} foods!`, 44, [255, 236, 179]), H * 0.36);
      const best = this.newBest ? "New best score!" : `Best: ${this.best}`;
      this.center(ctx, renderPill(best, 28, this.newBest ? [255, 224, 130] : [255, 255, 255]), H * 0.52);
    }
  }

  drawCursor(ctx, tip) {
    ctx.beginPath();
    ctx.arc(tip.x, tip.y, 14, 0, Math.PI * 2);
    ctx.fillStyle = "#fff";
    ctx.fill();
    ctx.lineWidth = 4;
    ctx.strokeStyle = rgb([220, 0, 255]);
    ctx.stroke();
  }

  // ---------- main loop ----------
  frame() {
    const ctx = this.ctx;
    const t = now();
    const dt = Math.min(t - this.lastTime, 0.05);
    this.lastTime = t;

    this.drawBackground(ctx);

    if (this.state !== "over" && t >= this.nextSpawn) this.spawnWave();
    for (const f of this.flyers) f.update(dt);
    this.flyers = this.flyers.filter((f) => f.y < H + FOOD_SIZE || f.vy < 0);

    const tip = this.readTip(t);
    if (tip?.source === "hand") {
      this.lastHandTime = t;
      this.addSample(tip.x, tip.y, t);
    } else if (tip?.source === "mouse") {
      for (const [x, y, st] of this.mouseSamples) this.addSample(x, y, st);
    } else {
      this.trail.length = 0;
      this.lastSample = null;
    }
    this.mouseSamples.length = 0;
    while (this.trail.length && t - this.trail[0][2] > TRAIL_TIME) this.trail.shift();
    this.updateHover(tip);
    if (this.overAt !== null && t >= this.overAt) this.gameOver();

    if (this.state !== "play") {
      ctx.fillStyle = "rgba(255,225,235,0.4)";
      ctx.fillRect(0, 0, W, H);
    }
    for (const f of this.flyers) f.draw(ctx);
    this.drawParticles(ctx, dt);
    if (t < this.flashUntil) {
      ctx.fillStyle = "rgba(255,255,255,0.6)";
      ctx.fillRect(0, 0, W, H);
    }

    this.drawScreenText(ctx);
    if (this.state === "play") this.drawHud(ctx);
    this.drawButtons(ctx);
    this.drawPopups(ctx);
    this.confetti.draw(ctx, dt, H);
    this.drawTrail(ctx);
    if (tip) {
      this.drawCursor(ctx, tip);
    } else if (this.tracker && t - this.lastHandTime > NO_HAND_HINT_DELAY) {
      const hint = renderPill("Show me your hand!", 40, [255, 255, 255]);
      this.center(ctx, hint, H * 0.82 + 8 * Math.sin(t * 4));
    }
  }

  start() {
    const loop = () => {
      this.frame();
      this.raf = requestAnimationFrame(loop);
    };
    this.lastTime = now();
    loop();
  }
}
