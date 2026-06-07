"""Map track positions to store zones using polygon definitions."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml
from shapely.geometry import Point, Polygon


@dataclass(frozen=True)
class Zone:
    name: str
    label: str
    polygon: Polygon


class ZoneMapper:
    def __init__(self, config_path: Path) -> None:
        with config_path.open() as f:
            config = yaml.safe_load(f)

        self.camera = config["camera"]
        self.frame_size = tuple(config["frame_size"])
        self.zones: list[Zone] = []

        for item in config["zones"]:
            self.zones.append(
                Zone(
                    name=item["name"],
                    label=item["label"],
                    polygon=Polygon(item["polygon"]),
                )
            )

    def zone_at(self, x: float, y: float) -> Zone | None:
        point = Point(x, y)
        matches = [zone for zone in self.zones if zone.polygon.contains(point)]
        if not matches:
            return None
        # Prefer smallest zone when polygons overlap.
        return min(matches, key=lambda zone: zone.polygon.area)

    def zone_name_at(self, x: float, y: float) -> str | None:
        zone = self.zone_at(x, y)
        return zone.name if zone else None
