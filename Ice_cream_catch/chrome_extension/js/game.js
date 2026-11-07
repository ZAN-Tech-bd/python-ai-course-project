// Ice Cream Catch game logic and rendering. Port of IceCreamCatch in main.py, with extras for the
// browser version: Easy/Super modes, power-ups, a team goal, catch streaks, an ice cream party,
// animal ears, sounds and a mouse/touch mode.
// The canvas is always 1280x720 internally; CSS scales it to fit the window.

import { Confetti, choice, rainbowTitle, rand, renderPill, rgb, roundRectPath } from "./ui.js";
import {
  FLAVORS, GOLD, RAINBOW, broccoliSprite, coneSprite, earsSprite, scoopSprite, snowflakeSprite,
  sparkleSprite, splatSprite,
} from "./sprites.js";
import { Player, PlayerTracker } from "./tracker.js";
import { sound } from "./sound.js";

export const W = 1280, H = 720;
const ROUND_TIME = 60;        // seconds per round
const COUNTDOWN = 3;
const TOWER_SIZE = 5;         // scoops in a full tower (bonus, then the tower is "eaten")
const HOLD_TIME = 1.1;        // seconds a head must stay on a button to press it
const ITEM_SIZE = 96;         // falling item size
const FALL_SPEED = 170;       // px/s, rises during the round
const BIG_TIME = 6;           // rainbow scoop: giant cone for this long
const FREEZE_TIME = 5;        // snowflake: slow motion for this long
const PARTY_AT = 25;          // seconds left when the ice cream party starts
const PARTY_TIME = 5;
const NO_FACE_HINT_DELAY = 1.5;
const MOUSE_FACE = 130;       // size of the pretend "face" in mouse mode
const BEST_KEY = "icecream.best";
const CHEERS = ["Yum!", "Tasty!", "Nice catch!", "Wow!", "Super!", "Delicious!"];
const STREAK_WORDS = { 3: "3 in a row!", 5: "5 in a row! +2", 10: "10 in a row!! +5", 15: "UNSTOPPABLE! +5", 20: "ICE CREAM HERO! +5" };
const MODES = {
  easy: { label: "Easy", broccoli: false, speed: 0.75, spawn: 0.85, ramp: 1.2 },
  super: { label: "Super", broccoli: true, speed: 1.0, spawn: 1.0, ramp: 2.2 },
};

const now = () => performance.now() / 1000;

/** Something falling from the sky. */
class Item {
  constructor(kind, flavor, x, y, vy, size) {
    Object.assign(this, { kind, flavor, x, y, vy, size });
    this.x0 = x;
    this.phase = rand(0, Math.PI * 2);
    if (kind === "broccoli") this.sprite = broccoliSprite(size);
    else if (kind === "snow") this.sprite = snowflakeSprite(size);
    else this.sprite = scoopSprite(flavor, size, true);
  }

  update(dt, t, slow) {
    this.y += this.vy * dt * slow;
    this.x = this.x0 + Math.sin(t * 1.6 + this.phase) * this.size * 0.3;
  }

