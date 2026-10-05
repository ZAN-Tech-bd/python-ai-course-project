"""Everyday-object detection with YOLOX (OpenCV DNN), run in a background thread so the video stays smooth."""

import threading
import time

import cv2
import numpy as np

COCO_NAMES = [
    "person", "bicycle", "car", "motorcycle", "airplane", "bus", "train", "truck", "boat", "traffic light",
    "fire hydrant", "stop sign", "parking meter", "bench", "bird", "cat", "dog", "horse", "sheep", "cow",
    "elephant", "bear", "zebra", "giraffe", "backpack", "umbrella", "handbag", "tie", "suitcase", "frisbee",
    "skis", "snowboard", "sports ball", "kite", "baseball bat", "baseball glove", "skateboard", "surfboard",
    "tennis racket", "bottle", "wine glass", "cup", "fork", "knife", "spoon", "bowl", "banana", "apple",
    "sandwich", "orange", "broccoli", "carrot", "hot dog", "pizza", "donut", "cake", "chair", "couch",
    "potted plant", "bed", "dining table", "toilet", "tv", "laptop", "mouse", "remote", "keyboard", "cell phone",
    "microwave", "oven", "toaster", "sink", "refrigerator", "book", "clock", "vase", "scissors", "teddy bear",
    "hair drier", "toothbrush",
]


class ObjectDetector:
    """YOLOX-S from the OpenCV model zoo. detect() returns [(name, score, (x, y, w, h)), ...]."""

    INPUT = 640
    STRIDES = (8, 16, 32)

    def __init__(self, model_path, score_threshold=0.45, nms_threshold=0.45):
        self.net = cv2.dnn.readNet(model_path)
        self.score_threshold = score_threshold
        self.nms_threshold = nms_threshold
        grids, strides = [], []
        for s in self.STRIDES:
            n = self.INPUT // s
            yv, xv = np.meshgrid(np.arange(n), np.arange(n), indexing="ij")
            grids.append(np.stack((xv, yv), 2).reshape(-1, 2))
            strides.append(np.full((n * n, 1), s))
        self.grids = np.concatenate(grids).astype(np.float32)
        self.strides = np.concatenate(strides).astype(np.float32)

    def detect(self, frame_bgr):
        h, w = frame_bgr.shape[:2]
        ratio = min(self.INPUT / h, self.INPUT / w)
        resized = cv2.resize(frame_bgr, (int(w * ratio), int(h * ratio)))
        padded = np.full((self.INPUT, self.INPUT, 3), 114, dtype=np.uint8)
        padded[:resized.shape[0], :resized.shape[1]] = resized
        blob = cv2.dnn.blobFromImage(cv2.cvtColor(padded, cv2.COLOR_BGR2RGB))  # raw 0-255 pixels, NCHW
        self.net.setInput(blob)
        out = self.net.forward()[0]

        xy = (out[:, :2] + self.grids) * self.strides
        wh = np.exp(out[:, 2:4]) * self.strides
        scores = out[:, 4:5] * out[:, 5:]
        cls = scores.argmax(1)
        conf = scores[np.arange(len(cls)), cls]
        keep = conf > self.score_threshold
        if not keep.any():
            return []
        xy, wh, cls, conf = xy[keep], wh[keep], cls[keep], conf[keep]
        boxes = np.concatenate([xy - wh / 2, wh], 1) / ratio
        idx = cv2.dnn.NMSBoxesBatched(boxes.tolist(), conf.tolist(), cls.tolist(),
                                      self.score_threshold, self.nms_threshold)
        results = []
        for i in np.array(idx).flatten():
            x, y, bw, bh = boxes[i]
            x0, y0 = max(0, int(x)), max(0, int(y))
            x1, y1 = min(w, int(x + bw)), min(h, int(y + bh))
            results.append((COCO_NAMES[cls[i]], float(conf[i]), (x0, y0, x1 - x0, y1 - y0)))
        return results


class BackgroundObjectDetector:
    """Runs ObjectDetector on the newest frame in a worker thread; .results always holds the latest answer."""

    def __init__(self, detector):
        self.detector = detector
        self.results = []
        self.ms = 0.0
        self._frame = None
        self._lock = threading.Lock()
        self._wake = threading.Event()
        self._stop = False
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def submit(self, frame):
        with self._lock:
            self._frame = frame.copy()
        self._wake.set()

    def _loop(self):
        while not self._stop:
            self._wake.wait()
            self._wake.clear()
            with self._lock:
                frame, self._frame = self._frame, None
            if frame is None:
                continue
            start = time.perf_counter()
            self.results = self.detector.detect(frame)
            self.ms = (time.perf_counter() - start) * 1000

    def stop(self):
        self._stop = True
        self._wake.set()
        self._thread.join(timeout=2)
