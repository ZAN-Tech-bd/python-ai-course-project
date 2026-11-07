// Cartoon ice cream sprites drawn on canvases and cached. Port of sprites.py plus new power-ups.
import { makeCanvas, pathPoly, rgb, starPoints } from "./ui.js";

const OUTLINE = [90, 55, 50];

// name, scoop color (RGB)
export const FLAVORS = [
  ["Strawberry", [255, 150, 185]],
  ["Vanilla", [255, 243, 205]],
  ["Chocolate", [150, 90, 60]],
  ["Mint", [150, 232, 195]],
  ["Blueberry", [150, 165, 255]],
  ["Mango", [255, 195, 70]],
];
export const GOLD = -1, RAINBOW = -2;
const GOLD_RGB = [255, 205, 40];
const RAINBOW_STRIPES = ["#ff6b6b", "#ffa94d", "#ffe066", "#8ce99a", "#74c0fc", "#b197fc"];

const cache = new Map();
const bucket = (size) => Math.max(8, Math.round(size / 6) * 6);

function cached(key, w, h, draw) {
  if (cache.has(key)) return cache.get(key);
  const c = makeCanvas(w, h);
  const ctx = c.getContext("2d");
  ctx.lineJoin = ctx.lineCap = "round";
  draw(ctx, w, h);
  if (cache.size > 400) cache.clear();
  cache.set(key, c);
  return c;
}

function circle(ctx, x, y, r, fill) {
  ctx.beginPath();
  ctx.arc(x, y, Math.max(0.5, r), 0, Math.PI * 2);
  ctx.fillStyle = fill;
  ctx.fill();
}

/** Union of circles with a cartoon outline. Circles are in 0..1 units of size S. */
function blob(ctx, S, circles, fill) {
  const edge = Math.max(2, S * 0.03);
  for (const [x, y, r] of circles) circle(ctx, x * S, y * S, r * S, rgb(OUTLINE));
  for (const [x, y, r] of circles) circle(ctx, x * S, y * S, r * S - edge, fill);
}

const SCOOP_SHAPE = [[0.5, 0.44, 0.38], [0.22, 0.66, 0.13], [0.42, 0.72, 0.13], [0.62, 0.72, 0.13], [0.8, 0.64, 0.12]];

/** flavor = index into FLAVORS, GOLD or RAINBOW */
export function scoopSprite(flavor, size, face = false) {
  const s = bucket(size);
  return cached(`scoop|${flavor}|${s}|${face}`, s, s, (ctx, S) => {
    if (flavor === RAINBOW) {
      blob(ctx, S, SCOOP_SHAPE, "#fff");
      ctx.save();
      ctx.beginPath();
      for (const [x, y, r] of SCOOP_SHAPE) { ctx.moveTo(x * S + r * S, y * S); ctx.arc(x * S, y * S, r * S - S * 0.03, 0, Math.PI * 2); }
      ctx.clip();
      RAINBOW_STRIPES.forEach((c, i) => {
        ctx.fillStyle = c;
        ctx.fillRect(0, S * (0.05 + i * 0.14), S, S * 0.15);
      });
      ctx.restore();
    } else {
      const color = flavor === GOLD ? GOLD_RGB : FLAVORS[flavor][1];
      blob(ctx, S, SCOOP_SHAPE, rgb(color));
    }
    circle(ctx, 0.37 * S, 0.3 * S, 0.07 * S, "rgba(255,255,255,0.5)");
    const name = flavor >= 0 ? FLAVORS[flavor][0] : "";
    if (name === "Mint") {
      for (const [x, y] of [[0.55, 0.35], [0.4, 0.55], [0.66, 0.55], [0.3, 0.42], [0.52, 0.62]]) {
        circle(ctx, x * S, y * S, 0.025 * S, "rgb(70,45,35)");
      }
    } else if (name === "Vanilla" || name === "Blueberry") {
      const cols = ["#ff5a78", "#50b4ff", "#78d25a", "#ffc832", "#be6ee6"];
      ctx.lineWidth = Math.max(2, S * 0.03);
      [[0.55, 0.3], [0.38, 0.52], [0.65, 0.5], [0.5, 0.62], [0.3, 0.4]].forEach(([x, y], i) => {
        ctx.strokeStyle = cols[i];
        ctx.beginPath();
        ctx.moveTo((x - 0.03) * S, y * S);
        ctx.lineTo((x + 0.03) * S, (y - 0.02) * S);
        ctx.stroke();
      });
    }
    if (face) { // a happy little face on falling scoops
      circle(ctx, 0.41 * S, 0.47 * S, 0.035 * S, "#3a2a2a");
      circle(ctx, 0.59 * S, 0.47 * S, 0.035 * S, "#3a2a2a");
      circle(ctx, 0.33 * S, 0.55 * S, 0.04 * S, "rgba(255,90,120,0.45)");
      circle(ctx, 0.67 * S, 0.55 * S, 0.04 * S, "rgba(255,90,120,0.45)");
      ctx.lineWidth = Math.max(2, S * 0.025);
      ctx.strokeStyle = "#3a2a2a";
      ctx.beginPath();
      ctx.arc(0.5 * S, 0.53 * S, 0.06 * S, 0.15 * Math.PI, 0.85 * Math.PI);
      ctx.stroke();
    }
    if (flavor === GOLD) {
      pathPoly(ctx, starPoints(0.5 * S, 0.44 * S, 0.17 * S));
      ctx.fillStyle = "rgb(255,250,220)";
      ctx.fill();
    } else {
      circle(ctx, 0.5 * S, 0.08 * S, 0.075 * S, rgb(OUTLINE)); // cherry on top
      circle(ctx, 0.5 * S, 0.08 * S, 0.06 * S, "rgb(230,30,50)");
    }
  });
}

