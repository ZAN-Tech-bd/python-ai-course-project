# Food Slice — Chrome Extension

The webcam fruit-cutting game from `Food_slice_game/`, rebuilt in JavaScript so it runs
in Google Chrome on **any PC** (Windows, macOS, Linux, Chromebook), as well as in Microsoft
Edge and Brave. No Python, no installs, no internet needed after it's added.

- **Hand tracking:** MediaPipe Hand Landmarker (web version), bundled inside the extension.
- **Privacy:** the camera video is processed on the computer and never leaves it. The
  extension asks for **no permissions** and makes no network requests.
- **No webcam?** Pick **Play with mouse**. A mouse or a touchscreen works as the "finger".

## Install on a PC (developer mode, for testing or classroom PCs)

1. Copy the `chrome_extension` folder (or unzip `food-slice-extension.zip`) onto the PC.
2. Open Chrome and go to `chrome://extensions`.
3. Turn on **Developer mode** (top-right switch).
4. Click **Load unpacked** and select the `chrome_extension` folder (the one containing `manifest.json`).
5. The game opens in a new tab. Later, click the Food Slice icon in the toolbar
   (pin it via the puzzle-piece menu) to play again.
6. When Chrome asks to use the camera, click **Allow**.

> For Edge use `edge://extensions`; the steps are the same.

## Publish for one-click install on every PC (recommended)

Developer mode is fine for a few PCs. For parents, schools and Chromebooks, publish to the
Chrome Web Store:

1. Register at the [Chrome Web Store Developer Dashboard](https://chrome.google.com/webstore/devconsole)
   (one-time registration fee).
2. Upload `food-slice-extension.zip`.
3. Fill in the listing: screenshots, description, and a privacy statement
   ("camera video is processed locally and never transmitted or stored").
4. After review, anyone installs it with one click. Schools can also push it to all
   managed Chromebooks from the Google Admin console.

## How to play

- **Start:** point at **Play!** and hold still until the pink bar fills (~0.8s), or click it.
- **Cut:** swipe your finger through the flying food. Each cut is +1.
- **Combo:** cut 3 or more quickly for a bonus point.
- **Bombs:** don't cut them! Each one costs a heart; lose all 3 and the round ends.
- **Keyboard (optional):** `Space` start, `Q` stop the round, `F` full screen.

The best score is saved in the browser.

## Project layout

```
chrome_extension/
├── manifest.json          Manifest V3, no permissions
├── background.js          toolbar icon → opens the game tab
├── game.html / game.css   page + loading/camera-help screens
├── js/
│   ├── main.js            boot: model, webcam, mouse fallback
│   ├── tracker.js         webcam + MediaPipe Hand Landmarker
│   ├── game.js            game logic (port of main.py)
│   ├── sprites.js         cartoon food / bomb / heart sprites
│   └── ui.js              pills, rainbow title, confetti (port of ui.py)
├── vendor/mediapipe/      @mediapipe/tasks-vision 0.10.35 (Apache-2.0)
├── models/                hand_landmarker.task (Apache-2.0)
├── fonts/                 Fredoka (SIL Open Font License)
└── icons/
```

## Differences from the Python version

- Runs at the webcam's frame rate in the browser; on slow PCs cuts are still detected
  between frames, so the game stays playable at low fps.
- Mouse/touch mode for PCs without a webcam.
- Best score is stored in the browser (not `best_score.txt`).
- `Q` stops the round instead of closing the program; use the **Exit** button to close the tab.
