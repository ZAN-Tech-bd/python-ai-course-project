# Draw in Air

Draw on-screen using just your fingertip in front of a webcam — no mouse, no
touchscreen. Includes a full 2D drawing toolset (pen, shapes, eraser, colors,
undo, save) and a 3D mode that uses your fingertip's tracked depth to let you
draw freehand in 3D space, viewable from any angle.

Built with OpenCV + MediaPipe (hand tracking) and PyOpenGL/pygame (3D mode).

## Quick start

Requires Python 3.9–3.12 installed and on PATH. A `.venv` virtual environment
is created automatically, so this works the same on any machine.

**Windows:**
```bash
run.bat
```

**macOS / Linux:**
```bash
chmod +x run.sh && ./run.sh
```

Either script creates `.venv`, installs dependencies from
`requirements.txt`, and launches the app. On later runs it reuses the
existing `.venv` and just updates dependencies.

To run manually instead:
```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

You can also jump straight into a mode: `python main.py 2d` or `python main.py 3d`.

## How it works

A webcam feed is passed through MediaPipe Hands each frame to get 21 hand
landmarks. Which fingers are extended decides the current **gesture**, which
decides what happens with your fingertip position:

| Gesture | Hand shape | Effect |
|---|---|---|
| Draw | Index finger only | Draws / moves the shape preview |
| Select | Index + middle finger | Moves cursor without drawing; hover over a toolbar button ~0.8s to select it |
| Idle | Open palm or closed fist | Pen lifted, nothing drawn |

## 2D mode

A toolbar across the top of the video feed gives you:

- **Colors** — 9 swatches (red, orange, yellow, green, cyan, blue, purple, white, black)
- **Tools** — pen, line, rectangle, circle
- **Brush sizes** — 4 preset thicknesses
- **Eraser**, **Undo**, **Clear**, **Save**, and a button to jump to **3D** mode

Select a tool/color by holding the "select" gesture (index + middle finger)
over its button until the yellow ring completes. Switch to "draw" gesture
(index finger only) to draw, or drag out a shape start-to-end point for
line/rectangle/circle tools.

Keyboard shortcuts (with the video window focused):
- `Q` / `Esc` — quit
- `C` — clear canvas
- `S` — save PNG to `saved_drawings/`
- `Z` — undo
- `E` / `P` — eraser / pen
- `1`–`9` — pick a color
- `+` / `-` — brush size
- `M` — switch to 3D mode

## 3D mode

Your fingertip's `x, y` position plus MediaPipe's estimated depth (`z`) are
mapped into 3D space and rendered live with OpenGL. Hold the "draw" gesture
(index finger only) to extend the current stroke through 3D space; lift the
gesture (open palm / fist / select) to end that stroke and start a new one
next time you draw.

A small camera preview window shows your hand and the detected gesture so
you can see what's being tracked, alongside the main 3D OpenGL window with
the drawing itself.

Controls in the 3D window:
- Left-click drag — orbit the camera manually (also disables auto-rotate)
- Scroll wheel — zoom in/out
- `R` — toggle auto-rotate
- `1`–`8` — pick a stroke color
- `+` / `-` — line thickness
- `C` — clear all strokes
- `Z` — undo last stroke
- `S` — save a screenshot to `saved_drawings/`
- `M` — switch back to 2D mode
- `Q` / `Esc` — quit

## Project layout

```
Draw in air/
├── main.py            entry point / mode menu
├── hand_tracker.py     MediaPipe hand-landmark wrapper
├── gestures.py          finger-pattern -> gesture classification
├── tools.py             2D toolbar layout, hit-testing, rendering
├── canvas2d.py           2D air-drawing app
├── canvas3d.py           3D air-drawing app (OpenGL)
├── config.py             colors, sizes, camera/window settings
├── requirements.txt
├── run.bat / run.sh      one-click setup + launch
└── saved_drawings/       PNG exports (created on first save)
```

## Troubleshooting

- **No camera window appears / "Could not access the webcam"** — another
  app may be using the camera, or `CAMERA_INDEX` in `config.py` needs to be
  `1` instead of `0` (common on laptops with multiple camera devices).
- **`mediapipe` fails to install** — MediaPipe's classic Python API supports
  Python 3.9–3.12; if you're on a newer Python, install Python 3.11 or 3.12
  alongside your current version and point `run.bat`/`run.sh` at it (edit
  the `PYLAUNCHER`/`PYBIN` line, or run `py -3.11 -m venv .venv` manually).
- **Hand tracking feels jittery** — make sure the room is well-lit and your
  hand is fully in frame; tracking quality depends heavily on lighting.
- **3D window is black / OpenGL errors** — update your GPU drivers; PyOpenGL
  needs a working OpenGL 2.1+ context, which is virtually all hardware from
  the last ~15 years but can be missing in some virtual machines.
