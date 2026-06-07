"""
Step 4: FastAPI backend for store intelligence analytics.
Run from project root:
    uvicorn api.main:app --reload --port 8000
"""

from __future__ import annotations

import asyncio
import json

from typing import List, Optional

from fastapi import FastAPI, Query, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from api.schemas import (
    Anomaly,
    FootfallResponse,
    HealthResponse,
    SummaryResponse,
    TrackSummary,
    ZoneAnalyticsResponse,
    ZoneEvent,
)
from api.store import DataStore

app = FastAPI(
    title="Store Intelligence API",
    description="Real-time retail analytics from CCTV tracking and zone events.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

store = DataStore()


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        camera=store.camera_id,
        events_loaded=len(store.events),
        assignments_loaded=len(store.assignments),
    )


@app.get("/analytics/summary", response_model=SummaryResponse)
def analytics_summary() -> SummaryResponse:
    return store.summary()


@app.get("/analytics/footfall", response_model=FootfallResponse)
def analytics_footfall() -> FootfallResponse:
    return store.footfall()


@app.get("/analytics/zones", response_model=ZoneAnalyticsResponse)
def analytics_zones() -> ZoneAnalyticsResponse:
    return store.zone_analytics()


@app.get("/events", response_model=List[ZoneEvent])
def list_events(
    event_type: Optional[str] = Query(default=None, description="zone_entered or zone_exited"),
    track_id: Optional[int] = Query(default=None),
    zone: Optional[str] = Query(default=None),
) -> List[ZoneEvent]:
    return store.get_events(event_type=event_type, track_id=track_id, zone=zone)


@app.get("/tracks", response_model=List[TrackSummary])
def list_tracks() -> List[TrackSummary]:
    return store.track_summaries()


@app.get("/anomalies", response_model=List[Anomaly])
def list_anomalies() -> List[Anomaly]:
    return store.anomalies()


@app.post("/reload")
def reload_data() -> dict[str, str]:
    store.reload()
    return {"status": "reloaded"}


@app.websocket("/ws/live")
async def live_updates(websocket: WebSocket) -> None:
    await websocket.accept()
    try:
        while True:
            payload = {
                "summary": store.summary().model_dump(),
                "footfall": store.footfall().model_dump(),
                "zones": store.zone_analytics().model_dump(),
                "recent_events": [event.model_dump() for event in store.events[-5:]],
            }
            await websocket.send_text(json.dumps(payload))
            await asyncio.sleep(2)
    except WebSocketDisconnect:
        return
