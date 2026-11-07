"""The Carpark Australia integration."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from math import asin, cos, radians, sin, sqrt
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import (
    CONF_API_KEY,
    CONF_PROVIDERS,
    CONF_SCAN_INTERVAL,
    CONF_SCOPE,
    CONF_SCOPE_RADIUS,
    CONF_SCOPE_ZONE,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_SCOPE_RADIUS,
    DOMAIN,
    MAX_SCAN_INTERVAL_MINUTES,
    MIN_SCAN_INTERVAL_MINUTES,
    SCOPE_HOME,
    SCOPE_ZONE,
)
from .models import Carpark
from .providers import PROVIDERS, ProviderContext

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.BINARY_SENSOR]

EARTH_RADIUS_METRES = 6_371_000


@dataclass
class CarparkData:
    """The result of one refresh."""

    carparks: dict[str, Carpark] = field(default_factory=dict)
    errors: dict[str, str] = field(default_factory=dict)
    fetched_at: datetime | None = None


@dataclass(frozen=True)
class SpaceTotals:
    """The parking spaces counted across the car parks in scope.

    ``free`` counts every car park that publishes a live free count, which
    may include car parks with no published capacity. ``occupied`` and
    ``free_percent`` only count car parks that publish both figures, so
    they stay consistent with each other.
    """

    free: int = 0
    total: int = 0
    occupied: int = 0
    free_with_capacity: int = 0
    total_with_capacity: int = 0
    carparks_with_free: int = 0
    carparks_with_total: int = 0
    carparks_with_both: int = 0

    @property
    def free_percent(self) -> float | None:
        """Return the share of the counted capacity that is free."""
        if not self.carparks_with_both or not self.total_with_capacity:
            return None
        return round(self.free_with_capacity / self.total_with_capacity * 100, 1)


def count_spaces(carparks: Iterable[Carpark]) -> SpaceTotals:
    """Return the parking space totals for *carparks*."""
    free = 0
    total = 0
    occupied = 0
    free_with_capacity = 0
    total_with_capacity = 0
    with_free = 0
    with_total = 0
    with_both = 0
    for carpark in carparks:
        carpark_total = carpark.spaces_total
        carpark_free = carpark.spaces_free
        if carpark_free is not None:
            free += carpark_free
            with_free += 1
        if carpark_total is not None:
            total += carpark_total
            with_total += 1
        if carpark_total is not None and carpark_free is not None:
            occupied += max(0, carpark_total - carpark_free)
            free_with_capacity += carpark_free
            total_with_capacity += carpark_total
            with_both += 1
    return SpaceTotals(
        free=free,
        total=total,
        occupied=occupied,
        free_with_capacity=free_with_capacity,
        total_with_capacity=total_with_capacity,
        carparks_with_free=with_free,
        carparks_with_total=with_total,
        carparks_with_both=with_both,
    )


def distance_metres(
    latitude_a: float,
    longitude_a: float,
    latitude_b: float,
    longitude_b: float,
) -> float:
    """Return the great circle distance between two points in metres."""
    lat_a = radians(latitude_a)
    lat_b = radians(latitude_b)
    delta_lat = lat_b - lat_a
    delta_lon = radians(longitude_b - longitude_a)
    haversine = (
        sin(delta_lat / 2) ** 2
        + cos(lat_a) * cos(lat_b) * sin(delta_lon / 2) ** 2
    )
    return 2 * EARTH_RADIUS_METRES * asin(sqrt(haversine))


class CarparkCoordinator(DataUpdateCoordinator[CarparkData]):
    """Fetch every configured provider and keep the car parks up to date."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialise the coordinator."""
        self.entry = entry
        self._carpark_listeners: list[Callable[[list[Carpark]], None]] = []
        self._known_ids: set[str] = set()
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=self._scan_interval(),
        )

    # Options -------------------------------------------------------------

    def _option(self, key: str, default: Any = None) -> Any:
        """Return an option, falling back to the entry data."""
        if key in self.entry.options:
            return self.entry.options[key]
        return self.entry.data.get(key, default)

    @property
    def provider_keys(self) -> list[str]:
        """Return the provider keys to poll."""
        raw = self._option(CONF_PROVIDERS, [])
        if isinstance(raw, str):
            raw = [raw]
        keys = [str(key) for key in raw if str(key) in PROVIDERS]
        return keys or list(PROVIDERS)

    @property
    def api_key(self) -> str | None:
        """Return the Transport for NSW API key, when one is set."""
        value = self._option(CONF_API_KEY)
        return str(value).strip() if value else None

    @property
    def scope(self) -> str:
        """Return the configured scope."""
        return str(self._option(CONF_SCOPE, SCOPE_HOME))

    @property
    def scope_radius(self) -> float:
        """Return the scope radius in metres."""
        value = self._option(CONF_SCOPE_RADIUS, DEFAULT_SCOPE_RADIUS)
        try:
            radius = float(value)
        except (TypeError, ValueError):
            return float(DEFAULT_SCOPE_RADIUS)
        return radius if radius > 0 else float(DEFAULT_SCOPE_RADIUS)

    @property
    def scope_zone(self) -> str | None:
        """Return the entity id of the zone used to scope the car parks."""
        value = self._option(CONF_SCOPE_ZONE)
        return str(value) if value else None

    def _scan_interval(self) -> timedelta:
        """Return the refresh interval."""
        minutes = self._option(CONF_SCAN_INTERVAL)
        try:
            value = int(minutes)
        except (TypeError, ValueError):
            return DEFAULT_SCAN_INTERVAL
        value = max(MIN_SCAN_INTERVAL_MINUTES, min(MAX_SCAN_INTERVAL_MINUTES, value))
        return timedelta(minutes=value)

    # Scope ---------------------------------------------------------------

    def scope_centre(self) -> tuple[float, float, float] | None:
        """Return ``(latitude, longitude, radius)`` for the configured scope."""
        if self.scope == SCOPE_ZONE:
            entity_id = self.scope_zone
            if entity_id:
                state = self.hass.states.get(entity_id)
                if state is not None:
                    latitude = state.attributes.get("latitude")
                    longitude = state.attributes.get("longitude")
                    radius = state.attributes.get("radius")
                    if latitude is not None and longitude is not None:
                        return (
                            float(latitude),
                            float(longitude),
                            float(radius or self.scope_radius or 0.0),
                        )
            return None
        if self.scope == SCOPE_HOME:
            config = self.hass.config
            radius = self.scope_radius or float(config.radius)
            return float(config.latitude), float(config.longitude), radius
        return None

    @property
    def scope_description(self) -> str:
        """Return a readable description of the area being tracked."""
        if self.scope == SCOPE_ZONE:
            entity_id = self.scope_zone
            if entity_id:
                state = self.hass.states.get(entity_id)
                if state is not None:
                    return str(state.name)
                return entity_id
            return "zone"
        if self.scope == SCOPE_HOME:
            return f"within {int(self.scope_radius)} m of home"
        return "Australia"

    def apply_scope(self, carparks: Iterable[Carpark]) -> list[Carpark]:
        """Return only the car parks inside the configured scope."""
        centre = self.scope_centre()
        if centre is None:
            if self.scope == SCOPE_ZONE:
                _LOGGER.warning(
                    "The zone %s could not be found, tracking no car parks",
                    self.scope_zone,
                )
                return []
            return list(carparks)
        latitude, longitude, radius = centre
        if radius <= 0:
            return list(carparks)
        kept: list[Carpark] = []
        for carpark in carparks:
            if carpark.latitude is None or carpark.longitude is None:
                continue
            distance = distance_metres(
                latitude, longitude, carpark.latitude, carpark.longitude
            )
            if distance <= radius:
                kept.append(carpark)
        return kept

    # Refresh -------------------------------------------------------------

    async def _fetch_provider(self, key: str) -> list[Carpark]:
        """Fetch one provider."""
        provider = PROVIDERS[key]
        context = ProviderContext(
            session=async_get_clientsession(self.hass),
            api_key=self.api_key,
        )
        return await provider.fetch(context)

    async def _async_update_data(self) -> CarparkData:
        """Fetch every configured provider."""
        keys = self.provider_keys
        results = await asyncio.gather(
            *(self._fetch_provider(key) for key in keys),
            return_exceptions=True,
        )
        carparks: dict[str, Carpark] = {}
        errors: dict[str, str] = {}
        for key, result in zip(keys, results, strict=True):
            if isinstance(result, BaseException):
                errors[key] = str(result) or result.__class__.__name__
                _LOGGER.warning("Provider %s failed: %s", key, errors[key])
                continue
            for carpark in result:
                carparks[carpark.unique_id] = carpark

        scoped = self.apply_scope(carparks.values())
        return CarparkData(
            carparks={carpark.unique_id: carpark for carpark in scoped},
            errors=errors,
            fetched_at=datetime.now(UTC),
        )

    # Listeners -----------------------------------------------------------

    def add_listener(self, listener: Callable[[list[Carpark]], None]) -> None:
        """Register a callback for car parks that appear after setup."""
        self._carpark_listeners.append(listener)

    def async_update_listeners(self) -> None:
        """Notify listeners about newly discovered car parks."""
        super().async_update_listeners()
        if self.data is None:
            return
        new = [
            carpark
            for unique_id, carpark in self.data.carparks.items()
            if unique_id not in self._known_ids
        ]
        if not new:
            return
        self._known_ids.update(carpark.unique_id for carpark in new)
        for listener in self._carpark_listeners:
            listener(new)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Carpark Australia from a config entry."""
    coordinator = CarparkCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)
    return unload_ok
