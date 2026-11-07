"""Registry of every carpark data source."""

from __future__ import annotations

from .act import ActProvider
from .adelaide import AdelaideProvider
from .base import CarparkProvider, ProviderContext
from .brisbane import BrisbaneProvider
from .hobart import HobartProvider
from .nsw import NswProvider
from .perth import PerthProvider
from .sydney import SydneyProvider
from .wilson import WilsonProvider

PROVIDER_CLASSES: tuple[type[CarparkProvider], ...] = (
    AdelaideProvider,
    NswProvider,
    BrisbaneProvider,
    WilsonProvider,
    SydneyProvider,
    PerthProvider,
    ActProvider,
    HobartProvider,
)

PROVIDERS: dict[str, CarparkProvider] = {cls.key: cls() for cls in PROVIDER_CLASSES}

# Providers that work without any credentials.
FREE_PROVIDER_KEYS: tuple[str, ...] = tuple(
    key for key, provider in PROVIDERS.items() if not provider.requires_api_key
)

DEFAULT_PROVIDER_KEYS: tuple[str, ...] = FREE_PROVIDER_KEYS


def get_provider(key: str) -> CarparkProvider | None:
    """Return the provider registered under *key*."""
    return PROVIDERS.get(key)


__all__ = [
    "DEFAULT_PROVIDER_KEYS",
    "FREE_PROVIDER_KEYS",
    "PROVIDERS",
    "PROVIDER_CLASSES",
    "CarparkProvider",
    "ProviderContext",
    "get_provider",
]
