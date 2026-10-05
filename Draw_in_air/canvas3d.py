import math
import os
from datetime import datetime

import cv2
import numpy as np
import pygame
from pygame.locals import DOUBLEBUF, OPENGL, QUIT, KEYDOWN, MOUSEBUTTONDOWN, MOUSEBUTTONUP, MOUSEMOTION
from OpenGL.GL import (
    GL_COLOR_BUFFER_BIT, GL_DEPTH_BUFFER_BIT, GL_DEPTH_TEST, GL_LINE_SMOOTH,
    GL_LINES, GL_LINE_STRIP, GL_MODELVIEW, GL_PROJECTION, GL_RGB, GL_UNSIGNED_BYTE,
    glBegin, glClear, glClearColor, glColor3f, glEnable, glEnd, glLineWidth,
    glLoadIdentity, glMatrixMode, glReadPixels, glVertex3f,
)
from OpenGL.GLU import gluLookAt, gluPerspective

import config
import gestures
from hand_tracker import HandTracker

GL_COLORS = [
    (1.0, 0.2, 0.2),
    (1.0, 0.6, 0.1),
    (1.0, 1.0, 0.2),
    (0.2, 0.9, 0.2),
    (0.2, 0.9, 0.9),
    (0.3, 0.4, 1.0),
    (0.8, 0.2, 1.0),
    (1.0, 1.0, 1.0),
]


