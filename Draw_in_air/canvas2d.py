import os
import time
from datetime import datetime

import cv2
import numpy as np

import config
import gestures
from hand_tracker import HandTracker
from tools import Confetti, ToolBar, bgr_to_rgb, blend_bgra, render_pill

TOAST_TIME = 1.2  # seconds a pop-up message stays on screen
SHAPE_TOOLS = ("line", "rectangle", "circle")
HOVER_GRACE = 0.3  # seconds the fingertip may slip off a button without restarting the hold timer


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
        self.toolbar = ToolBar(w, h)
        self.confetti = Confetti(self.toolbar.s)

        self.canvas = np.zeros((h, w, 3), dtype=np.uint8)
        self.undo_stack = []

        self.color = config.COLORS[0][1]
        self.rainbow_hue = 0
        self.tool = "pen"
        self.brush_size = config.BRUSH_SIZES[config.DEFAULT_BRUSH_INDEX]

        self.prev_point = None
        self.shape_start = None

        self.hover_button = None
        self.hover_start_time = 0.0
        self.hover_seen_time = 0.0

        self.toast_img = None
        self.toast_start = 0.0
        self.last_hand_time = time.time()

        os.makedirs(config.SAVE_DIR, exist_ok=True)
        self.next_mode = None  # "3d" to switch modes, None to quit
        self.running = True

    # ---------- state helpers ----------
    def _toast(self, text, fill_rgb=(255, 236, 179)):
        self.toast_img = render_pill(text, max(14, self.toolbar.S(34)), tuple(fill_rgb))
        self.toast_start = time.time()

    def _ink(self, advance=False):
        """Current drawing color; the rainbow color shifts hue a little on every stroke segment."""
        if self.color != config.RAINBOW:
            return self.color
        if advance:
            self.rainbow_hue = (self.rainbow_hue + 3) % 180
        hsv = np.uint8([[[self.rainbow_hue, 255, 255]]])
        return tuple(int(c) for c in cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)[0, 0])

    def _set_color(self, name, value):
        self.color = value
        self._toast(f"{name}!", bgr_to_rgb(self._ink()))

    def _push_undo(self):
        self.undo_stack.append(self.canvas.copy())
        if len(self.undo_stack) > 20:
            self.undo_stack.pop(0)

    def _undo(self):
        if self.undo_stack:
            self.canvas = self.undo_stack.pop()
            self._toast("Oops! Undo")
        else:
            self._toast("Nothing to undo")

    def _clear(self):
        self._push_undo()
        self.canvas[:] = 0
        self._toast("Fresh new page!", (255, 205, 210))

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
        self._toast("Saved! Great job!", (255, 224, 130))
        self.confetti.burst(self.width, self.height)

    def _apply_button(self, button):
        kind, value = button.action
        if kind == "color":
            self._set_color(button.label, value)
        elif kind == "tool":
            self.tool = value
            self._toast(button.label, (186, 225, 255))
        elif kind == "brush":
            self.brush_size = value
            self._toast(f"{button.label} brush", (200, 240, 200))
        elif kind == "action":
            if value == "undo":
                self._undo()
            elif value == "clear":
                self._clear()
            elif value == "save":
                self._save()
            elif value == "mode3d":
                self.next_mode = "3d"
                self.running = False
            elif value == "quit":
                self.running = False

    def _update_hover(self, btn):
        """Select a button once the fingertip has rested on it for HOVER_SELECT_TIME."""
        now = time.time()
        if btn is None:
            # forgive a brief wobble off the button (or a missed frame) before resetting the timer
            if self.hover_button is not None and now - self.hover_seen_time > HOVER_GRACE:
                self.hover_button = None
            return
        self.hover_seen_time = now
        if btn is not self.hover_button:
            self.hover_button = btn
            self.hover_start_time = now
        elif now - self.hover_start_time >= config.HOVER_SELECT_TIME:
            self._apply_button(btn)
            self.hover_start_time = now + 1.0  # cooldown so it doesn't re-fire

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
        cv2.line(self.canvas, self.prev_point, pt, self._ink(advance=True), self.brush_size, cv2.LINE_AA)
        self.prev_point = pt

    def _draw_shape(self, img, pt):
        color = self._ink()
        if self.tool == "line":
            cv2.line(img, self.shape_start, pt, color, self.brush_size, cv2.LINE_AA)
        elif self.tool == "rectangle":
            cv2.rectangle(img, self.shape_start, pt, color, self.brush_size, cv2.LINE_AA)
        elif self.tool == "circle":
            radius = int(np.hypot(pt[0] - self.shape_start[0], pt[1] - self.shape_start[1]))
            cv2.circle(img, self.shape_start, radius, color, self.brush_size, cv2.LINE_AA)

    def _preview_shape(self, frame, pt):
        if self.shape_start is not None:
            self._draw_shape(frame, pt)

    def _commit_shape(self, pt):
        if self.shape_start is None:
            return
        self._draw_shape(self.canvas, pt)
        self._ink(advance=True)
        self.shape_start = None

    # ---------- overlays ----------
    def _draw_cursor(self, frame, pt, gesture):
        white, ink = (255, 255, 255), (90, 50, 40)
        if gesture == gestures.GESTURE_DRAW:
            if self.tool == "eraser":
                cv2.circle(frame, pt, config.ERASER_SIZE, white, 3, cv2.LINE_AA)
                cv2.circle(frame, pt, config.ERASER_SIZE + 2, ink, 1, cv2.LINE_AA)
            else:
                r = max(self.brush_size // 2, 6)
                cv2.circle(frame, pt, r + 3, white, -1, cv2.LINE_AA)
                cv2.circle(frame, pt, r, self._ink(), -1, cv2.LINE_AA)
        elif gesture == gestures.GESTURE_SELECT:
            r = self.toolbar.S(16)
            cv2.circle(frame, pt, r, white, 4, cv2.LINE_AA)
            cv2.circle(frame, pt, r + 3, ink, 1, cv2.LINE_AA)
            cv2.circle(frame, pt, max(4, r // 3), self._ink(), -1, cv2.LINE_AA)

    def _draw_messages(self, frame, hand_seen):
        if self.toast_img is not None:
            age = time.time() - self.toast_start
            if age > TOAST_TIME:
                self.toast_img = None
            else:
                fade = min(1.0, (TOAST_TIME - age) / 0.3)
                pop = min(1.0, age / 0.12)  # quick slide-down when it appears
                th, tw = self.toast_img.shape[:2]
                y = self.toolbar.top_h + int(self.toolbar.S(14) * pop)
                blend_bgra(frame, self.toast_img, (self.width - tw) // 2, y, fade)

        if not hand_seen and time.time() - self.last_hand_time > config.NO_HAND_HINT_DELAY:
            hint = render_pill("Show me your hand!", max(14, self.toolbar.S(40)), (255, 255, 255))
            bob = int(self.toolbar.S(8) * np.sin(time.time() * 4))
            th, tw = hint.shape[:2]
            blend_bgra(frame, hint, (self.width - tw) // 2, (self.height - th) // 2 + bob)

    # ---------- main loop ----------
    def run(self):
        window = "Draw in Air"
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
                self.last_hand_time = time.time()
                handedness = self.tracker.get_handedness_label()
                fingers = self.tracker.fingers_up(points, handedness)
                index_tip = points[8][:2]
                gesture = gestures.classify(fingers)

            is_shape_tool = self.tool in SHAPE_TOOLS
            pointing = gesture in (gestures.GESTURE_DRAW, gestures.GESTURE_SELECT) and index_tip
            over_ui = pointing and self.toolbar.is_ui_area(*index_tip)

            if over_ui:
                # pointing at the buttons: finish any shape, never draw, and pick whatever is held on
                if is_shape_tool and self.shape_start is not None:
                    self._commit_shape(index_tip)
                self.prev_point = None
                self._update_hover(self.toolbar.hit_test(*index_tip))
            elif gesture == gestures.GESTURE_DRAW and index_tip:
                if is_shape_tool:
                    if self.shape_start is None:
                        self._push_undo()
                        self.shape_start = index_tip
                    self._preview_shape(frame, index_tip)
                else:
                    if self.prev_point is None:
                        self._push_undo()
                    self._draw_stroke(index_tip)
                self._update_hover(None)
            else:
                self.prev_point = None
                if is_shape_tool and self.shape_start is not None and index_tip:
                    self._commit_shape(index_tip)
                self._update_hover(None)

            frame = self._merge(frame)

            hover_progress = 0.0
            if self.hover_button is not None:
                hover_progress = (time.time() - self.hover_start_time) / config.HOVER_SELECT_TIME
            frame = self.toolbar.draw(frame, self.color, self.tool, self.brush_size,
                                      self.hover_button, hover_progress)

            if index_tip:
                self._draw_cursor(frame, index_tip, gestures.GESTURE_SELECT if over_ui else gesture)
            self.confetti.draw(frame)
            self._draw_messages(frame, points is not None and len(points) > 0)

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
                self.next_mode = "3d"
                self.running = False
            elif ord('1') <= key <= ord('9'):
                idx = key - ord('1')
                if idx < len(config.COLORS):
                    self._set_color(*config.COLORS[idx])
            elif key in (ord('+'), ord('=')):
                self.brush_size = min(60, self.brush_size + 2)
            elif key == ord('-'):
                self.brush_size = max(2, self.brush_size - 2)

        self.cap.release()
        cv2.destroyWindow(window)
        self.tracker.close()
        return self.next_mode
