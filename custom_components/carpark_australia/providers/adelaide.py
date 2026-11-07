"""City of Adelaide UPark car parks.

The council publishes one XML report per car park on S3. Each report
carries the number of free spaces and the time the figure was produced.
"""

from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import NamedTuple
from xml.etree import ElementTree

from aiohttp import ClientSession

from ..models import Carpark
from .base import ProviderContext, as_int

OPERATOR = "City of Adelaide"
BASE_URL = (
    "https://s3.ap-southeast-2.amazonaws.com/dmzweb.adelaidecitycouncil.com/"
    "UParkXML/UPark+Space+Availability+by+Carpark+-+{feed}.xml"
)


class Feed(NamedTuple):
    """One UPark availability report."""

    feed: str
    name: str
    latitude: float
    longitude: float


# The council publishes one report per car park, but the reports carry no
# location. The coordinates below come from the OpenStreetMap mapping of
# each UPark car park, licensed under the Open Database License (ODbL).
FEEDS: tuple[Feed, ...] = (
    Feed("Andrew+St", "Andrew Street", -34.9279653, 138.5948771),
    Feed("Central+Market", "Central Market", -34.9295469, 138.5973147),
    Feed("Frome", "Frome Street", -34.9219701, 138.6080057),
    Feed("Gawler+Place", "Gawler Place", -34.9220166, 138.6014186),
    Feed("Grote+Street", "Grote Street", -34.9280876, 138.5958756),
    Feed("Light+Square", "Light Square", -34.9240735, 138.5947647),
    Feed("Pirie-Flinders", "Pirie / Flinders Street", -34.9257166, 138.6073639),
    Feed("Rundle+Street", "Rundle Street", -34.9229201, 138.6061807),
    Feed("Topham+Mall", "Topham Mall", -34.9253465, 138.5973565),
    Feed("Wyatt+Street", "Wyatt Street", -34.9250983, 138.604112),
)

_TIME_RE = re.compile(r"As at:\s*(.+?)\s*$")


def _localname(tag: str) -> str:
    """Return an XML tag without its namespace."""
    return tag.rsplit("}", 1)[-1]


def parse_upark_xml(payload: bytes) -> tuple[str | None, int | None]:
    """Return ``(car_park_name, free_spaces)`` from an UPark report.

    Returns ``(None, None)`` when the report carries no usable reading.
    """
    try:
        root = ElementTree.fromstring(payload)
    except ElementTree.ParseError:
        return None, None

    name: str | None = None
    free: int | None = None
    for element in root.iter():
        if _localname(element.tag) != "CarparkName":
            continue
        name = (element.get("Textbox31") or element.get("Name") or "").strip() or None
        free = as_int(element.get("FreeSpaces"))
        break
    return name, free


def parse_report_time(payload: bytes) -> datetime | None:
    """Return the timestamp the council stamped on the report."""
    try:
        root = ElementTree.fromstring(payload)
    except ElementTree.ParseError:
        return None
    raw = root.get("Textbox3") or ""
    match = _TIME_RE.search(raw)
    if not match:
        return None
    stamp = match.group(1)
    for fmt in ("%I:%M:%S %p", "%H:%M:%S", "%I:%M %p"):
        try:
            parsed = datetime.strptime(stamp, fmt)
        except ValueError:
            continue
        now = datetime.now(UTC)
        return parsed.replace(
            year=now.year,
            month=now.month,
            day=now.day,
            tzinfo=UTC,
        )
    return None


class AdelaideProvider:
    """UPark availability for the City of Adelaide."""

    key = "adelaide"
    name = "City of Adelaide (UPark)"
    requires_api_key = False

    async def fetch(self, context: ProviderContext) -> list[Carpark]:
        """Return the live free space count for every UPark car park."""
        carparks: list[Carpark] = []
        for entry in FEEDS:
            url = BASE_URL.format(feed=entry.feed)
            async with context.session.get(url) as response:
                response.raise_for_status()
                payload = await response.read()
            name, free = parse_upark_xml(payload)
            if name is None and free is None:
                continue
            carparks.append(
                Carpark(
                    provider=self.key,
                    key=entry.feed.replace("+", "-").lower(),
                    name=name or entry.name,
                    operator=OPERATOR,
                    spaces_free=free,
                    latitude=entry.latitude,
                    longitude=entry.longitude,
                    updated=parse_report_time(payload),
                    url=url,
                    extra={"feed": entry.name},
                )
            )
        return carparks


async def fetch_all(session: ClientSession) -> list[Carpark]:
    """Fetch every UPark car park with a plain session."""
    provider = AdelaideProvider()
    return await provider.fetch(ProviderContext(session=session))
