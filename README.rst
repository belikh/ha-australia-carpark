.. raw:: html

   <p align="right">
     <picture>
       <source media="(prefers-color-scheme: dark)" srcset="https://github.com/belikh/design/releases/latest/download/logo-dark.svg">
       <img alt="jupiter.au" src="https://github.com/belikh/design/releases/latest/download/logo-light.svg" width="260">
     </picture>
   </p>

   <h1>Carpark Australia</h1>

.. meta::
   :description: Home Assistant integration for car park availability in Australia.

Home Assistant integration for car park availability in Australia. It reads the car parks that councils and private operators publish and creates a device with sensors for each one. It also adds counts for the whole area you choose, so one sensor can answer how many parking spaces are free near home.

`Install`_ · `Entities`_ · `Choose an area`_ · `Data sources`_ · `Develop`_

|

.. raw:: html

   <p align="center"><picture><source media="(prefers-color-scheme: dark)" srcset="https://github.com/belikh/design/releases/latest/download/rule-end-dark.svg"><img alt="" src="https://github.com/belikh/design/releases/latest/download/rule-end-light.svg" width="50%"></picture></p>

Install
-------

1. In HACS, add a custom repository: ``https://github.com/belikh/ha-australia-carpark``, type **Integration**.
2. Install **Carpark Australia** and restart Home Assistant.
3. Add the integration from **Settings → Devices & Services → Add integration**.
4. Choose the data sources and the area to track.

Transport for NSW needs an API key. Register at
`developer.transport.nsw.gov.au <https://developer.transport.nsw.gov.au/>`__ and
paste it into the config flow. Every other source is token-free.

|

Entities
--------

**Per car park** (only for car parks that publish something):

.. list-table::
   :header-rows: 1

   * - Entity
     - Type
     - Meaning
   * - |check-l| |check-d| ``Spaces free``
     - sensor
     - Free spaces right now
   * - |chart-l| |chart-d| ``Occupancy``
     - sensor
     - Percentage of the car park that is occupied
   * - |database-l| |database-d| ``Total spaces``
     - sensor
     - Capacity, for car parks that publish no live count
   * - |success-l| |success-d| ``Spaces available``
     - binary sensor
     - On when at least one space is free

**For the whole area in scope**:

.. list-table::
   :header-rows: 1

   * - Entity
     - Type
     - Meaning
   * - |check-l| |check-d| ``Parking spaces free``
     - sensor
     - Free spaces counted across every car park in scope
   * - |database-l| |database-d| ``Parking spaces total``
     - sensor
     - Capacity counted across every car park in scope
   * - |chart-l| |chart-d| ``Parking spaces occupied``
     - sensor
     - Occupied spaces counted across every car park in scope
   * - |trend-l| |trend-d| ``Parking spaces free percentage``
     - sensor
     - Free share of the counted capacity
   * - |pin-l| |pin-d| ``Car parks tracked``
     - sensor
     - How many car parks are in scope

**Per data source**:

.. list-table::
   :header-rows: 1

   * - Entity
     - Type
     - Meaning
   * - |folder-l| |folder-d| ``Car parks (<provider>)``
     - sensor
     - Every car park a source reported, as a list attribute

The roll-up sensors carry a ``scope`` attribute naming the area they cover, plus
``carparks_counted_free``, ``carparks_counted_total`` and ``carparks_counted_both``
so you can see how many car parks contributed to each figure.

The catalogue sensor lists at most 500 car parks per source. When a source
publishes more, the attributes ``carpark_count``, ``listed_count`` and ``truncated``
tell you how many were left out.

|

.. raw:: html

   <p align="center"><picture><source media="(prefers-color-scheme: dark)" srcset="https://github.com/belikh/design/releases/latest/download/rule-end-dark.svg"><img alt="" src="https://github.com/belikh/design/releases/latest/download/rule-end-light.svg" width="50%"></picture></p>

Choose an area
--------------

Tracking every car park in Australia creates roughly **1,900 entities**. The
config flow asks for the area to count, and you can change it later under
**Configure** on the integration card.