  draw(ctx, t) {
    const s = this.sprite.width;
    if (this.kind === "gold" || this.kind === "rainbow") {
      const sp = sparkleSprite(s * 1.5);
      ctx.globalAlpha = 0.6 + 0.4 * Math.sin(t * 8);
      ctx.drawImage(sp, this.x - sp.width / 2, this.y - sp.height / 2);
      ctx.globalAlpha = 1;
    }
    ctx.save();
    ctx.translate(this.x, this.y);
    ctx.rotate(Math.sin(t * 3 + this.phase) * 0.15);
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
  overlaps(x, y, w, h) {
    return x < this.x + this.w && x + w > this.x && y < this.y + this.h && y + h > this.y;
  }
  contains(px, py) {
    return px >= this.x && px <= this.x + this.w && py >= this.y && py <= this.y + this.h;
  }
}

export class IceCreamGame {
  /**
   * @param canvas  the 1280x720 game canvas
   * @param camera  FaceTracker, or null to play with mouse/touch only
   * @param onExit  called when the Exit button is chosen
   */
  constructor(canvas, camera, onExit) {
    this.canvas = canvas;
    this.ctx = canvas.getContext("2d");
    this.camera = camera;
    this.onExit = onExit;
    this.tracker = new PlayerTracker();
    this.tracker.onJoin = (p) => this._joined(p);
    this.confetti = new Confetti();

    const easy = new PillButton("Easy", [140, 220, 120], "easy", 58);
    const sup = new PillButton("Super", [255, 140, 190], "super", 58);
    easy.x = Math.round(W * 0.27 - easy.w / 2);
    sup.x = Math.round(W * 0.73 - sup.w / 2);
    easy.y = sup.y = Math.round(H * 0.6);
    const easy2 = new PillButton("Easy again", [140, 220, 120], "easy", 44);
    const sup2 = new PillButton("Super again", [255, 140, 190], "super", 44);
    easy2.x = Math.round(W * 0.25 - easy2.w / 2);
    sup2.x = Math.round(W * 0.75 - sup2.w / 2);
    easy2.y = sup2.y = Math.round(H * 0.78);
    const exit = new PillButton("Exit", [255, 175, 175], "exit", 24);
    exit.x = W - exit.w - 20;
    exit.y = 16;
    this.buttons = { start: [easy, sup, exit], over: [easy2, sup2, exit], countdown: [], play: [] };

    this.best = this._loadBest();
    this.mode = "easy";
    this.state = "start";
    this.items = [];
    this.debris = [];
    this.splats = [];
    this.popups = [];
    this.results = [];
    this.nextSpawn = now() + 1;
    this.stateStart = this.roundStart = now();
    this.freezeUntil = 0;
    this.partyDone = false;
    this.lastBeep = -1;
    this.hover = { button: null, start: 0, seen: 0 };
    this.lastFaceTime = now();
    this.lastTime = now();

    this.mouse = { x: W / 2, y: H * 0.55, seen: -10 };
    this.mousePlayer = null;
    this._bindPointer();
  }

  // ---------- setup ----------
  _bindPointer() {
    const toGame = (e) => {
      const r = this.canvas.getBoundingClientRect();
      return [(e.clientX - r.left) * (W / r.width), (e.clientY - r.top) * (H / r.height)];
    };
    this.canvas.addEventListener("pointermove", (e) => {
      const [x, y] = toGame(e);
      Object.assign(this.mouse, { x, y, seen: now() });
    });
    this.canvas.addEventListener("pointerdown", (e) => {
      sound.unlock();
      const [x, y] = toGame(e);
      Object.assign(this.mouse, { x, y, seen: now() });
      const btn = this.buttons[this.state].find((b) => b.contains(x, y));
      if (btn) this._press(btn.action);
    });
  }

  _loadBest() {
    try { return parseInt(localStorage.getItem(BEST_KEY) || "0", 10) || 0; } catch { return 0; }
  }
  _saveBest() {
    try { localStorage.setItem(BEST_KEY, String(this.best)); } catch { /* storage unavailable */ }
  }

  start() {
    const loop = () => {
      this.frame();
      this.raf = requestAnimationFrame(loop);
    };
    this.raf = requestAnimationFrame(loop);
  }

  // ---------- players ----------
  /** Face boxes from the camera, mapped to game pixels (mirrored like a selfie, cover-fit). */
  _cameraBoxes(tMs) {
    if (!this.camera?.ready) return [];
    const v = this.camera.video;
    const { dx, dy, dw, dh } = this._coverRect(v.videoWidth, v.videoHeight);
    return this.camera.detect(tMs).map((f) => ({
      x: W - (dx + (f.x + f.w) * dw), y: dy + f.y * dh, w: f.w * dw, h: f.h * dh,
    }));
  }

  _coverRect(vw, vh) {
    const s = Math.max(W / vw, H / vh);
    const dw = vw * s, dh = vh * s;
    return { dx: (W - dw) / 2, dy: (H - dh) / 2, dw, dh };
  }

  _players(t, tMs) {
    if (this.camera) {
      this.tracker.update(this._cameraBoxes(tMs));
      return this.tracker.activePlayers();
    }
    // mouse / touch mode: one pretend player whose face follows the pointer
    if (!this.mousePlayer) {
      this.mousePlayer = new Player(0, { x: W / 2 - MOUSE_FACE / 2, y: H * 0.55, w: MOUSE_FACE, h: MOUSE_FACE });
      this.tracker.players = [this.mousePlayer];
    }
    const p = this.mousePlayer;
    const y = Math.min(Math.max(this.mouse.y - MOUSE_FACE / 2, H * 0.3), H - MOUSE_FACE - 40);
    p.update({ x: this.mouse.x - MOUSE_FACE / 2, y, w: MOUSE_FACE, h: MOUSE_FACE }, 0.6);
    return [p];
  }

