"""
Step 3: map tracked people to store zones and emit zone events.
Run from project root:
    python pipeline/zone_events.py
"""

from __future__ import annotations

import csv
import json
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np
import yaml

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))

from zone_mapper import ZoneMapper

TRACKS_CSV = PROJECT_ROOT / "pipeline" / "tracks_cam1.csv"
ZONES_CONFIG = PROJECT_ROOT / "config" / "zones_cam1.yaml"
VIDEO_PATH = PROJECT_ROOT / "data" / "CCTV Footage" / "CAM 1.mp4"
OUTPUT_CSV = PROJECT_ROOT / "pipeline" / "zone_assignments_cam1.csv"
OUTPUT_EVENTS = PROJECT_ROOT / "pipeline" / "zone_events_cam1.json"
OUTPUT_VIDEO = PROJECT_ROOT / "pipeline" / "output_cam1_zones.mp4"
OUTPUT_FRAME = PROJECT_ROOT / "pipeline" / "cam1_zones_overlay.jpg"

MAX_SECONDS = 15


@dataclass
class TrackRow:
    frame: int
    timestamp_sec: float
    track_id: int
    x_center: float
    y_center: float


def load_tracks(path: Path) -> list[TrackRow]:
    rows: list[TrackRow] = []
    with path.open() as f:
        for row in csv.DictReader(f):
            rows.append(
                TrackRow(
                    frame=int(row["frame"]),
                    timestamp_sec=float(row["timestamp_sec"]),
                    track_id=int(row["track_id"]),
                    x_center=float(row["x_center"]),
                    y_center=float(row["y_center"]),
                )
            )
    return rows


def load_zone_colors(config_path: Path) -> dict[str, tuple[int, int, int]]:
    with config_path.open() as f:
        config = yaml.safe_load(f)

    palette = [
        (86, 180, 233),
        (230, 159, 0),
        (0, 158, 115),
        (204, 121, 167),
        (240, 228, 66),
    ]
    return {
        zone["name"]: palette[i % len(palette)]
        for i, zone in enumerate(config["zones"])
    }


def build_events(assignments: list[dict], mapper: ZoneMapper) -> list[dict]:
    events: list[dict] = []
    by_track: dict[int, list[dict]] = defaultdict(list)

    for row in assignments:
        by_track[row["track_id"]].append(row)

    zone_labels = {zone.name: zone.label for zone in mapper.zones}

    for track_id, rows in sorted(by_track.items()):
        current_zone: str | None = None
        entered_at: float | None = None

        for row in rows:
            zone = row["zone"]
            if zone == current_zone:
                continue

            if current_zone is not None and entered_at is not None:
                events.append(
                    {
                        "event_type": "zone_exited",
                        "camera_id": mapper.camera,
                        "track_id": track_id,
                        "zone": current_zone,
                        "zone_label": zone_labels[current_zone],
                        "timestamp_sec": row["timestamp_sec"],
                        "frame": row["frame"],
                        "dwell_sec": round(row["timestamp_sec"] - entered_at, 3),
                    }
                )

            if zone is not None:
                events.append(
                    {
                        "event_type": "zone_entered",
                        "camera_id": mapper.camera,
                        "track_id": track_id,
                        "zone": zone,
                        "zone_label": zone_labels[zone],
                        "timestamp_sec": row["timestamp_sec"],
                        "frame": row["frame"],
                    }
                )
                entered_at = row["timestamp_sec"]
            else:
                entered_at = None

            current_zone = zone

        if current_zone is not None and entered_at is not None:
            last = rows[-1]
            events.append(
                {
                    "event_type": "zone_exited",
                    "camera_id": mapper.camera,
                    "track_id": track_id,
                    "zone": current_zone,
                    "zone_label": zone_labels[current_zone],
                    "timestamp_sec": last["timestamp_sec"],
                    "frame": last["frame"],
                    "dwell_sec": round(last["timestamp_sec"] - entered_at, 3),
                }
            )

    events.sort(key=lambda event: (event["timestamp_sec"], event["track_id"]))
    return events