export function coneSprite(width) {
  const w = bucket(width), h = Math.round(w * 1.15);
  return cached(`cone|${w}`, w, h, (ctx) => {
    const P = (x, y) => [x * w, y * h];
    pathPoly(ctx, [P(0.08, 0.04), P(0.92, 0.04), P(0.5, 0.98)]);
    ctx.fillStyle = rgb(OUTLINE);
    ctx.fill();
    const inner = [P(0.13, 0.06), P(0.87, 0.06), P(0.5, 0.93)];
    pathPoly(ctx, inner);
    ctx.fillStyle = "rgb(235,175,95)";
    ctx.fill();
    ctx.save();
    pathPoly(ctx, inner);
    ctx.clip();
    ctx.strokeStyle = "rgb(200,135,65)";
    ctx.lineWidth = Math.max(2, w * 0.035);
    for (let i = -6; i < 10; i++) {
      const off = i * 0.14;
      ctx.beginPath(); ctx.moveTo(off * w, 0); ctx.lineTo((off + 1) * w, h); ctx.stroke();
      ctx.beginPath(); ctx.moveTo((off + 1) * w, 0); ctx.lineTo(off * w, h); ctx.stroke();
    }
    ctx.restore();
    ctx.fillStyle = "rgb(215,150,75)";
    ctx.strokeStyle = rgb(OUTLINE);
    ctx.lineWidth = Math.max(2, w * 0.03);
    ctx.beginPath();
    ctx.roundRect(0.06 * w, 0.005 * h, 0.88 * w, 0.09 * h, 0.03 * w);
    ctx.fill();
    ctx.stroke();
  });
}

export function broccoliSprite(size) {
  const s = bucket(size);
  return cached(`broc|${s}`, s, s, (ctx, S) => {
    const P = (x, y) => [x * S, y * S];
    pathPoly(ctx, [P(0.38, 0.5), P(0.62, 0.5), P(0.58, 0.95), P(0.42, 0.95)]);
    ctx.fillStyle = "rgb(165,210,110)";
    ctx.fill();
    ctx.lineWidth = Math.max(2, S * 0.03);
    ctx.strokeStyle = rgb(OUTLINE);
    ctx.stroke();
    blob(ctx, S, [[0.28, 0.42, 0.18], [0.5, 0.3, 0.22], [0.72, 0.42, 0.18], [0.38, 0.5, 0.14], [0.62, 0.5, 0.14]],
         "rgb(70,160,70)");
    for (const [x, y] of [[0.4, 0.22], [0.62, 0.25], [0.28, 0.42], [0.72, 0.45]]) {
      circle(ctx, x * S, y * S, 0.035 * S, "rgb(50,125,55)");
    }
    // a grumpy face
    circle(ctx, 0.43 * S, 0.38 * S, 0.03 * S, "#282828");
    circle(ctx, 0.57 * S, 0.38 * S, 0.03 * S, "#282828");
    ctx.strokeStyle = "#282828";
    ctx.beginPath();
    ctx.arc(0.5 * S, 0.53 * S, 0.07 * S, 1.15 * Math.PI, 1.85 * Math.PI);
    ctx.stroke();
  });
}

/** Freeze power-up: an icy blue snowflake in a bubble. */
export function snowflakeSprite(size) {
  const s = bucket(size);
  return cached(`snow|${s}`, s, s, (ctx, S) => {
    circle(ctx, S / 2, S / 2, S * 0.44, "rgba(200,235,255,0.85)");
    ctx.lineWidth = Math.max(2, S * 0.03);
    ctx.strokeStyle = "#fff";
    ctx.stroke();
    ctx.strokeStyle = "rgb(60,150,230)";
    ctx.lineWidth = Math.max(2, S * 0.05);
    for (let i = 0; i < 6; i++) {
      const a = (i * Math.PI) / 3;
      const ex = S / 2 + Math.cos(a) * S * 0.32, ey = S / 2 + Math.sin(a) * S * 0.32;
      ctx.beginPath(); ctx.moveTo(S / 2, S / 2); ctx.lineTo(ex, ey); ctx.stroke();
      for (const side of [-1, 1]) {
        const mx = S / 2 + Math.cos(a) * S * 0.2, my = S / 2 + Math.sin(a) * S * 0.2;
        const b = a + side * 0.7;
        ctx.beginPath(); ctx.moveTo(mx, my); ctx.lineTo(mx + Math.cos(b) * S * 0.1, my + Math.sin(b) * S * 0.1); ctx.stroke();
      }
    }
    circle(ctx, S * 0.34, S * 0.3, S * 0.06, "rgba(255,255,255,0.8)");
  });
}

