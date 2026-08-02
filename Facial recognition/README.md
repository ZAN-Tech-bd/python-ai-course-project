# Facial Recognition (Face Detection)

Detects human faces in real time from a webcam (or in a still image) using OpenCV's Haar cascade classifier.

## Requirements

- Python 3.9+ (Windows: install from https://www.python.org/downloads/, check "Add to PATH")
- A webcam (for live detection)

## Setup (first time on any PC)

Double-click `setup.bat`, or run in a terminal:

```bash
setup.bat
```

This creates an isolated `.venv` folder in the project and installs the exact dependencies from `requirements.txt` into it. Nothing is installed globally, so it won't conflict with other Python projects on the machine.

## Run

Double-click `run.bat`, or run:

```bash
run.bat
```

This activates `.venv` and starts webcam face detection. Press **q** or **Esc** to quit.

To run on an image file instead of the webcam:

```bash
run.bat --image path\to\photo.jpg
```

The annotated result is saved next to the original as `photo_detected.jpg`.

To use a different camera (if you have more than one):

```bash
run.bat --camera 1
```

## macOS / Linux

The same project works cross-platform; just create/activate the venv manually:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

## Project structure

```
Facial recognition/
├── main.py           # face detection logic (webcam + image modes)
├── requirements.txt  # pinned dependencies (opencv-python, numpy)
├── setup.bat          # creates .venv and installs dependencies
├── run.bat            # activates .venv and runs main.py
└── .gitignore
```

## Sharing this project with another PC

Copy/clone the whole folder (the `.venv` folder is excluded via `.gitignore` and should NOT be copied — it's machine-specific). On the new PC, just run `setup.bat` once, then `run.bat` any time.
