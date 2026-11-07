"""Tests for the Carpark Australia config entry."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import device_registry as dr
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.carpark_australia.const import (
    CONF_API_KEY,
    CONF_PROVIDERS,
    CONF_SCAN_INTERVAL,
    CONF_SCOPE,
    CONF_SCOPE_RADIUS,
    CONF_SCOPE_ZONE,
    DOMAIN,
    SCOPE_ALL,
    SCOPE_HOME,
    SCOPE_ZONE,
)
from custom_components.carpark_australia.models import Carpark

CARPARKS = [
    Carpark(
        provider="adelaide",
        key="rundle-street",
        name="Rundle Street",
        operator="City of Adelaide",
        spaces_total=700,
        spaces_free=614,
        latitude=-34.9228,
        longitude=138.6017,
    ),
    Carpark(
        provider="wilson",
        key="2078",
        name="25 Martin Place Car Park",
        operator="Wilson Parking",
        latitude=-33.8688,
        longitude=151.2093,
    ),
    Carpark(
        provider="perth",
        key="1",
        name="Barrack Street Car Park",
        operator="City of Perth",
        spaces_total=120,
        latitude=-31.9530,
        longitude=115.8560,
    ),
]

ENTRY_DATA = {
    CONF_PROVIDERS: ["adelaide", "wilson", "perth"],
    CONF_SCAN_INTERVAL: 15,
    CONF_API_KEY: "",
    CONF_SCOPE: SCOPE_ALL,
    CONF_SCOPE_RADIUS: 5000,
    CONF_SCOPE_ZONE: "",
}


@pytest.fixture(name="mock_provider")
def mock_provider_fixture() -> AsyncMock:
    """Patch the provider fetches so no network calls are made."""
    with patch(
        "custom_components.carpark_australia.CarparkCoordinator._fetch_provider",
        new=AsyncMock(return_value=CARPARKS),
    ) as mocked:
        yield mocked


async def test_setup_entry_creates_entities(
    hass, mock_provider: AsyncMock
) -> None:
    """Each car park with availability gets a sensor."""
    entry = MockConfigEntry(domain=DOMAIN, data=ENTRY_DATA, options={})
    entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert hass.states.get("sensor.rundle_street_spaces_free").state == "614"
    assert hass.states.get("sensor.rundle_street_occupancy").state == "12.3"
    assert hass.states.get("binary_sensor.rundle_street_spaces_available").state == "on"
    assert hass.states.get("sensor.barrack_street_car_park_total_spaces").state == "120"
    assert hass.states.get("sensor.car_parks_tracked").state == "3"


async def test_setup_entry_groups_entities_under_devices(
    hass, mock_provider: AsyncMock
) -> None:
    """Entities are attached to a device for their car park."""
    entry = MockConfigEntry(domain=DOMAIN, data=ENTRY_DATA, options={})
    entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    registry = dr.async_get(hass)
    devices = registry.async_get_devices(
        identifiers={(DOMAIN, "adelaide_rundle-street")}
    )
    assert devices
    device = devices[0]
    assert device.name == "Rundle Street"
    assert device.manufacturer == "City of Adelaide"


async def test_setup_entry_counts_spaces(hass, mock_provider: AsyncMock) -> None:
    """The parking spaces in scope are counted."""
    entry = MockConfigEntry(domain=DOMAIN, data=ENTRY_DATA, options={})
    entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert hass.states.get("sensor.parking_spaces_free").state == "614"
    assert hass.states.get("sensor.parking_spaces_total").state == "820"
    assert hass.states.get("sensor.parking_spaces_occupied").state == "86"
    assert hass.states.get("sensor.parking_spaces_free_percentage").state == "87.7"
    assert hass.states.get("sensor.car_parks_tracked").state == "3"

    attributes = hass.states.get("sensor.parking_spaces_free").attributes
    assert attributes["scope"] == "Australia"
    assert attributes["carparks_counted_free"] == 1
    assert attributes["carparks_counted_total"] == 2
    assert attributes["carparks_counted_both"] == 1
    assert attributes["by_provider"] == {"adelaide": 1, "perth": 1, "wilson": 1}


async def test_scope_limits_car_parks(hass, mock_provider: AsyncMock) -> None:
    """Only car parks inside the scope become entities."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            **ENTRY_DATA,
            CONF_SCOPE: SCOPE_HOME,
            CONF_SCOPE_RADIUS: 1000,
        },
        options={},
    )
    entry.add_to_hass(hass)
    hass.config.latitude = -34.9228
    hass.config.longitude = 138.6017

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert hass.states.get("sensor.rundle_street_spaces_free") is not None
    assert hass.states.get("sensor.25_martin_place_car_park_total_spaces") is None
    assert hass.states.get("sensor.car_parks_tracked").state == "1"
    assert hass.states.get("sensor.parking_spaces_free").state == "614"
    assert (
        hass.states.get("sensor.parking_spaces_free").attributes["scope"]
        == "within 1000 m of home"
    )


async def test_scope_by_zone_counts_spaces(hass, mock_provider: AsyncMock) -> None:
    """A zone scopes the car parks and names the area."""
    hass.states.async_set(
        "zone.work",
        "zoning",
        {
            "friendly_name": "Work",
            "latitude": -34.9228,
            "longitude": 138.6017,
            "radius": 500,
        },
    )
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            **ENTRY_DATA,
            CONF_SCOPE: SCOPE_ZONE,
            CONF_SCOPE_ZONE: "zone.work",
        },
        options={},
    )
    entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert hass.states.get("sensor.car_parks_tracked").state == "1"
    assert hass.states.get("sensor.parking_spaces_free").state == "614"
    assert (
        hass.states.get("sensor.parking_spaces_free").attributes["scope"] == "Work"
    )


async def test_scope_by_a_missing_zone_tracks_nothing(
    hass, mock_provider: AsyncMock
) -> None:
    """A zone that no longer exists does not fall back to the whole country."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            **ENTRY_DATA,
            CONF_SCOPE: SCOPE_ZONE,
            CONF_SCOPE_ZONE: "zone.gone",
        },
        options={},
    )
    entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert hass.states.get("sensor.car_parks_tracked").state == "0"
    assert hass.states.get("sensor.parking_spaces_free").state == "0"
    assert hass.states.get("sensor.rundle_street_spaces_free") is None


async def test_config_flow(hass, mock_provider: AsyncMock) -> None:
    """The config flow asks for providers and the area to track."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_PROVIDERS: ["adelaide", "wilson"],
            CONF_SCAN_INTERVAL: 30,
            CONF_API_KEY: "secret-key",
        },
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "scope"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={CONF_SCOPE: SCOPE_HOME},
    )
    assert result["step_id"] == "scope_home"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={CONF_SCOPE_RADIUS: 2500},
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_PROVIDERS] == ["adelaide", "wilson"]
    assert result["data"][CONF_SCOPE_RADIUS] == 2500


async def test_config_flow_with_a_zone(hass, mock_provider: AsyncMock) -> None:
    """Choosing a zone asks for the zone to count."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={CONF_PROVIDERS: ["adelaide"]},
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={CONF_SCOPE: SCOPE_ZONE},
    )
    assert result["step_id"] == "scope_zone"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={CONF_SCOPE_ZONE: "zone.work"},
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_SCOPE_ZONE] == "zone.work"


async def test_unload_entry(hass, mock_provider: AsyncMock) -> None:
    """The entry unloads cleanly."""
    entry = MockConfigEntry(domain=DOMAIN, data=ENTRY_DATA, options={})
    entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
    assert hass.states.get("sensor.parking_spaces_free").state == "unavailable"