def draw_zone_overlay(
    frame,
    mapper: ZoneMapper,
    colors: dict[str, tuple[int, int, int]],
    active_tracks: dict[int, tuple[float, float, str | None]],
) -> None:
    overlay = frame.copy()
    for zone in mapper.zones:
        color = colors[zone.name]
        points = np.array(zone.polygon.exterior.coords[:-1], dtype=np.int32)
        cv2.fillPoly(overlay, [points], color)

    cv2.addWeighted(overlay, 0.25, frame, 0.75, 0, frame)

    for zone in mapper.zones:
        color = colors[zone.name]
        points = np.array(zone.polygon.exterior.coords[:-1], dtype=np.int32)
        cv2.polylines(frame, [points], True, color, 2)
        cx = int(points[:, 0].mean())
        cy = int(points[:, 1].mean())
        cv2.putText(
            frame,
            zone.label,
            (cx - 80, cy),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            color,
            2,
        )

    for track_id, (x, y, zone_name) in active_tracks.items():
        cv2.circle(frame, (int(x), int(y)), 8, (255, 255, 255), -1)
        label = f"ID {track_id}"
        if zone_name:
            label += f" | {zone_name}"
        cv2.putText(
            frame,
            label,
            (int(x) + 12, int(y) - 12),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (255, 255, 255),
            2,
        )


def main() -> None:
    if not TRACKS_CSV.exists():
        raise FileNotFoundError(
            f"Missing {TRACKS_CSV}. Run `python pipeline/track_demo.py` first."
        )

    mapper = ZoneMapper(ZONES_CONFIG)
    colors = load_zone_colors(ZONES_CONFIG)
    tracks = load_tracks(TRACKS_CSV)

    assignments: list[dict] = []
    tracks_by_frame: dict[int, list[TrackRow]] = defaultdict(list)
    for row in tracks:
        zone = mapper.zone_at(row.x_center, row.y_center)
        assignment = {
            "frame": row.frame,
            "timestamp_sec": row.timestamp_sec,
            "track_id": row.track_id,
            "x_center": row.x_center,
            "y_center": row.y_center,
            "zone": zone.name if zone else None,
            "zone_label": zone.label if zone else None,
        }
        assignments.append(assignment)
        tracks_by_frame[row.frame].append(row)

    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_CSV.open("w", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "frame",
                "timestamp_sec",
                "track_id",
                "x_center",
                "y_center",
                "zone",
                "zone_label",
            ],
        )
        writer.writeheader()
        writer.writerows(assignments)

    events = build_events(assignments, mapper)
    OUTPUT_EVENTS.write_text(json.dumps(events, indent=2))

    cap = cv2.VideoCapture(str(VIDEO_PATH))
    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    max_frames = int(fps * MAX_SECONDS)

    writer = cv2.VideoWriter(
        str(OUTPUT_VIDEO),
        cv2.VideoWriter_fourcc(*"mp4v"),
        fps,
        (width, height),
    )

    frame_idx = 0
    while frame_idx < max_frames:
        ok, frame = cap.read()
        if not ok:
            break

        active: dict[int, tuple[float, float, str | None]] = {}
        for row in tracks_by_frame.get(frame_idx, []):
            zone_name = mapper.zone_name_at(row.x_center, row.y_center)
            active[row.track_id] = (row.x_center, row.y_center, zone_name)

        draw_zone_overlay(frame, mapper, colors, active)
        if frame_idx == 0:
            cv2.imwrite(str(OUTPUT_FRAME), frame)
        writer.write(frame)
        frame_idx += 1

    cap.release()
    writer.release()

    zone_counts: dict[str, int] = defaultdict(int)
    for row in assignments:
        if row["zone"]:
            zone_counts[row["zone"]] += 1

    print("Zone mapping complete.")
    print(f"Assignments: {OUTPUT_CSV}")
    print(f"Events:      {OUTPUT_EVENTS}")
    print(f"Video:       {OUTPUT_VIDEO}")
    print(f"Preview:     {OUTPUT_FRAME}")
    print("\nZone occupancy (frame counts):")
    for zone in mapper.zones:
        print(f"  {zone.label}: {zone_counts.get(zone.name, 0)}")
    print(f"\nEvents generated: {len(events)}")
    for event in events[:8]:
        print(f"  {event['event_type']} | track {event['track_id']} | {event['zone_label']} @ {event['timestamp_sec']}s")
    if len(events) > 8:
        print("  ...")


if __name__ == "__main__":
    main()
