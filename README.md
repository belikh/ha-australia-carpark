<p align="right">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/belikh/design/main/packages/graphics/logo/jupiter-logo-dark.svg">
    <img alt="jupiter.au" src="https://raw.githubusercontent.com/belikh/design/main/packages/graphics/logo/jupiter-logo-light.svg" width="260">
  </picture>
</p>

# Carpark Australia

Home Assistant integration for car park availability in Australia. It reads the car parks that councils and private operators publish and creates a device with sensors for each one. It also adds counts for the whole area you choose, so one sensor can answer how many parking spaces are free near home.

<p>
  <a href="#install">Install</a> ·
  <a href="#entities">Entities</a> ·
  <a href="#choose-an-area">Choose an area</a> ·
  <a href="#data-sources">Data sources</a> ·
  <a href="#develop">Develop</a>
</p>

<br>

---

<br>

## Install

1. In HACS, add a custom repository: `https://github.com/belikh/ha-australia-carpark`, type **Integration**.
2. Install **Carpark Australia** and restart Home Assistant.
3. Add the integration from **Settings → Devices & Services → Add integration**.
4. Choose the data sources and the area to track.

Transport for NSW needs an API key. Register at
[developer.transport.nsw.gov.au](https://developer.transport.nsw.gov.au/) and
paste it into the config flow. Every other source is token-free.

<br>

## Entities

**Per car park** (only for car parks that publish something):

| Entity | Type | Meaning |
| --- | --- | --- |
| `Spaces free` | sensor | Free spaces right now |
| `Occupancy` | sensor | Percentage of the car park that is occupied |
| `Total spaces` | sensor | Capacity, for car parks that publish no live count |
| `Spaces available` | binary sensor | On when at least one space is free |

**For the whole area in scope**:

| Entity | Type | Meaning |
| --- | --- | --- |
| `Parking spaces free` | sensor | Free spaces counted across every car park in scope |
| `Parking spaces total` | sensor | Capacity counted across every car park in scope |
| `Parking spaces occupied` | sensor | Occupied spaces counted across every car park in scope |
| `Parking spaces free percentage` | sensor | Free share of the counted capacity |
| `Car parks tracked` | sensor | How many car parks are in scope |

**Per data source**:

| Entity | Type | Meaning |
| --- | --- | --- |
| `Car parks (<provider>)` | sensor | Every car park a source reported, as a list attribute |

The roll-up sensors carry a `scope` attribute naming the area they cover, plus
`carparks_counted_free`, `carparks_counted_total` and `carparks_counted_both`
so you can see how many car parks contributed to each figure.

The catalogue sensor lists at most 500 car parks per source. When a source
publishes more, the attributes `carpark_count`, `listed_count` and `truncated`
tell you how many were left out.

<br>

## Choose an area

Tracking every car park in Australia creates roughly **1,900 entities**. The
config flow asks for the area to count, and you can change it later under
**Configure** on the integration card.

| Scope | What it counts |
| --- | --- |
| Around the Home Assistant location | Car parks within a radius (default 5,000 m) of your configured home position |
| Inside an existing zone | Car parks inside any Home Assistant zone you have defined |
| All of Australia | Everything the selected sources publish |

### Zones

Pick **Inside an existing zone** and choose one of your zones — `zone.home`,
`zone.work`, a suburb boundary you drew, anything. The integration reads the
zone's latitude, longitude and radius, and counts the parking spaces inside
it:

```yaml
automation:
  - alias: "Find parking before I leave work"
    trigger:
      - platform: state
        entity_id: sensor.parking_spaces_free
        below: 50
    action:
      - service: notify.mobile_app
        data:
          message: "Only {{ states('sensor.parking_spaces_free') }} parking spaces free near work."
```

The `scope` attribute on each roll-up sensor tells you which area a figure
covers — the zone name, `within 5000 m of home`, or `Australia`.

> [!NOTE]
> The integration does not create zones. It only reads the ones you already have.

<br>

## Data sources

| Source | Data | Car parks | Availability |
| --- | --- | --- | --- |
| City of Adelaide (UPark) | Free spaces per car park | 10 | Live |
| Transport for NSW | Occupancy per facility | — | Live, needs an API key |
| Brisbane City Council | Occupancy forecast per paid parking zone | 617 | Forecast only |
| Wilson Parking | Locations, services, EV and accessible parking | 568 | Locations only |
| City of Sydney | Council car park locations | 2 | Locations only |
| City of Perth | Car park locations and capacity | 32 | Capacity only |
| ACT Government | Car park asset locations | 1,368 | Locations only |
| City of Hobart | Car park and parking structure locations | 12 | Locations only |

Counts are as published by each source and change over time.

<details><summary><b>Notes on the data</b></summary>

<br>

- **Brisbane publishes a forecast.** The council's occupancy
  forecasting dataset predicts how many bays will be occupied for each hour of
  the day, using parking meter transactions and occupancy surveys. Treat the
  Brisbane figures as estimates.
- **Adelaide publishes free spaces but no capacity.** Its free-space counts are
  included in `Parking spaces free`, but they are not part of the percentage
  calculation, which needs both figures.
- **Several sources publish locations only.** Wilson Parking, the City of
  Sydney, the ACT Government and the City of Hobart do not publish live
  availability, so those car parks appear in the `Car parks (<provider>)`
  catalogue sensor and count towards `Car parks tracked`, but produce no
  per-park sensors.
- **Private operators are included.** Wilson Parking operates car parks in
  every state and territory and is listed as a source in its own right, with
  the services each site offers (monthly parking, book-a-bay, EV charging,
  accessible parking).
- **Car parks without coordinates are skipped when you scope by distance or
  zone.** Every source listed above publishes coordinates except the ACT
  Government polygon layer, whose centroids are used instead.

</details>

<br>

## Develop

```bash
uv sync
uv run pytest
uv run ruff check .
uv run mypy
```

The `hacs` and `hassfest` workflows in `.github/workflows/` run the HACS and Home Assistant validations on GitHub.

<br>

## Attribution

- City of Adelaide UPark availability reports — City of Adelaide open data.
- Brisbane City Council parking meter and occupancy forecasting data — Brisbane
  City Council open data, CC BY 4.0.
- City of Sydney, City of Perth, ACT Government and City of Hobart car park
  data — the relevant council's ArcGIS open data service.
- Transport for NSW car park data — Transport for NSW Car Park API.
- Wilson Parking car park details — wilsonparking.com.au.
- Adelaide car park coordinates — © OpenStreetMap contributors, licensed under
  the Open Database License (ODbL).

<br>

## Licence

MIT. Unofficial; not endorsed by any council or operator.

<br>

<p align="right"><sub>jupiter.au</sub></p>
