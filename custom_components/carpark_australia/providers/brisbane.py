"""Brisbane City Council paid parking.

The council publishes the location and capacity of every parking meter
zone, plus a machine learning forecast of how many bays will be occupied
for each hour of the day.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from ..models import Carpark
from .base import ProviderContext, as_float, as_int

OPERATOR = "Brisbane City Council"
BASE_URL = "https://data.brisbane.qld.gov.au/api/explore/v2.1/catalog/datasets"
METERS_DATASET = f"{BASE_URL}/brisbane-parking-meters/records"
FORECAST_DATASET = f"{BASE_URL}/parking-occupancy-forecasting/records"

# The portal caps a single response at 100 records.
PAGE_SIZE = 100

# How far ahead to look for a published forecast.
FORECAST_HORIZON_DAYS = 7


def parse_meters(payload: Any) -> dict[str, dict[str, Any]]:
    """Return the parking meter zones keyed by ``mobile_zone``."""
    zones: dict[str, dict[str, Any]] = {}
    results = payload.get("results") if isinstance(payload, dict) else payload
    if not isinstance(results, list):
        return zones
    for record in results:
        if not isinstance(record, dict):
            continue
        zone = str(record.get("mobile_zone") or "").strip()
        if not zone:
            continue
        zones[zone] = record
    return zones


def _meter_records(payload: Any) -> list[dict[str, Any]]:
    """Return the raw meter records from a portal response."""
    results = payload.get("results") if isinstance(payload, dict) else payload
    if not isinstance(results, list):
        return []
    return [record for record in results if isinstance(record, dict)]


def parse_forecast(payload: Any) -> tuple[str | None, dict[str, int]]:
    """Return the forecast date and the occupied bay count per zone."""
    results = payload.get("results") if isinstance(payload, dict) else payload
    if not isinstance(results, list) or not results:
        return None, {}
    dates = {
        str(record.get("date") or "")[:10]
        for record in results
        if isinstance(record, dict)
    }
    latest = max(dates) if dates else None
    occupancy: dict[str, int] = {}
    for record in results:
        if not isinstance(record, dict):
            continue
        zone = str(record.get("mobile_zone") or "").strip()
        occupied = as_int(record.get("occupancy_pred"))
        if not zone or occupied is None:
            continue
        occupancy[zone] = occupied
    return latest, occupancy


def _zone_name(record: dict[str, Any]) -> str:
    """Return a readable name for a parking meter zone."""
    description = record.get("loc_desc")
    if description:
        return str(description)
    street = record.get("street") or "Parking zone"
    suburb = record.get("suburb")
    if suburb:
        return f"{street}, {suburb}"
    return str(street)


class BrisbaneProvider:
    """Forecast parking availability for Brisbane paid parking zones."""

    key = "brisbane"
    name = "Brisbane City Council (parking forecast)"
    requires_api_key = False

    async def _forecast_date(
        self,
        context: ProviderContext,
        now: datetime,
    ) -> str | None:
        """Return the earliest published forecast date from today on."""
        start, _ = _date_window(now)
        params = {
            "where": (
                f"date >= date'{start}T00:00:00' AND hour = {now.hour}"
            ),
            "limit": "1",
            "order_by": "date ASC",
        }
        async with context.session.get(FORECAST_DATASET, params=params) as response:
            response.raise_for_status()
            payload = await response.json(content_type=None)
        results = payload.get("results") if isinstance(payload, dict) else None
        if not isinstance(results, list) or not results:
            return None
        return str(results[0].get("date") or "")[:10] or None

    async def _forecast_occupancy(
        self,
        context: ProviderContext,
        forecast_date: str,
        hour: int,
    ) -> dict[str, int]:
        """Return the predicted occupied bays for every zone."""
        occupancy: dict[str, int] = {}
        offset = 0
        while True:
            params = {
                "where": (
                    f"date = date'{forecast_date}T00:00:00' AND hour = {hour}"
                ),
                "limit": str(PAGE_SIZE),
                "offset": str(offset),
            }
            async with context.session.get(
                FORECAST_DATASET, params=params
            ) as response:
                response.raise_for_status()
                payload = await response.json(content_type=None)
            results = payload.get("results") if isinstance(payload, dict) else None
            if not isinstance(results, list) or not results:
                break
            for record in results:
                zone = str(record.get("mobile_zone") or "").strip()
                occupied = as_int(record.get("occupancy_pred"))
                if zone and occupied is not None:
                    occupancy[zone] = occupied
            if len(results) < PAGE_SIZE:
                break
            offset += PAGE_SIZE
        return occupancy

    async def fetch(self, context: ProviderContext) -> list[Carpark]:
        """Return every paid parking zone with its forecast occupancy."""
        meters: dict[str, dict[str, Any]] = {}
        offset = 0
        while True:
            async with context.session.get(
                METERS_DATASET,
                params={"limit": str(PAGE_SIZE), "offset": str(offset)},
            ) as response:
                response.raise_for_status()
                payload = await response.json(content_type=None)
            records = _meter_records(payload)
            for record in records:
                zone = str(record.get("mobile_zone") or "").strip()
                if zone:
                    meters[zone] = record
            if len(records) < PAGE_SIZE:
                break
            offset += PAGE_SIZE

        if not meters:
            return []

        now = datetime.now(UTC)
        forecast_date = await self._forecast_date(context, now)
        occupancy: dict[str, int] = {}
        if forecast_date is not None:
            occupancy = await self._forecast_occupancy(context, forecast_date, now.hour)

        carparks: list[Carpark] = []
        for zone, record in meters.items():
            total = as_int(record.get("veh_bays")) or as_int(record.get("veh_bays_int"))
            occupied = occupancy.get(zone)
            free: int | None = None
            percent: float | None = None
            if occupied is not None and total:
                free = max(0, total - occupied)
                percent = round(min(occupied, total) / total * 100, 1)
            elif occupied is not None:
                free = None
                percent = None
            latitude = as_float(record.get("latitude"))
            longitude = as_float(record.get("longitude"))
            carparks.append(
                Carpark(
                    provider=self.key,
                    key=zone,
                    name=_zone_name(record),
                    operator=OPERATOR,
                    kind="forecast",
                    spaces_total=total,
                    spaces_free=free,
                    occupancy_percent=percent,
                    latitude=latitude,
                    longitude=longitude,
                    address=record.get("loc_desc") or None,
                    extra={
                        "mobile_zone": zone,
                        "forecast_date": forecast_date,
                        "predicted_occupied": occupied,
                        "tariff": record.get("tar_zone"),
                        "max_stay_hours": record.get("max_stay_hrs"),
                    },
                )
            )
        carparks.sort(key=lambda item: item.name.lower())
        return carparks


def _date_window(now: datetime) -> tuple[str, str]:
    """Return the first and last date to look for a forecast in."""
    start = now.date()
    end = start + timedelta(days=FORECAST_HORIZON_DAYS)
    return start.isoformat(), end.isoformat()
