"""Downloads the pre-trained models (once) into the models/ folder."""

import sys
import urllib.request
from pathlib import Path

MODELS_DIR = Path(__file__).resolve().parent / "models"
ZOO = "https://github.com/opencv/opencv_zoo/raw/main/models"

MODELS = {
    # face detector (finds faces + 5 landmarks)
    "face_detector": ("face_detection_yunet_2023mar.onnx",
                      f"{ZOO}/face_detection_yunet/face_detection_yunet_2023mar.onnx"),
    # face recognizer (turns a face into a 128-number "fingerprint")
    "face_recognizer": ("face_recognition_sface_2021dec.onnx",
                        f"{ZOO}/face_recognition_sface/face_recognition_sface_2021dec.onnx"),
    # object detector (80 everyday object types, COCO dataset)
    "object_detector": ("object_detection_yolox_2022nov.onnx",
                        f"{ZOO}/object_detection_yolox/object_detection_yolox_2022nov.onnx"),
}


def _download(url: str, dest: Path) -> None:
    tmp = dest.with_suffix(dest.suffix + ".part")
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=60) as resp, open(tmp, "wb") as out:
        total = int(resp.headers.get("Content-Length") or 0)
        done, shown = 0, -1
        while True:
            chunk = resp.read(1 << 16)
            if not chunk:
                break
            out.write(chunk)
            done += len(chunk)
            percent = done * 100 // total if total else -1
            if percent != shown and percent % 10 == 0:
                print(f"  {dest.name}: {percent}% of {total / 1e6:.1f} MB", flush=True)
                shown = percent
    tmp.replace(dest)


def model_path(key: str) -> str:
    """Returns the local path of a model, downloading it first if needed."""
    filename, url = MODELS[key]
    path = MODELS_DIR / filename
    if not path.exists():
        MODELS_DIR.mkdir(exist_ok=True)
        print(f"Downloading {filename} (first run only)...")
        try:
            _download(url, path)
        except OSError as e:
            sys.exit(f"Could not download {filename}: {e}\nCheck your internet connection, or download it from\n"
                     f"  {url}\ninto {MODELS_DIR}")
    return str(path)
