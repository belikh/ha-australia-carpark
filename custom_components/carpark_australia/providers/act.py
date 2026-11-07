"""ACT Government car park assets."""

from __future__ import annotations

from ..models import Carpark
from .arcgis import fetch_features, geometry_point
from .base import ProviderContext, as_int

OPERATOR = "ACT Government"
SERVICE_URL = (
    "https://services1.arcgis.com/E5n4f1VY84i0xSjy/arcgis/rest/services/"
    "ACTGOV_Car_Park_Assets/FeatureServer"
)
LAYER = 1


class ActProvider:
    """Car park assets maintained by the ACT Government."""

    key = "act"
    name = "ACT Government car parks"
    requires_api_key = False

    async def fetch(self, context: ProviderContext) -> list[Carpark]:
        """Return every ACT Government car park asset."""
        features = await fetch_features(
            context.session,
            SERVICE_URL,
            layer=LAYER,
            out_fields=(
                "ASSET_ID,ASSET_NAME,LOCATION,OPERATIONAL_STATE,CAR_PARK_TYPE,"
                "NUMBER_OF_LEVELS,PARK_AND_RIDE,SUBURB,ADDRESS,OWNERSHIP,MAINTAINED_BY"
            ),
        )
        carparks: list[Carpark] = []
        seen: set[str] = set()
        for feature in features:
            attributes = feature.get("attributes") or {}
            name = str(attributes.get("ASSET_NAME") or "").strip()
            if not name or name in seen:
                continue
            seen.add(name)
            latitude, longitude = geometry_point(feature)
            levels = as_int(attributes.get("NUMBER_OF_LEVELS"))
            carparks.append(
                Carpark(
                    provider=self.key,
                    key=str(attributes.get("ASSET_ID") or name),
                    name=name,
                    operator=str(attributes.get("MAINTAINED_BY") or OPERATOR),
                    latitude=latitude,
                    longitude=longitude,
                    address=attributes.get("ADDRESS") or None,
                    extra={
                        "asset_type": attributes.get("ASSET_TYPE"),
                        "asset_sub_type": attributes.get("ASSET_SUB_TYPE"),
                        "car_park_type": attributes.get("CAR_PARK_TYPE"),
                        "levels": levels,
                        "operational_state": attributes.get("OPERATIONAL_STATE"),
                        "park_and_ride": attributes.get("PARK_AND_RIDE"),
                        "suburb": attributes.get("SUBURB"),
                    },
                )
            )
        carparks.sort(key=lambda item: item.name.lower())
        return carparks
