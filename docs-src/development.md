---
title: Develop
summary: Run tests, lint and type checks.
section: contribute
order: 10
icon: edit
audience: developers
status: stable
---

```bash
uv sync
uv run pytest
uv run ruff check .
uv run mypy
```

Hassfest can be run with `python -m homeassistant.hassfest` via the script in `.github/workflows/`.

## Attribution

- City of Adelaide UPark availability reports — City of Adelaide open data.
- Brisbane City Council parking meter and occupancy forecasting data — Brisbane City Council open data, CC BY 4.0.
- City of Sydney, City of Perth, ACT Government and City of Hobart car park data — the relevant council's ArcGIS open data service.
- Transport for NSW car park data — Transport for NSW Car Park API.
- Wilson Parking car park details — wilsonparking.com.au.
- Adelaide car park coordinates — © OpenStreetMap contributors, licensed under the Open Database License (ODbL).

## Licence

MIT. Unofficial; not endorsed by any council or operator.

[[install]]
