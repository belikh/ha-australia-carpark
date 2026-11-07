"""Helpers for reading ArcGIS FeatureServer layers.

Several Australian councils publish their car park data as ArcGIS
FeatureServers. Those services are public and need no token.
"""

from __future__ import annotations

from typing import Any

from aiohttp import ClientSession

from .base import as_float

# ArcGIS caps a single response; page through the rest when it says so.
_MAX_PAGE_SIZE = 1000


async def fetch_features(
    session: ClientSession,
    service_url: str,
    *,
    layer: int = 0,
    where: str = "1=1",
    out_fields: str = "*",
    result_record_count: int = _MAX_PAGE_SIZE,
) -> list[dict[str, Any]]:
    """Return every feature in *layer* as a list of dictionaries.

    Features carry an ``attributes`` dictionary and, when geometry is
    requested, a ``geometry`` dictionary in WGS 84.
    """
    features: list[dict[str, Any]] = []
    offset = 0
    while True:
        params = {
            "where": where,
            "outFields": out_fields,
            "outSR": "4326",
            "returnGeometry": "true",
            "resultRecordCount": str(result_record_count),
            "resultOffset": str(offset),
            "f": "json",
        }
        url = f"{service_url.rstrip('/')}/{layer}/query"
        async with session.get(url, params=params) as response:
            response.raise_for_status()
            payload = await response.json(content_type=None)

        if "error" in payload:
            message = payload["error"].get("message", "ArcGIS query failed")
            raise ValueError(message)

        page = payload.get("features") or []
        features.extend(page)
        if not payload.get("exceededTransferLimit"):
            break
        offset += len(page)
        if not page:
            break
    return features


def _polygon_centroid(rings: list[list[list[float]]]) -> tuple[float, float] | None:
    """Return the area weighted centroid of a polygon."""
    if not rings:
        return None
    points = rings[0]
    if len(points) < 3:
        return None
    area = 0.0
    centroid_x = 0.0
    centroid_y = 0.0
    for index in range(len(points) - 1):
        x0, y0 = points[index][0], points[index][1]
        x1, y1 = points[index + 1][0], points[index + 1][1]
        cross = x0 * y1 - x1 * y0
        area += cross
        centroid_x += (x0 + x1) * cross
        centroid_y += (y0 + y1) * cross
    if area == 0:
        return None
    area *= 0.5
    return centroid_x / (6 * area), centroid_y / (6 * area)


def geometry_point(
    feature: dict[str, Any],
) -> tuple[float | None, float | None]:
    """Return ``(latitude, longitude)`` for a feature queried in WGS 84.

    Point features are used as they are. Polygon features, such as the
    ACT Government car park assets, are reduced to their centroid.
    """
    geometry = feature.get("geometry") or {}
    latitude = as_float(geometry.get("y"))
    longitude = as_float(geometry.get("x"))
    if latitude is None or longitude is None:
        rings = geometry.get("rings")
        if isinstance(rings, list):
            centroid = _polygon_centroid(rings)
            if centroid is not None:
                longitude, latitude = centroid
    if latitude is None or longitude is None:
        return None, None
    if not (-90 <= latitude <= 90) or not (-180 <= longitude <= 180):
        return None, None
    return latitude, longitude
