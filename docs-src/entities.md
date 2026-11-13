---
title: Entities
summary: Scope-level sensors and per-car-park entities.
section: build
order: 10
icon: app
audience: users
status: stable
---

## Scope-level sensors

The scope sensor is the main roll-up entity. It counts parking spaces across the whole area in scope, so you get one number instead of one sensor per car park:

| Entity | Type | Meaning |
|---|---|---|
| `Parking spaces free` | sensor | Free spaces counted across every car park in scope |
| `Parking spaces total` | sensor | Capacity counted across every car park in scope |
| `Parking spaces occupied` | sensor | Occupied spaces counted across every car park in scope |
| `Parking spaces free percentage` | sensor | Free share of the counted capacity |
| `Car parks tracked` | sensor | How many car parks are in scope |

The roll-up sensors carry a `scope` attribute naming the area they cover, plus `carparks_counted_free`, `carparks_counted_total` and `carparks_counted_both` so you can see how many car parks contributed to each figure.

## Scope sensor attributes

The `carparks` attribute on each roll-up sensor lists every car park in scope:

- name, provider, operator
- free, total and occupied spaces
- occupancy percentage
- pricing (when the source publishes it)
- address, coordinates, URL

The `free_carparks` attribute lists only the car parks that currently have at least one free space, with the same detail. Long lists are truncated to keep the attribute readable.

## Per-car-park entities (opt-in)

During setup you can search and select specific car parks to track individually. Each selected car park becomes a device with its own entities:

| Entity | Type | Meaning |
|---|---|---|
| `Spaces free` | sensor | Free spaces right now |
| `Occupancy` | sensor | Percentage of the car park that is occupied |
| `Total spaces` | sensor | Capacity, for car parks that publish no live count |
| `Spaces available` | binary sensor | On when at least one space is free |

Leave the selection empty to only use the scope-level sensors.

[[configure]]