  _joined(p) {
    if (this.camera) {
      sound.join();
      this._popup(`Hi ${p.name}!`, p.cx, p.y - p.h * 1.6, p.color, true);
    }
  }

  // ---------- cone + stack geometry for one player ----------
  _geometry(p, t) {
    const big = p.bigUntil > t ? 1.6 : 1;
    const coneW = Math.max(50, p.w * 0.8) * big;
    const coneH = coneW * 1.15;
    const scoopD = coneW * 1.05;
    const headTop = p.y - p.h * 0.18; // face boxes start around the eyebrows
    const coneTop = headTop - coneH * 0.95;
    return { coneW, coneH, scoopD, coneTop, headTop };
  }

  _scoopCenter(p, i, t) {
    const { scoopD, coneTop } = this._geometry(p, t);
    const wobble = Math.sin(t * 3 + p.slot) * i * 3;
    return [p.cx + wobble, coneTop - scoopD * 0.12 - i * scoopD * 0.55];
  }

  _catchPoint(p, t) {
    const { scoopD, coneTop } = this._geometry(p, t);
    if (!p.stack.length) return [p.cx, coneTop];
    const [x, y] = this._scoopCenter(p, p.stack.length - 1, t);
    return [x, y - scoopD * 0.35];
  }

  // ---------- game flow ----------
  _press(action) {
    sound.unlock();
    if (action === "easy" || action === "super") {
      this.mode = action;
      this.tracker.resetScores();
      this.items = [];
      this.debris = [];
      this.splats = [];
      this.state = "countdown";
      this.stateStart = now();
      this.lastBeep = -1;
    } else if (action === "exit") {
      sound.stopMusic();
      this.onExit?.();
    }
  }

  _startRound() {
    const t = now();
    this.state = "play";
    this.roundStart = this.stateStart = t;
    this.tracker.keepTime = 20; // keep a kid's score if they step away for a bit during the round
    this.tracker.resetScores();
    this.nextSpawn = t + 0.3;
    this.freezeUntil = 0;
    this.partyDone = false;
    this.partyUntil = 0;
    this.teamScoops = 0;
    this.teamGoal = this._nextGoal(0);
    this.teamGoalsHit = 0;
    this._popup("Go!", W / 2, H * 0.45, [140, 220, 120], true);
    sound.go();
    sound.startMusic();
  }

  _nextGoal(from) {
    const n = Math.max(1, this.tracker.activePlayers().length);
    return from + 10 + 6 * n;
  }

  _endRound() {
    this.state = "over";
    this.stateStart = now();
    this.tracker.keepTime = 3;
    this.results = [...this.tracker.players].sort((a, b) => b.score - a.score)
      .map((p) => ({ name: p.name, color: p.color, score: p.score }));
    this.newBest = false;
    if (this.results.length && this.results[0].score > this.best) {
      this.best = this.results[0].score;
      this.newBest = true;
      this._saveBest();
    }
    if (this.results.length && this.results[0].score > 0) {
      this.confetti.burst(W, H, 120);
      sound.win();
    }
    sound.stopMusic();
    this.items = [];
    for (const p of this.tracker.players) { p.stack = []; p.bigUntil = 0; }
    this.freezeUntil = 0;
  }

  _spawn(players, t) {
    const playing = this.state === "play";
    const mode = MODES[this.mode];
    const elapsed = playing ? t - this.roundStart : 0;
    const party = playing && t < this.partyUntil;
    const size = ITEM_SIZE;
    let x = rand(W * 0.08, W * 0.92);
    // aim some items above a player so everyone gets a fair chance
    if (players.length && Math.random() < 0.6) {
      x = choice(players).cx + rand(-1, 1) * W * 0.15;
      x = Math.min(Math.max(x, W * 0.05), W * 0.95);
    }
    const speed = (FALL_SPEED + elapsed * mode.ramp) * mode.speed * rand(0.85, 1.2);
    const r = Math.random();
    const snowFalling = this.items.some((i) => i.kind === "snow");
    let item;
    if (party) {
      item = r > 0.9 ? new Item("gold", GOLD, x, -size, speed * 1.1, size)
                     : new Item("scoop", Math.floor(rand(0, FLAVORS.length)), x, -size, speed, size);
    } else if (playing && mode.broccoli && elapsed > 10 && r < 0.14) {
      item = new Item("broccoli", 0, x, -size, speed * 1.1, size);
    } else if (playing && elapsed > 5 && r >= 0.14 && r < 0.17 && !snowFalling && t > this.freezeUntil) {
      item = new Item("snow", 0, x, -size, speed * 0.9, size);
    } else if (playing && elapsed > 5 && r >= 0.17 && r < 0.2) {
      item = new Item("rainbow", RAINBOW, x, -size, speed * 1.15, size);
    } else if (playing && r > 0.94) {
      item = new Item("gold", GOLD, x, -size, speed * 1.2, size);
    } else {
      item = new Item("scoop", Math.floor(rand(0, FLAVORS.length)), x, -size, speed, size);
    }
    this.items.push(item);
    const crowd = Math.sqrt(Math.max(1, players.length));
    let interval = (playing ? Math.max(0.45, 1.2 - elapsed * 0.01) * mode.spawn : 1.6) / crowd;
    if (party) interval = 0.13;
    this.nextSpawn = t + interval * rand(0.8, 1.2);
  }

