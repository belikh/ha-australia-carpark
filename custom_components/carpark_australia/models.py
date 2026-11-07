"""Data model shared by every carpark provider."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

_SLUG_RE = re.compile(r"[^a-z0-9]+")


def slugify(value: str) -> str:
    """Return a lowercase ASCII slug suitable for entity ids.

    Accented characters are folded rather than dropped so ``Saint-Kilda``
    and ``St Kilda`` stay readable in entity ids.
    """
    folded = unicodedata.normalize("NFKD", value)
    ascii_text = folded.encode("ascii", "ignore").decode("ascii")
    slug = _SLUG_RE.sub("_", ascii_text.lower()).strip("_")
    return slug or "carpark"


@dataclass(frozen=True)
class Carpark:
    """One parking facility reported by a provider.

    ``spaces_total`` and ``spaces_free`` are optional because several
    councils publish the location and capacity of a car park without
    publishing a live occupancy count.
    """

    provider: str
    key: str
    name: str
    operator: str
    kind: str = "carpark"
    spaces_total: int | None = None
    spaces_free: int | None = None
    occupancy_percent: float | None = None
    latitude: float | None = None
    longitude: float | None = None
    address: str | None = None
    url: str | None = None
    updated: datetime | None = None
    extra: dict[str, Any] = field(default_factory=dict)

    @property
    def unique_id(self) -> str:
        """Return the identifier unique across all providers."""
        return f"{self.provider}_{self.key}"

    @property
    def slug(self) -> str:
        """Return a slug built from the provider key and the car park name."""
        return slugify(f"{self.provider}_{self.name}")

    @property
    def spaces_occupied(self) -> int | None:
        """Return the number of occupied spaces, when both counts are known."""
        if self.spaces_total is None or self.spaces_free is None:
            return None
        return max(0, self.spaces_total - self.spaces_free)

    @property
    def computed_occupancy_percent(self) -> float | None:
        """Return the occupancy percentage, preferring a published value."""
        if self.occupancy_percent is not None:
            return round(self.occupancy_percent, 1)
        if self.spaces_total and self.spaces_free is not None and self.spaces_total > 0:
            return round((self.spaces_occupied or 0) / self.spaces_total * 100, 1)
        return None

    @property
    def has_availability(self) -> bool:
        """Return whether the provider published a live availability count."""
        return self.spaces_free is not None
