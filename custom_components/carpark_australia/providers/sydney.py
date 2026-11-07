"""City of Sydney council car parks.

The council publishes the location of every car park it contracts,
including the private operator that runs it.
"""

from __future__ import annotations

from ..models import Carpark
from .arcgis import fetch_features, geometry_point
from .base import ProviderContext

OPERATOR = "City of Sydney"
SERVICE_URL = (
    "https://services1.arcgis.com/cNVyNtjGVZybOQWZ/arcgis/rest/services/"
    "Council_car_parks/FeatureServer"
)


class SydneyProvider:
    """Council car parks in the City of Sydney."""

    key = "sydney"
    name = "City of Sydney car parks"
    requires_api_key = False

    async def fetch(self, context: ProviderContext) -> list[Carpark]:
        """Return every council car park."""
        features = await fetch_features(
            context.session,
            SERVICE_URL,
            out_fields="CarParkName,Street,Suburb,AccessPoint,Operator,ContactPhoneNumber",
        )
        carparks: list[Carpark] = []
        seen: set[str] = set()
        for feature in features:
            attributes = feature.get("attributes") or {}
            name = str(attributes.get("CarParkName") or "").strip()
            if not name or name in seen:
                continue
            seen.add(name)
            latitude, longitude = geometry_point(feature)
            street = attributes.get("Street")
            suburb = attributes.get("Suburb")
            address = ", ".join(str(part) for part in (street, suburb) if part)
            carparks.append(
                Carpark(
                    provider=self.key,
                    key=name,
                    name=name,
                    operator=str(attributes.get("Operator") or OPERATOR),
                    latitude=latitude,
                    longitude=longitude,
                    address=address or None,
                    extra={
                        "access_point": attributes.get("AccessPoint"),
                        "contact_phone": attributes.get("ContactPhoneNumber"),
                        "suburb": suburb,
                    },
                )
            )
        carparks.sort(key=lambda item: item.name.lower())
        return carparks
