"""Transport for NSW car park API.

The API needs a Transport for NSW API key. Register for one at
https://developer.transport.nsw.gov.au/ and paste it into the integration.
"""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime
from typing import Any

from ..models import Carpark
from .base import ProviderContext, as_float, as_int, first_value

OPERATOR = "Transport for NSW"
BASE_URL = "https://api.transport.nsw.gov.au/v1/carpark"
FULL_LIST_URL = f"{BASE_URL}/full-list"

_NAME_KEYS = ("facility_name", "facilityName", "name", "Name")
_ID_KEYS = ("facility_id", "facilityId", "id", "Id", "tsn", "TSN")
_TOTAL_KEYS = (
    "spots",
    "total_spots",
    "totalSpots",
    "capacity",
    "total",
    "space_count",
)
_FREE_KEYS = (
    "total_availability",
    "totalAvailability",
    "available",
    "availability",
    "free",
    "spaces_available",
)
_OCCUPIED_KEYS = (
    "total_occupied",
    "totalOccupied",
    "occupied",
    "spaces_occupied",
)
_LAT_KEYS = ("latitude", "Latitude", "lat")
_LON_KEYS = ("longitude", "Longitude", "lon", "lng")


def _entries(payload: Any) -> list[dict[str, Any]]:
    """Return the car park entries from an API payload."""
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if isinstance(payload, dict):
        for key in ("facilities", "carparks", "carParks", "results", "features"):
            value = payload.get(key)
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]
    return []


def _nested(entry: dict[str, Any], *names: str) -> dict[str, Any]:
    """Return the first nested dictionary found under *names*."""
    for name in names:
        value = entry.get(name)
        if isinstance(value, dict):
            return value
    return {}


def _coordinate(entry: dict[str, Any], keys: tuple[str, ...]) -> float | None:
    """Return a latitude or longitude from the entry or its coordinates."""
    value = first_value(entry, *keys)
    if value is None:
        coordinates = _nested(entry, "coordinates", "coordinate", "location")
        value = first_value(coordinates, *keys)
    if value is None:
        geometry = _nested(entry, "geometry")
        if keys is _LAT_KEYS:
            value = as_float(geometry.get("y"))
        else:
            value = as_float(geometry.get("x"))
    return as_float(value)


def _zone_totals(entry: dict[str, Any]) -> tuple[int | None, int | None]:
    """Return summed ``(total, free)`` for the zones inside an entry."""
    zones = entry.get("zones") or entry.get("Zones")
    if not isinstance(zones, list):
        return None, None
    total = 0
    free = 0
    seen_total = False
    seen_free = False
    for zone in zones:
        if not isinstance(zone, dict):
            continue
        zone_total = as_int(
            first_value(zone, "spots", "total_spots", "totalSpots", "capacity")
        )
        zone_free = as_int(
            first_value(
                zone,
                "availability",
                "total_availability",
                "totalAvailability",
                "free",
            )
        )
        if zone_total is not None:
            total += zone_total
            seen_total = True
        if zone_free is not None:
            free += zone_free
            seen_free = True
    return (total if seen_total else None, free if seen_free else None)


def parse_carpark_entry(entry: dict[str, Any]) -> Carpark | None:
    """Convert one API entry into a :class:`Carpark`.

    The API has changed field names across versions, so every value is
    looked up through a list of known aliases.
    """
    name = first_value(entry, *_NAME_KEYS)
    if not name:
        return None

    occupancy = _nested(entry, "occupancy", "Occupancy")
    zone_total, zone_free = _zone_totals(entry)

    total = as_int(first_value(entry, *_TOTAL_KEYS))
    if total is None:
        total = as_int(first_value(occupancy, "total", "occupied", "spots"))
    if total is None:
        total = zone_total

    free = as_int(first_value(entry, *_FREE_KEYS))
    if free is None:
        free = as_int(first_value(occupancy, "free", "available", "availability"))
    if free is None:
        free = zone_free

    occupied = as_int(first_value(entry, *_OCCUPIED_KEYS))
    if occupied is None:
        occupied = as_int(first_value(occupancy, "occupied", "total"))

    if free is None and occupied is not None and total is not None:
        free = max(0, total - occupied)

    key = first_value(entry, *_ID_KEYS)
    updated_raw = first_value(entry, "date", "Date", "last_updated", "updated")
    updated: datetime | None = None
    if isinstance(updated_raw, str) and updated_raw:
        try:
            updated = datetime.fromisoformat(updated_raw.replace("Z", "+00:00"))
        except ValueError:
            updated = None

    return Carpark(
        provider="nsw",
        key=str(key) if key else str(name),
        name=str(name),
        operator=OPERATOR,
        spaces_total=total,
        spaces_free=free,
        latitude=_coordinate(entry, _LAT_KEYS),
        longitude=_coordinate(entry, _LON_KEYS),
        address=(first_value(entry, "suburb", "Suburb", "address") or None),
        updated=updated,
        extra={"facility_id": key},
    )


def parse_carpark_payload(payload: Any) -> list[Carpark]:
    """Convert an API payload into a list of car parks."""
    carparks: list[Carpark] = []
    seen: set[str] = set()
    for entry in _entries(payload):
        carpark = parse_carpark_entry(entry)
        if carpark is None:
            continue
        if carpark.unique_id in seen:
            continue
        seen.add(carpark.unique_id)
        carparks.append(carpark)
    carparks.sort(key=lambda item: item.name.lower())
    return carparks


class NswProvider:
    """Live occupancy for Transport for NSW car parks."""

    key = "nsw"
    name = "Transport for NSW car parks"
    requires_api_key = True

    async def fetch(self, context: ProviderContext) -> list[Carpark]:
        """Return every car park the API reports on."""
        if not context.api_key:
            raise PermissionError("A Transport for NSW API key is required")
        headers = {"Authorization": f"apikey {context.api_key}"}
        async with context.session.get(
            FULL_LIST_URL,
            headers=headers,
            params={"v": "1"},
        ) as response:
            response.raise_for_status()
            payload = await response.json(content_type=None)
        carparks = parse_carpark_payload(payload)
        now = datetime.now(UTC)
        return [
            carpark if carpark.updated else replace(carpark, updated=now)
            for carpark in carparks
        ]
