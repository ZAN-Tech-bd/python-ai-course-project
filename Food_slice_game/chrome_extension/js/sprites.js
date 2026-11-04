// Cartoon food, bomb and heart sprites drawn with Canvas 2D. Port of the _Pen sprites in main.py.
// Every sprite is drawn at 2x on a square using 0..1 coordinates, then scaled down for smooth edges.

import { makeCanvas, pathPoly, rgb, starPoints } from "./ui.js";

const OUTLINE = [70, 45, 50];

// Small seeded RNG so the kiwi seeds and donut sprinkles look the same every time.
function seeded(seed) {
  let s = seed >>> 0 || 1;
  return () => {
    s = (s * 1664525 + 1013904223) >>> 0;
    return s / 4294967296;
  };
}

class Pen {
  constructor(size) {
    this.size = size;
    this.S = size * 2;
    this.canvas = makeCanvas(this.S, this.S);
    this.d = this.canvas.getContext("2d");
    this.w = Math.max(2, Math.floor(this.S * 0.025));
    this.d.lineCap = "round";
    this.d.lineJoin = "round";
  }

  p(x, y) { return [x * this.S, y * this.S]; }

  disk(cx, cy, r, color) {
    if (r <= 0) return;
    const S = this.S;
    this.d.beginPath();
    this.d.arc(cx * S, cy * S, r * S, 0, Math.PI * 2);
    this.d.fillStyle = Array.isArray(color) ? rgb(color, color[3] !== undefined ? color[3] / 255 : 1) : color;
    this.d.fill();
  }

  /** Filled circle with an optional cartoon outline drawn just inside its edge (like PIL). */
  circle(cx, cy, r, fill, outline = null, width = null) {
    const wPx = width === null ? this.w : width;
    if (outline && wPx > 0) {
      this.disk(cx, cy, r, outline);
      if (fill) this.disk(cx, cy, r - wPx / this.S, fill);
    } else if (fill) {
      this.disk(cx, cy, r, fill);
    }
  }

  ellipse(cx, cy, rx, ry, fill) {
    const S = this.S;
    this.d.beginPath();
    this.d.ellipse(cx * S, cy * S, rx * S, ry * S, 0, 0, Math.PI * 2);
    this.d.fillStyle = rgb(fill, fill[3] !== undefined ? fill[3] / 255 : 1);
    this.d.fill();
  }

  /** Union of circles with a cartoon outline: outline color first, then the fill slightly inside. */
  blob(circles, fill, inset = 0) {
    const edge = this.w / this.S;
    if (inset === 0) for (const [cx, cy, r] of circles) this.disk(cx, cy, r, OUTLINE);
    for (const [cx, cy, r] of circles) this.disk(cx, cy, r - edge - inset, fill);
  }

  line(points, color, width) {
    this.d.beginPath();
    this.d.moveTo(...this.p(...points[0]));
    for (let i = 1; i < points.length; i++) this.d.lineTo(...this.p(...points[i]));
    this.d.strokeStyle = rgb(color);
    this.d.lineWidth = width;
    this.d.stroke();
  }

  polygon(ptsPx, fill, outline = null) {
    pathPoly(this.d, ptsPx);
    this.d.fillStyle = rgb(fill);
    this.d.fill();
    if (outline) {
      this.d.strokeStyle = rgb(outline);
      this.d.lineWidth = 2;
      this.d.stroke();
    }
  }

  shine(cx = 0.36, cy = 0.32, r = 0.08) {
    this.ellipse(cx, cy, r, r * 0.65, [255, 255, 255, 110]);
  }

  done() {
    const out = makeCanvas(this.size, this.size);
    const ctx = out.getContext("2d");
    ctx.imageSmoothingEnabled = true;
    ctx.imageSmoothingQuality = "high";
    ctx.drawImage(this.canvas, 0, 0, this.size, this.size);
    return out;
  }
}

// ---------------------------------------------------------------- foods
function watermelon(pen, cut) {
  pen.circle(0.5, 0.5, 0.46, [70, 170, 70], OUTLINE);
  if (!cut) {
    for (const dx of [-0.24, -0.08, 0.08, 0.24]) {
      const hh = Math.sqrt(0.43 ** 2 - dx ** 2) * 0.92;
      pen.ellipse(0.5 + dx, 0.5, 0.035, hh, [40, 120, 50]);
    }
    pen.shine();
    return;
  }
  pen.circle(0.5, 0.5, 0.40, [235, 250, 220]);
  pen.circle(0.5, 0.5, 0.36, [240, 70, 85]);
  for (let i = 0; i < 8; i++) {
    const a = (i * 45 + 20) * Math.PI / 180;
    pen.ellipse(0.5 + 0.21 * Math.cos(a), 0.5 + 0.21 * Math.sin(a), 0.022, 0.035, [40, 30, 30]);
  }
  for (let i = 0; i < 4; i++) {
    const a = (i * 90 + 45) * Math.PI / 180;
    pen.ellipse(0.5 + 0.09 * Math.cos(a), 0.5 + 0.09 * Math.sin(a), 0.022, 0.035, [40, 30, 30]);
  }
}

