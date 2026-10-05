"""Real-time human face detection using OpenCV Haar cascades.

Usage:
    python main.py                 # detect faces from the webcam
    python main.py --camera 1      # use a different camera index
    python main.py --image photo.jpg   # detect faces in an image file instead
"""

import argparse
import sys
from pathlib import Path

import cv2


def build_face_detector(cascade_name: str = "haarcascade_frontalface_default.xml") -> cv2.CascadeClassifier:
    cascade_path = Path(cv2.data.haarcascades) / cascade_name
    detector = cv2.CascadeClassifier(str(cascade_path))
    if detector.empty():
        raise RuntimeError(f"Could not load face cascade from: {cascade_path}")
    return detector


def detect_faces(detector: cv2.CascadeClassifier, frame) -> list:
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    gray = cv2.equalizeHist(gray)
    faces = detector.detectMultiScale(
        gray,
        scaleFactor=1.1,
        minNeighbors=5,
        minSize=(40, 40),
    )
    return faces


def draw_faces(frame, faces) -> None:
    for (x, y, w, h) in faces:
        cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
    cv2.putText(
        frame,
        f"Faces: {len(faces)}",
        (10, 30),
        cv2.FONT_HERSHEY_SIMPLEX,
        1,
        (0, 255, 0),
        2,
    )


def run_on_image(detector: cv2.CascadeClassifier, image_path: str) -> None:
    frame = cv2.imread(image_path)
    if frame is None:
        raise FileNotFoundError(f"Could not read image: {image_path}")

    faces = detect_faces(detector, frame)
    draw_faces(frame, faces)
    print(f"Detected {len(faces)} face(s) in {image_path}")

    out_path = str(Path(image_path).with_stem(Path(image_path).stem + "_detected"))
    cv2.imwrite(out_path, frame)
    print(f"Saved annotated image to {out_path}")

    cv2.imshow("Face Detection - press any key to close", frame)
    cv2.waitKey(0)
    cv2.destroyAllWindows()


def run_on_webcam(detector: cv2.CascadeClassifier, camera_index: int) -> None:
    cap = cv2.VideoCapture(camera_index)
    if not cap.isOpened():
        raise RuntimeError(f"Could not open camera index {camera_index}")

    print("Starting webcam face detection. Press 'q' or ESC to quit.")
    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                print("Failed to read frame from camera.")
                break

            faces = detect_faces(detector, frame)
            draw_faces(frame, faces)

            cv2.imshow("Face Detection - press 'q' to quit", frame)
            key = cv2.waitKey(1) & 0xFF
            if key in (ord("q"), 27):
                break
    finally:
        cap.release()
        cv2.destroyAllWindows()


def parse_args(argv=None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Detect human faces with OpenCV.")
    parser.add_argument("--image", help="Path to an image file to run detection on.")
    parser.add_argument("--camera", type=int, default=0, help="Webcam index (default: 0).")
    return parser.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)
    detector = build_face_detector()

    if args.image:
        run_on_image(detector, args.image)
    else:
        run_on_webcam(detector, args.camera)
    return 0


if __name__ == "__main__":
    sys.exit(main())
