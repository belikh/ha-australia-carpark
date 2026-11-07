"""City of Perth car parks."""

from __future__ import annotations

from ..models import Carpark
from .arcgis import fetch_features, geometry_point
from .base import ProviderContext, as_int

OPERATOR = "City of Perth"
SERVICE_URL = (
    "https://services7.arcgis.com/v8XBa2naYNQGOjlG/arcgis/rest/services/"
    "PS_OTH_CARPARKCENTROID_PV/FeatureServer"
)


class PerthProvider:
    """Car parks owned or operated by the City of Perth."""

    key = "perth"
    name = "City of Perth car parks"
    requires_api_key = False

    async def fetch(self, context: ProviderContext) -> list[Carpark]:
        """Return every City of Perth car park."""
        features = await fetch_features(
            context.session,
            SERVICE_URL,
            out_fields="CARPARK_ID,CARPARK_NAME,URL,MC_BAYS,CAR_BAYS,ACROD_BAYS",
        )
        carparks: list[Carpark] = []
        for feature in features:
            attributes = feature.get("attributes") or {}
            name = str(attributes.get("CARPARK_NAME") or "").strip()
            if not name:
                continue
            motorbike = as_int(attributes.get("MC_BAYS")) or 0
            accessible = as_int(attributes.get("ACROD_BAYS")) or 0
            cars = as_int(attributes.get("CAR_BAYS")) or 0
            total = motorbike + accessible + cars
            latitude, longitude = geometry_point(feature)
            carparks.append(
                Carpark(
                    provider=self.key,
                    key=str(attributes.get("CARPARK_ID") or name),
                    name=name,
                    operator=OPERATOR,
                    spaces_total=total or None,
                    latitude=latitude,
                    longitude=longitude,
                    url=attributes.get("URL") or None,
                    extra={
                        "car_bays": cars,
                        "motorcycle_bays": motorbike,
                        "accessible_bays": accessible,
                    },
                )
            )
        carparks.sort(key=lambda item: item.name.lower())
        return carparks
