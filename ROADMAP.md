# Project Roadmap — DOBISS NXT × Home Assistant

Two repositories, one goal: a professional-grade DOBISS NXT integration
for Home Assistant, meaningfully better than the existing community
alternative, with a path towards HA core submission.

Legend: ✅ done · 🔨 in progress · ⬜ planned

---

## Phase 1 — `pydobiss-nxt` library ✅ (v0.1.0 on PyPI)

The standalone async Python library. Complete, tested, published.

| Step | What | Status |
|---|---|---|
| 1 | `pyproject.toml` — hatchling, aiohttp, Pydantic v2, `mypy --strict`, src/ layout | ✅ |
| 2 | `const.py` — module types, icon IDs, actions as typed `IntEnum` | ✅ |
| 3 | `exceptions.py` — `DobissError` hierarchy (connection / auth / api) | ✅ |
| 4 | `models.py` — Pydantic models, validated against a real 4.30 payload | ✅ |
| 5 | `auth.py` — self-signed JWT (HS256), auto-refresh, pairing-mode secret fetch | ✅ |
| 6 | `client.py` — REST client (discover/status/action), injected session | ✅ |
| 7 | Real-world validation — discovery of 48 outputs on the real house | ✅ |
| 8 | `websocket.py` — push listener, wamp subprotocol, exponential backoff | ✅ |
| 9 | `status.py` — unified parser for the 3 wire formats + `StateTracker` | ✅ |
| 10 | Test suite — 35 tests incl. a fake NXT server (REST + WS) | ✅ |
| 11 | CI — GitHub Actions: mypy --strict + ruff + pytest, Python 3.12/3.13 | ✅ |
| 12 | Published to PyPI, tagged `v0.1.0` | ✅ |

### Library backlog (v0.2+)

- ⬜ `get_output_state()` helper (single-channel /status returns a bare
  value — quirk found in the field)
- ⬜ Investigate unknown virtual addresses **208** and **251** seen in
  WS captures (ventilation? system status?)
- ⬜ Temperature/thermostat helpers (setpoint encoding: (t−5)×10,
  quarter-hour periods, 0xFE = forever)
- ⬜ Audio zone helpers (sources from discovery `audio_sources`)
- ⬜ Publish v0.2.0 when the integration needs any of the above

---

## Phase 2 — `ha-dobiss-nxt` integration 🔨 (v0.2.0)

### Done

- ✅ Repo scaffold: manifest (`requirements: pydobiss-nxt`), hacs.json
- ✅ Config flow — host + secret, live validation, EN/FR translations
- ✅ Setup lifecycle — `ConfigEntryNotReady` / `ConfigEntryAuthFailed`
- ✅ `DobissCoordinator` — discovery + initial status + WebSocket push
- ✅ **Light platform** — 32 entities live on the real house; dimmers
  (ANALOG) with brightness, relays on/off

### Next entity platforms (in intended order)

- ⬜ `switch` — plug/heating icons (incl. the boiler plug: consider
  safety category so "turn everything off" doesn't kill the heating)
- ⬜ `button` — scenarios (semantic choice: button, not switch)
- ⬜ `switch` or `binary_sensor` — flags (206) and automations (202)
  enable/disable
- ⬜ `cover` — UP/DOWN buddy pairs (same name, icons 3/4)
- ⬜ `sensor` / `binary_sensor` — NXT inputs, light sensors (icons
  100/101)
- ⬜ `media_player` — audio zones (205), sources from discovery
- ⬜ `climate` — thermostat zones (204) + temp calendars as presets

### Quality Scale climb

- ⬜ Reauth flow (secret changed → guided re-entry)
- ⬜ Options flow (per-entity reclassification for ambiguous icons)
- ⬜ Diagnostics (redacted discovery dump — `extra="allow"` pays off)
- ⬜ Zeroconf/discovery of the NXT on the network
- ⬜ NL translations (FR ✅, EN ✅)
- ⬜ Icon/brand assets (home-assistant/brands PR)
- ⬜ Integration test suite (pytest-homeassistant-custom-component)
- ⬜ HACS distribution (repo public + release + default store PR)
- ⬜ Silver → Gold Quality Scale checklist
- ⬜ Core submission exploration

---

## Field notes — quirks discovered on real hardware (fw 4.30)

Documented here so future-us remembers *why* the code is the way it is:

1. Numbers arrive inconsistently: `"8"` (string) for physical outputs,
   `202` (int) for virtual ones → explicit enum coercion validators.
2. `dimmable` is `null` (not `false`) for non-dimmable outputs.
3. `settings` is a dict — or an empty **list** when empty (PHP-ism).
4. Groups overlap: one output can appear in several rooms →
   `unique_subjects()` dedup before entity creation.
5. WS status has 3 shapes: list per channel (relay/dimmer modules),
   `{"ch": {"status": x}}` (NXT module, 251), `{"ch": "0"}` strings
   (virtual 202/206/208).
6. The NXT always pushes the **full** module state — merge, no deltas.
7. Single-channel `GET /status` returns a bare value, not the module
   structure.
8. `GET /status` takes a JSON **body** (non-standard but required).
9. JWT expiry is declared in the JWT **header** (`expiresIn: 24h`),
   not in standard claims.
10. Icons are user intent: a plug icon `HEATING` = boiler control; a
    plug driving Christmas lights is configured as `LIGHT`. Icon
    decides the entity class, module type decides capabilities.

---

## Infrastructure chores (separate track)

- ⬜ Regenerate the DOBISS API secret (was pasted in a chat — rotate)
- ⬜ Revive Proxmox on the EliteDesk 850 (headless: probe SSH :22,
  blind power-cycle, or TV-as-monitor)
- ⬜ Migrate HA from the Pi (SD at 96%!) to a Proxmox VM — fresh
  backup already downloaded ✅
- ⬜ Move `ha-dobiss-nxt` checkout out of the `pydobiss-nxt` folder
  (repos are currently nested on the dev PC)
- ⬜ Clean up legacy homelab DNS remnants (the `192.168.1.51` fossil)