export function sparkleSprite(size) {
  const s = bucket(size);
  return cached(`sparkle|${s}`, s, s, (ctx, S) => {
    for (let i = 0; i < 6; i++) {
      const a = (i * 60 * Math.PI) / 180;
      pathPoly(ctx, starPoints((0.5 + 0.38 * Math.cos(a)) * S, (0.5 + 0.38 * Math.sin(a)) * S, 0.09 * S));
      ctx.fillStyle = "rgb(255,240,120)";
      ctx.fill();
    }
  });
}

/** A melted puddle left where a scoop hit the ground. */
export function splatSprite(flavor, size) {
  const s = bucket(size);
  return cached(`splat|${flavor}|${s}`, s, Math.round(s * 0.45), (ctx, S, H) => {
    const color = flavor === GOLD ? GOLD_RGB : flavor === RAINBOW ? [255, 160, 220] : FLAVORS[flavor][1];
    const blobs = [[0.5, 0.6, 0.3], [0.25, 0.7, 0.16], [0.75, 0.68, 0.17], [0.1, 0.8, 0.07], [0.9, 0.82, 0.06]];
    for (const [x, y, r] of blobs) {
      ctx.beginPath();
      ctx.ellipse(x * S, y * H, r * S + 2, r * H * 1.2 + 2, 0, 0, Math.PI * 2);
      ctx.fillStyle = rgb(OUTLINE);
      ctx.fill();
    }
    for (const [x, y, r] of blobs) {
      ctx.beginPath();
      ctx.ellipse(x * S, y * H, r * S, r * H * 1.2, 0, 0, Math.PI * 2);
      ctx.fillStyle = rgb(color);
      ctx.fill();
    }
  });
}

/** Animal ears worn on each player's head (drawn around the cone). width ~ face width. */
export function earsSprite(style, width, color) {
  const w = bucket(width), h = Math.round(w * 0.9);
  return cached(`ears|${style}|${w}|${color}`, w, h, (ctx) => {
    const line = Math.max(2, w * 0.035);
    const out = rgb(OUTLINE);
    const fur = rgb(color);
    const pink = "rgb(255,190,210)";
    ctx.lineWidth = line;
    ctx.strokeStyle = out;
    const ellipse = (x, y, rx, ry, rot, fill) => {
      ctx.beginPath();
      ctx.ellipse(x * w, y * h, rx * w, ry * h, rot, 0, Math.PI * 2);
      ctx.fillStyle = fill;
      ctx.fill();
      ctx.stroke();
    };
    const tri = (pts, fill) => {
      pathPoly(ctx, pts.map(([x, y]) => [x * w, y * h]));
      ctx.fillStyle = fill;
      ctx.fill();
      ctx.stroke();
    };
    for (const side of [-1, 1]) {
      const cx = 0.5 + side * 0.36;
      switch (style) {
        case "bunny":
          ellipse(cx, 0.42, 0.11, 0.4, side * 0.2, fur);
          ellipse(cx, 0.46, 0.055, 0.28, side * 0.2, pink);
          break;
        case "kitty":
          tri([[cx - 0.15, 0.95], [cx + side * 0.05, 0.4], [cx + 0.15, 0.95]], fur);
          tri([[cx - 0.08, 0.92], [cx + side * 0.04, 0.58], [cx + 0.08, 0.92]], pink);
          break;
        case "puppy":
          ellipse(cx + side * 0.06, 0.82, 0.11, 0.22, side * -0.5, "rgb(150,100,70)");
          break;
        case "froggy":
          ellipse(cx - side * 0.08, 0.78, 0.14, 0.15, 0, fur);
          ellipse(cx - side * 0.08, 0.78, 0.08, 0.09, 0, "#fff");
          ctx.beginPath();
          ctx.arc((cx - side * 0.08) * w, 0.8 * h, 0.04 * w, 0, Math.PI * 2);
          ctx.fillStyle = "#222";
          ctx.fill();
          break;
        case "panda":
          ellipse(cx, 0.8, 0.12, 0.13, 0, "#2a2a2a");
          break;
        case "tiger":
          ellipse(cx, 0.8, 0.13, 0.14, 0, fur);
          ellipse(cx, 0.82, 0.065, 0.07, 0, "#2a2a2a");
          break;
      }
    }
  });
}
