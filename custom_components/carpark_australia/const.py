"""Constants for the Carpark Australia integration."""

from __future__ import annotations

from datetime import timedelta

DOMAIN = "carpark_australia"

CONF_PROVIDERS = "providers"
CONF_SCAN_INTERVAL = "scan_interval_hours"
CONF_API_KEY = "api_key"
CONF_SCOPE = "scope"
CONF_SCOPE_ZONE = "scope_zone"
CONF_SCOPE_RADIUS = "scope_radius"

SCOPE_ALL = "all"
SCOPE_HOME = "home"
SCOPE_ZONE = "zone"

DEFAULT_SCAN_INTERVAL = timedelta(minutes=15)
MIN_SCAN_INTERVAL_MINUTES = 5
MAX_SCAN_INTERVAL_MINUTES = 1440

# Default radius around the Home Assistant location, in metres.
DEFAULT_SCOPE_RADIUS = 5000
MIN_SCOPE_RADIUS = 100
MAX_SCOPE_RADIUS = 50000

ATTR_SPACES_TOTAL = "spaces_total"
ATTR_SPACES_FREE = "spaces_free"
ATTR_SPACES_OCCUPIED = "spaces_occupied"
ATTR_OCCUPANCY_PERCENT = "occupancy_percent"
ATTR_OPERATOR = "operator"
ATTR_PROVIDER = "provider"
ATTR_ADDRESS = "address"
ATTR_LATITUDE = "latitude"
ATTR_LONGITUDE = "longitude"
ATTR_URL = "url"
ATTR_KIND = "kind"
ATTR_LAST_UPDATED = "last_updated"
ATTR_SCOPE = "scope"

KIND_CARPARK = "carpark"
KIND_METER = "parking_meter"
KIND_FORECAST = "forecast"
