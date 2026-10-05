# Facial Recognition (Faces + Names + Objects)

Recognizes **who** is in front of the webcam and labels everyday **objects**,
in real time, using only OpenCV:

- **People:** finds faces and shows the person's name. Teach it a new person
  by pressing **A** and typing their name. It remembers them next time too.
- **Objects:** labels 80 kinds of everyday things (cup, cell phone, laptop,
  chair, bottle, book, dog, ...) with a confidence score. A "person" box is
  labeled with the person's name when their face is recognized.

## Requirements

- Python 3.9+ (Windows: install from https://www.python.org/downloads/, check "Add to PATH")
- A webcam (for live mode)
- Internet on the first run, to download the models (~75 MB, saved in `models/`)

## Setup (first time on any PC)

Double-click `setup.bat`, or run in a terminal:

```bash
setup.bat
```

This creates an isolated `.venv` folder in the project and installs the dependencies from
`requirements.txt` into it. Nothing is installed globally.

## Run

Double-click `run.bat`, or run:

```bash
run.bat
```

Keys in the webcam window:

| Key | What it does |
|---|---|
| `A` | Add the person in front of the camera: type their name, press **Enter** to save (**Esc** cancels). Pressing `A` on someone already known and pressing Enter adds more face samples, which makes recognition more reliable. |
| `D` | Forget the recognized person in view (press `Y` to confirm) |
| `O` | Turn object labels on/off (off makes it faster on slow PCs) |
| `Q` / `Esc` | Quit |

Tip: when adding someone, look at the camera and turn your head a little while
you type the name. The app collects several face samples during that time.

### Other options

```bash
run.bat --image path\to\photo.jpg            # label faces + objects in a photo (saved as photo_detected.jpg)
run.bat --add "Alice" --image alice.jpg      # remember the face in a photo as "Alice"
run.bat --list                               # who is remembered
run.bat --forget "Alice"                     # forget someone
run.bat --camera 1                           # use a different camera
run.bat --no-objects                         # start with object labels off
```

## How it works

| Part | Model (from the [OpenCV model zoo](https://github.com/opencv/opencv_zoo)) |
|---|---|
| Face detection | YuNet: finds faces and 5 landmarks (eyes, nose, mouth corners) |
| Face recognition | SFace: turns each face into 128 numbers (a "face fingerprint"). Two fingerprints that point the same way belong to the same person. |
| Object detection | YOLOX-S: trained on the COCO dataset (80 object types). Runs in a background thread so the video stays smooth. |

Remembered people are stored in `people/people.json` (up to 30 face
fingerprints per name) with a photo of each person in `people/`. The
`people/` folder is personal data, so it is excluded from git.

## macOS / Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

## Project structure

```
Facial_recognition/
├── main.py           # webcam app, image mode, command-line options
├── people.py         # face detection + recognition, and the people memory
├── objects.py        # YOLOX object detection (+ background thread)
├── models.py         # downloads the models on first run
├── requirements.txt  # opencv-python, numpy
├── setup.bat          # creates .venv and installs dependencies
├── run.bat            # activates .venv and runs main.py
├── models/            # downloaded models (not in git)
└── people/            # remembered people (not in git)
```

## Sharing this project with another PC

Copy/clone the whole folder (the `.venv` folder is machine-specific and excluded via `.gitignore`).
On the new PC, run `setup.bat` once, then `run.bat` any time. To bring the
remembered people along, copy the `people/` folder too.
