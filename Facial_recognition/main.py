"""Real-time face recognition + object naming with OpenCV.

Recognizes people you have taught it (their names are remembered in the people/ folder) and labels
everyday objects (cup, phone, laptop, chair, ...).

Usage:
    python main.py                              # webcam
    python main.py --camera 1                   # use a different camera index
    python main.py --image photo.jpg            # label faces + objects in an image file
    python main.py --add "Alice" --image a.jpg  # remember the face in a photo as "Alice"
    python main.py --list                       # show everyone who is remembered
    python main.py --forget "Alice"             # forget a person

Webcam keys:
    A  add the person in front of the camera (type their name, Enter to save)
    D  forget the recognized person in front of the camera
    O  objects on/off      Q / Esc  quit
"""

import argparse
import sys
import time
from pathlib import Path

import cv2
import numpy as np

from models import model_path
from objects import BackgroundObjectDetector, ObjectDetector
from people import FaceEngine, PeopleDB

FONT = cv2.FONT_HERSHEY_SIMPLEX
KNOWN = (80, 200, 80)       # BGR
UNKNOWN = (0, 160, 255)
TARGET = (255, 200, 0)
ADD_SAMPLES = 10            # face samples collected while you type a new name


def object_color(name):
    """A stable, bright color per object type."""
    hue = (sum(map(ord, name)) * 37) % 180
    bgr = cv2.cvtColor(np.uint8([[[hue, 200, 255]]]), cv2.COLOR_HSV2BGR)[0, 0]
    return tuple(int(c) for c in bgr)


def draw_label(img, text, x, y, color, scale=0.6, above=True):
    """Text on a filled tag, placed above (or inside the top of) a box corner."""
    (tw, th), base = cv2.getTextSize(text, FONT, scale, 2)
    y0 = y - th - base - 8 if above and y - th - base - 8 > 0 else y
    cv2.rectangle(img, (x, y0), (x + tw + 10, y0 + th + base + 8), color, -1)
    luminance = 0.114 * color[0] + 0.587 * color[1] + 0.299 * color[2]
    text_color = (20, 20, 20) if luminance > 140 else (255, 255, 255)
    cv2.putText(img, text, (x + 5, y0 + th + 4), FONT, scale, text_color, 2, cv2.LINE_AA)


def draw_panel(img, lines, x, y, scale=0.55, alpha=0.6):
    """Semi-transparent dark panel with lines of text."""
    sizes = [cv2.getTextSize(t, FONT, scale, 1)[0] for t in lines]
    w = max(s[0] for s in sizes) + 20
    h = sum(s[1] + 10 for s in sizes) + 10
    x = min(x, img.shape[1] - w)
    roi = img[y:y + h, x:x + w]
    roi[:] = (roi * (1 - alpha)).astype(np.uint8)
    yy = y + 5
    for t, (tw, th) in zip(lines, sizes):
        yy += th + 10
        cv2.putText(img, t, (x + 10, yy - 5), FONT, scale, (255, 255, 255), 1, cv2.LINE_AA)


def annotate(frame, faces, objects, show_objects=True, target=None, unknown_label="Unknown - press A to add"):
    """Draws objects (with 'person' boxes renamed to the recognized name) and face boxes."""
    if show_objects:
        for name, score, (x, y, w, h) in objects:
            label, color = name, object_color(name)
            if name == "person":
                inside = [f for f in faces if x <= f.center[0] <= x + w and y <= f.center[1] <= y + h]
                known = [f for f in inside if f.name]
                if known:
                    label, color = known[0].name, KNOWN
                elif inside:
                    continue  # the face box already says "Unknown"
            cv2.rectangle(frame, (x, y), (x + w, y + h), color, 2)
            draw_label(frame, f"{label} {score * 100:.0f}%", x, y, color, scale=0.55)

    for f in faces:
        x, y, w, h = f.box
        if f is target:
            color, label = TARGET, "New person"
        elif f.name:
            color, label = KNOWN, f"{f.name} ({f.similarity * 100:.0f}%)"
        else:
            color, label = UNKNOWN, unknown_label
        cv2.rectangle(frame, (x, y), (x + w, y + h), color, 3)
        for lx, ly in f.row[4:14].reshape(5, 2).astype(int):
            cv2.circle(frame, (lx, ly), 2, color, -1, cv2.LINE_AA)
        draw_label(frame, label, x, y, color, scale=0.7)


