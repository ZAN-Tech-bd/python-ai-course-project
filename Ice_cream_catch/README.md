# Ice Cream Catch

A kid-friendly party game for the webcam: ice cream falls from the sky and
everyone catches it on a waffle cone balanced on their **head**. Several kids
can play at once: every face the camera sees becomes a player with their own
name, color and score (Bunny, Kitty, Puppy, Froggy, Panda and Tiger, up to 6).

Built with OpenCV + MediaPipe face detection and Pillow (cartoon graphics).

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

Stand back far enough that everyone's whole head fits in the picture, with
some space above it for the cones.

## How to play

- **Start:** move your head onto the **Play!** button and hold still until the
  pink bar fills (~1s). A 3-2-1 countdown starts a 60-second round.
- **Catch:** move under the falling ice cream so it lands on your cone. Each
  scoop is +1 and stacks up on your cone.
- **Tower:** stack 5 scoops for a +5 bonus. The tower is then "eaten" and you
  start a new one.
- **Golden scoop:** the sparkly one is worth +3.
- **Broccoli:** yuck! Catching it knocks your whole stack off (you keep your
  points). Broccoli only starts falling after 10 seconds.
- At the end, everyone's score is shown and the winner is announced. Move your
  head onto **Play again!** for another round.

More players means more ice cream falls, and some of it is aimed near each
player so everyone gets a fair chance. If a kid steps out of the picture for
a moment during a round, they keep their score when they come back to about
the same spot.

Keyboard (optional, with the game window focused): `Space` starts a round,
`Q` / `Esc` quits. The **Exit** button sits in the top-right corner so it
isn't pressed by accident.

The best score ever is kept in `best_score.txt`.

## Project layout

```
Ice_cream_catch/
├── main.py             the game (falling items, catching, screens)
├── faces.py            MediaPipe face detection + stable player tracking
├── sprites.py          cartoon scoops, cone, broccoli
├── ui.py               fonts, pill labels, blending, confetti
├── requirements.txt
└── run.bat / run.sh    one-click setup + launch
```
