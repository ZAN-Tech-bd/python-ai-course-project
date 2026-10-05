"""Face detection + recognition, and a small on-disk memory of named people."""

import json
import re
from pathlib import Path

import cv2
import numpy as np

PEOPLE_DIR = Path(__file__).resolve().parent / "people"
DB_FILE = PEOPLE_DIR / "people.json"
MATCH_THRESHOLD = 0.40   # cosine similarity; OpenCV suggests 0.363 for SFace, a bit stricter avoids mix-ups
MAX_SAMPLES = 30         # face samples kept per person


class Face:
    def __init__(self, row, feature):
        self.row = row                       # YuNet output: x, y, w, h, 5 landmarks, score
        self.box = tuple(int(v) for v in row[:4])
        self.feature = feature               # normalized 128-d SFace embedding
        self.name = None
        self.similarity = 0.0

    @property
    def center(self):
        x, y, w, h = self.box
        return x + w // 2, y + h // 2

    @property
    def area(self):
        return self.box[2] * self.box[3]


class FaceEngine:
    """Finds faces and computes a recognition fingerprint for each."""

    def __init__(self, detector_path, recognizer_path, score_threshold=0.8):
        self.detector = cv2.FaceDetectorYN.create(detector_path, "", (320, 320), score_threshold, 0.3, 5000)
        self.recognizer = cv2.FaceRecognizerSF.create(recognizer_path, "")

    def find_faces(self, frame):
        h, w = frame.shape[:2]
        self.detector.setInputSize((w, h))
        _, rows = self.detector.detect(frame)
        faces = []
        for row in rows if rows is not None else []:
            aligned = self.recognizer.alignCrop(frame, row)
            feat = self.recognizer.feature(aligned).flatten()
            faces.append(Face(row, feat / (np.linalg.norm(feat) + 1e-9)))
        return faces


def _safe_filename(name):
    return re.sub(r"[^A-Za-z0-9_-]+", "_", name).strip("_") or "person"


class PeopleDB:
    """name -> list of face fingerprints, saved as JSON in people/people.json (plus a photo per person)."""

    def __init__(self):
        self.people = {}
        self._matrix, self._owners = None, []
        self.load()

    def load(self):
        if DB_FILE.exists():
            data = json.loads(DB_FILE.read_text(encoding="utf-8"))
            self.people = {name: [np.array(f, dtype=np.float32) for f in feats] for name, feats in data.items()}
        self._rebuild()

    def save(self):
        PEOPLE_DIR.mkdir(exist_ok=True)
        data = {name: [f.round(5).tolist() for f in feats] for name, feats in self.people.items()}
        DB_FILE.write_text(json.dumps(data), encoding="utf-8")

    def _rebuild(self):
        self._owners = [name for name, feats in self.people.items() for _ in feats]
        feats = [f for fs in self.people.values() for f in fs]
        self._matrix = np.stack(feats) if feats else None

    def names(self):
        return sorted(self.people, key=str.lower)

    def find_name(self, name):
        """Case-insensitive lookup so 'alice' adds to an existing 'Alice'."""
        return next((n for n in self.people if n.lower() == name.lower()), None)

    def add(self, name, features, photo=None):
        name = self.find_name(name) or name
        merged = self.people.get(name, []) + list(features)
        self.people[name] = merged[-MAX_SAMPLES:]
        self._rebuild()
        self.save()
        if photo is not None and photo.size:
            cv2.imwrite(str(PEOPLE_DIR / f"{_safe_filename(name)}.jpg"), photo)
        return name

    def remove(self, name):
        if self.people.pop(name, None) is None:
            return False
        (PEOPLE_DIR / f"{_safe_filename(name)}.jpg").unlink(missing_ok=True)
        self._rebuild()
        self.save()
        return True

    def identify(self, face):
        """Sets face.name / face.similarity to the best match, or leaves name None if nobody matches."""
        if self._matrix is None:
            return
        sims = self._matrix @ face.feature
        best = int(sims.argmax())
        face.similarity = float(sims[best])
        if face.similarity >= MATCH_THRESHOLD:
            face.name = self._owners[best]
