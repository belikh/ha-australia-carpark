"""City of Hobart car parks and parking structures."""

from __future__ import annotations

from ..models import Carpark
from .arcgis import fetch_features, geometry_point
from .base import ProviderContext

OPERATOR = "City of Hobart"
BASE_URL = "https://services1.arcgis.com/NHqdsnvwfSTg42I8/arcgis/rest/services"
CAR_PARKS_URL = f"{BASE_URL}/Car_Parks/FeatureServer"
STRUCTURES_URL = f"{BASE_URL}/Parking_Structures/FeatureServer"


class HobartProvider:
    """Car parks and parking structures in the City of Hobart."""

    key = "hobart"
    name = "City of Hobart car parks"
    requires_api_key = False

    async def fetch(self, context: ProviderContext) -> list[Carpark]:
        """Return every Hobart car park and parking structure."""
        carparks: list[Carpark] = []

        features = await fetch_features(
            context.session,
            CAR_PARKS_URL,
            out_fields="Name,Voucher_Parking,Short_Term_Parking,Website",
        )
        for feature in features:
            attributes = feature.get("attributes") or {}
            name = str(attributes.get("Name") or "").strip()
            if not name:
                continue
            latitude, longitude = geometry_point(feature)
            carparks.append(
                Carpark(
                    provider=self.key,
                    key=name,
                    name=name,
                    operator=OPERATOR,
                    latitude=latitude,
                    longitude=longitude,
                    url=attributes.get("Website") or None,
                    extra={
                        "voucher_parking": attributes.get("Voucher_Parking"),
                        "short_term_parking": attributes.get("Short_Term_Parking"),
                    },
                )
            )

        structures = await fetch_features(
            context.session,
            STRUCTURES_URL,
            out_fields="carParkID,carParkName,informationURL",
        )
        for feature in structures:
            attributes = feature.get("attributes") or {}
            name = str(attributes.get("carParkName") or "").strip()
            if not name:
                continue
            latitude, longitude = geometry_point(feature)
            carparks.append(
                Carpark(
                    provider=self.key,
                    key=str(attributes.get("carParkID") or name),
                    name=name,
                    operator=OPERATOR,
                    latitude=latitude,
                    longitude=longitude,
                    url=attributes.get("informationURL") or None,
                    extra={"kind": "parking_structure"},
                )
            )

        carparks.sort(key=lambda item: item.name.lower())
        return carparks