  _checkCatches(players, t) {
    for (const item of [...this.items]) {
      for (const p of players) {
        const { coneW, scoopD } = this._geometry(p, t);
        const [cx, cy] = this._catchPoint(p, t);
        if (Math.abs(item.x - cx) < coneW * 0.55 + item.size * 0.2 && Math.abs(item.y - cy) < scoopD * 0.4) {
          this.items.splice(this.items.indexOf(item), 1);
          this._caught(p, item, t);
          break;
        }
      }
    }
  }

  _caught(p, item, t) {
    const playing = this.state === "play";
    const [x, y] = this._catchPoint(p, t);
    if (item.kind === "broccoli") {
      this._dropStack(p, t);
      p.streak = 0;
      this._popup("Yuck! Broccoli!", x, y - 40, [190, 240, 190], true);
      sound.yuck();
      return;
    }
    if (item.kind === "snow") {
      this.freezeUntil = t + FREEZE_TIME;
      if (playing) p.score += 1;
      this._popup("Brrr! Slow motion!", W / 2, H * 0.32, [170, 220, 255], true);
      sound.freeze();
      return;
    }
    p.stack.push(item.flavor);
    p.streak += 1;
    if (playing) {
      let points = 1;
      if (item.kind === "gold") {
        points = 3;
        this._popup("Golden! +3", x, y - 30, [255, 224, 130], true);
        sound.gold();
      } else if (item.kind === "rainbow") {
        points = 2;
        p.bigUntil = t + BIG_TIME;
        this._popup(`${p.name}: GIANT CONE!`, x, y - 40, [255, 190, 230], true);
        sound.rainbow();
      } else {
        this._popup("+1", x, y - 30, p.color);
        sound.catch(p.streak);
      }
      const word = STREAK_WORDS[p.streak];
      if (word) {
        const bonus = p.streak >= 10 ? 5 : p.streak === 5 ? 2 : 0;
        points += bonus;
        this._popup(`${p.name}: ${word}`, W / 2, H * 0.22, p.color, true);
      }
      p.score += points;
      this._teamCatch(points);
    } else {
      sound.catch(0);
    }
    if (p.stack.length >= TOWER_SIZE) {
      if (playing) {
        p.score += TOWER_SIZE;
        this._popup(`${p.name}: Tower! +${TOWER_SIZE}`, W / 2, H * 0.3, p.color, true);
        this._teamCatch(TOWER_SIZE);
      }
      this.confetti.burst(W, H, 30);
      sound.tower();
      p.stack = [];
    } else if (playing && Math.random() < 0.15) {
      this._popup(choice(CHEERS), x, y - 80, [255, 255, 255]);
    }
  }

  _teamCatch(points) {
    this.teamScoops += points;
    if (this.teamScoops >= this.teamGoal) {
      this.teamGoalsHit += 1;
      for (const p of this.tracker.players) p.score += 3;
      this._popup("TEAM GOAL! Everyone +3", W / 2, H * 0.4, [255, 224, 130], true);
      this.confetti.burst(W, H, 60);
      sound.win();
      this.teamGoal = this._nextGoal(this.teamGoal);
    }
  }

  _dropStack(p, t) {
    const { scoopD } = this._geometry(p, t);
    p.stack.forEach((flavor, i) => {
      const [x, y] = this._scoopCenter(p, i, t);
      this.debris.push({ sprite: scoopSprite(flavor, scoopD), x, y, vx: rand(-200, 200), vy: rand(-300, -100) });
    });
    p.stack = [];
  }

