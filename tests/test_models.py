"""Tests for the shared data model and the coordinator helpers."""

from __future__ import annotations

from datetime import UTC, datetime

from custom_components.carpark_australia import count_spaces, distance_metres
from custom_components.carpark_australia.models import Carpark, slugify


def test_slugify() -> None:
    """Names become readable entity id fragments."""
    assert slugify("Rundle Street") == "rundle_street"
    assert slugify("Pirie / Flinders Street") == "pirie_flinders_street"
    assert slugify("Saint-Kilda") == "saint_kilda"
    assert slugify("") == "carpark"


def test_carpark_occupied_and_occupancy() -> None:
    """Occupied spaces and the occupancy percentage are derived."""
    carpark = Carpark(
        provider="adelaide",
        key="rundle",
        name="Rundle Street",
        operator="City of Adelaide",
        spaces_total=700,
        spaces_free=100,
    )
    assert carpark.spaces_occupied == 600
    assert carpark.computed_occupancy_percent == 85.7
    assert carpark.has_availability is True
    assert carpark.unique_id == "adelaide_rundle"


def test_carpark_without_availability() -> None:
    """A car park without a free count reports no occupancy."""
    carpark = Carpark(
        provider="wilson",
        key="1",
        name="Car park",
        operator="Wilson Parking",
    )
    assert carpark.spaces_occupied is None
    assert carpark.computed_occupancy_percent is None
    assert carpark.has_availability is False


def test_carpark_published_occupancy_wins() -> None:
    """A published occupancy percentage is preferred over a calculation."""
    carpark = Carpark(
        provider="brisbane",
        key="1",
        name="Zone",
        operator="Brisbane City Council",
        spaces_total=10,
        spaces_free=5,
        occupancy_percent=42.0,
    )
    assert carpark.computed_occupancy_percent == 42.0


def test_carpark_updated_is_kept() -> None:
    """The provider timestamp survives on the model."""
    stamp = datetime(2026, 11, 7, 12, 0, tzinfo=UTC)
    carpark = Carpark(
        provider="adelaide",
        key="rundle",
        name="Rundle Street",
        operator="City of Adelaide",
        updated=stamp,
    )
    assert carpark.updated == stamp


def test_count_spaces() -> None:
    """The parking spaces in scope are counted."""
    carparks = [
        Carpark(
            provider="adelaide",
            key="1",
            name="Rundle Street",
            operator="City of Adelaide",
            spaces_total=700,
            spaces_free=614,
        ),
        Carpark(
            provider="perth",
            key="2",
            name="Barrack Street Car Park",
            operator="City of Perth",
            spaces_total=120,
        ),
        Carpark(
            provider="wilson",
            key="3",
            name="25 Martin Place Car Park",
            operator="Wilson Parking",
        ),
    ]
    totals = count_spaces(carparks)
    assert totals.free == 614
    assert totals.total == 820
    assert totals.occupied == 86
    assert totals.carparks_with_free == 1
    assert totals.carparks_with_total == 2
    assert totals.carparks_with_both == 1
    # The percentage only uses the car parks that publish both figures.
    assert totals.free_percent == 87.7


def test_count_spaces_without_capacity() -> None:
    """A car park with no capacity contributes only its free count."""
    carparks = [
        Carpark(
            provider="adelaide",
            key="1",
            name="Rundle Street",
            operator="City of Adelaide",
            spaces_free=614,
        ),
    ]
    totals = count_spaces(carparks)
    assert totals.free == 614
    assert totals.total == 0
    assert totals.carparks_with_both == 0
    assert totals.free_percent is None


def test_distance_metres() -> None:
    """Distances between Australian cities are plausible."""
    sydney = (-33.8688, 151.2093)
    melbourne = (-37.8136, 144.9631)
    distance = distance_metres(*sydney, *melbourne)
    assert 700_000 < distance < 800_000
    assert distance_metres(*sydney, *sydney) < 1
