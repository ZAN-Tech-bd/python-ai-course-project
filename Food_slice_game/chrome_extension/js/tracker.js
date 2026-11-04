// Webcam + MediaPipe Hand Landmarker, fully bundled inside the extension (works offline).
import { FilesetResolver, HandLandmarker } from "../vendor/mediapipe/vision_bundle.mjs";

const WASM_DIR = new URL("../vendor/mediapipe/wasm", import.meta.url).href;
const MODEL_URL = new URL("../models/hand_landmarker.task", import.meta.url).href;

export class CameraError extends Error {
  constructor(kind, message) {
    super(message);
    this.kind = kind; // "denied" | "missing" | "busy" | "other"
  }
}

export class HandTracker {
  constructor(video) {
    this.video = video;
    this.landmarker = null;
    this.stream = null;
    this.lastVideoTime = -1;
    this.lastResult = null;
    this.delegate = null;
  }

  async loadModel() {
    const fileset = await FilesetResolver.forVisionTasks(WASM_DIR);
    const options = (delegate) => ({
      baseOptions: { modelAssetPath: MODEL_URL, delegate },
      runningMode: "VIDEO",
      numHands: 1,
      minHandDetectionConfidence: 0.6,
      minHandPresenceConfidence: 0.6,
      minTrackingConfidence: 0.5,
    });
    try {
      this.landmarker = await HandLandmarker.createFromOptions(fileset, options("GPU"));
      this.delegate = "GPU";
    } catch (err) {
      console.warn("GPU hand tracking unavailable, using CPU:", err);
      this.landmarker = await HandLandmarker.createFromOptions(fileset, options("CPU"));
      this.delegate = "CPU";
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
    return !!(this.landmarker && this.stream && this.video.readyState >= 2);
  }

  /** Index fingertip in normalized *camera* coords {x, y} (not mirrored), or null. */
  detect(nowMs) {
    if (!this.ready) return null;
    if (this.video.currentTime !== this.lastVideoTime) {
      this.lastVideoTime = this.video.currentTime;
      try {
        this.lastResult = this.landmarker.detectForVideo(this.video, nowMs);
      } catch (err) {
        console.warn("hand detection failed for a frame:", err);
        this.lastResult = null;
      }
    }
    const hand = this.lastResult?.landmarks?.[0];
    return hand ? { x: hand[8].x, y: hand[8].y } : null;
  }

  stop() {
    this.stream?.getTracks().forEach((t) => t.stop());
    this.landmarker?.close();
  }
}
