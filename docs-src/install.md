---
title: Install
summary: Add the integration from HACS and choose your data sources.
section: use
order: 10
icon: terminal
audience: users
status: stable
---

## Install (HACS)

1. Open HACS and add a custom repository: `https://github.com/belikh/ha-australia-carpark` as type **Integration**.
2. Install **Carpark Australia** and restart Home Assistant.
3. Add the integration from **Settings → Devices & Services → Add integration**.
4. Choose the data sources, any car parks to track individually, and the area to track.

Transport for NSW needs an API key. Register at [developer.transport.nsw.gov.au](https://developer.transport.nsw.gov.au/) and paste it into the config flow. Every other source is token-free.

[[configure]]
