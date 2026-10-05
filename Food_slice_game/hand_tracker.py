import cv2
import mediapipe as mp


class HandTracker:
    """Thin wrapper around MediaPipe Hands for fingertip tracking and gesture helpers."""

    TIP_IDS = [4, 8, 12, 16, 20]

    def __init__(self, max_hands=1, detection_confidence=0.7, tracking_confidence=0.6):
        self.mp_hands = mp.solutions.hands
        self.hands = self.mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=max_hands,
            min_detection_confidence=detection_confidence,
            min_tracking_confidence=tracking_confidence,
        )
        self.mp_draw = mp.solutions.drawing_utils
        self.mp_styles = mp.solutions.drawing_styles
        self.results = None

    def process(self, frame_bgr):
        rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        rgb.flags.writeable = False
        self.results = self.hands.process(rgb)
        return self.results

    def draw_landmarks(self, frame):
        if self.results and self.results.multi_hand_landmarks:
            for hand_landmarks in self.results.multi_hand_landmarks:
                self.mp_draw.draw_landmarks(
                    frame,
                    hand_landmarks,
                    self.mp_hands.HAND_CONNECTIONS,
                    self.mp_styles.get_default_hand_landmarks_style(),
                    self.mp_styles.get_default_hand_connections_style(),
                )
        return frame

    def get_landmark_list(self, frame, hand_index=0):
        """Returns [(px, py, z), ...] for the requested hand, in pixel coords + raw depth."""
        h, w = frame.shape[:2]
        points = []
        if self.results and self.results.multi_hand_landmarks:
            if hand_index >= len(self.results.multi_hand_landmarks):
                return points
            hand = self.results.multi_hand_landmarks[hand_index]
            for lm in hand.landmark:
                points.append((int(lm.x * w), int(lm.y * h), lm.z))
        return points

    def get_handedness_label(self, hand_index=0):
        if self.results and self.results.multi_handedness:
            if hand_index < len(self.results.multi_handedness):
                return self.results.multi_handedness[hand_index].classification[0].label
        return "Right"

    def fingers_up(self, points, handedness_label="Right"):
        """Returns [thumb, index, middle, ring, pinky] as 1 (up) / 0 (down).

        Uses distances instead of "tip above joint", so it still works when the hand
        points sideways or down (e.g. reaching for the color buttons on the left).
        """
        if len(points) < 21:
            return [0, 0, 0, 0, 0]

        def dist(a, b):
            return ((points[a][0] - points[b][0]) ** 2 + (points[a][1] - points[b][1]) ** 2) ** 0.5

        # thumb is out when its tip is farther from the pinky knuckle than its middle joint is
        fingers = [1 if dist(4, 17) > dist(3, 17) * 1.1 else 0]
        # other fingers are straight when the tip is farther from the wrist than the middle joint
        for tip_id in (8, 12, 16, 20):
            fingers.append(1 if dist(tip_id, 0) > dist(tip_id - 2, 0) * 1.1 else 0)
        return fingers

    def close(self):
        self.hands.close()
