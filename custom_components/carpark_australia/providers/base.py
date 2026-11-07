"""Shared plumbing for carpark providers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from aiohttp import ClientSession

from ..models import Carpark


@dataclass(frozen=True)
class ProviderContext:
    """Everything a provider needs to fetch data."""

    session: ClientSession
    api_key: str | None = None


class CarparkProvider(Protocol):
    """Protocol implemented by every data source."""

    key: str
    name: str
    requires_api_key: bool

    async def fetch(self, context: ProviderContext) -> list[Carpark]:
        """Return the car parks this provider knows about."""


def as_int(value: Any) -> int | None:
    """Return *value* as an integer, or None when it cannot be converted."""
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return None


def as_float(value: Any) -> float | None:
    """Return *value* as a float, or None when it cannot be converted."""
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(str(value).strip())
    except (TypeError, ValueError):
        return None


def first_value(payload: dict[str, Any], *names: str) -> Any:
    """Return the first present, non-empty value among *names*."""
    for name in names:
        if name in payload:
            value = payload[name]
            if value not in (None, ""):
                return value
    return None
