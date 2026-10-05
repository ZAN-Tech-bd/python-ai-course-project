import cv2

import config


class Button:
    def __init__(self, x, y, w, h, label, action, color=None):
        self.x, self.y, self.w, self.h = x, y, w, h
        self.label = label
        self.action = action  # (kind, value) e.g. ("color", (0,0,255)) / ("tool", "pen") / ("action", "clear")
        self.color = color

    def contains(self, px, py):
        return self.x <= px <= self.x + self.w and self.y <= py <= self.y + self.h

    def center(self):
        return self.x + self.w // 2, self.y + self.h // 2


class ToolBar:
    def __init__(self, frame_width):
        self.width = frame_width
        self.buttons = []
        self.height = 0
        self._layout()

    def _layout(self):
        x, y, size, gap = 10, 10, 46, 8

        for name, color in config.COLORS:
            self.buttons.append(Button(x, y, size, size, name, ("color", color), color))
            x += size + gap

        x += 20
        for tool in config.TOOLS:
            self.buttons.append(Button(x, y, size, size, tool, ("tool", tool)))
            x += size + gap

        x += 20
        for i, s in enumerate(config.BRUSH_SIZES):
            self.buttons.append(Button(x, y, size, size, f"B{i + 1}", ("brush", s)))
            x += size + gap

        x += 20
        extras = [
            ("Eraser", ("tool", "eraser")),
            ("Undo", ("action", "undo")),
            ("Clear", ("action", "clear")),
            ("Save", ("action", "save")),
            ("3D", ("action", "mode3d")),
        ]
        for label, action in extras:
            self.buttons.append(Button(x, y, size, size, label, action))
            x += size + gap

        self.height = y + size + 10

    def hit_test(self, px, py):
        for b in self.buttons:
            if b.contains(px, py):
                return b
        return None

    def draw(self, frame, active_color, active_tool, active_brush, hover_button=None, hover_progress=0.0):
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0), (self.width, self.height), (30, 30, 30), -1)
        cv2.addWeighted(overlay, 0.75, frame, 0.25, 0, frame)

        for b in self.buttons:
            kind = b.action[0]
            if kind == "color":
                cv2.rectangle(frame, (b.x, b.y), (b.x + b.w, b.y + b.h), b.color, -1)
                if b.action[1] == active_color:
                    cv2.rectangle(frame, (b.x - 3, b.y - 3), (b.x + b.w + 3, b.y + b.h + 3), (255, 255, 255), 2)
            else:
                is_active = (kind == "tool" and b.action[1] == active_tool) or \
                            (kind == "brush" and b.action[1] == active_brush)
                bg = (90, 90, 90) if is_active else (60, 60, 60)
                cv2.rectangle(frame, (b.x, b.y), (b.x + b.w, b.y + b.h), bg, -1)
                cv2.rectangle(frame, (b.x, b.y), (b.x + b.w, b.y + b.h), (200, 200, 200), 1)
                cv2.putText(frame, b.label[:4], (b.x + 4, b.y + b.h - 16),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.35, (255, 255, 255), 1, cv2.LINE_AA)

            if hover_button is b and hover_progress > 0:
                cx, cy = b.center()
                radius = int(max(b.w, b.h) * 0.6)
                angle = int(360 * min(hover_progress, 1.0))
                cv2.ellipse(frame, (cx, cy), (radius, radius), -90, 0, angle, (0, 255, 255), 3)

        return frame
