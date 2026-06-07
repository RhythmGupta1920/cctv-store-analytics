"""
Step 1 demo: person detection on CAM 1 (first N seconds).
Run from project root:
    python pipeline/detect_demo.py
"""

from pathlib import Path

import cv2
from ultralytics import YOLO

PROJECT_ROOT = Path(__file__).resolve().parent.parent
VIDEO_PATH = PROJECT_ROOT / "data" / "CCTV Footage" / "CAM 1.mp4"
OUTPUT_PATH = PROJECT_ROOT / "pipeline" / "output_cam1_demo.mp4"

# Process only this many seconds (keeps first run fast on Mac)
MAX_SECONDS = 15
MODEL_NAME = "yolov8n.pt"  # nano — fast; use yolov8s.pt for better accuracy
PERSON_CLASS_ID = 0


def main() -> None:
    if not VIDEO_PATH.exists():
        raise FileNotFoundError(f"Video not found: {VIDEO_PATH}")

    print(f"Loading model: {MODEL_NAME}")
    model = YOLO(MODEL_NAME)

    cap = cv2.VideoCapture(str(VIDEO_PATH))
    if not cap.isOpened():
        raise RuntimeError(f"Could not open video: {VIDEO_PATH}")

    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    max_frames = int(fps * MAX_SECONDS)

    print(f"Input: {VIDEO_PATH.name} ({width}x{height} @ {fps:.1f} fps)")
    print(f"Processing first {MAX_SECONDS}s (~{max_frames} frames)...")

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    writer = cv2.VideoWriter(
        str(OUTPUT_PATH),
        cv2.VideoWriter_fourcc(*"mp4v"),
        fps,
        (width, height),
    )

    frame_idx = 0
    person_count = 0

    while frame_idx < max_frames:
        ok, frame = cap.read()
        if not ok:
            break

        results = model(frame, classes=[PERSON_CLASS_ID], verbose=False)
        annotated = results[0].plot()
        person_count += len(results[0].boxes) if results[0].boxes is not None else 0

        writer.write(annotated)
        frame_idx += 1

        if frame_idx % 30 == 0:
            print(f"  {frame_idx}/{max_frames} frames...")

    cap.release()
    writer.release()

    print(f"\nDone! Processed {frame_idx} frames.")
    print(f"Total person detections (all frames): {person_count}")
    print(f"Output saved to: {OUTPUT_PATH}")
    print("Open that file in QuickTime to verify bounding boxes.")


if __name__ == "__main__":
    main()
