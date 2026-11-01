# Ignition integration is a gated milestone, not a claimed feature

**Compatibility warning:** A 2025–2026 Cirrus Link community report documents
MQTT Engine/Distributor v5.0.0 failing to load on Ignition Maker Edition 8.3
with `Not eligible for use with Ignition Maker Edition`.

- Ignition 8.3 Maker Edition license is intended for noncommercial personal use.
- Cirrus Link MQTT module versions must match the installed Ignition version;
  check the official compatibility matrix and license state before any install.
- Do not attempt to bypass licensing. Choose an authorized standard Ignition
  trial or confirmed compatible free mode if a vendor-integrated demo is needed.
- The main required topology should eventually be implemented in Perspective
  using the built-in Drawing component and evidence bindings; current HTML
  preview has NO claim of being a Perspective export.

## Human configuration checklist (no live result asserted)

1. Install an authorized Ignition 8.3 Gateway in an isolated lab.
2. Confirm version, licensing, supported MQTT Engine module and dependencies.
3. Configure an authenticated MQTT read-only connection to SignalAtlas broker.
4. Connect the Sparkplug namespace and verify actual born edge tags.
5. Record genuine Gateway system tag paths and available gateway diagnostics.
6. Bind Perspective Drawing/link states to actual read-only REST/Tag evidence.
7. Export the actual Perspective project resources and store safe artifacts here.
8. Produce live screenshots, gateway logs and a failure/recovery recording.

`perspective/` is intentionally empty until authentic exported resources exist.
