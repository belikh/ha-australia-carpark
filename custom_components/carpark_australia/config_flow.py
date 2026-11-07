"""Config flow for Carpark Australia."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.config_entries import ConfigFlowResult
from homeassistant.helpers.selector import (
    EntitySelector,
    EntitySelectorConfig,
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)

from .const import (
    CONF_API_KEY,
    CONF_PROVIDERS,
    CONF_SCAN_INTERVAL,
    CONF_SCOPE,
    CONF_SCOPE_RADIUS,
    CONF_SCOPE_ZONE,
    DEFAULT_SCOPE_RADIUS,
    DOMAIN,
    MAX_SCAN_INTERVAL_MINUTES,
    MAX_SCOPE_RADIUS,
    MIN_SCAN_INTERVAL_MINUTES,
    MIN_SCOPE_RADIUS,
    SCOPE_ALL,
    SCOPE_HOME,
    SCOPE_ZONE,
)
from .providers import DEFAULT_PROVIDER_KEYS, PROVIDERS

SCOPE_OPTIONS: list[SelectOptionDict] = [
    {"value": SCOPE_ALL, "label": "All of Australia"},
    {"value": SCOPE_HOME, "label": "Around the Home Assistant location"},
    {"value": SCOPE_ZONE, "label": "Inside an existing zone"},
]


def provider_options() -> list[SelectOptionDict]:
    """Return the selectable providers."""
    return [
        {"value": key, "label": provider.name}
        for key, provider in sorted(PROVIDERS.items(), key=lambda item: item[1].name)
    ]


def _providers_schema(default: list[str]) -> vol.Schema:
    """Return the schema for choosing providers."""
    return vol.Schema(
        {
            vol.Required(CONF_PROVIDERS, default=default): SelectSelector(
                SelectSelectorConfig(
                    options=provider_options(),
                    multiple=True,
                    mode=SelectSelectorMode.DROPDOWN,
                )
            ),
            vol.Optional(
                CONF_SCAN_INTERVAL, default=15
            ): NumberSelector(
                NumberSelectorConfig(
                    min=MIN_SCAN_INTERVAL_MINUTES,
                    max=MAX_SCAN_INTERVAL_MINUTES,
                    step=5,
                    mode=NumberSelectorMode.BOX,
                    unit_of_measurement="minutes",
                )
            ),
            vol.Optional(CONF_API_KEY, default=""): TextSelector(
                TextSelectorConfig(type=TextSelectorType.PASSWORD)
            ),
        }
    )


def _radius_selector(default: int) -> NumberSelector:
    """Return the selector for a radius in metres."""
    return NumberSelector(
        NumberSelectorConfig(
            min=MIN_SCOPE_RADIUS,
            max=MAX_SCOPE_RADIUS,
            step=500,
            mode=NumberSelectorMode.BOX,
            unit_of_measurement="m",
        )
    )


def _stored_radius(entry: config_entries.ConfigEntry) -> int:
    """Return the radius stored on a config entry."""
    value = entry.options.get(
        CONF_SCOPE_RADIUS,
        entry.data.get(CONF_SCOPE_RADIUS, DEFAULT_SCOPE_RADIUS),
    )
    try:
        radius = int(value)
    except (TypeError, ValueError):
        return DEFAULT_SCOPE_RADIUS
    return max(MIN_SCOPE_RADIUS, min(MAX_SCOPE_RADIUS, radius))


class CarparkAustraliaConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle the config flow for Carpark Australia."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialise the flow."""
        self._data: dict[str, Any] = {}
        self._reauth_key: str | None = None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Choose the providers to poll."""
        if user_input is not None:
            self._data.update(user_input)
            return await self.async_step_scope()
        return self.async_show_form(
            step_id="user",
            data_schema=_providers_schema(list(DEFAULT_PROVIDER_KEYS)),
        )

    async def async_step_scope(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Choose how much of Australia to track."""
        if user_input is not None:
            self._data[CONF_SCOPE] = user_input[CONF_SCOPE]
            if user_input[CONF_SCOPE] == SCOPE_ZONE:
                return await self.async_step_scope_zone()
            if user_input[CONF_SCOPE] == SCOPE_HOME:
                return await self.async_step_scope_home()
            return self._create_entry()
        return self.async_show_form(
            step_id="scope",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_SCOPE, default=SCOPE_HOME): SelectSelector(
                        SelectSelectorConfig(
                            options=SCOPE_OPTIONS,
                            mode=SelectSelectorMode.DROPDOWN,
                        )
                    ),
                }
            ),
        )

    async def async_step_scope_home(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Choose the radius around the Home Assistant location."""
        if user_input is not None:
            self._data[CONF_SCOPE_RADIUS] = user_input[CONF_SCOPE_RADIUS]
            return self._create_entry()
        return self.async_show_form(
            step_id="scope_home",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_SCOPE_RADIUS, default=DEFAULT_SCOPE_RADIUS
                    ): _radius_selector(DEFAULT_SCOPE_RADIUS),
                }
            ),
        )

    async def async_step_scope_zone(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Choose the zone to count the parking spaces in."""
        errors: dict[str, str] = {}
        if user_input is not None:
            entity_id = str(user_input.get(CONF_SCOPE_ZONE) or "")
            if not entity_id:
                errors[CONF_SCOPE_ZONE] = "zone_required"
            else:
                self._data[CONF_SCOPE_ZONE] = entity_id
                return self._create_entry()
        return self.async_show_form(
            step_id="scope_zone",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_SCOPE_ZONE): EntitySelector(
                        EntitySelectorConfig(domain="zone")
                    ),
                }
            ),
            errors=errors,
        )

    def _create_entry(self) -> ConfigFlowResult:
        """Create the config entry."""
        providers = [
            key for key in self._data.get(CONF_PROVIDERS, []) if key in PROVIDERS
        ]
        data = {
            CONF_PROVIDERS: providers or list(DEFAULT_PROVIDER_KEYS),
            CONF_SCAN_INTERVAL: self._data.get(CONF_SCAN_INTERVAL, 15),
            CONF_API_KEY: self._data.get(CONF_API_KEY, ""),
            CONF_SCOPE: self._data.get(CONF_SCOPE, SCOPE_HOME),
            CONF_SCOPE_RADIUS: self._data.get(
                CONF_SCOPE_RADIUS, DEFAULT_SCOPE_RADIUS
            ),
            CONF_SCOPE_ZONE: self._data.get(CONF_SCOPE_ZONE, ""),
        }
        return self.async_create_entry(title="Australian car parks", data=data)

    async def async_step_reauth(
        self, entry_data: dict[str, Any]
    ) -> ConfigFlowResult:
        """Ask for the API key again after an authentication failure."""
        self._reauth_key = str(entry_data.get(CONF_API_KEY) or "")
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Collect a new API key."""
        errors: dict[str, str] = {}
        if user_input is not None:
            api_key = str(user_input.get(CONF_API_KEY) or "").strip()
            if not api_key:
                errors[CONF_API_KEY] = "api_key_required"
            else:
                return self.async_update_reload_and_abort(
                    self._get_reauth_entry(),
                    data_updates={CONF_API_KEY: api_key},
                )
        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_API_KEY, default=self._reauth_key or ""
                    ): TextSelector(
                        TextSelectorConfig(type=TextSelectorType.PASSWORD)
                    ),
                }
            ),
            errors=errors,
        )

    @staticmethod
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Return the options flow."""
        return CarparkAustraliaOptionsFlow()


