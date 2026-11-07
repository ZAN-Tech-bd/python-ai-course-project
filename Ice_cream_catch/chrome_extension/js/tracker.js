// Webcam + MediaPipe Face Detector (bundled, works offline) and stable player tracking.
// Port of faces.py.
import { FaceDetector, FilesetResolver } from "../vendor/mediapipe/vision_bundle.mjs";

const WASM_DIR = new URL("../vendor/mediapipe/wasm", import.meta.url).href;
const MODEL_URL = new URL("../models/blaze_face_short_range.tflite", import.meta.url).href;

// name, RGB color, ear style - one per player, in the order kids join
export const PLAYER_STYLES = [
  { name: "Bunny", color: [255, 120, 170], ears: "bunny" },
  { name: "Kitty", color: [255, 160, 60], ears: "kitty" },
  { name: "Puppy", color: [80, 160, 255], ears: "puppy" },
  { name: "Froggy", color: [90, 200, 90], ears: "froggy" },
  { name: "Panda", color: [170, 110, 230], ears: "panda" },
  { name: "Tiger", color: [255, 210, 50], ears: "tiger" },
];
const ACTIVE_TIME = 0.5; // a player whose face was seen this recently is "here"
const now = () => performance.now() / 1000;

export class CameraError extends Error {
  constructor(kind, message) {
    super(message);
    this.kind = kind; // "denied" | "missing" | "busy" | "other"
  }
}

export class FaceTracker {
  constructor(video) {
    this.video = video;
    this.detector = null;
    this.stream = null;
    this.lastVideoTime = -1;
    this.faces = [];
  }

  async loadModel() {
    const fileset = await FilesetResolver.forVisionTasks(WASM_DIR);
    const options = (delegate) => ({
      baseOptions: { modelAssetPath: MODEL_URL, delegate },
      runningMode: "VIDEO",
      minDetectionConfidence: 0.5,
      minSuppressionThreshold: 0.3,
    });
    try {
      this.detector = await FaceDetector.createFromOptions(fileset, options("GPU"));
    } catch (err) {
      console.warn("GPU face detection unavailable, using CPU:", err);
      this.detector = await FaceDetector.createFromOptions(fileset, options("CPU"));
    }
  }

  async startCamera() {
    if (!navigator.mediaDevices?.getUserMedia) {
      throw new CameraError("missing", "This browser can't use a webcam.");
    }
    try {
      this.stream = await navigator.mediaDevices.getUserMedia({
        video: { width: { ideal: 1280 }, height: { ideal: 720 }, facingMode: "user" },
        audio: false,
      });
    } catch (err) {
      const name = err?.name || "";
      if (name === "NotAllowedError" || name === "SecurityError") throw new CameraError("denied", err.message);
      if (name === "NotFoundError" || name === "OverconstrainedError") throw new CameraError("missing", err.message);
      if (name === "NotReadableError" || name === "AbortError") throw new CameraError("busy", err.message);
      throw new CameraError("other", err?.message || String(err));
    }
    this.video.srcObject = this.stream;
    await this.video.play();
    if (!this.video.videoWidth) {
      await new Promise((resolve) => this.video.addEventListener("loadeddata", resolve, { once: true }));
    }
  }

  get ready() {
    return !!(this.detector && this.stream && this.video.readyState >= 2);
  }

  /** Face boxes in normalized *camera* coords [{x, y, w, h}] (not mirrored). */
  detect(nowMs) {
    if (!this.ready) return [];
    if (this.video.currentTime !== this.lastVideoTime) {
      this.lastVideoTime = this.video.currentTime;
      try {
        const res = this.detector.detectForVideo(this.video, nowMs);
        const vw = this.video.videoWidth, vh = this.video.videoHeight;
        this.faces = (res.detections || []).map((d) => {
          const b = d.boundingBox;
          return { x: b.originX / vw, y: b.originY / vh, w: b.width / vw, h: b.height / vh };
        });
      } catch (err) {
        console.warn("face detection failed for a frame:", err);
        this.faces = [];
      }
    }
    return this.faces;
  }

  stop() {
    this.stream?.getTracks().forEach((t) => t.stop());
    this.detector?.close();
  }
}

export class Player {
  constructor(slot, box) {
    this.slot = slot;
    Object.assign(this, PLAYER_STYLES[slot]);
    ({ x: this.x, y: this.y, w: this.w, h: this.h } = box);
    this.score = 0;
    this.stack = [];      // flavor indexes of scoops balanced on the cone
    this.streak = 0;      // catches in a row without broccoli
    this.bigUntil = 0;    // rainbow power-up: giant cone until this time
    this.lastSeen = now();
    this.joined = now();
  }

  update(box, smooth = 0.55) {
    this.x += (box.x - this.x) * smooth;
    this.y += (box.y - this.y) * smooth;
    this.w += (box.w - this.w) * smooth;
    this.h += (box.h - this.h) * smooth;
    this.lastSeen = now();
  }

  get active() { return now() - this.lastSeen < ACTIVE_TIME; }
  get cx() { return this.x + this.w / 2; }
  get faceCenter() { return [this.cx, this.y + this.h / 2]; }
}

/** Gives each face a stable player (name, color, score) from frame to frame.
 *  A kid who turns away or steps out briefly keeps their player if they come back near the same spot. */
export class PlayerTracker {
  constructor(keepTime = 3.0) {
    this.keepTime = keepTime;
    this.players = [];
    this.onJoin = null;
  }

  /** boxes are in game pixels {x, y, w, h} */
  update(boxes) {
    const t = now();
    const unmatched = [...this.players];
    for (const box of [...boxes].sort((a, b) => b.w - a.w)) {
      const fx = box.x + box.w / 2, fy = box.y + box.h / 2;
      let best = null, bestD = Infinity;
      for (const p of unmatched) {
        const [px, py] = p.faceCenter;
        const d = Math.hypot(px - fx, py - fy);
        if (d < Math.max(p.w, box.w) * 1.2 && d < bestD) { best = p; bestD = d; }
      }
      if (best) {
        best.update(box);
        unmatched.splice(unmatched.indexOf(best), 1);
      } else {
        this._add(box, t);
      }
    }
    this.players = this.players.filter((p) => t - p.lastSeen < this.keepTime);
  }

  _add(box, t) {
    const used = new Set(this.players.map((p) => p.slot));
    const free = PLAYER_STYLES.map((_, i) => i).filter((i) => !used.has(i));
    let player = null;
    if (free.length) {
      player = new Player(free[0], box);
    } else {
      // everyone is taken: reuse a player who has been gone a while
      const stale = this.players.filter((p) => t - p.lastSeen > 1.0);
      if (!stale.length) return;
      const old = stale.reduce((a, b) => (a.lastSeen < b.lastSeen ? a : b));
      this.players.splice(this.players.indexOf(old), 1);
      player = new Player(old.slot, box);
    }
    this.players.push(player);
    this.onJoin?.(player);
  }

  activePlayers() { return this.players.filter((p) => p.active); }

  resetScores() {
    for (const p of this.players) {
      p.score = 0;
      p.stack = [];
      p.streak = 0;
      p.bigUntil = 0;
    }
  }
}