class App:
    def __init__(self, camera_index, show_objects=True):
        self.cap = cv2.VideoCapture(camera_index)
        if not self.cap.isOpened():
            raise RuntimeError(f"Could not open camera index {camera_index}")
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
        self.engine = FaceEngine(model_path("face_detector"), model_path("face_recognizer"))
        self.db = PeopleDB()
        self.objects = BackgroundObjectDetector(ObjectDetector(model_path("object_detector")))
        self.show_objects = show_objects

        self.mode = "normal"          # "normal", "naming" (typing a new name), "confirm_forget"
        self.typed = ""
        self.samples, self.photo = [], None
        self.target_box = None
        self.forget_name = None
        self.message, self.message_until = "", 0.0

    def say(self, text, seconds=2.5):
        print(text)
        self.message, self.message_until = text, time.time() + seconds

    # ---------- adding / forgetting ----------
    def _pick_target(self, faces):
        """The face being named: the one nearest the last target, else the biggest face."""
        if not faces:
            return None
        if self.target_box is None:
            return max(faces, key=lambda f: f.area)
        tx, ty = self.target_box[0] + self.target_box[2] / 2, self.target_box[1] + self.target_box[3] / 2
        return min(faces, key=lambda f: (f.center[0] - tx) ** 2 + (f.center[1] - ty) ** 2)

    def start_naming(self, faces, frame):
        target = self._pick_target(faces)
        if target is None:
            self.say("No face found - look at the camera and press A again")
            return
        self.mode, self.typed, self.samples = "naming", "", []
        self.target_box = target.box
        if target.name:
            self.typed = target.name  # already known: Enter adds more samples, or type a new name
        self._collect(target, frame)

    def _collect(self, face, frame):
        self.target_box = face.box
        if len(self.samples) < ADD_SAMPLES:
            self.samples.append(face.feature)
        x, y, w, h = face.box
        pad = int(0.25 * max(w, h))
        crop = frame[max(0, y - pad):y + h + pad, max(0, x - pad):x + w + pad]
        if crop.size:
            self.photo = crop.copy()

    def finish_naming(self):
        name = " ".join(self.typed.split())
        if not name:
            self.say("Type a name first (or Esc to cancel)")
            return
        if not self.samples:
            self.say("Lost the face - look at the camera")
            return
        existed = self.db.find_name(name) is not None
        saved = self.db.add(name, self.samples, self.photo)
        self.say(f"Updated {saved}'s face" if existed else f"Nice to meet you, {saved}! I'll remember you.")
        self.mode, self.target_box = "normal", None

    def start_forget(self, faces):
        known = [f for f in faces if f.name]
        if not known:
            self.say("No remembered person in view")
            return
        self.forget_name = max(known, key=lambda f: f.area).name
        self.mode = "confirm_forget"

    # ---------- keyboard ----------
    def handle_key(self, key, faces, frame):
        if key == -1:
            return True
        code = key & 0xFF
        if self.mode == "naming":
            if code == 27:
                self.mode, self.target_box = "normal", None
                self.say("Cancelled")
            elif code in (13, 10):
                self.finish_naming()
            elif code == 8:
                self.typed = self.typed[:-1]
            elif 32 <= code < 127 and len(self.typed) < 30:
                self.typed += chr(code)
            return True
        if self.mode == "confirm_forget":
            if code in (ord("y"), ord("Y")):
                self.db.remove(self.forget_name)
                self.say(f"Forgot {self.forget_name}")
            else:
                self.say("Kept everyone")
            self.mode = "normal"
            return True

        if code in (ord("q"), ord("Q"), 27):
            return False
        if code in (ord("a"), ord("A")):
            self.start_naming(faces, frame)
        elif code in (ord("d"), ord("D")):
            self.start_forget(faces)
        elif code in (ord("o"), ord("O")):
            self.show_objects = not self.show_objects
            self.say(f"Objects {'on' if self.show_objects else 'off'}")
        return True

    # ---------- drawing ----------
    def draw_overlay(self, frame, faces):
        h, w = frame.shape[:2]
        names = self.db.names()
        remembered = ", ".join(names[:8]) + (f" +{len(names) - 8} more" if len(names) > 8 else "")
        draw_panel(frame, [
            f"People: {len(faces)} in view   Objects: {'on' if self.show_objects else 'off'}"
            + (f" ({self.objects.ms:.0f} ms)" if self.show_objects else ""),
            f"Remembered: {remembered or 'nobody yet'}",
            "A add person   D forget person   O objects on/off   Q quit",
        ], 10, 10)

        if self.mode == "naming":
            box = [f"Who is this?  {self.typed}_",
                   f"Type the name, Enter to save, Esc to cancel   (face samples: {len(self.samples)})"]
            draw_panel(frame, box, (w - 620) // 2, h - 110, scale=0.75, alpha=0.75)
        elif self.mode == "confirm_forget":
            draw_panel(frame, [f"Forget {self.forget_name}?  Press Y to confirm, any other key to keep"],
                       (w - 700) // 2, h - 80, scale=0.75, alpha=0.75)
        elif time.time() < self.message_until:
            draw_panel(frame, [self.message], (w - 600) // 2, h - 80, scale=0.75, alpha=0.75)

    def run(self):
        window = "Face & Object Recognition"
        cv2.namedWindow(window)
        print(__doc__.split("Webcam keys:")[1])
        try:
            while True:
                ok, frame = self.cap.read()
                if not ok:
                    print("Failed to read frame from camera.")
                    break
                frame = cv2.flip(frame, 1)
                if self.show_objects:
                    self.objects.submit(frame)

                faces = self.engine.find_faces(frame)
                for f in faces:
                    self.db.identify(f)

                target = None
                if self.mode == "naming":
                    target = self._pick_target(faces)
                    if target is not None:
                        self._collect(target, frame)

                annotate(frame, faces, self.objects.results, self.show_objects, target)
                self.draw_overlay(frame, faces)

                cv2.imshow(window, frame)
                if not self.handle_key(cv2.waitKey(1), faces, frame):
                    break
                if cv2.getWindowProperty(window, cv2.WND_PROP_VISIBLE) < 1:
                    break
        finally:
            self.objects.stop()
            self.cap.release()
            cv2.destroyAllWindows()


def run_on_image(image_path, add_name=None):
    frame = cv2.imread(image_path)
    if frame is None:
        raise FileNotFoundError(f"Could not read image: {image_path}")
    engine = FaceEngine(model_path("face_detector"), model_path("face_recognizer"))
    db = PeopleDB()
    faces = engine.find_faces(frame)

    if add_name:
        if not faces:
            sys.exit(f"No face found in {image_path}")
        face = max(faces, key=lambda f: f.area)
        x, y, w, h = face.box
        saved = db.add(add_name, [face.feature], frame[max(0, y):y + h, max(0, x):x + w])
        print(f"Remembered {saved} from {image_path}")
        return

    for f in faces:
        db.identify(f)
    objects = ObjectDetector(model_path("object_detector")).detect(frame)
    annotate(frame, faces, objects, unknown_label="Unknown")
    for f in faces:
        print(f"Face: {f.name or 'Unknown'}" + (f" ({f.similarity * 100:.0f}%)" if f.name else ""))
    for name, score, _ in objects:
        print(f"Object: {name} ({score * 100:.0f}%)")

    out_path = str(Path(image_path).with_stem(Path(image_path).stem + "_detected"))
    cv2.imwrite(out_path, frame)
    print(f"Saved annotated image to {out_path}")
    cv2.imshow("Face & Object Recognition - press any key to close", frame)
    cv2.waitKey(0)
    cv2.destroyAllWindows()


def parse_args(argv=None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Recognize people and name objects with OpenCV.")
    parser.add_argument("--image", help="Path to an image file to label (or to learn a face from, with --add).")
    parser.add_argument("--camera", type=int, default=0, help="Webcam index (default: 0).")
    parser.add_argument("--add", metavar="NAME", help="Remember the face in --image under this name.")
    parser.add_argument("--forget", metavar="NAME", help="Forget a remembered person.")
    parser.add_argument("--list", action="store_true", help="List remembered people.")
    parser.add_argument("--no-objects", action="store_true", help="Start with object labels turned off.")
    return parser.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)
    if args.list:
        db = PeopleDB()
        names = db.names()
        print("\n".join(f"{n} ({len(db.people[n])} face samples)" for n in names) or "Nobody remembered yet.")
        return 0
    if args.forget:
        db = PeopleDB()
        name = db.find_name(args.forget)
        print(f"Forgot {name}" if name and db.remove(name) else f"Nobody called {args.forget!r} is remembered")
        return 0
    if args.add and not args.image:
        sys.exit("--add needs --image (or press A in the webcam window instead)")

    if args.image:
        run_on_image(args.image, args.add)
    else:
        App(args.camera, show_objects=not args.no_objects).run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
