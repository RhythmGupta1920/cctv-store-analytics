from __future__ import annotations

from typing import List, Literal, Optional

from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str
    camera: str
    events_loaded: int
    assignments_loaded: int


class ZoneEvent(BaseModel):
    event_type: Literal["zone_entered", "zone_exited"]
    camera_id: str
    track_id: int
    zone: str
    zone_label: str
    timestamp_sec: float
    frame: int
    dwell_sec: Optional[float] = None


class FootfallResponse(BaseModel):
    camera_id: str
    unique_visitors: int
    total_track_records: int
    duration_sec: float
    visitors: List[int]


class ZoneStat(BaseModel):
    zone: str
    zone_label: str
    frame_count: int
    unique_visitors: int
    total_dwell_sec: float


class ZoneAnalyticsResponse(BaseModel):
    camera_id: str
    zones: List[ZoneStat]


class TrackSummary(BaseModel):
    track_id: int
    zones_visited: List[str]
    total_frames: int
    first_seen_sec: float
    last_seen_sec: float


class Anomaly(BaseModel):
    anomaly_type: str
    severity: Literal["low", "medium", "high"]
    message: str
    track_id: Optional[int] = None
    zone: Optional[str] = None
    timestamp_sec: Optional[float] = None
    value: Optional[float] = None


class SummaryResponse(BaseModel):
    camera_id: str
    unique_visitors: int
    total_events: int
    busiest_zone: Optional[str]
    avg_dwell_sec: float
    anomalies_count: int
