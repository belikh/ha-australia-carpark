---
title: Configure
summary: Choose your data sources, tracked car parks and area.
section: use
order: 20
icon: sliders
audience: users
status: stable
---

The config flow asks for:

1. **Data sources** — the providers to poll. Only selected providers are polled on each refresh.
2. **Tracked car parks** — optional. Search and select specific car parks to track with their own entities. Leave empty to only use the scope-level sensors.
3. **Area to track** — around the Home Assistant location, inside a zone, or all of Australia.

## Area to track

Tracking every car park in Australia creates a lot of entities. Choose the area that covers where you actually park:

| Scope | What it counts |
|---|---|
| Around the Home Assistant location | Car parks within a radius (default 5,000 m) of your configured home position |
| Inside an existing zone | Car parks inside any Home Assistant zone you have defined |
| All of Australia | Everything the selected sources publish |

### Zones

Pick **Inside an existing zone** and choose one of your zones — `zone.home`, `zone.work`, a suburb boundary you drew, anything. The integration reads the zone's latitude, longitude and radius, and counts the parking spaces inside it:

```yaml title="Find parking before I leave work"
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

The `scope` attribute on each roll-up sensor tells you which area a figure covers — the zone name, `within 5000 m of home`, or `Australia`.

**The integration does not create zones.** It only reads the ones you already have.

## Tracked car parks

During setup you can search and select specific car parks to track individually. Each selected car park becomes a device with its own entities:

| Entity | Type | Meaning |
|---|---|---|
| `Spaces free` | sensor | Free spaces right now |
| `Occupancy` | sensor | Percentage of the car park that is occupied |
| `Total spaces` | sensor | Capacity, for car parks that publish no live count |
| `Spaces available` | binary sensor | On when at least one space is free |

Leave the selection empty to only use the scope-level sensors. You can change the selection later under **Configure** on the integration card.

[[entities]]