function orange(pen, cut) {
  pen.circle(0.5, 0.53, 0.43, [255, 150, 30], OUTLINE);
  if (!cut) {
    for (const [x, y] of [[0.35, 0.6], [0.6, 0.42], [0.65, 0.7], [0.45, 0.78], [0.72, 0.55], [0.3, 0.45]]) {
      pen.circle(x, y, 0.018, [255, 185, 90]);
    }
    pen.ellipse(0.62, 0.1, 0.11, 0.05, [80, 170, 60]);
    pen.shine(0.36, 0.38);
    return;
  }
  pen.circle(0.5, 0.53, 0.38, [255, 240, 200]);
  const [cx, cy] = pen.p(0.5, 0.53);
  const r = 0.34 * pen.S;
  for (let i = 0; i < 8; i++) {
    const a0 = (i * 45 + 4) * Math.PI / 180, a1 = ((i + 1) * 45 - 4) * Math.PI / 180;
    pen.d.beginPath();
    pen.d.moveTo(cx, cy);
    pen.d.arc(cx, cy, r, a0, a1);
    pen.d.closePath();
    pen.d.fillStyle = rgb([255, 175, 50]);
    pen.d.fill();
  }
  pen.circle(0.5, 0.53, 0.04, [255, 240, 200]);
}

function apple(pen, cut) {
  pen.blob([[0.38, 0.56, 0.32], [0.62, 0.56, 0.32]], [230, 40, 55]);
  pen.line([[0.5, 0.3], [0.54, 0.1]], [110, 70, 40], pen.w * 2);
  if (!cut) {
    pen.polygon([pen.p(0.54, 0.18), pen.p(0.68, 0.07), pen.p(0.78, 0.1), pen.p(0.64, 0.2)],
                [80, 180, 60], OUTLINE);
    pen.shine(0.3, 0.45);
    return;
  }
  pen.blob([[0.38, 0.57, 0.27], [0.62, 0.57, 0.27]], [255, 240, 200], 0.0001);
  pen.ellipse(0.46, 0.57, 0.025, 0.045, [110, 60, 30]);
  pen.ellipse(0.54, 0.57, 0.025, 0.045, [110, 60, 30]);
}

function kiwi(pen, cut) {
  pen.circle(0.5, 0.5, 0.42, [150, 105, 60], OUTLINE);
  if (!cut) {
    const rnd = seeded(7);
    for (let i = 0; i < 26; i++) {
      const a = rnd() * Math.PI * 2, rr = rnd() * 0.36;
      pen.circle(0.5 + rr * Math.cos(a), 0.5 + rr * Math.sin(a), 0.012, [115, 80, 45]);
    }
    pen.shine();
    return;
  }
  pen.circle(0.5, 0.5, 0.37, [130, 205, 60]);
  pen.circle(0.5, 0.5, 0.15, [240, 248, 205]);
  for (let i = 0; i < 14; i++) {
    const a = (i * 360 / 14) * Math.PI / 180;
    pen.ellipse(0.5 + 0.22 * Math.cos(a), 0.5 + 0.22 * Math.sin(a), 0.016, 0.016, [30, 30, 30]);
  }
}

function donut(pen, _cut) {
  pen.circle(0.5, 0.5, 0.45, [215, 160, 90], OUTLINE);
  pen.circle(0.5, 0.48, 0.38, [255, 120, 185]);
  const rnd = seeded(3);
  const colors = [[255, 255, 255], [80, 200, 255], [255, 220, 40], [120, 220, 120], [180, 120, 255]];
  for (let i = 0; i < 18; i++) {
    const a = rnd() * Math.PI * 2, rr = 0.2 + rnd() * 0.13;
    const x = 0.5 + rr * Math.cos(a), y = 0.48 + rr * Math.sin(a);
    const t = rnd() * Math.PI;
    pen.line([[x - 0.03 * Math.cos(t), y - 0.03 * Math.sin(t)], [x + 0.03 * Math.cos(t), y + 0.03 * Math.sin(t)]],
             colors[Math.floor(rnd() * colors.length)], pen.w);
  }
  // the hole: outline ring, then punch the middle out so the camera shows through
  pen.disk(0.5, 0.5, 0.13, OUTLINE);
  pen.d.globalCompositeOperation = "destination-out";
  pen.disk(0.5, 0.5, 0.13 - pen.w / pen.S, "#000");
  pen.d.globalCompositeOperation = "source-over";
}

