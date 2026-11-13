"""Binary sensors for Carpark Australia."""

from __future__ import annotations

from typing import Any

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import CarparkCoordinator
from .const import CONF_TRACKED_CARPARKS, DOMAIN
from .models import Carpark
from .sensor import carpark_attributes, device_info


class CarparkSpacesAvailableSensor(
    CoordinatorEntity[CarparkCoordinator], BinarySensorEntity
):
    """True when a car park has at least one free space."""

    _attr_has_entity_name = True
    _attr_name = "Spaces available"
    _attr_icon = "mdi:car"

    def __init__(self, coordinator: CarparkCoordinator, carpark: Carpark) -> None:
        """Initialise the sensor."""
        super().__init__(coordinator)
        self._carpark = carpark
        self._attr_unique_id = f"{DOMAIN}_{carpark.unique_id}_spaces_available"
        self._attr_device_info = device_info(carpark)

    @property
    def is_on(self) -> bool | None:
        """Return whether a space is free."""
        if self._carpark.spaces_free is None:
            return None
        return self._carpark.spaces_free > 0

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the car park details."""
        return carpark_attributes(self._carpark)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Carpark Australia binary sensors."""
    coordinator: CarparkCoordinator = hass.data[DOMAIN][entry.entry_id]
    tracked: set[str] = set(
        entry.options.get(
            CONF_TRACKED_CARPARKS,
            entry.data.get(CONF_TRACKED_CARPARKS, []),
        )
    )
    known: set[str] = set()

    def _add_new(new: list[Carpark]) -> None:
        """Add sensors for car parks that appeared after setup."""
        created: list[BinarySensorEntity] = []
        for carpark in new:
            if (
                carpark.unique_id in known
                or carpark.unique_id not in tracked
                or not carpark.has_availability
            ):
                continue
            known.add(carpark.unique_id)
            created.append(CarparkSpacesAvailableSensor(coordinator, carpark))
        if created:
            async_add_entities(created)

    entities: list[BinarySensorEntity] = []
    for carpark in coordinator.data.carparks.values() if coordinator.data else []:
        if (
            carpark.unique_id in known
            or carpark.unique_id not in tracked
            or not carpark.has_availability
        ):
            continue
        known.add(carpark.unique_id)
        entities.append(CarparkSpacesAvailableSensor(coordinator, carpark))

    async_add_entities(entities)
    coordinator.add_listener(_add_new)
