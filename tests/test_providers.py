"""Tests for the provider parsers."""

from __future__ import annotations

from custom_components.carpark_australia.providers.adelaide import (
    parse_report_time,
    parse_upark_xml,
)
from custom_components.carpark_australia.providers.arcgis import geometry_point
from custom_components.carpark_australia.providers.brisbane import (
    parse_forecast,
    parse_meters,
)
from custom_components.carpark_australia.providers.nsw import parse_carpark_payload
from custom_components.carpark_australia.providers.wilson import parse_carparks

UPARK_XML = b"""<?xml version="1.0" encoding="utf-8"?>
<Report Name="UPark Space Availability by Carpark_Updated"
 Textbox3="As at: 4:18:08 AM"
 xmlns:UPark_x0020_Space="http://accpvrspapp01">
  <table1>
    <CarparkName_Collection>
      <CarparkName Textbox31="Rundle Street" FreeSpaces="614" />
    </CarparkName_Collection>
  </table1>
</Report>
"""

UPARK_XML_EMPTY = b"""<?xml version="1.0" encoding="utf-8"?>
<Report Textbox3="As at: 4:18:08 AM"><table1 /></Report>
"""

WILSON_PAYLOAD = {
    "carParks": [
        {
            "carParkName": "25 Martin Place Car Park",
            "carParkNumber": 2078,
            "legacyID": 102,
            "state": "NSW",
            "url": "/parking-locations/new-south-wales/sydney-cbd/25-martin-place/",
            "location": {
                "latitude": -33.86887888048701,
                "longitude": 151.20893776416779,
                "address": "108 King Street, Sydney",
                "region": {"name": "Sydney CBD"},
            },
            "services": ["monthly"],
            "evChargerIsAvailable": True,
        },
        {
            "carParkName": "Rundle Plaza Car Park",
            "carParkNumber": 2099,
            "state": "SA",
            "location": {
                "latitude": -34.921,
                "longitude": 138.6,
                "address": "Rundle Plaza, Adelaide",
            },
        },
    ]
}

NSW_PAYLOAD = [
    {
        "facility_id": "1",
        "facility_name": "Tallawong Station Car Park",
        "spots": 1004,
        "occupancy": {"total": 981, "free": 23},
        "coordinates": {"latitude": -33.7711, "longitude": 150.9895},
        "suburb": "Tallawong",
        "date": "2026-11-07T12:48:39",
    }
]

NSW_PAYLOAD_ZONES = [
    {
        "facilityId": "501",
        "facilityName": "Parramatta Station Car Park",
        "zones": [
            {"spots": 200, "availability": 20},
            {"spots": 150, "availability": 30},
        ],
        "latitude": -33.815,
        "longitude": 151.0,
    }
]

BRISBANE_METERS = {
    "results": [
        {
            "mobile_zone": "4000493",
            "veh_bays": "3",
            "loc_desc": "Edmondstone St between Folkestone Rd & Abbotsford Rd",
            "street": "EDMONDSTONE RD",
            "suburb": "BOWEN HILLS",
            "latitude": -27.442549,
            "longitude": 153.039649,
        }
    ]
}

BRISBANE_FORECAST = {
    "results": [
        {
            "mobile_zone": "4000493",
            "date": "2026-11-10",
            "hour": 12,
            "occupancy_pred": 2,
        }
    ]
}


def test_parse_upark_xml() -> None:
    """The free space count is read from the report."""
    name, free = parse_upark_xml(UPARK_XML)
    assert name == "Rundle Street"
    assert free == 614


def test_parse_upark_xml_without_a_reading() -> None:
    """A report without a reading returns nothing."""
    assert parse_upark_xml(UPARK_XML_EMPTY) == (None, None)
    assert parse_upark_xml(b"not xml at all") == (None, None)


def test_parse_report_time() -> None:
    """The report timestamp is parsed."""
    stamp = parse_report_time(UPARK_XML)
    assert stamp is not None
    assert (stamp.hour, stamp.minute, stamp.second) == (4, 18, 8)


def test_parse_wilson_carparks() -> None:
    """Wilson car parks keep their location and operator."""
    carparks = parse_carparks(WILSON_PAYLOAD)
    assert len(carparks) == 2
    # Car parks are sorted by state, then by name.
    assert carparks[0].name == "25 Martin Place Car Park"
    assert carparks[0].operator == "Wilson Parking"
    assert carparks[0].latitude == -33.86887888048701
    assert carparks[0].url.startswith("https://www.wilsonparking.com.au/")
    assert carparks[0].extra["state"] == "NSW"
    assert carparks[1].name == "Rundle Plaza Car Park"
    assert carparks[1].latitude == -34.921


def test_parse_wilson_empty_payload() -> None:
    """An unexpected payload yields no car parks."""
    assert parse_carparks({}) == []
    assert parse_carparks(None) == []


def test_parse_nsw_payload() -> None:
    """The Transport for NSW payload is converted to car parks."""
    carparks = parse_carpark_payload(NSW_PAYLOAD)
    assert len(carparks) == 1
    carpark = carparks[0]
    assert carpark.name == "Tallawong Station Car Park"
    assert carpark.spaces_total == 1004
    assert carpark.spaces_free == 23
    assert carpark.spaces_occupied == 981
    assert carpark.latitude == -33.7711
    assert carpark.longitude == 150.9895


def test_parse_nsw_payload_with_zones() -> None:
    """Zone totals are summed when the API reports them per zone."""
    carparks = parse_carpark_payload(NSW_PAYLOAD_ZONES)
    assert len(carparks) == 1
    assert carparks[0].spaces_total == 350
    assert carparks[0].spaces_free == 50


def test_parse_nsw_payload_ignores_junk() -> None:
    """Entries without a name are dropped."""
    assert parse_carpark_payload([{"spots": 10}]) == []
    assert parse_carpark_payload("nonsense") == []


def test_parse_brisbane_meters() -> None:
    """Parking meter zones are keyed by their mobile zone."""
    zones = parse_meters(BRISBANE_METERS)
    assert set(zones) == {"4000493"}
    assert zones["4000493"]["veh_bays"] == "3"


def test_parse_brisbane_forecast() -> None:
    """The forecast is keyed by the date it was published for."""
    date, occupancy = parse_forecast(BRISBANE_FORECAST)
    assert date == "2026-11-10"
    assert occupancy == {"4000493": 2}


def test_geometry_point_rejects_out_of_range() -> None:
    """Coordinates outside the world are ignored."""
    assert geometry_point({"geometry": {"x": 151.2, "y": -33.8}}) == (
        -33.8,
        151.2,
    )
    assert geometry_point({"geometry": {"x": 1234567.0, "y": 987654.0}}) == (
        None,
        None,
    )
    assert geometry_point({}) == (None, None)
