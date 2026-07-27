# DOBISS NXT for Home Assistant

A modern, fully typed Home Assistant integration for the **DOBISS NXT**
home automation server — real-time, local, no cloud.

Built on top of [`pydobiss-nxt`](https://pypi.org/project/pydobiss-nxt/),
a standalone async Python library developed alongside this integration.

> **Status: work in progress.** Lights (relays + dimmers) are live.
> See [ROADMAP.md](ROADMAP.md) for what's done and what's next.

## Features

- **Local push** — state changes arrive over the NXT WebSocket in
  real time. Press a wall switch, watch Home Assistant update within a
  second. No polling, no cloud.
- **Config flow UI** — set up from the interface with host + API
  secret; connection is validated live against the NXT.
- **Lights** — every relay output configured with a light icon becomes
  a `light` entity; dimmer (0-10V/DALI) outputs get full brightness
  control.
- **Resilient by design** — automatic WebSocket reconnection with
  exponential backoff; NXT reboots are absorbed silently
  (`ConfigEntryNotReady` → Home Assistant retries).

## Architecture

The project is deliberately split in two repositories, following Home
Assistant best practice:

| Repository | Role |
|---|---|
| [`pydobiss-nxt`](https://github.com/Difre-kab/pydobiss-nxt) | Standalone async Python library: JWT auth, REST client, WebSocket listener, typed models (Pydantic v2), unified state tracking. Published on PyPI, usable without Home Assistant. |
| `ha-dobiss-nxt` (this repo) | The Home Assistant integration: config flow, update coordinator, entity platforms. Declares `pydobiss-nxt` in its manifest; HA installs it from PyPI automatically. |

Data flow at runtime:

```
Wall switch ──► DOBISS NXT ──WebSocket──► DobissWebSocket ──► StateTracker
                                                                  │ changed keys
DOBISS NXT ◄──REST /action── DobissClient ◄── light.turn_on   Coordinator
                                                                  │
                                                          HA entities update
```

## Requirements

- A DOBISS NXT server on your local network, **firmware 4.x**
  (developed and tested against 4.30)
- API enabled on the NXT: *Global settings → API → API enabled*, and
  the JWT secret from that same screen
- Home Assistant 2026.x

## Installation (manual, for now)

1. Copy `custom_components/dobiss_nxt/` into the `custom_components/`
   folder of your Home Assistant config directory.
2. Restart Home Assistant (it will install `pydobiss-nxt` from PyPI).
3. *Settings → Devices & services → Add integration → "DOBISS NXT"*.
4. Enter the NXT host (IP address) and the API secret.

HACS distribution is planned — see the roadmap.

## Entity mapping

The DOBISS *icon* chosen in the configuration software decides what an
output becomes in Home Assistant; the *module type* decides its
capabilities:

| DOBISS icon | Module type | HA entity |
|---|---|---|
| Light, table light | Relay | `light` (on/off) |
| Light, table light | 0-10V / DALI / dimmer | `light` (brightness) |
| Plug, heating, ... | Relay | `switch` *(planned)* |
| Scenario | virtual | `button` *(planned)* |
| Up/Down pair | Relay | `cover` *(planned)* |
| Audio zone | virtual | `media_player` *(planned)* |

## Development

Everyday loop while developing against a real Home Assistant:

```
edit code on the PC
  → copy custom_components/dobiss_nxt to HA config (Samba share add-on)
  → restart Home Assistant
  → check Settings → System → Logs (search "dobiss")
```

The heavy lifting (protocol, parsing, reconnection) lives in the
library, which has its own test suite (35 tests, `mypy --strict`,
ruff, CI on Python 3.12/3.13) — see the
[`pydobiss-nxt`](https://github.com/Difre-kab/pydobiss-nxt) repo.

## License

MIT