class AirCanvas3D:
    """Draw freehand strokes in 3D space using the fingertip's tracked depth (z)."""

    def __init__(self):
        self.cap = cv2.VideoCapture(config.CAMERA_INDEX)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        self.tracker = HandTracker(max_hands=1)

        self.strokes = []
        self.current_stroke = None
        self.color_index = 5
        self.line_width = 3.0

        self.yaw = 25.0
        self.pitch = 15.0
        self.distance = 6.0
        self.auto_rotate = True
        self.dragging = False
        self.last_mouse = (0, 0)

        os.makedirs(config.SAVE_DIR, exist_ok=True)
        self.switch_to_2d = False
        self.running = True
        self.win_w, self.win_h = 1000, 750

    def _init_gl(self):
        pygame.init()
        pygame.display.set_caption("Draw in Air - 3D")
        pygame.display.set_mode((self.win_w, self.win_h), DOUBLEBUF | OPENGL)
        glEnable(GL_DEPTH_TEST)
        glEnable(GL_LINE_SMOOTH)
        glClearColor(0.06, 0.06, 0.09, 1.0)
        glMatrixMode(GL_PROJECTION)
        gluPerspective(50, self.win_w / self.win_h, 0.1, 100.0)
        glMatrixMode(GL_MODELVIEW)

    @staticmethod
    def _map_to_gl(x, y, z):
        # MediaPipe x,y are normalized [0,1]; z is a small relative-depth value.
        gx = (x - 0.5) * 6.0
        gy = -(y - 0.5) * 6.0
        gz = -z * 14.0  # scaled up since raw z has a tiny dynamic range
        return gx, gy, gz

    @staticmethod
    def _draw_grid():
        glColor3f(0.25, 0.25, 0.3)
        glLineWidth(1.0)
        glBegin(GL_LINES)
        for i in range(-5, 6):
            glVertex3f(i, -3, -5)
            glVertex3f(i, -3, 5)
            glVertex3f(-5, -3, i)
            glVertex3f(5, -3, i)
        glEnd()
        glBegin(GL_LINES)
        glColor3f(0.8, 0.2, 0.2)
        glVertex3f(0, 0, 0)
        glVertex3f(2, 0, 0)
        glColor3f(0.2, 0.8, 0.2)
        glVertex3f(0, 0, 0)
        glVertex3f(0, 2, 0)
        glColor3f(0.2, 0.4, 0.9)
        glVertex3f(0, 0, 0)
        glVertex3f(0, 0, 2)
        glEnd()

    def _draw_strokes(self):
        glLineWidth(self.line_width)
        all_strokes = self.strokes + ([self.current_stroke] if self.current_stroke else [])
        for stroke in all_strokes:
            if not stroke or len(stroke["points"]) < 2:
                continue
            r, g, b = stroke["color"]
            glColor3f(r, g, b)
            glBegin(GL_LINE_STRIP)
            for p in stroke["points"]:
                glVertex3f(*p)
            glEnd()

    def _save_screenshot(self):
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = os.path.join(config.SAVE_DIR, f"drawing3d_{ts}.png")
        buf = glReadPixels(0, 0, self.win_w, self.win_h, GL_RGB, GL_UNSIGNED_BYTE)
        img = np.frombuffer(buf, dtype=np.uint8).reshape(self.win_h, self.win_w, 3)
        img = np.flipud(img)
        cv2.imwrite(path, cv2.cvtColor(img, cv2.COLOR_RGB2BGR))
        print(f"Saved: {path}")

    def _clear(self):
        self.strokes = []
        self.current_stroke = None

    def _undo(self):
        if self.strokes:
            self.strokes.pop()

    def _end_current_stroke(self):
        if self.current_stroke is not None:
            if len(self.current_stroke["points"]) > 1:
                self.strokes.append(self.current_stroke)
            self.current_stroke = None

    def _handle_events(self):
        for event in pygame.event.get():
            if event.type == QUIT:
                self.running = False
            elif event.type == KEYDOWN:
                key = event.key
                if key in (pygame.K_ESCAPE, pygame.K_q):
                    self.running = False
                elif key == pygame.K_c:
                    self._clear()
                elif key == pygame.K_s:
                    self._save_screenshot()
                elif key == pygame.K_z:
                    self._undo()
                elif key == pygame.K_r:
                    self.auto_rotate = not self.auto_rotate
                elif key == pygame.K_m:
                    self.switch_to_2d = True
                    self.running = False
                elif key == pygame.K_EQUALS:
                    self.line_width = min(12, self.line_width + 1)
                elif key == pygame.K_MINUS:
                    self.line_width = max(1, self.line_width - 1)
                elif pygame.K_1 <= key <= pygame.K_8:
                    self.color_index = key - pygame.K_1
            elif event.type == MOUSEBUTTONDOWN:
                if event.button == 1:
                    self.dragging = True
                    self.last_mouse = event.pos
                    self.auto_rotate = False
                elif event.button in (4, 5):
                    self.distance += -0.5 if event.button == 4 else 0.5
                    self.distance = max(2.0, min(20.0, self.distance))
            elif event.type == MOUSEBUTTONUP:
                if event.button == 1:
                    self.dragging = False
            elif event.type == MOUSEMOTION and self.dragging:
                dx = event.pos[0] - self.last_mouse[0]
                dy = event.pos[1] - self.last_mouse[1]
                self.yaw += dx * 0.4
                self.pitch = max(-85, min(85, self.pitch + dy * 0.4))
                self.last_mouse = event.pos

    def _handle_hand_frame(self, preview_window):
        ok, frame = self.cap.read()
        if not ok:
            return
        frame = cv2.flip(frame, 1)
        self.tracker.process(frame)
        self.tracker.draw_landmarks(frame)
        points = self.tracker.get_landmark_list(frame)

        if points:
            handedness = self.tracker.get_handedness_label()
            fingers = self.tracker.fingers_up(points, handedness)
            gesture = gestures.classify(fingers)

            raw = self.tracker.results.multi_hand_landmarks[0].landmark[8]
            gl_pt = self._map_to_gl(raw.x, raw.y, raw.z)

            if gesture == gestures.GESTURE_DRAW:
                if self.current_stroke is None:
                    self.current_stroke = {"points": [], "color": GL_COLORS[self.color_index]}
                self.current_stroke["points"].append(gl_pt)
            else:
                self._end_current_stroke()

            cv2.putText(frame, f"Gesture: {gesture}", (10, 25),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
        else:
            self._end_current_stroke()

        cv2.putText(frame, "Index=Draw  Palm/Fist=Lift pen  1-8=Color  C=Clear  S=Save  Z=Undo  R=Rotate  M=2D",
                    (10, frame.shape[0] - 12), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (200, 200, 200), 1, cv2.LINE_AA)
        cv2.imshow(preview_window, frame)
        cv2.waitKey(1)

    def run(self):
        self._init_gl()
        preview_window = "Hand Camera (3D mode)"
        clock = pygame.time.Clock()

        while self.running:
            self._handle_events()
            self._handle_hand_frame(preview_window)

            if self.auto_rotate:
                self.yaw += 0.3

            glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
            glLoadIdentity()
            eye_x = self.distance * math.cos(math.radians(self.pitch)) * math.sin(math.radians(self.yaw))
            eye_y = self.distance * math.sin(math.radians(self.pitch))
            eye_z = self.distance * math.cos(math.radians(self.pitch)) * math.cos(math.radians(self.yaw))
            gluLookAt(eye_x, eye_y, eye_z, 0, 0, 0, 0, 1, 0)

            self._draw_grid()
            self._draw_strokes()

            pygame.display.flip()
            clock.tick(60)

        self.cap.release()
        try:
            cv2.destroyWindow(preview_window)
        except cv2.error:
            pass
        self.tracker.close()
        pygame.quit()
        return self.switch_to_2d