.. list-table::
   :header-rows: 1

   * - Scope
     - What it counts
   * - |home-l| |home-d| Around the Home Assistant location
     - Car parks within a radius (default 5,000 m) of your configured home position
   * - |pin-l| |pin-d| Inside an existing zone
     - Car parks inside any Home Assistant zone you have defined
   * - |globe-l| |globe-d| All of Australia
     - Everything the selected sources publish

Zones
~~~~~

Pick **Inside an existing zone** and choose one of your zones — ``zone.home``,
``zone.work``, a suburb boundary you drew, anything. The integration reads the
zone's latitude, longitude and radius, and counts the parking spaces inside
it:

.. code-block:: yaml

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

The ``scope`` attribute on each roll-up sensor tells you which area a figure
covers — the zone name, ``within 5000 m of home``, or ``Australia``.

.. raw:: html

   <table>
     <tr align="left"><th>Note</th></tr>
     <tr><td>

The integration does not create zones. It only reads the ones you already have.

.. raw:: html

   </td></tr>
   </table>

|

.. raw:: html

   <p align="center"><picture><source media="(prefers-color-scheme: dark)" srcset="https://github.com/belikh/design/releases/latest/download/rule-end-dark.svg"><img alt="" src="https://github.com/belikh/design/releases/latest/download/rule-end-light.svg" width="50%"></picture></p>

Data sources
------------

.. list-table::
   :header-rows: 1

   * - Source
     - Data
     - Car parks
     - Availability
   * - |signal-l| |signal-d| City of Adelaide (UPark)
     - Free spaces per car park
     - 10
     - Live
   * - |key-l| |key-d| Transport for NSW
     - Occupancy per facility
     - —
     - Live, needs an API key
   * - |trend-l| |trend-d| Brisbane City Council
     - Occupancy forecast per paid parking zone
     - 617
     - Forecast only
   * - |pin-l| |pin-d| Wilson Parking
     - Locations, services, EV and accessible parking
     - 568
     - Locations only
   * - |pin-l| |pin-d| City of Sydney
     - Council car park locations
     - 2
     - Locations only
   * - |database-l| |database-d| City of Perth
     - Car park locations and capacity
     - 32
     - Capacity only
   * - |pin-l| |pin-d| ACT Government
     - Car park asset locations
     - 1,368
     - Locations only
   * - |pin-l| |pin-d| City of Hobart
     - Car park and parking structure locations
     - 12
     - Locations only

Counts are as published by each source and change over time.

.. raw:: html

   <details><summary><b>Notes on the data</b></summary>

- **Brisbane publishes a forecast.** The council's occupancy
  forecasting dataset predicts how many bays will be occupied for each hour of
  the day, using parking meter transactions and occupancy surveys. Treat the
  Brisbane figures as estimates.
- **Adelaide publishes free spaces but no capacity.** Its free-space counts are
  included in ``Parking spaces free``, but they are not part of the percentage
  calculation, which needs both figures.
- **Several sources publish locations only.** Wilson Parking, the City of
  Sydney, the ACT Government and the City of Hobart do not publish live
  availability, so those car parks appear in the ``Car parks (<provider>)``
  catalogue sensor and count towards ``Car parks tracked``, but produce no
  per-park sensors.
- **Private operators are included.** Wilson Parking operates car parks in
  every state and territory and is listed as a source in its own right, with
  the services each site offers (monthly parking, book-a-bay, EV charging,
  accessible parking).
- **Car parks without coordinates are skipped when you scope by distance or
  zone.** Every source listed above publishes coordinates except the ACT
  Government polygon layer, whose centroids are used instead.

.. raw:: html

   </details>

|

Develop
-------

.. code-block:: bash

   uv sync
   uv run pytest
   uv run ruff check .
   uv run mypy

The ``hacs`` and ``hassfest`` workflows in ``.github/workflows/`` run the HACS and Home Assistant validations on GitHub.

|

.. raw:: html

   <p align="center"><picture><source media="(prefers-color-scheme: dark)" srcset="https://github.com/belikh/design/releases/latest/download/rule-end-dark.svg"><img alt="" src="https://github.com/belikh/design/releases/latest/download/rule-end-light.svg" width="50%"></picture></p>

Attribution
-----------

- City of Adelaide UPark availability reports — City of Adelaide open data.
- Brisbane City Council parking meter and occupancy forecasting data — Brisbane
  City Council open data, CC BY 4.0.