class CarparkAustraliaOptionsFlow(config_entries.OptionsFlow):
    """Handle the options for Carpark Australia."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage the options."""
        entry = self.config_entry
        current_providers = list(
            entry.options.get(CONF_PROVIDERS, entry.data.get(CONF_PROVIDERS, []))
        )
        current_radius = _stored_radius(entry)
        if user_input is not None:
            providers = [
                key for key in user_input.get(CONF_PROVIDERS, []) if key in PROVIDERS
            ]
            return self.async_create_entry(
                data={
                    CONF_PROVIDERS: providers or list(DEFAULT_PROVIDER_KEYS),
                    CONF_SCAN_INTERVAL: user_input.get(CONF_SCAN_INTERVAL, 15),
                    CONF_API_KEY: user_input.get(CONF_API_KEY, ""),
                    CONF_SCOPE: user_input.get(CONF_SCOPE, SCOPE_HOME),
                    CONF_SCOPE_RADIUS: user_input.get(
                        CONF_SCOPE_RADIUS, DEFAULT_SCOPE_RADIUS
                    ),
                    CONF_SCOPE_ZONE: user_input.get(CONF_SCOPE_ZONE, ""),
                }
            )

        schema = _providers_schema(current_providers).extend(
            {
                vol.Required(
                    CONF_SCOPE, default=entry.data.get(CONF_SCOPE, SCOPE_HOME)
                ): SelectSelector(
                    SelectSelectorConfig(
                        options=SCOPE_OPTIONS,
                        mode=SelectSelectorMode.DROPDOWN,
                    )
                ),
                vol.Optional(
                    CONF_SCOPE_RADIUS,
                    default=current_radius,
                ): _radius_selector(current_radius),
                vol.Optional(
                    CONF_SCOPE_ZONE, default=entry.data.get(CONF_SCOPE_ZONE, "")
                ): EntitySelector(EntitySelectorConfig(domain="zone")),
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)
