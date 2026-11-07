"""Wilson Parking car parks.

Wilson Parking operates several hundred car parks across Australia. The
public website publishes every location through an unauthenticated JSON
endpoint, including coordinates, address, state and the services offered.
"""

from __future__ import annotations

from typing import Any

from ..models import Carpark
from .base import ProviderContext, as_float, as_int

OPERATOR = "Wilson Parking"
BASE_URL = "https://www.wilsonparking.com.au/api/v2/GetParkingByLocation"

# The endpoint ignores the centre point when the distance is this large,
# so one request returns the whole national network.
QUERY = {
    "latitude": "-33.8688197",
    "longitude": "151.2092955",
    "sort": "undefined",
    "distance": "5000000",
}

_HEADERS = {
    "authority": "www.wilsonparking.com.au",
    "accept": "*/*",
    "referer": "https://www.wilsonparking.com.au/",
    "user-agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
}


def parse_carparks(payload: Any) -> list[Carpark]:
    """Convert the Wilson Parking payload into car parks."""
    entries: list[dict[str, Any]] = []
    if isinstance(payload, dict):
        raw = payload.get("carParks")
        if isinstance(raw, list):
            entries = [item for item in raw if isinstance(item, dict)]
    elif isinstance(payload, list):
        entries = [item for item in payload if isinstance(item, dict)]

    carparks: list[Carpark] = []
    seen: set[str] = set()
    for entry in entries:
        name = str(entry.get("carParkName") or entry.get("name") or "").strip()
        if not name:
            continue
        number = as_int(entry.get("carParkNumber")) or as_int(entry.get("legacyID"))
        key = str(number) if number else name
        if key in seen:
            continue
        seen.add(key)

        location = entry.get("location")
        location = location if isinstance(location, dict) else {}
        latitude = as_float(location.get("latitude"))
        longitude = as_float(location.get("longitude"))
        address = location.get("address") or None

        region = location.get("region")
        region_name = region.get("name") if isinstance(region, dict) else None

        path = entry.get("url") or ""
        url = (
            f"https://www.wilsonparking.com.au{path}"
            if path.startswith("/")
            else path
        )

        services = entry.get("services")
        carparks.append(
            Carpark(
                provider="wilson",
                key=key,
                name=name,
                operator=OPERATOR,
                latitude=latitude,
                longitude=longitude,
                address=address,
                url=url or None,
                extra={
                    "state": entry.get("state"),
                    "region": region_name,
                    "services": list(services) if isinstance(services, list) else [],
                    "ev_charging": bool(entry.get("evChargerIsAvailable")),
                    "disabled_parking": bool(entry.get("disabledParkingIsAvailable")),
                    "height_restriction": entry.get("heightRestriction"),
                },
            )
        )
    carparks.sort(
        key=lambda item: (str(item.extra.get("state") or ""), item.name.lower())
    )
    return carparks


class WilsonProvider:
    """Wilson Parking locations across Australia."""

    key = "wilson"
    name = "Wilson Parking"
    requires_api_key = False

    async def fetch(self, context: ProviderContext) -> list[Carpark]:
        """Return every Wilson Parking car park."""
        async with context.session.get(
            BASE_URL,
            params=QUERY,
            headers=_HEADERS,
        ) as response:
            response.raise_for_status()
            payload = await response.json(content_type=None)
        return parse_carparks(payload)
