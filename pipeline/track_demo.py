"""
Step 2 demo: person tracking on CAM 1 (stable IDs across frames).
Run from project root:
    python pipeline/track_demo.py
"""

import csv
from pathlib import Path

import cv2
from ultralytics import YOLO

PROJECT_ROOT = Path(__file__).resolve().parent.parent
VIDEO_PATH = PROJECT_ROOT / "data" / "CCTV Footage" / "CAM 1.mp4"
OUTPUT_VIDEO = PROJECT_ROOT / "pipeline" / "output_cam1_tracked.mp4"
OUTPUT_CSV = PROJECT_ROOT / "pipeline" / "tracks_cam1.csv"

MAX_SECONDS = 15
MODEL_NAME = "yolov8n.pt"
PERSON_CLASS_ID = 0
TRACKER = "bytetrack.yaml"


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
    print(f"Tracker: {TRACKER}")
    print(f"Processing first {MAX_SECONDS}s (~{max_frames} frames)...")

    OUTPUT_VIDEO.parent.mkdir(parents=True, exist_ok=True)
    writer = cv2.VideoWriter(
        str(OUTPUT_VIDEO),
        cv2.VideoWriter_fourcc(*"mp4v"),
        fps,
        (width, height),
    )

    track_rows: list[dict] = []
    unique_ids: set[int] = set()
    frame_idx = 0

    while frame_idx < max_frames:
        ok, frame = cap.read()
        if not ok:
            break

        results = model.track(
            frame,
            classes=[PERSON_CLASS_ID],
            tracker=TRACKER,
            persist=True,
            verbose=False,
        )

        result = results[0]
        annotated = result.plot()

        if result.boxes is not None and result.boxes.id is not None:
            boxes = result.boxes.xyxy.cpu().numpy()
            ids = result.boxes.id.int().cpu().tolist()

            for track_id, (x1, y1, x2, y2) in zip(ids, boxes):
                unique_ids.add(track_id)
                cx = (x1 + x2) / 2
                cy = (y1 + y2) / 2
                track_rows.append(
                    {
                        "frame": frame_idx,
                        "timestamp_sec": round(frame_idx / fps, 3),
                        "track_id": track_id,
                        "x_center": round(cx, 1),
                        "y_center": round(cy, 1),
                        "x1": round(x1, 1),
                        "y1": round(y1, 1),
                        "x2": round(x2, 1),
                        "y2": round(y2, 1),
                    }
                )

        writer.write(annotated)
        frame_idx += 1

        if frame_idx % 30 == 0:
            print(f"  {frame_idx}/{max_frames} frames...")

    cap.release()
    writer.release()

    with OUTPUT_CSV.open("w", newline="") as f:
        writer_csv = csv.DictWriter(
            f,
            fieldnames=[
                "frame",
                "timestamp_sec",
                "track_id",
                "x_center",
                "y_center",
                "x1",
                "y1",
                "x2",
                "y2",
            ],
        )
        writer_csv.writeheader()
        writer_csv.writerows(track_rows)

    print(f"\nDone! Processed {frame_idx} frames.")
    print(f"Unique people tracked: {len(unique_ids)}")
    print(f"Track records saved: {len(track_rows)}")
    print(f"Video: {OUTPUT_VIDEO}")
    print(f"CSV:   {OUTPUT_CSV}")
    print("Open the video — each person should keep the same ID label as they move.")


if __name__ == "__main__":
    main()