function strawberry(pen, cut) {
  pen.blob([[0.33, 0.4, 0.22], [0.67, 0.4, 0.22], [0.5, 0.55, 0.3], [0.5, 0.72, 0.18]], [235, 50, 70]);
  if (cut) {
    pen.blob([[0.36, 0.42, 0.16], [0.64, 0.42, 0.16], [0.5, 0.56, 0.23], [0.5, 0.7, 0.12]],
             [255, 150, 165], 0.0001);
    pen.ellipse(0.5, 0.52, 0.08, 0.17, [255, 215, 220]);
  } else {
    for (const [x, y] of [[0.32, 0.42], [0.5, 0.42], [0.68, 0.42], [0.4, 0.57], [0.6, 0.57], [0.5, 0.72],
                          [0.28, 0.32], [0.72, 0.32]]) {
      pen.ellipse(x, y, 0.015, 0.024, [255, 230, 120]);
    }
    pen.shine(0.3, 0.35, 0.06);
  }
  pen.polygon(starPoints(0.5 * pen.S, 0.2 * pen.S, 0.17 * pen.S), [70, 175, 60], OUTLINE);
}

function bomb(pen) {
  pen.line([[0.5, 0.17], [0.58, 0.08], [0.68, 0.1]], [150, 110, 70], pen.w * 2);
  pen.polygon(starPoints(0.72 * pen.S, 0.09 * pen.S, 0.08 * pen.S), [255, 210, 40]);
  const [x0, y0] = pen.p(0.42, 0.14), [x1, y1] = pen.p(0.58, 0.24);
  pen.d.fillStyle = rgb([120, 120, 140]);
  pen.d.fillRect(x0, y0, x1 - x0, y1 - y0);
  pen.d.strokeStyle = rgb(OUTLINE);
  pen.d.lineWidth = pen.w;
  pen.d.strokeRect(x0 + pen.w / 2, y0 + pen.w / 2, x1 - x0 - pen.w, y1 - y0 - pen.w);
  pen.circle(0.5, 0.58, 0.38, [45, 45, 60], [20, 20, 25]);
  pen.shine(0.36, 0.44, 0.09);
}

// name, draw function, juice color (RGB)
export const FOODS = [
  ["watermelon", watermelon, [240, 70, 85]],
  ["orange", orange, [255, 150, 30]],
  ["apple", apple, [255, 225, 170]],
  ["kiwi", kiwi, [130, 205, 60]],
  ["donut", donut, [255, 120, 185]],
  ["strawberry", strawberry, [235, 60, 90]],
];

const cache = new Map();
function cached(key, make) {
  if (!cache.has(key)) cache.set(key, make());
  return cache.get(key);
}

/** [whole, leftHalf, rightHalf]. Halves keep the full square so they rotate around the same center. */
export function foodSprites(index, size) {
  return cached(`food|${index}|${size}`, () => {
    const draw = FOODS[index][1];
    const whole = new Pen(size);
    draw(whole, false);
    const cutPen = new Pen(size);
    draw(cutPen, true);
    const cutImg = cutPen.done();
    const half = (keepLeft) => {
      const c = makeCanvas(size, size);
      const ctx = c.getContext("2d");
      const hw = Math.floor(size / 2);
      if (keepLeft) ctx.drawImage(cutImg, 0, 0, hw, size, 0, 0, hw, size);
      else ctx.drawImage(cutImg, hw, 0, size - hw, size, hw, 0, size - hw, size);
      return c;
    };
    return [whole.done(), half(true), half(false)];
  });
}

export function bombSprite(size) {
  return cached(`bomb|${size}`, () => {
    const pen = new Pen(size);
    bomb(pen);
    return pen.done();
  });
}

export function heartSprite(size, full) {
  return cached(`heart|${size}|${full}`, () => {
    const pen = new Pen(size);
    const fill = full ? [255, 70, 100] : [210, 210, 220];
    pen.blob([[0.32, 0.38, 0.22], [0.68, 0.38, 0.22]], fill);
    pen.polygon([pen.p(0.13, 0.45), pen.p(0.87, 0.45), pen.p(0.5, 0.9)], OUTLINE);
    pen.polygon([pen.p(0.17, 0.46), pen.p(0.83, 0.46), pen.p(0.5, 0.84)], fill);
    if (full) pen.shine(0.3, 0.3, 0.06);
    return pen.done();
  });
}
