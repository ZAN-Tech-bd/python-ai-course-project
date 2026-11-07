# Ice Cream Catch — Chrome Extension

The webcam ice-cream game from `Ice_cream_catch/`, rebuilt in JavaScript so it runs in
Google Chrome on **any PC** (Windows, macOS, Linux, Chromebook), as well as in Microsoft
Edge and Brave. No Python, no installs, no internet needed after it's added.

Ice cream falls from the sky and kids catch it on a waffle cone balanced on their **head**.
**Up to 6 kids play at the same time**: every face the camera sees becomes a player with
their own animal ears, name, color and score (Bunny, Kitty, Puppy, Froggy, Panda, Tiger).
Kids can walk in and out of the picture at any time; whoever the camera sees is playing.

- **Face tracking:** MediaPipe Face Detector (web version), bundled inside the extension.
- **Privacy:** the camera video is processed on the computer and never leaves it. The
  extension asks for **no permissions** and makes no network requests.
- **No webcam?** Pick **Play with mouse**. A mouse or a touchscreen moves the cone.

## Install on a PC (developer mode)

1. Copy the `chrome_extension` folder onto the PC.
2. Open Chrome and go to `chrome://extensions`.
3. Turn on **Developer mode** (top-right switch).
4. Click **Load unpacked** and select the `chrome_extension` folder (the one containing `manifest.json`).
5. The game opens in a new tab. Later, click the ice cream icon in the toolbar
   (pin it via the puzzle-piece menu) to play again.
6. When Chrome asks to use the camera, click **Allow**.

> For Edge use `edge://extensions`; the steps are the same.

To publish for one-click install, zip the contents of this folder and upload it to the
[Chrome Web Store Developer Dashboard](https://chrome.google.com/webstore/devconsole).

## How to play

- **Pick a mode:** move your head onto **Easy** (slower, no broccoli — for little kids) or
  **Super** (faster, with broccoli) and hold still until the pink bar fills. You can also click.
- **Catch:** move under the falling ice cream so it lands on your cone. Each scoop is +1 and
  stacks up. Every catch in a row plays a higher note!
- **Tower:** stack 5 scoops for +5. The tower is "eaten" and you start a new one.
- **Golden scoop:** +3.
- **Rainbow scoop:** +2 and a **giant cone** for 6 seconds.
- **Snowflake:** slow motion for everyone for 5 seconds.
- **Broccoli (Super mode):** yuck! It knocks your stack off (you keep your points).
- **Streaks:** 3, 5, 10… catches in a row give bonus points.
- **Team goal:** everyone's catches fill the team bar together. When it's full, every
  player gets +3, and a bigger goal starts.
- **Ice cream party:** with 25 seconds left, ice cream rains from the sky for 5 seconds!
- At the end, everyone's score is shown and the winner is announced.

Tips: stand back so every head fits in the picture with space above for the cones; good
light on faces helps. The short-range face model works best within about 2 metres.

**Keyboard:** `Space` start, `Q` end the round, `F` full screen, `M` sound on/off.
The best score is saved in the browser.

## Project layout

```
chrome_extension/
├── manifest.json          Manifest V3, no permissions
├── background.js          toolbar icon → opens the game tab
├── game.html / game.css   page + loading/camera-help screens
├── js/
│   ├── main.js            boot: model, webcam, mouse fallback, keys
│   ├── tracker.js         webcam + MediaPipe Face Detector + stable players (port of faces.py)
│   ├── game.js            game logic (port of main.py, plus modes and power-ups)
│   ├── sprites.js         scoops, cone, broccoli, snowflake, animal ears
│   ├── sound.js           sound effects + background tune (Web Audio, no files)
│   └── ui.js              pills, rainbow title, confetti
├── vendor/mediapipe/      @mediapipe/tasks-vision 0.10.35 (Apache-2.0)
├── models/                blaze_face_short_range.tflite (Apache-2.0)
├── fonts/                 Fredoka (SIL Open Font License)
└── icons/
```
