from __future__ import annotations

import csv
import json
from collections import defaultdict
from pathlib import Path

from api.schemas import (
    Anomaly,
    FootfallResponse,
    SummaryResponse,
    TrackSummary,
    ZoneAnalyticsResponse,
    ZoneEvent,
    ZoneStat,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
EVENTS_PATH = PROJECT_ROOT / "pipeline" / "zone_events_cam1.json"
ASSIGNMENTS_PATH = PROJECT_ROOT / "pipeline" / "zone_assignments_cam1.csv"

LONG_DWELL_SEC = 10.0


class DataStore:
    def __init__(self) -> None:
        self.events: list[ZoneEvent] = []
        self.assignments: list[dict] = []
        self.camera_id = "CAM 1"
        self.reload()

    def reload(self) -> None:
        if not EVENTS_PATH.exists():
            raise FileNotFoundError(
                f"Missing {EVENTS_PATH}. Run `python pipeline/zone_events.py` first."
            )
        if not ASSIGNMENTS_PATH.exists():
            raise FileNotFoundError(
                f"Missing {ASSIGNMENTS_PATH}. Run `python pipeline/zone_events.py` first."
            )

        raw_events = json.loads(EVENTS_PATH.read_text())
        self.events = [ZoneEvent(**event) for event in raw_events]

        with ASSIGNMENTS_PATH.open() as f:
            self.assignments = list(csv.DictReader(f))

        if self.assignments:
            self.camera_id = self.assignments[0].get("camera_id") or self.events[0].camera_id

    def get_events(
        self,
        event_type: str | None = None,
        track_id: int | None = None,
        zone: str | None = None,
    ) -> list[ZoneEvent]:
        results = self.events
        if event_type:
            results = [event for event in results if event.event_type == event_type]
        if track_id is not None:
            results = [event for event in results if event.track_id == track_id]
        if zone:
            results = [event for event in results if event.zone == zone]
        return results

    def footfall(self) -> FootfallResponse:
        track_ids = sorted({int(row["track_id"]) for row in self.assignments})
        timestamps = [float(row["timestamp_sec"]) for row in self.assignments]
        duration = max(timestamps) - min(timestamps) if timestamps else 0.0

        return FootfallResponse(
            camera_id=self.camera_id,
            unique_visitors=len(track_ids),
            total_track_records=len(self.assignments),
            duration_sec=round(duration, 3),
            visitors=track_ids,
        )

    def zone_analytics(self) -> ZoneAnalyticsResponse:
        frame_counts: dict[str, int] = defaultdict(int)
        visitors: dict[str, set[int]] = defaultdict(set)
        dwell_totals: dict[str, float] = defaultdict(float)
        labels: dict[str, str] = {}

        for row in self.assignments:
            zone = row.get("zone")
            if not zone:
                continue
            frame_counts[zone] += 1
            visitors[zone].add(int(row["track_id"]))
            labels[zone] = row.get("zone_label") or zone

        for event in self.events:
            if event.event_type == "zone_exited" and event.dwell_sec is not None:
                dwell_totals[event.zone] += event.dwell_sec
                labels[event.zone] = event.zone_label

        zones = [
            ZoneStat(
                zone=zone,
                zone_label=labels.get(zone, zone),
                frame_count=frame_counts[zone],
                unique_visitors=len(visitors[zone]),
                total_dwell_sec=round(dwell_totals.get(zone, 0.0), 3),
            )
            for zone in sorted(frame_counts.keys())
        ]

        return ZoneAnalyticsResponse(camera_id=self.camera_id, zones=zones)

    def track_summaries(self) -> list[TrackSummary]:
        by_track: dict[int, list[dict]] = defaultdict(list)
        for row in self.assignments:
            by_track[int(row["track_id"])].append(row)

        summaries: list[TrackSummary] = []
        for track_id, rows in sorted(by_track.items()):
            zones = []
            seen = set()
            for row in rows:
                zone = row.get("zone")
                if zone and zone not in seen:
                    seen.add(zone)
                    zones.append(zone)

            timestamps = [float(row["timestamp_sec"]) for row in rows]
            summaries.append(
                TrackSummary(
                    track_id=track_id,
                    zones_visited=zones,
                    total_frames=len(rows),
                    first_seen_sec=min(timestamps),
                    last_seen_sec=max(timestamps),
                )
            )
        return summaries

    def anomalies(self) -> list[Anomaly]:
        results: list[Anomaly] = []

        for event in self.events:
            if event.event_type == "zone_exited" and event.dwell_sec is not None:
                if event.dwell_sec >= LONG_DWELL_SEC:
                    results.append(
                        Anomaly(
                            anomaly_type="long_dwell",
                            severity="medium",
                            message=(
                                f"Track {event.track_id} stayed in {event.zone_label} "
                                f"for {event.dwell_sec:.1f}s"
                            ),
                            track_id=event.track_id,
                            zone=event.zone,
                            timestamp_sec=event.timestamp_sec,
                            value=event.dwell_sec,
                        )
                    )

        footfall = self.footfall()
        if footfall.unique_visitors >= 2:
            billing_visitors = {
                int(row["track_id"])
                for row in self.assignments
                if row.get("zone") == "billing_counter"
            }
            if len(billing_visitors) >= 2:
                results.append(
                    Anomaly(
                        anomaly_type="billing_crowd",
                        severity="low",
                        message=(
                            f"{len(billing_visitors)} people detected at billing counter"
                        ),
                        zone="billing_counter",
                        value=float(len(billing_visitors)),
                    )
                )

        return results

    def summary(self) -> SummaryResponse:
        footfall = self.footfall()
        zones = self.zone_analytics().zones
        anomalies = self.anomalies()

        busiest = max(zones, key=lambda zone: zone.frame_count) if zones else None
        dwell_values = [
            event.dwell_sec
            for event in self.events
            if event.event_type == "zone_exited" and event.dwell_sec is not None
        ]
        avg_dwell = sum(dwell_values) / len(dwell_values) if dwell_values else 0.0

        return SummaryResponse(
            camera_id=self.camera_id,
            unique_visitors=footfall.unique_visitors,
            total_events=len(self.events),
            busiest_zone=busiest.zone_label if busiest else None,
            avg_dwell_sec=round(avg_dwell, 3),
            anomalies_count=len(anomalies),
        )