- City of Sydney, City of Perth, ACT Government and City of Hobart car park
  data — the relevant council's ArcGIS open data service.
- Transport for NSW car park data — Transport for NSW Car Park API.
- Wilson Parking car park details — wilsonparking.com.au.
- Adelaide car park coordinates — © OpenStreetMap contributors, licensed under
  the Open Database License (ODbL).

|

Licence
-------

MIT. Unofficial; not endorsed by any council or operator.

|

.. raw:: html

   <p align="right"><sub>jupiter.au</sub></p>

.. |check-l| image:: https://github.com/belikh/design/releases/latest/download/icon-check-light.svg#gh-light-mode-only
   :width: 20
   :alt:
.. |check-d| image:: https://github.com/belikh/design/releases/latest/download/icon-check-dark.svg#gh-dark-mode-only
   :width: 20
   :alt:
.. |chart-l| image:: https://github.com/belikh/design/releases/latest/download/icon-chart-light.svg#gh-light-mode-only
   :width: 20
   :alt:
.. |chart-d| image:: https://github.com/belikh/design/releases/latest/download/icon-chart-dark.svg#gh-dark-mode-only
   :width: 20
   :alt:
.. |database-l| image:: https://github.com/belikh/design/releases/latest/download/icon-database-light.svg#gh-light-mode-only
   :width: 20
   :alt:
.. |database-d| image:: https://github.com/belikh/design/releases/latest/download/icon-database-dark.svg#gh-dark-mode-only
   :width: 20
   :alt:
.. |success-l| image:: https://github.com/belikh/design/releases/latest/download/icon-success-light.svg#gh-light-mode-only
   :width: 20
   :alt:
.. |success-d| image:: https://github.com/belikh/design/releases/latest/download/icon-success-dark.svg#gh-dark-mode-only
   :width: 20
   :alt:
.. |trend-l| image:: https://github.com/belikh/design/releases/latest/download/icon-trend-light.svg#gh-light-mode-only
   :width: 20
   :alt:
.. |trend-d| image:: https://github.com/belikh/design/releases/latest/download/icon-trend-dark.svg#gh-dark-mode-only
   :width: 20
   :alt:
.. |pin-l| image:: https://github.com/belikh/design/releases/latest/download/icon-pin-light.svg#gh-light-mode-only
   :width: 20
   :alt:
.. |pin-d| image:: https://github.com/belikh/design/releases/latest/download/icon-pin-dark.svg#gh-dark-mode-only
   :width: 20
   :alt:
.. |folder-l| image:: https://github.com/belikh/design/releases/latest/download/icon-folder-light.svg#gh-light-mode-only
   :width: 20
   :alt:
.. |folder-d| image:: https://github.com/belikh/design/releases/latest/download/icon-folder-dark.svg#gh-dark-mode-only
   :width: 20
   :alt:
.. |home-l| image:: https://github.com/belikh/design/releases/latest/download/icon-home-light.svg#gh-light-mode-only
   :width: 20
   :alt:
.. |home-d| image:: https://github.com/belikh/design/releases/latest/download/icon-home-dark.svg#gh-dark-mode-only
   :width: 20
   :alt:
.. |globe-l| image:: https://github.com/belikh/design/releases/latest/download/icon-globe-light.svg#gh-light-mode-only
   :width: 20
   :alt:
.. |globe-d| image:: https://github.com/belikh/design/releases/latest/download/icon-globe-dark.svg#gh-dark-mode-only
   :width: 20
   :alt:
.. |signal-l| image:: https://github.com/belikh/design/releases/latest/download/icon-signal-light.svg#gh-light-mode-only
   :width: 20
   :alt:
.. |signal-d| image:: https://github.com/belikh/design/releases/latest/download/icon-signal-dark.svg#gh-dark-mode-only
   :width: 20
   :alt:
.. |key-l| image:: https://github.com/belikh/design/releases/latest/download/icon-key-light.svg#gh-light-mode-only
   :width: 20
   :alt:
.. |key-d| image:: https://github.com/belikh/design/releases/latest/download/icon-key-dark.svg#gh-dark-mode-only
   :width: 20
   :alt:
