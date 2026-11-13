"""Sensors for Carpark Australia."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from homeassistant.components.sensor import (
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import CarparkCoordinator, SpaceTotals, count_spaces
from .const import (
    ATTR_CARPARKS,
    ATTR_FREE_CARPARKS,
    ATTR_LAST_UPDATED,
    ATTR_LATITUDE,
    ATTR_LONGITUDE,
    ATTR_OCCUPANCY_PERCENT,
    ATTR_OPERATOR,
    ATTR_PRICING,
    ATTR_PROVIDER,
    ATTR_SCOPE,
    ATTR_SPACES_FREE,
    ATTR_SPACES_OCCUPIED,
    ATTR_SPACES_TOTAL,
    ATTR_URL,
    CONF_TRACKED_CARPARKS,
    DOMAIN,
)
from .models import Carpark

# The catalogue sensor lists every car park in scope. Long lists are cut
# off so a single attribute does not swamp the recorder database.
MAX_CATALOGUE_ENTRIES = 500
# The scope sensor lists the car parks in scope. Long lists are cut off
# the same way so the attribute stays readable.
MAX_SCOPE_ENTRIES = 200


def device_info(carpark: Carpark) -> DeviceInfo:
    """Return the device a car park's entities belong to."""
    return DeviceInfo(
        identifiers={(DOMAIN, carpark.unique_id)},
        name=carpark.name,
        manufacturer=carpark.operator,
        model=carpark.kind.replace("_", " ").title(),
        configuration_url=carpark.url,
    )


def carpark_attributes(carpark: Carpark) -> dict[str, Any]:
    """Return the attributes shared by every car park entity."""
    return {
        ATTR_PROVIDER: carpark.provider,
        ATTR_OPERATOR: carpark.operator,
        "kind": carpark.kind,
        ATTR_SPACES_TOTAL: carpark.spaces_total,
        ATTR_SPACES_FREE: carpark.spaces_free,
        ATTR_SPACES_OCCUPIED: carpark.spaces_occupied,
        ATTR_OCCUPANCY_PERCENT: carpark.computed_occupancy_percent,
        "address": carpark.address,
        ATTR_LATITUDE: carpark.latitude,
        ATTR_LONGITUDE: carpark.longitude,
        ATTR_URL: carpark.url,
        ATTR_PRICING: carpark.pricing,
        ATTR_LAST_UPDATED: (
            carpark.updated.isoformat()
            if isinstance(carpark.updated, datetime)
            else None
        ),
    }


def carpark_summary(carpark: Carpark) -> dict[str, Any]:
    """Return a compact summary of one car park for an attribute."""
    return {
        "name": carpark.name,
        "provider": carpark.provider,
        "operator": carpark.operator,
        ATTR_SPACES_TOTAL: carpark.spaces_total,
        ATTR_SPACES_FREE: carpark.spaces_free,
        ATTR_OCCUPANCY_PERCENT: carpark.computed_occupancy_percent,
        ATTR_PRICING: carpark.pricing,
        "address": carpark.address,
        ATTR_LATITUDE: carpark.latitude,
        ATTR_LONGITUDE: carpark.longitude,
        ATTR_URL: carpark.url,
    }


class CarparkSpacesFreeSensor(CoordinatorEntity[CarparkCoordinator], SensorEntity):
    """Number of free spaces at a car park."""

    _attr_has_entity_name = True
    _attr_name = "Spaces free"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_icon = "mdi:parking"

    def __init__(self, coordinator: CarparkCoordinator, carpark: Carpark) -> None:
        """Initialise the sensor."""
        super().__init__(coordinator)
        self._carpark = carpark
        self._attr_unique_id = f"{DOMAIN}_{carpark.unique_id}_spaces_free"
        self._attr_device_info = device_info(carpark)

    @property
    def native_value(self) -> int | None:
        """Return the number of free spaces."""
        return self._carpark.spaces_free

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the car park details."""
        return carpark_attributes(self._carpark)


class CarparkOccupancySensor(CoordinatorEntity[CarparkCoordinator], SensorEntity):
    """Percentage of a car park that is occupied."""

    _attr_has_entity_name = True
    _attr_name = "Occupancy"
    _attr_native_unit_of_measurement = "%"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_icon = "mdi:percent"

    def __init__(self, coordinator: CarparkCoordinator, carpark: Carpark) -> None:
        """Initialise the sensor."""
        super().__init__(coordinator)
        self._carpark = carpark
        self._attr_unique_id = f"{DOMAIN}_{carpark.unique_id}_occupancy"
        self._attr_device_info = device_info(carpark)

    @property
    def native_value(self) -> float | None:
        """Return the occupancy percentage."""
        return self._carpark.computed_occupancy_percent

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the car park details."""
        return carpark_attributes(self._carpark)


class CarparkTotalSpacesSensor(CoordinatorEntity[CarparkCoordinator], SensorEntity):
    """Total number of spaces at a car park that publishes its capacity."""

    _attr_has_entity_name = True
    _attr_name = "Total spaces"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_icon = "mdi:parking"

    def __init__(self, coordinator: CarparkCoordinator, carpark: Carpark) -> None:
        """Initialise the sensor."""
        super().__init__(coordinator)
        self._carpark = carpark
        self._attr_unique_id = f"{DOMAIN}_{carpark.unique_id}_total_spaces"
        self._attr_device_info = device_info(carpark)

    @property
    def native_value(self) -> int | None:
        """Return the total number of spaces."""
        return self._carpark.spaces_total

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the car park details."""
        return carpark_attributes(self._carpark)


class ProviderCatalogueSensor(CoordinatorEntity[CarparkCoordinator], SensorEntity):
    """Every car park a provider reported."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:map-marker-multiple"

    def __init__(self, coordinator: CarparkCoordinator, provider: str) -> None:
        """Initialise the sensor."""
        super().__init__(coordinator)
        self._provider = provider
        self._attr_unique_id = f"{DOMAIN}_{provider}_carparks"
        self._attr_name = f"Car parks ({provider})"

    @property
    def native_value(self) -> int:
        """Return the number of car parks the provider reported."""
        return len(self._carparks)

    @property
    def _carparks(self) -> list[Carpark]:
        """Return the car parks reported by this provider."""
        data = self.coordinator.data
        if data is None:
            return []
        return [
            carpark
            for carpark in data.carparks.values()
            if carpark.provider == self._provider
        ]

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the car park list."""
        carparks = self._carparks
        listed = carparks[:MAX_CATALOGUE_ENTRIES]
        return {
            ATTR_PROVIDER: self._provider,
            "carpark_count": len(carparks),
            "listed_count": len(listed),
            "truncated": len(listed) < len(carparks),
            "carparks": [
                {
                    "name": carpark.name,
                    "operator": carpark.operator,
                    ATTR_SPACES_TOTAL: carpark.spaces_total,
                    ATTR_SPACES_FREE: carpark.spaces_free,
                    "address": carpark.address,
                    ATTR_LATITUDE: carpark.latitude,
                    ATTR_LONGITUDE: carpark.longitude,
                    ATTR_URL: carpark.url,
                }
                for carpark in listed
            ],
        }


class ScopeTotalsSensor(CoordinatorEntity[CarparkCoordinator], SensorEntity):
    """A parking space total counted across the area in scope."""

    _attr_has_entity_name = True
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(
        self,
        coordinator: CarparkCoordinator,
        name: str,
        key: str,
        unit: str | None = None,
    ) -> None:
        """Initialise the sensor."""
        super().__init__(coordinator)
        self._key = key
        self._attr_name = name
        self._attr_unique_id = f"{DOMAIN}_{key}"
        self._attr_native_unit_of_measurement = unit
        self._attr_icon = "mdi:percent" if unit == "%" else "mdi:counter"

    @property
    def _totals(self) -> SpaceTotals:
        """Return the parking space totals in scope."""
        data = self.coordinator.data
        if data is None:
            return SpaceTotals()
        return count_spaces(data.carparks.values())

    @property
    def native_value(self) -> int | float | None:
        """Return the counted value."""
        totals = self._totals
        match self._key:
            case "spaces_free":
                return totals.free
            case "spaces_total":
                return totals.total
            case "spaces_occupied":
                return totals.occupied
            case "spaces_free_percent":
                return totals.free_percent
            case "carparks_tracked":
                data = self.coordinator.data
                return len(data.carparks) if data else 0
        return None

    @property
    def _carparks_in_scope(self) -> list[Carpark]:
        """Return the car parks in scope, sorted by name."""
        data = self.coordinator.data
        if data is None:
            return []
        return sorted(data.carparks.values(), key=lambda item: item.name.lower())

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the breakdown behind the counted value."""
        data = self.coordinator.data
        totals = self._totals
        carparks = self._carparks_in_scope
        listed = carparks[:MAX_SCOPE_ENTRIES]
        free_carparks = [
            carpark
            for carpark in carparks
            if carpark.spaces_free is not None and carpark.spaces_free > 0
        ]
        counts: dict[str, int] = {}
        for carpark in carparks:
            counts[carpark.provider] = counts.get(carpark.provider, 0) + 1
        return {
            ATTR_SCOPE: self.coordinator.scope_description,
            "carparks_tracked": sum(counts.values()),
            "carparks_counted_free": totals.carparks_with_free,
            "carparks_counted_total": totals.carparks_with_total,
            "carparks_counted_both": totals.carparks_with_both,
            "by_provider": counts,
            ATTR_CARPARKS: [carpark_summary(carpark) for carpark in listed],
            ATTR_FREE_CARPARKS: [
                carpark_summary(carpark)
                for carpark in free_carparks[:MAX_SCOPE_ENTRIES]
            ],
            "carparks_listed": len(listed),
            "carparks_truncated": len(listed) < len(carparks),
            "free_carparks_count": len(free_carparks),
            "provider_errors": data.errors if data else {},
            ATTR_LAST_UPDATED: (
                data.fetched_at.isoformat() if data and data.fetched_at else None
            ),
        }


def build_entities(
    coordinator: CarparkCoordinator,
    carpark: Carpark,
) -> list[SensorEntity]:
    """Return the sensors for one car park."""
    entities: list[SensorEntity] = []
    if carpark.has_availability:
        entities.append(CarparkSpacesFreeSensor(coordinator, carpark))
        if carpark.spaces_total:
            entities.append(CarparkOccupancySensor(coordinator, carpark))
    elif carpark.spaces_total:
        entities.append(CarparkTotalSpacesSensor(coordinator, carpark))
    return entities


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Carpark Australia sensors."""
    coordinator: CarparkCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities: list[SensorEntity] = [
        ScopeTotalsSensor(coordinator, "Parking spaces free", "spaces_free"),
        ScopeTotalsSensor(coordinator, "Parking spaces total", "spaces_total"),
        ScopeTotalsSensor(coordinator, "Parking spaces occupied", "spaces_occupied"),
        ScopeTotalsSensor(
            coordinator,
            "Parking spaces free percentage",
            "spaces_free_percent",
            unit="%",
        ),
        ScopeTotalsSensor(coordinator, "Car parks tracked", "carparks_tracked"),
    ]

    tracked: set[str] = set(
        entry.options.get(
            CONF_TRACKED_CARPARKS,
            entry.data.get(CONF_TRACKED_CARPARKS, []),
        )
    )

    known: set[str] = set()

    def _add_new(new: list[Carpark]) -> None:
        """Add sensors for car parks that appeared after setup."""
        created: list[SensorEntity] = []
        for carpark in new:
            if carpark.unique_id in known or carpark.unique_id not in tracked:
                continue
            known.add(carpark.unique_id)
            created.extend(build_entities(coordinator, carpark))
        if created:
            async_add_entities(created)

    for carpark in coordinator.data.carparks.values() if coordinator.data else []:
        known.add(carpark.unique_id)
        if carpark.unique_id in tracked:
            entities.extend(build_entities(coordinator, carpark))

    for provider in coordinator.provider_keys:
        entities.append(ProviderCatalogueSensor(coordinator, provider))

    async_add_entities(entities)
    coordinator.add_listener(_add_new)
