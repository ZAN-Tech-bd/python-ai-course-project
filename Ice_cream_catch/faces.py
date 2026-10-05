import time

import cv2
import mediapipe as mp

# name, RGB color - one per player, in the order kids join
PLAYER_STYLES = [
    ("Bunny", (255, 120, 170)),
    ("Kitty", (255, 160, 60)),
    ("Puppy", (80, 160, 255)),
    ("Froggy", (90, 200, 90)),
    ("Panda", (170, 110, 230)),
    ("Tiger", (255, 210, 50)),
]
ACTIVE_TIME = 0.5  # a player whose face was seen this recently is "here"


class FaceDetector:
    """MediaPipe face detection, set up for several people standing a few metres from the camera."""

    def __init__(self, min_confidence=0.5):
        # model_selection=1 is the full-range model (faces up to ~5 m away)
        self.detector = mp.solutions.face_detection.FaceDetection(
            model_selection=1, min_detection_confidence=min_confidence)

    def detect(self, frame_bgr):
        """Returns [(x, y, w, h), ...] face boxes in pixels."""
        h, w = frame_bgr.shape[:2]
        rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        rgb.flags.writeable = False
        results = self.detector.process(rgb)
        faces = []
        for det in results.detections or []:
            bb = det.location_data.relative_bounding_box
            faces.append((bb.xmin * w, bb.ymin * h, bb.width * w, bb.height * h))
        return faces

    def close(self):
        self.detector.close()


class Player:
    def __init__(self, slot, box):
        self.slot = slot
        self.name, self.color = PLAYER_STYLES[slot]
        self.x, self.y, self.w, self.h = box
        self.score = 0
        self.stack = []  # flavor indexes of scoops balanced on the cone
        self.last_seen = time.time()

    def update(self, box, smooth=0.5):
        x, y, w, h = box
        self.x += (x - self.x) * smooth
        self.y += (y - self.y) * smooth
        self.w += (w - self.w) * smooth
        self.h += (h - self.h) * smooth
        self.last_seen = time.time()

    @property
    def active(self):
        return time.time() - self.last_seen < ACTIVE_TIME

    @property
    def cx(self):
        return self.x + self.w / 2

    @property
    def face_center(self):
        return self.cx, self.y + self.h / 2


class PlayerTracker:
    """Gives each face a stable player (name, color, score) from frame to frame.

    A kid who turns away or steps out briefly keeps their player if they come back near the same spot.
    """

    def __init__(self, keep_time=3.0):
        self.keep_time = keep_time
        self.players = []

    def update(self, faces):
        now = time.time()
        unmatched = list(self.players)
        # biggest faces first: they are the clearest detections
        for box in sorted(faces, key=lambda b: -b[2]):
            fx, fy = box[0] + box[2] / 2, box[1] + box[3] / 2
            best, best_d = None, None
            for p in unmatched:
                d = ((p.face_center[0] - fx) ** 2 + (p.face_center[1] - fy) ** 2) ** 0.5
                if d < max(p.w, box[2]) * 1.2 and (best_d is None or d < best_d):
                    best, best_d = p, d
            if best is not None:
                best.update(box)
                unmatched.remove(best)
            else:
                self._add(box, now)

        self.players = [p for p in self.players if now - p.last_seen < self.keep_time]

    def _add(self, box, now):
        used = {p.slot for p in self.players}
        free = [s for s in range(len(PLAYER_STYLES)) if s not in used]
        if free:
            self.players.append(Player(free[0], box))
            return
        # everyone is taken: reuse a player who has been gone a while
        stale = [p for p in self.players if now - p.last_seen > 1.0]
        if stale:
            old = min(stale, key=lambda p: p.last_seen)
            self.players.remove(old)
            self.players.append(Player(old.slot, box))

    def active_players(self):
        return [p for p in self.players if p.active]

    def reset_scores(self):
        for p in self.players:
            p.score = 0
            p.stack = []