  _popup(text, x, y, fill, big = false) {
    this.popups.push({ img: renderPill(text, big ? 40 : 28, fill), x, y, t0: now() });
  }

  _updateHover(players, t) {
    // mouse mode uses clicks; after a round give kids a moment so nobody restarts by accident
    if (!this.camera || (this.state === "over" && t - this.stateStart < 2.5)) {
      this.hover.button = null;
      return;
    }
    let btn = null;
    for (const p of players) {
      // any part of the face touching the button counts
      btn = this.buttons[this.state].find((b) => b.overlaps(p.x, p.y, p.w, p.h));
      if (btn) break;
    }
    if (!btn) {
      if (this.hover.button && t - this.hover.seen > 0.3) this.hover.button = null;
      return;
    }
    this.hover.seen = t;
    if (btn !== this.hover.button) {
      this.hover.button = btn;
      this.hover.start = t;
    } else if (t - this.hover.start >= HOLD_TIME) {
      this.hover.button = null;
      this._press(btn.action);
    }
  }

  // ---------- drawing ----------
  _center(img, y, alpha = 1) {
    this.ctx.globalAlpha = alpha;
    this.ctx.drawImage(img, Math.round((W - img.width) / 2), Math.round(y));
    this.ctx.globalAlpha = 1;
  }

  _drawBackground(t) {
    const ctx = this.ctx;
    const v = this.camera?.video;
    if (this.camera?.ready && v.videoWidth) {
      const { dx, dy, dw, dh } = this._coverRect(v.videoWidth, v.videoHeight);
      ctx.save();
      ctx.translate(W, 0);
      ctx.scale(-1, 1); // mirror like a selfie
      ctx.drawImage(v, dx, dy, dw, dh);
      ctx.restore();
    } else {
      const g = ctx.createLinearGradient(0, 0, 0, H);
      g.addColorStop(0, "#9fdcff");
      g.addColorStop(1, "#ffe1f0");
      ctx.fillStyle = g;
      ctx.fillRect(0, 0, W, H);
      ctx.fillStyle = "rgba(255,255,255,0.85)";
      for (let i = 0; i < 4; i++) { // drifting clouds
        const cx = ((t * 18 + i * 360) % (W + 300)) - 150, cy = 90 + (i % 2) * 120;
        for (const [ox, oy, r] of [[0, 0, 40], [40, -18, 48], [85, 0, 38], [42, 14, 40]]) {
          ctx.beginPath(); ctx.arc(cx + ox, cy + oy, r, 0, Math.PI * 2); ctx.fill();
        }
      }
      ctx.fillStyle = "#9be38a";
      ctx.fillRect(0, H - 40, W, 40);
    }
    if (this.state === "start" || this.state === "over") {
      ctx.fillStyle = "rgba(255,230,240,0.42)";
      ctx.fillRect(0, 0, W, H);
    }
    if (t < this.freezeUntil) {
      const left = this.freezeUntil - t;
      ctx.fillStyle = `rgba(150,210,255,${0.25 * Math.min(1, left)})`;
      ctx.fillRect(0, 0, W, H);
    }
  }

  /** Mouse mode has no real face under the cone, so draw a happy cartoon one. */
  _drawCartoonFace(p, t) {
    const ctx = this.ctx;
    const r = p.w * 0.5, cx = p.cx, cy = p.y + p.h * 0.5;
    const dot = (x, y, rr, fill) => { ctx.beginPath(); ctx.arc(x, y, rr, 0, Math.PI * 2); ctx.fillStyle = fill; ctx.fill(); };
    dot(cx, cy, r, "rgb(90,55,50)");
    dot(cx, cy, r - 4, rgb(p.color));
    dot(cx, cy + r * 0.25, r * 0.55, "rgba(255,255,255,0.75)");
    const blink = (t % 3.5) < 0.12 ? 0.2 : 1;
    for (const s of [-1, 1]) {
      ctx.beginPath();
      ctx.ellipse(cx + s * r * 0.35, cy - r * 0.12, r * 0.1, r * 0.13 * blink, 0, 0, Math.PI * 2);
      ctx.fillStyle = "#2a2030";
      ctx.fill();
      dot(cx + s * r * 0.6, cy + r * 0.2, r * 0.12, "rgba(255,90,120,0.4)");
    }
    dot(cx, cy + r * 0.12, r * 0.08, "#2a2030");
    ctx.lineWidth = Math.max(3, r * 0.07);
    ctx.lineCap = "round";
    ctx.strokeStyle = "#2a2030";
    ctx.beginPath();
    ctx.arc(cx, cy + r * 0.2, r * 0.25, 0.15 * Math.PI, 0.85 * Math.PI);
    ctx.stroke();
  }

