// Boots the game: loads the face model + webcam, falls back to mouse/touch play if there is no camera.
import { CameraError, FaceTracker } from "./tracker.js";
import { IceCreamGame } from "./game.js";
import { sound } from "./sound.js";

const $ = (id) => document.getElementById(id);
const canvas = $("game");
const video = $("cam");
const overlay = $("overlay");

function showOverlay({ status, spinner = false, retry = false, mouse = false, hint = "" }) {
  overlay.classList.add("show");
  $("status").textContent = status;
  $("spinner").classList.toggle("hidden", !spinner);
  $("retry").classList.toggle("hidden", !retry);
  $("mouse").classList.toggle("hidden", !mouse);
  $("hint").classList.toggle("hidden", !hint);
  $("hint").textContent = hint;
}
const hideOverlay = () => overlay.classList.remove("show");

function exitGame() {
  if (globalThis.chrome?.tabs?.getCurrent) {
    chrome.tabs.getCurrent((tab) => (tab ? chrome.tabs.remove(tab.id) : window.close()));
  } else {
    window.close();
  }
}

function toggleFullscreen() {
  if (document.fullscreenElement) document.exitFullscreen();
  else document.documentElement.requestFullscreen().catch(() => {});
}
function showMute() {
  $("sound").textContent = sound.muted ? "🔇" : "🔊";
}
function toggleMute() {
  sound.unlock();
  sound.toggleMute();
  showMute();
}
showMute();
$("fullscreen").addEventListener("click", toggleFullscreen);
$("sound").addEventListener("click", toggleMute);
window.addEventListener("pointerdown", () => sound.unlock());
window.addEventListener("keydown", (e) => {
  if (e.key === "f" || e.key === "F") toggleFullscreen();
  else if (e.key === "m" || e.key === "M") toggleMute();
  else game?.key(e.key);
});

const CAMERA_HELP = {
  denied: ["The camera is blocked.",
           "Click the camera icon in the address bar, choose “Allow”, then press Try again."],
  missing: ["No webcam was found.", "Plug in a webcam and press Try again, or play with the mouse."],
  busy: ["The webcam is busy.", "Close other apps using the camera (Zoom, Meet, Camera app), then press Try again."],
  other: ["The webcam could not start.", "Press Try again, or play with the mouse."],
};

let game = null;
let tracker = null;

function startGame(withCamera) {
  hideOverlay();
  sound.unlock();
  if (game) {
    game.camera = withCamera;
    return;
  }
  game = new IceCreamGame(canvas, withCamera, exitGame);
  game.start();
}

async function boot() {
  showOverlay({ status: "Getting the game ready…", spinner: true });
  await document.fonts.load('700 40px "Fredoka"').catch(() => {});

  tracker = tracker || new FaceTracker(video);
  try {
    if (!tracker.detector) {
      showOverlay({ status: "Loading face tracking…", spinner: true });
      await tracker.loadModel();
    }
  } catch (err) {
    console.error("face model failed to load", err);
    showOverlay({ status: "Face tracking can't run on this computer.", mouse: true,
                  hint: "You can still play with the mouse or a touchscreen." });
    return;
  }

  try {
    showOverlay({ status: "Starting the webcam…", spinner: true,
                  hint: "If Chrome asks, click “Allow” so the game can see you." });
    await tracker.startCamera();
  } catch (err) {
    const kind = err instanceof CameraError ? err.kind : "other";
    const [status, hint] = CAMERA_HELP[kind];
    console.warn("camera failed:", err);
    showOverlay({ status, hint, retry: true, mouse: true });
    return;
  }

  startGame(tracker);
}

$("retry").addEventListener("click", boot);
$("mouse").addEventListener("click", () => startGame(null));
window.addEventListener("beforeunload", () => tracker?.stop());

boot();
