import os
import time
from datetime import datetime

import cv2
import numpy as np

import config
import gestures
from hand_tracker import HandTracker
from tools import ToolBar


class AirCanvas2D:
    """Finger-tracked 2D drawing canvas with a gesture-driven toolbar."""

    def __init__(self):
        self.cap = cv2.VideoCapture(config.CAMERA_INDEX)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, config.FRAME_WIDTH)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, config.FRAME_HEIGHT)

        ok, frame = self.cap.read()
        if not ok:
            raise RuntimeError("Could not access the webcam.")
        h, w = frame.shape[:2]
        self.width, self.height = w, h

        self.tracker = HandTracker(max_hands=1)
        self.toolbar = ToolBar(w)

        self.canvas = np.zeros((h, w, 3), dtype=np.uint8)
        self.undo_stack = []

        self.color = config.COLORS[0][1]
        self.tool = "pen"
        self.brush_size = config.BRUSH_SIZES[config.DEFAULT_BRUSH_INDEX]

        self.prev_point = None
        self.shape_start = None

        self.hover_button = None
        self.hover_start_time = 0.0

        os.makedirs(config.SAVE_DIR, exist_ok=True)
        self.switch_to_3d = False
        self.running = True

    # ---------- state helpers ----------
    def _push_undo(self):
        self.undo_stack.append(self.canvas.copy())
        if len(self.undo_stack) > 20:
            self.undo_stack.pop(0)

    def _undo(self):
        if self.undo_stack:
            self.canvas = self.undo_stack.pop()

    def _clear(self):
        self._push_undo()
        self.canvas[:] = 0

    def _save(self):
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = os.path.join(config.SAVE_DIR, f"drawing_{ts}.png")
        white_bg = np.full_like(self.canvas, 255)
        gray = cv2.cvtColor(self.canvas, cv2.COLOR_BGR2GRAY)
        _, mask_inv = cv2.threshold(gray, 5, 255, cv2.THRESH_BINARY_INV)
        white_bg = cv2.bitwise_and(white_bg, white_bg, mask=mask_inv)
        out = cv2.add(white_bg, self.canvas)
        cv2.imwrite(path, out)
        print(f"Saved: {path}")

    def _apply_button(self, button):
        kind, value = button.action
        if kind == "color":
            self.color = value
        elif kind == "tool":
            self.tool = value
        elif kind == "brush":
            self.brush_size = value
        elif kind == "action":
            if value == "undo":
                self._undo()
            elif value == "clear":
                self._clear()
            elif value == "save":
                self._save()
            elif value == "mode3d":
                self.switch_to_3d = True
                self.running = False

    def _merge(self, frame):
        gray = cv2.cvtColor(self.canvas, cv2.COLOR_BGR2GRAY)
        _, mask = cv2.threshold(gray, 5, 255, cv2.THRESH_BINARY)
        mask_inv = cv2.bitwise_not(mask)
        bg = cv2.bitwise_and(frame, frame, mask=mask_inv)
        fg = cv2.bitwise_and(self.canvas, self.canvas, mask=mask)
        return cv2.add(bg, fg)

    def _draw_stroke(self, pt):
        if self.tool == "eraser":
            cv2.circle(self.canvas, pt, config.ERASER_SIZE, (0, 0, 0), -1)
            self.prev_point = pt
            return
        if self.prev_point is None:
            self.prev_point = pt
            return
        cv2.line(self.canvas, self.prev_point, pt, self.color, self.brush_size, cv2.LINE_AA)
        self.prev_point = pt

    def _preview_shape(self, frame, pt):
        if self.shape_start is None:
            return
        if self.tool == "line":
            cv2.line(frame, self.shape_start, pt, self.color, self.brush_size, cv2.LINE_AA)
        elif self.tool == "rectangle":
            cv2.rectangle(frame, self.shape_start, pt, self.color, self.brush_size)
        elif self.tool == "circle":
            radius = int(np.hypot(pt[0] - self.shape_start[0], pt[1] - self.shape_start[1]))
            cv2.circle(frame, self.shape_start, radius, self.color, self.brush_size)

    def _commit_shape(self, pt):
        if self.shape_start is None:
            return
        if self.tool == "line":
            cv2.line(self.canvas, self.shape_start, pt, self.color, self.brush_size, cv2.LINE_AA)
        elif self.tool == "rectangle":
            cv2.rectangle(self.canvas, self.shape_start, pt, self.color, self.brush_size)
        elif self.tool == "circle":
            radius = int(np.hypot(pt[0] - self.shape_start[0], pt[1] - self.shape_start[1]))
            cv2.circle(self.canvas, self.shape_start, radius, self.color, self.brush_size)
        self.shape_start = None

    # ---------- main loop ----------
    def run(self):
        window = "Draw in Air - 2D"
        cv2.namedWindow(window)

        while self.running:
            ok, frame = self.cap.read()
            if not ok:
                break
            frame = cv2.flip(frame, 1)

            self.tracker.process(frame)
            points = self.tracker.get_landmark_list(frame)
            gesture = gestures.GESTURE_UNKNOWN
            index_tip = None

            if points:
                handedness = self.tracker.get_handedness_label()
                fingers = self.tracker.fingers_up(points, handedness)
                index_tip = points[8][:2]
                gesture = gestures.classify(fingers)

            is_shape_tool = self.tool in ("line", "rectangle", "circle")

            if gesture == gestures.GESTURE_DRAW and index_tip:
                if index_tip[1] > self.toolbar.height:
                    if is_shape_tool:
                        if self.shape_start is None:
                            self._push_undo()
                            self.shape_start = index_tip
                        self._preview_shape(frame, index_tip)
                    else:
                        if self.prev_point is None:
                            self._push_undo()
                        self._draw_stroke(index_tip)
                self.hover_button = None
            elif gesture == gestures.GESTURE_SELECT and index_tip:
                if is_shape_tool and self.shape_start is not None:
                    self._commit_shape(index_tip)
                self.prev_point = None

                btn = self.toolbar.hit_test(*index_tip)
                if btn is not None and btn is self.hover_button:
                    if time.time() - self.hover_start_time >= config.HOVER_SELECT_TIME:
                        self._apply_button(btn)
                        self.hover_start_time = time.time() + 1.0  # cooldown so it doesn't re-fire
                elif btn is not None:
                    self.hover_button = btn
                    self.hover_start_time = time.time()
                else:
                    self.hover_button = None
            else:
                self.prev_point = None
                if is_shape_tool and self.shape_start is not None and index_tip:
                    self._commit_shape(index_tip)
                self.hover_button = None

            frame = self._merge(frame)

            hover_progress = 0.0
            if self.hover_button is not None:
                hover_progress = (time.time() - self.hover_start_time) / config.HOVER_SELECT_TIME
            frame = self.toolbar.draw(frame, self.color, self.tool, self.brush_size,
                                       self.hover_button, hover_progress)

            cv2.putText(frame, f"Tool: {self.tool}  Brush: {self.brush_size}",
                        (10, self.height - 15), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1, cv2.LINE_AA)
            cv2.putText(frame, "Index=Draw  Index+Middle=Select  Q=Quit  C=Clear  S=Save  Z=Undo  M=3D mode",
                        (10, self.height - 40), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1, cv2.LINE_AA)

            cv2.imshow(window, frame)
            key = cv2.waitKey(1) & 0xFF
            if key in (ord('q'), 27):
                self.running = False
            elif key == ord('c'):
                self._clear()
            elif key == ord('s'):
                self._save()
            elif key == ord('z'):
                self._undo()
            elif key == ord('e'):
                self.tool = "eraser"
            elif key == ord('p'):
                self.tool = "pen"
            elif key == ord('m'):
                self.switch_to_3d = True
                self.running = False
            elif ord('1') <= key <= ord('9'):
                idx = key - ord('1')
                if idx < len(config.COLORS):
                    self.color = config.COLORS[idx][1]
            elif key in (ord('+'), ord('=')):
                self.brush_size = min(60, self.brush_size + 2)
            elif key == ord('-'):
                self.brush_size = max(2, self.brush_size - 2)

        self.cap.release()
        cv2.destroyWindow(window)
        self.tracker.close()
        return self.switch_to_3d