  _drawPlayer(p, t) {
    const ctx = this.ctx;
    const { coneW, scoopD, coneTop, headTop } = this._geometry(p, t);
    if (!this.camera) this._drawCartoonFace(p, t);
    const ears = earsSprite(p.ears, p.w * 1.35, p.color);
    ctx.drawImage(ears, p.cx - ears.width / 2, headTop - ears.height * 0.7);
    if (p.bigUntil > t) { // rainbow glow around a giant cone
      ctx.globalAlpha = 0.35 + 0.25 * Math.sin(t * 10);
      const sp = sparkleSprite(coneW * 1.6);
      ctx.drawImage(sp, p.cx - sp.width / 2, coneTop - sp.height * 0.4);
      ctx.globalAlpha = 1;
    }
    const cone = coneSprite(coneW);
    ctx.drawImage(cone, p.cx - cone.width / 2, coneTop);
    p.stack.forEach((flavor, i) => {
      const [x, y] = this._scoopCenter(p, i, t);
      const sp = scoopSprite(flavor, scoopD);
      ctx.drawImage(sp, x - sp.width / 2, y - sp.height / 2);
    });
    const label = this.state === "play" || this.state === "over" ? `${p.name}  ${p.score}` : p.name;
    const tag = renderPill(label, 26, p.color);
    ctx.drawImage(tag, p.cx - tag.width / 2, Math.min(p.y + p.h + 12, H - tag.height - 4));
  }

  _drawItems(dt, t) {
    const ctx = this.ctx;
    // melted puddles fade away
    this.splats = this.splats.filter((s) => t - s.t0 < 2.5);
    for (const s of this.splats) {
      ctx.globalAlpha = Math.min(1, (2.5 - (t - s.t0)) / 0.8);
      ctx.drawImage(s.sprite, s.x - s.sprite.width / 2, H - s.sprite.height);
    }
    ctx.globalAlpha = 1;
    for (const item of this.items) item.draw(ctx, t);
    const alive = [];
    for (const d of this.debris) {
      d.vy += 1300 * dt;
      d.x += d.vx * dt;
      d.y += d.vy * dt;
      if (d.y < H + 100) {
        ctx.drawImage(d.sprite, d.x - d.sprite.width / 2, d.y - d.sprite.height / 2);
        alive.push(d);
      }
    }
    this.debris = alive;
  }

  _drawPopups(t) {
    const ctx = this.ctx;
    this.popups = this.popups.filter((p) => t - p.t0 <= 1.1);
    for (const p of this.popups) {
      const age = t - p.t0;
      const pop = age < 0.12 ? 0.6 + age / 0.3 : 1; // quick "pop" grow-in
      ctx.globalAlpha = Math.min(1, (1.1 - age) / 0.3);
      const w = p.img.width * pop, h = p.img.height * pop;
      ctx.drawImage(p.img, p.x - w / 2, p.y - h / 2 - age * 60, w, h);
    }
    ctx.globalAlpha = 1;
  }

  _drawButtons(t) {
    const ctx = this.ctx;
    for (const b of this.buttons[this.state]) {
      const hovered = b === this.hover.button;
      const bob = b.action === "exit" ? 0 : Math.sin(t * 3 + b.x) * 4;
      ctx.drawImage(b.img, b.x, b.y + bob);
      if (hovered) {
        const progress = Math.min(1, (t - this.hover.start) / HOLD_TIME);
        const pad = 6;
        roundRectPath(ctx, b.x - pad, b.y - pad + bob, b.w + 2 * pad, b.h + 2 * pad, b.h / 2 + pad);
        ctx.lineWidth = 5;
        ctx.strokeStyle = "rgb(255,140,0)";
        ctx.stroke();
        const y = b.y + b.h + 12 + bob, x0 = b.x + b.h / 2, x1 = b.x + b.w - b.h / 2;
        ctx.lineCap = "round";
        ctx.lineWidth = 10;
        ctx.strokeStyle = "#fff";
        ctx.beginPath(); ctx.moveTo(x0, y); ctx.lineTo(x1, y); ctx.stroke();
        ctx.strokeStyle = "rgb(220,0,255)";
        ctx.beginPath(); ctx.moveTo(x0, y); ctx.lineTo(x0 + (x1 - x0) * progress, y); ctx.stroke();
      }
    }
  }

  _drawLegend(y) {
    const ctx = this.ctx;
    const entries = [
      [scoopSprite(0, 54, true), "+1"],
      [scoopSprite(GOLD, 54, true), "+3"],
      [scoopSprite(RAINBOW, 54, true), "Giant cone"],
      [snowflakeSprite(54), "Slow motion"],
      [broccoliSprite(54), "Yuck! (Super)"],
    ];
    const pills = entries.map(([, text]) => renderPill(text, 20, [255, 255, 255]));
    const gap = 22;
    const total = entries.reduce((s, [sp], i) => s + sp.width + 4 + pills[i].width, 0) + gap * (entries.length - 1);
    let x = (W - total) / 2;
    entries.forEach(([sp], i) => {
      ctx.drawImage(sp, x, y);
      x += sp.width + 4;
      ctx.drawImage(pills[i], x, y + (sp.height - pills[i].height) / 2);
      x += pills[i].width + gap;
    });
  }

  _drawTeamBar(t) {
    const ctx = this.ctx;
    const w = 360, h = 26, x = (W - w) / 2, y = 78;
    const frac = Math.min(1, this.teamScoops / this.teamGoal);
    roundRectPath(ctx, x, y, w, h, h / 2);
    ctx.fillStyle = "rgba(255,255,255,0.85)";
    ctx.fill();
    ctx.lineWidth = 3;
    ctx.strokeStyle = "#fff";
    ctx.stroke();
    if (frac > 0) {
      roundRectPath(ctx, x + 3, y + 3, Math.max(h - 6, (w - 6) * frac), h - 6, (h - 6) / 2);
      const g = ctx.createLinearGradient(x, 0, x + w, 0);
      g.addColorStop(0, "#ff8ac2");
      g.addColorStop(0.5, "#ffd56b");
      g.addColorStop(1, "#7fe0a8");
      ctx.fillStyle = g;
      ctx.fill();
    }
    const label = renderPill(`Team goal ${this.teamScoops} / ${this.teamGoal}`, 18, [255, 236, 179]);
    ctx.drawImage(label, (W - label.width) / 2, y + h + 4);
    const icon = scoopSprite(3, 44, true);
    ctx.drawImage(icon, x + w - 20, y - 12 + Math.sin(t * 4) * 3);
  }

