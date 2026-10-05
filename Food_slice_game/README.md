# Food Slice

A kid-friendly fruit-cutting game played with just your finger in front of a
webcam: no mouse, no touchscreen. Fruit and treats fly up from the bottom of
the screen; swipe your fingertip through them to cut them in half.

Built with OpenCV + MediaPipe (hand tracking) and Pillow (cartoon graphics).

## Quick start

Requires Python 3.9–3.12 (MediaPipe doesn't support newer versions yet). A
`.venv` virtual environment is created automatically on the first run.

**Windows:**
```bash
run.bat
```

**macOS / Linux:**
```bash
chmod +x run.sh && ./run.sh
```

To run manually instead:
```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
python main.py              # or: python main.py --camera 1
```

## How to play

- **Start:** point at **Play!** and hold still until the pink bar fills (~0.8s).
- **Cut:** swipe your finger through the flying food: watermelon, orange,
  apple, kiwi, donut and strawberry. Each cut is +1.
- **Combo:** cut 3 or more foods quickly for a bonus point.
- **Bombs:** don't cut them! Each bomb costs a heart; lose all 3 hearts and
  the round ends. Bombs only start appearing after 8 seconds, and the game
  speeds up slowly.
- **Stop / Play again / Exit:** every button is picked the same way, by
  pointing and holding, so no keyboard is needed.

Your best score is kept in `best_score.txt`.

Keyboard (optional, with the game window focused): `Space` starts a round,
`Q` / `Esc` quits.

## Project layout

```
Food_slice_game/
├── main.py             the game (food sprites, physics, screens)
├── hand_tracker.py     MediaPipe hand-landmark wrapper
├── ui.py               fonts, pill labels, blending, confetti
├── requirements.txt
└── run.bat / run.sh    one-click setup + launch
```
