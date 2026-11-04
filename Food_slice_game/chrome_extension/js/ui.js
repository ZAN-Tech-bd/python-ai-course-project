// Kid-friendly drawing helpers: bubbly pill labels, rainbow title, stars and confetti.
// Port of ui.py. All colors here are RGB.

export const INK = [40, 50, 90];
export const RAINBOW = [[255, 70, 70], [255, 150, 40], [255, 220, 40], [80, 200, 80],
                        [60, 170, 255], [90, 90, 230], [190, 90, 220]];
const CONFETTI = [[240, 50, 50], [255, 150, 0], [255, 230, 0], [60, 200, 60],
                  [40, 110, 230], [160, 80, 220], [255, 105, 180]];

export const FONT_FAMILY = '"Fredoka", "Comic Sans MS", "Chalkboard SE", sans-serif';
export const font = (px) => `700 ${px}px ${FONT_FAMILY}`;
export const rgb = (c, a = 1) => `rgba(${c[0]},${c[1]},${c[2]},${a})`;
export const rand = (a, b) => a + Math.random() * (b - a);
export const choice = (arr) => arr[Math.floor(Math.random() * arr.length)];

export function makeCanvas(w, h) {
  const c = document.createElement("canvas");
  c.width = Math.max(1, Math.ceil(w));
  c.height = Math.max(1, Math.ceil(h));
  return c;
}

export function textColorFor(fill) {
  const lum = 0.299 * fill[0] + 0.587 * fill[1] + 0.114 * fill[2];
  return lum > 150 ? INK : [255, 255, 255];
}

export function starPoints(cx, cy, rOut, rotDeg = -90) {
  const pts = [];
  for (let i = 0; i < 10; i++) {
    const r = i % 2 === 0 ? rOut : rOut * 0.45;
    const a = (rotDeg + i * 36) * Math.PI / 180;
    pts.push([cx + r * Math.cos(a), cy + r * Math.sin(a)]);
  }
  return pts;
}

export function pathPoly(ctx, pts) {
  ctx.beginPath();
  ctx.moveTo(pts[0][0], pts[0][1]);
  for (let i = 1; i < pts.length; i++) ctx.lineTo(pts[i][0], pts[i][1]);
  ctx.closePath();
}

function roundRectPath(ctx, x, y, w, h, r) {
  r = Math.min(r, w / 2, h / 2);
  ctx.beginPath();
  ctx.moveTo(x + r, y);
  ctx.arcTo(x + w, y, x + w, y + h, r);
  ctx.arcTo(x + w, y + h, x, y + h, r);
  ctx.arcTo(x, y + h, x, y, r);
  ctx.arcTo(x, y, x + w, y, r);
  ctx.closePath();
}
export { roundRectPath };

const pillCache = new Map();

/** A rounded "bubble" with text, returned as a canvas. Cached by (text, size, color). */
export function renderPill(text, px, fill, textRgb = null) {
  const key = `${text}|${px}|${fill}|${textRgb}`;
  const hit = pillCache.get(key);
  if (hit) return hit;

  const m = makeCanvas(1, 1).getContext("2d");
  m.font = font(px);
  const tm = m.measureText(text);
  const ascent = tm.actualBoundingBoxAscent;
  const descent = tm.actualBoundingBoxDescent;
  const textW = tm.actualBoundingBoxLeft + tm.actualBoundingBoxRight;
  const padX = Math.round(px * 0.9), padY = Math.round(px * 0.45);
  const w = Math.round(textW + 2 * padX), h = Math.round(ascent + descent + 2 * padY);
  const shadow = Math.max(2, Math.floor(px / 10));
  const border = Math.max(2, Math.floor(px / 9));

  const c = makeCanvas(w + shadow, h + shadow);
  const ctx = c.getContext("2d");
  roundRectPath(ctx, shadow, shadow, w, h, h / 2);
  ctx.fillStyle = "rgba(0,0,0,0.24)";
  ctx.fill();
  roundRectPath(ctx, border / 2, border / 2, w - border, h - border, (h - border) / 2);
  ctx.fillStyle = rgb(fill, 0.94);
  ctx.fill();
  ctx.lineWidth = border;
  ctx.strokeStyle = "#fff";
  ctx.stroke();

  ctx.font = font(px);
  ctx.fillStyle = rgb(textRgb || textColorFor(fill));
  ctx.textBaseline = "alphabetic";
  ctx.fillText(text, padX + tm.actualBoundingBoxLeft, padY + ascent);

  if (pillCache.size > 200) pillCache.clear();
  pillCache.set(key, c);
  return c;
}

const titleCache = new Map();

/** Big bubbly title: each letter a rainbow color with a white outline and soft shadow. */
export function rainbowTitle(text, px) {
  const key = `${text}|${px}`;
  if (titleCache.has(key)) return titleCache.get(key);

  const stroke = Math.max(3, Math.floor(px / 12));
  const m = makeCanvas(1, 1).getContext("2d");
  m.font = font(px);
  const width = Math.ceil(m.measureText(text).width) + 2 * stroke + 12;
  const height = Math.ceil(px * 1.3) + 2 * stroke;

  const c = makeCanvas(width, height);
  const ctx = c.getContext("2d");
  ctx.font = font(px);
  ctx.textBaseline = "top";
  ctx.lineJoin = "round";
  ctx.lineWidth = stroke * 2;

  let x = stroke + 4, i = 0;
  for (const ch of text) {
    const w = ctx.measureText(ch).width;
    if (ch.trim()) {
      const color = RAINBOW[i++ % RAINBOW.length];
      ctx.strokeStyle = ctx.fillStyle = "rgba(0,0,0,0.27)";
      ctx.strokeText(ch, x + 4, stroke + 5);
      ctx.fillText(ch, x + 4, stroke + 5);
      ctx.strokeStyle = "#fff";
      ctx.strokeText(ch, x, stroke);
      ctx.fillStyle = rgb(color);
      ctx.fillText(ch, x, stroke);
    }
    x += w;
  }
  titleCache.set(key, c);
  return c;
}

/** Falling stars, used to celebrate the end of a round. */
export class Confetti {
  constructor() {
    this.parts = [];
  }

  burst(width, height, count = 70) {
    for (let i = 0; i < count; i++) {
      this.parts.push({
        x: rand(0, width), y: rand(-height * 0.4, 0),
        vx: rand(-60, 60), vy: rand(180, 380),
        r: rand(9, 18), rot: rand(0, 360), spin: rand(-240, 240),
        color: choice(CONFETTI),
      });
    }
  }

  draw(ctx, dt, height) {
    if (!this.parts.length) return;
    const alive = [];
    for (const p of this.parts) {
      p.x += p.vx * dt;
      p.y += p.vy * dt;
      p.rot += p.spin * dt;
      if (p.y - p.r > height) continue;
      pathPoly(ctx, starPoints(p.x, p.y, p.r, p.rot));
      ctx.fillStyle = rgb(p.color);
      ctx.fill();
      alive.push(p);
    }
    this.parts = alive;
  }
}