  _drawScreen(players, t) {
    const ctx = this.ctx;
    if (this.state === "start") {
      this._center(rainbowTitle("Ice Cream Catch!", 92), H * 0.03 + Math.sin(t * 2) * 4);
      this._center(renderPill("Catch the ice cream with the cone on your head!", 30, [255, 255, 255]), H * 0.22);
      this._drawLegend(H * 0.33);
      const who = this.camera
        ? (players.length ? `${players.length} player${players.length > 1 ? "s" : ""} ready!  Up to 6 friends can play.`
                          : "Up to 6 friends can play together!")
        : "Mouse mode: move the mouse to move your cone";
      this._center(renderPill(who, 22, [173, 216, 255]), H * 0.47);
      const hint = this.camera ? "Put your head on Easy or Super and hold still" : "Click Easy or Super to start";
      this._center(renderPill(hint, 22, [255, 236, 179]), H * 0.6 + 120);
    } else if (this.state === "countdown") {
      const left = COUNTDOWN - (t - this.stateStart);
      if (left <= 0) {
        this._startRound();
      } else {
        const n = Math.ceil(left);
        if (n !== this.lastBeep) { this.lastBeep = n; sound.beep(); }
        const frac = left - Math.floor(left);
        const img = rainbowTitle(String(n), 220);
        const s = 0.7 + 0.3 * frac + 0.3 * Math.max(0, frac - 0.8) * 5;
        ctx.drawImage(img, (W - img.width * s) / 2, (H - img.height * s) / 2, img.width * s, img.height * s);
        this._center(renderPill(`${MODES[this.mode].label} mode - get ready!`, 30, [255, 255, 255]), H * 0.08);
      }
    } else if (this.state === "play") {
      const left = Math.max(0, ROUND_TIME - (t - this.roundStart));
      if (!this.partyDone && left <= PARTY_AT) {
        this.partyDone = true;
        this.partyUntil = t + PARTY_TIME;
        this._popup("ICE CREAM PARTY!!", W / 2, H * 0.4, [255, 140, 190], true);
        this.confetti.burst(W, H, 40);
        sound.tower();
      }
      if (left <= 5 && left > 0 && Math.ceil(left) !== this.lastBeep) {
        this.lastBeep = Math.ceil(left);
        sound.beep();
      }
      const fill = left <= 10 ? [255, 175, 175] : [255, 255, 255];
      const timer = renderPill(`Time ${Math.floor(left / 60)}:${String(Math.floor(left) % 60).padStart(2, "0")}`, 34, fill);
      this._center(timer, 14, left <= 10 ? 0.75 + 0.25 * Math.sin(t * 8) : 1);
      this._drawTeamBar(t);
      let y = 14;
      for (const p of [...this.tracker.players].sort((a, b) => b.score - a.score)) {
        const tag = renderPill(`${p.name} ${p.score}`, 22, p.color);
        ctx.globalAlpha = p.active ? 1 : 0.5;
        ctx.drawImage(tag, 16, y);
        y += tag.height + 6;
      }
      ctx.globalAlpha = 1;
      if (t < this.partyUntil) {
        this._center(renderPill("Ice cream party! Catch them all!", 26, [255, 140, 190]), H * 0.86,
                     0.7 + 0.3 * Math.sin(t * 10));
      } else if (t < this.freezeUntil) {
        this._center(renderPill(`Slow motion ${Math.ceil(this.freezeUntil - t)}`, 26, [170, 220, 255]), H * 0.86);
      }
      if (left <= 0) this._endRound();
    } else if (this.state === "over") {
      const r = this.results;
      let title;
      if (!r.length) title = "Nobody played!";
      else if (r.length > 1 && r[0].score === r[1].score) title = "It's a tie!";
      else title = `${r[0].name} wins!`;
      this._center(rainbowTitle(title, 86), H * 0.03 + Math.sin(t * 2) * 4);
      let y = H * 0.2;
      r.slice(0, 6).forEach((res, i) => {
        const medal = ["1st", "2nd", "3rd"][i] || `${i + 1}th`;
        const tag = renderPill(`${medal}  ${res.name}  ${res.score} point${res.score !== 1 ? "s" : ""}`, 26, res.color);
        this._center(tag, y);
        y += tag.height + 6;
      });
      const team = r.length > 1 ? `Team goals reached: ${this.teamGoalsHit || 0}   ` : "";
      const best = this.newBest ? "New best score!" : `Best ever: ${this.best}`;
      this._center(renderPill(team + best, 24, [255, 224, 130]), H * 0.68);
    }

    if (this.camera && !players.length && t - this.lastFaceTime > NO_FACE_HINT_DELAY) {
      this._center(renderPill("Step in front of the camera!", 40, [255, 255, 255]), H * 0.44 + 8 * Math.sin(t * 4));
    }
  }

  // ---------- main loop ----------
  frame() {
    const t = now();
    const dt = Math.min(t - this.lastTime, 0.05);
    this.lastTime = t;

    const players = this._players(t, performance.now());
    if (players.length) this.lastFaceTime = t;

    if ((this.state === "start" || this.state === "play") && t >= this.nextSpawn) this._spawn(players, t);
    const slow = t < this.freezeUntil ? 0.35 : 1;
    for (const item of this.items) item.update(dt, t, slow);
    for (const item of this.items) {
      if (item.y >= H - 30 && item.kind !== "broccoli" && item.kind !== "snow" && !item.splatted) {
        item.splatted = true;
        this.splats.push({ sprite: splatSprite(item.flavor, item.size * 0.9), x: item.x, t0: t });
        if (this.state === "play") sound.splat();
        players.forEach((p) => { if (Math.abs(p.cx - item.x) < p.w) p.streak = 0; });
      }
    }
    this.items = this.items.filter((i) => i.y < H - 20 || (i.kind !== "scoop" && i.kind !== "gold" && i.kind !== "rainbow" && i.y < H + i.size));
    if (this.state === "start" || this.state === "play") this._checkCatches(players, t);
    this._updateHover(players, t);

    this._drawBackground(t);
    this._drawItems(dt, t);
    for (const p of players) this._drawPlayer(p, t);
    this._drawScreen(players, t);
    this._drawButtons(t);
    this._drawPopups(t);
    this.confetti.draw(this.ctx, dt, H);
  }

  /** Keyboard helpers. */
  key(k) {
    sound.unlock();
    if (k === " " && (this.state === "start" || this.state === "over")) this._press(this.mode);
    else if ((k === "q" || k === "Q") && this.state === "play") this._endRound();
  }
}
