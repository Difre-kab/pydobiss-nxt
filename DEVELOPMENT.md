# Developer Documentation — DOBISS NXT × Home Assistant

> **Purpose of this document.** Everything a developer needs to resume
> or join this project after months away: architecture, the DOBISS
> protocol as we reverse-engineered it, environment setup, workflows,
> release process, deployment topology, and hard-won field knowledge.
> Read [README.md](README.md) first for the 5-minute overview, and
> [ROADMAP.md](ROADMAP.md) for current status. This document is the
> deep dive.

---

## 1. Project in one paragraph

Two repositories deliver a professional-grade Home Assistant
integration for the DOBISS NXT home automation server:
[`pydobiss-nxt`](https://github.com/Difre-kab/pydobiss-nxt) is a
standalone, fully typed async Python library that speaks the NXT's
local REST + WebSocket API (published on PyPI); `ha-dobiss-nxt` (this
repo) is the Home Assistant integration built on top of it. The split
is mandatory for eventual HA core submission and keeps protocol logic
testable in isolation. Everything is developed and validated against
real hardware (NXT firmware 4.30, a Belgian residential installation
with ~48 outputs).

## 2. Repository layout

```
pydobiss-nxt/                     # THE LIBRARY (PyPI: pydobiss-nxt)
├── pyproject.toml                # hatchling, deps, mypy/ruff/pytest config
├── src/pydobiss_nxt/
│   ├── __init__.py               # public API surface (17 symbols) + __version__
│   ├── const.py                  # ModuleType / IconId / Action IntEnums + magic values
│   ├── exceptions.py             # DobissError hierarchy
│   ├── models.py                 # Pydantic v2 models for discovery payload
│   ├── auth.py                   # JWT generation, refresh, pairing-mode fetch
│   ├── client.py                 # REST client (discover/status/action)
│   ├── websocket.py              # push listener with reconnect
│   ├── status.py                 # wire-format parser + StateTracker
│   └── py.typed                  # PEP 561 marker (do not delete)
├── tests/                        # 35 tests; conftest.py hosts a fake NXT server
├── examples/                     # discover.py / listen.py / control.py (real-HW tools)
└── .github/workflows/ci.yml      # mypy --strict + ruff + pytest on 3.12/3.13

ha-dobiss-nxt/                    # THE INTEGRATION
├── custom_components/dobiss_nxt/
│   ├── manifest.json             # domain, version, requirements=["pydobiss-nxt==X"]
│   ├── __init__.py               # setup/unload lifecycle
│   ├── config_flow.py            # UI onboarding (host + secret, live validation)
│   ├── coordinator.py            # DataUpdateCoordinator, push-based
│   ├── light.py                  # light platform (relays + dimmers)
│   ├── const.py                  # DOMAIN, CONF_SECRET
│   ├── strings.json              # + translations/en.json, fr.json
├── hacs.json                     # future HACS metadata
├── README.md / ROADMAP.md / DEVELOPMENT.md (this file)
```

**Golden rule of the split:** protocol knowledge lives in the library,
platform adaptation lives in the integration. If you find yourself
parsing NXT payloads inside `custom_components/`, stop and move it to
the library.

---

## 3. The DOBISS NXT protocol (as reverse-engineered)

Official docs are sparse; most of this was learned from the community
`pydobiss` source and from live captures against firmware 4.30. Treat
this section as the protocol reference.

### 3.1 Transport & URLs

- REST base: `http(s)://<host>/api/local/`
- WebSocket: `ws(s)://<host>/sockets/api`, **subprotocol `"wamp"`**
  (required; it is not actual WAMP framing, just the name)
- All numbers below use `address` = module address, `channel` = output
  index on that module. Stable output key convention everywhere in our
  code: `"{address}_{channel}"` (e.g. `"2_0"`).

### 3.2 Authentication (unusual — read carefully)

There is **no login endpoint**. The NXT holds a shared secret
(*Global settings → API* in its web UI). The **client signs its own
JWT** (HS256) with that secret; the server merely verifies the
signature.

- Payload: `{"name": "<anything>"}`
- Quirk: expiry is declared in the JWT **header** as
  `{"expiresIn": "24h"}` — not in standard `exp` claims. Replicate
  exactly; do not "fix" it.
- Our `DobissAuth.token` regenerates 4 h before the declared 24 h
  expiry (see `TOKEN_VALIDITY` / `TOKEN_REFRESH_MARGIN`).
- Pairing mode: while the blue button in the API section is enabled,
  `GET /api/local/jwtsecret` (unauthenticated) returns
  `{"jwt_secret": "..."}`. This is what a future zeroconf config flow
  can use for one-click onboarding.
- Auth failures: HTTP 401/403 → map to `DobissAuthError`.

### 3.3 Endpoints

| Method & path | Body | Returns |
|---|---|---|
| `GET discover` | – | Full topology (see 3.4) |
| `GET status` | **JSON body** (yes, a GET with a body — required): `{}` for everything, `{"address": N}` for one module, `{"address": N, "channel": M}` for one output | Module-shaped status, **or a bare value** for single-channel queries (quirk #7) |
| `POST action` | `{"address": N, "channel": M, "action": A, ...}` | `{}` |
| `GET jwtsecret` | – | secret (pairing mode only) |

`POST action` optional fields: `option1` (dimmer % 0-100 / audio
volume / temperature), `option2` (soft start 0-254 / audio source /
temp period), `delayon` / `delayoff` as `{"value": V, "unit": "s"|"min"}`
— ≤120 s sent in seconds, above converted to minutes, capped at
120 min (`_encode_delay` in client.py).

Known actions (`const.Action`): `0`=OFF, `1`=ON, `2`=TOGGLE,
`110`=thermostat calendar/preset. `option1=9` on an ON marks a
PIR-triggered switch-on (`BRIGHTNESS_FROM_PIR`). The full action list
is not public; only add values observed in the wild.

### 3.4 Discovery payload

Root keys: `groups`, `icons` (catalog of ~39 icons with metadata),
`temp_calendars`, `audio_sources`, `ventilation_modes`. Each group:
`{"group": {"id", "name"}, "subjects": [...]}`. Each subject:
`name, address, channel, type, icons_id, dimmable, tags,
device_info, settings` (+ unknown extras — we keep them via
Pydantic `extra="allow"` for future diagnostics).

Semantics that drive entity mapping:

- `type` (ModuleType): physical CAN modules — 0=NXT itself, 1=input,
  4=DALI, 8=relay, 16=dimmer, 24=0-10V analog; virtual NXT outputs —
  201=scenario, 202=automation, 203=condition, 204=temperature,
  205=audio, 206=flag. Address > 200 ⇒ virtual (`is_virtual`).
- `icons_id` (IconId) is **user intent** and decides the HA entity
  class: 0=light, 1=plug, 3/4=cover up/down buddy pair, 5=heating,
  6=table light, 100=input status, 101=light sensor, 201-206 mirror
  virtual types. Real-world example: a wall plug feeding the gas
  boiler is configured with the *heating* icon; a plug feeding
  Christmas lights is configured as *light*. **Icon decides entity
  class; module type decides capabilities (dimmable etc.).**

### 3.5 Status wire formats (three shapes!)

WebSocket messages and `GET status` use the same shapes, keyed by
module address (as *string*):

1. Relay/dimmer modules → **list**, index = channel:
   `"1": [0,0,1,...]` (on/off) · `"2": [85,100,0,...]` (dim 0-100)
2. NXT module itself, and address 251 → dict of dicts:
   `"0": {"13": {"status": 1}, ...}`
3. Virtual outputs (202, 206, 208…) → dict of **strings**:
   `"202": {"1": "0"}`

`status.parse_status_update()` flattens all three into
`{"addr_ch": int}`. Additional facts: on WS connect the NXT sends a
**full initial snapshot** (great: no extra REST round-trip needed);
every subsequent message contains the **full state of the affected
module** (merge semantics, never deltas); dimmer ramps stream every
step (1,10,20,…100). Legacy quirk (fw 3.20): module-0 status may
arrive as a bare one-element list — normalized in
`websocket._normalize`.

### 3.6 The 10 field quirks (why the code looks like it does)

1. Numbers arrive as `"8"` (str) for physical, `202` (int) for
   virtual → explicit enum-coercion `field_validator`s (Pydantic
   smart-union would otherwise keep raw ints).
2. `dimmable` is `null` (not `false`) when not dimmable.
3. `settings` is a dict — or an empty **list** when empty (PHP-ism).
4. Groups overlap (same output in several rooms) →
   `unique_subjects()` before creating entities.
5. Three status shapes (see 3.5).
6. Full-module pushes, merge don't diff.
7. Single-channel `GET status` returns a bare value.
8. `GET status` requires a JSON body.
9. JWT expiry in the **header** (`expiresIn`).
10. Icons are user intent (boiler-plug example above).

Unknowns still open: virtual addresses **208** and **251** appear in
WS snapshots but not in discovery — suspected ventilation / system
status. Investigate before mapping.

---

## 4. Library internals & invariants

- **Session is injected, never owned.** `DobissClient(auth, session)`
  and `DobissWebSocket(auth, session)` never create or close the
  `aiohttp.ClientSession`. In HA it is the shared
  `async_get_clientsession(hass)`. Do not break this.
- **Error translation is total.** Callers never see raw aiohttp
  errors: network → `DobissConnectionError` (transient, retryable),
  401/403 → `DobissAuthError` (permanent, needs new secret), other
  HTTP/schema failures → `DobissApiError(status=…)`. The integration
  maps these 1:1 to `ConfigEntryNotReady` / `ConfigEntryAuthFailed`.
- **Tolerance over strictness at the data edge.** Unknown enum values
  fall back to `int`; unknown JSON keys are preserved
  (`extra="allow"`); unknown status shapes are skipped with a debug
  log. A firmware update must degrade gracefully, never crash
  discovery.
- **WS lifecycle**: `start(callback)` spawns a named asyncio task;
  reconnect loop backs off 1 s → 60 s (doubling), resets after a
  successful connection; `stop()` cancels and awaits. Callbacks may
  be sync or async.
- **StateTracker.apply(update) → set of changed keys** — this is the
  contract the HA coordinator relies on to notify only on real
  changes (periodic no-op re-announcements from the NXT are filtered
  here).
- **Public API** is whatever `__init__.py.__all__` exports; keep it
  deliberate. `py.typed` must ship (PEP 561).

## 5. Integration internals

- `manifest.json` — bump `version` on every change you deploy (helps
  cache-busting and support); `requirements` pins the library
  (`pydobiss-nxt==X.Y.Z`): **HA installs it from PyPI**, so any
  library change must be *published* before the integration can use
  it (see workflow 7.2).
- `config_flow.py` — single `user` step (host + secret), validates by
  calling `discover()` live; `unique_id = host` prevents duplicates.
  Translation keys live in `strings.json` (+ `translations/*.json`;
  keep FR in sync, NL planned).
- `coordinator.py` — `DataUpdateCoordinator[dict[str,int]]` with
  `update_interval=None` (pure push). `async_setup()` does:
  discover → `unique_subjects()` → initial `GET status` →
  `tracker.apply` → start WS. WS callback applies updates and calls
  `async_set_updated_data` only when keys changed. `async_stop()`
  stops the WS; called from `async_unload_entry`.
- `light.py` — entity per non-virtual subject with icon in
  `{LIGHT, TABLE_LIGHT}`. Dimmable → `ColorMode.BRIGHTNESS`
  (DOBISS 0-100 ↔ HA 0-255, min clamp 1 %); else ONOFF. `unique_id =
  f"{entry_id}_{subject.key}"`. State reads from
  `coordinator.data[key]`; commands go through `coordinator.client`.
- Adding a platform: create `<platform>.py`, add
  `Platform.X` to `PLATFORMS` in `__init__.py`, filter subjects by
  icon/type per the mapping table in README. Follow `light.py` as the
  template.

## 6. Development environment (from scratch)

Reference setup: Windows + Git Bash. Linux/macOS: same commands,
`Scripts` → `bin`.

```bash
# Library
cd ~/dev && git clone https://github.com/Difre-kab/pydobiss-nxt.git
cd pydobiss-nxt
python -m venv .venv && source .venv/Scripts/activate
pip install -e ".[dev]"
mypy --strict && ruff check src tests && pytest    # all green = ready

# Integration (keep it OUTSIDE the library folder!)
cd ~/dev && git clone https://github.com/Difre-kab/ha-dobiss-nxt.git
```

Per-session ritual (venv and env vars die with the terminal):

```bash
cd ~/dev/pydobiss-nxt && source .venv/Scripts/activate
export DOBISS_HOST="<NXT ip>"        # see §9 for current value
export DOBISS_SECRET="<api secret>"  # NEVER commit, paste, or screenshot
```

Windows gotchas learned the hard way: browsers rename duplicate
downloads to `name (1).py` (always check before `cp`); `Path.write_text`
defaults to cp1252 — always pass `encoding="utf-8"`; enforce LF via
`.gitattributes` (`* text=auto eol=lf`).

## 7. Core workflows

### 7.1 Change the library only

```
edit → mypy --strict → pytest → commit → push (CI re-checks)
```
If the change affects protocol behavior, re-run the example scripts
against real hardware (§8) before releasing.

### 7.2 Change the library AND use it in the integration

The integration consumes the library **from PyPI** — local edits are
invisible to HA until released:

1. Library: implement, test, bump `__version__` in `__init__.py` and
   `version` in `pyproject.toml`.
2. Release to PyPI (see 7.4).
3. Integration: bump `requirements` in `manifest.json` to the new
   version, bump manifest `version`.
4. Deploy (7.3) and verify in HA logs that the new lib version
   installed.

### 7.3 Deploy the integration to a live Home Assistant

```
copy custom_components/dobiss_nxt → <HA config>/custom_components/
    (Samba share add-on: \\<HA-ip>\config\custom_components\)
restart HA (Settings → System → power icon)
check Settings → System → Logs, filter "dobiss"
```
Config-flow / strings changes may additionally need a browser
hard-refresh. Entity-selection changes (which subjects become
entities) require removing/re-adding the integration entry or a HA
restart.

### 7.4 Release the library to PyPI

```bash
cd ~/dev/pydobiss-nxt && source .venv/Scripts/activate
rm -rf dist && python -m build && twine check dist/*
twine upload dist/*        # username: __token__ ; password: pypi-… token
git tag vX.Y.Z && git push origin vX.Y.Z
```
Token is project-scoped, stored in the password manager — never in
the repo, never in a chat. If a secret ever leaks anywhere: use it or
not, then **revoke immediately** and regenerate (this applies to the
DOBISS API secret too — rotating it will require re-auth in HA; until
the reauth flow ships, update via re-adding the entry).

### 7.5 Capture new protocol knowledge

The `examples/` scripts are the lab instruments (all use
`DOBISS_HOST`/`DOBISS_SECRET`):

- `discover.py` — dumps parsed topology + raw `discovery_raw.json`
  (keep out of git; inspect for new fields after firmware updates)
- `listen.py` — live WS feed + `ws_captures.jsonl` (walk around,
  press wall switches, dim; captured lines feed new tests)
- `control.py [addr ch]` — blinks one output and restores its state
  (default 1_3); the end-to-end command smoke test

**Method:** every new quirk found → (a) handle tolerantly in the
library, (b) pin with a test using the captured payload, (c) add to
the field-quirks list (§3.6 and ROADMAP). That loop is the project's
quality engine.

## 8. Quality gates

Library: `mypy --strict` (config in pyproject: `files=["src"]`,
`mypy_path="src"` — run bare `mypy --strict`), `ruff check src tests`,
`pytest` (35 tests; `tests/conftest.py` provides `discovery_payload`
fixture with every known quirk, and `fake_nxt` — a real aiohttp server
faking all endpoints + WS, with spies (`actions`, `status_bodies`) and
sabotage switches (`reject_auth`, `ws_close_after_send`)). CI mirrors
all three on Python 3.12 & 3.13; a red X on main is a stop-the-line
event. Integration tests: planned via
`pytest-homeassistant-custom-component` (see ROADMAP).

## 9. Deployment topology (current reality — verify before relying)

```
Proximus ISP box ── 192.168.129.0/24
│    └─ DOBISS NXT server @ 192.168.129.0  (fw 4.30; yes, a .0 host IP)
└── UniFi Cloud Gateway Ultra (WAN 192.168.129.54)
     └─ homelab LAN 192.168.1.0/24, Wi-Fi SSID "Proximus-Home-450527"
         ├─ HA OS on Raspberry Pi 4 @ 192.168.1.224   ← integration runs here
         │    (⚠ 16 GB SD ~96 % full — migration planned)
         ├─ HP EliteDesk 850 (Proxmox, currently unreachable — see ROADMAP)
         └─ dev PC
```

Consequences: HA reaches the NXT **through the UniFi router** (works,
~4 ms); the NXT is *not* reachable from phone hotspots; HomeKit needs
iPhone/HomePod on the 192.168.1.x Wi-Fi. Fresh full HA backup
procedure: Settings → System → Backups → create → download the .tar
off-device. Planned migration: HA OS VM on Proxmox, restore from
backup.

## 10. Troubleshooting quick table

| Symptom | Likely cause → fix |
|---|---|
| Entities unavailable, log `DobissAuthError` | API secret changed/disabled → re-enter secret (reauth flow planned) |
| Entities unavailable, `ConfigEntryNotReady` loop | NXT unreachable → ping it; check API enabled; HA network |
| "DOBISS NXT" absent from Add-Integration search | folder misplaced (must be `config/custom_components/dobiss_nxt/manifest.json`) or HA not restarted; hard-refresh browser |
| Lib import errors in HA log | `requirements` version not on PyPI yet (workflow 7.2 order!) |
| WS updates stop after NXT reboot | should self-heal ≤60 s (backoff); if not, check logs for the reconnect warnings |
| mypy "missing py.typed" | run bare `mypy --strict` from repo root (editable-install import-hook issue); ensure `py.typed` exists |
| Dimmer feels "stuck bright" below 50 % slider | perceptual linearity issue — gamma curve pending (ROADMAP); verify with `light.turn_on` + `brightness_pct: 5` |
| HomeKit "No response" while HA works | reload the HomeKit Bridge entry; check HomePod/iPhone on same LAN as HA |

## 11. Conventions

- Commits: conventional prefixes (`feat:`, `fix:`, `test:`, `docs:`,
  `chore:`, `ci:`) — the history reads as a narrative; keep it so.
- Versioning: semver-ish; library and integration versions move
  independently; manifest pins the library exactly (`==`).
- Style: enforced by ruff + mypy strict — no debates, the tools win.
- Language: code, comments, docs in English; UI strings translated
  (EN/FR live, NL planned).
- Never in git: secrets, `discovery_raw.json`, `ws_captures.jsonl`,
  `.venv`, backups.

## 12. Where to go next

Open [ROADMAP.md](ROADMAP.md): pick the next ⬜ item. Current top of
the queue: `switch` platform (mind the boiler-plug safety note),
scenario `button`s, dimmer gamma curve, reauth flow. The pattern for
any new platform: filter subjects → follow `light.py` → deploy → test
against the real house → pin discoveries with tests.
