# pydobiss-nxt

[![CI](https://github.com/Difre-kab/pydobiss-nxt/actions/workflows/ci.yml/badge.svg)](https://github.com/Difre-kab/pydobiss-nxt/actions)
[![PyPI](https://img.shields.io/pypi/v/pydobiss-nxt)](https://pypi.org/project/pydobiss-nxt/)
[![Python](https://img.shields.io/pypi/pyversions/pydobiss-nxt)](https://pypi.org/project/pydobiss-nxt/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Async Python client for the **DOBISS NXT** home automation server
(local REST + WebSocket API). Fully typed (`mypy --strict`), built on
`aiohttp` and Pydantic v2. Powers the
[`ha-dobiss-nxt`](https://github.com/Difre-kab/ha-dobiss-nxt) Home
Assistant integration, but is usable entirely on its own.

## Install

```bash
pip install pydobiss-nxt
```

## Quick start

```python
import asyncio
from aiohttp import ClientSession
from pydobiss_nxt import DobissAuth, DobissClient, DobissWebSocket, StateTracker

async def main():
    auth = DobissAuth("192.168.1.10", "your-api-secret")
    async with ClientSession() as session:
        client = DobissClient(auth, session)

        # Discover the installation
        discovery = await client.discover()
        for s in discovery.unique_subjects():
            print(s.key, s.name, s.type, "dimmable" if s.dimmable else "")

        # Control an output
        await client.turn_on(2, 0, brightness=60)   # dim to 60 %
        await client.toggle(1, 3)

        # Real-time state over WebSocket
        tracker = StateTracker()
        ws = DobissWebSocket(auth, session)
        ws.start(lambda update: print("changed:", tracker.apply(update)))
        await asyncio.sleep(60)
        await ws.stop()

asyncio.run(main())
```

The API secret comes from the NXT web UI: *Global settings → API*.

## What's inside

| Module | Purpose |
|---|---|
| `auth` | Self-signed JWT (HS256) with auto-refresh; pairing-mode `fetch_secret()` |
| `client` | REST: `discover()`, `get_status()`, `action()` + `turn_on/off/toggle` |
| `websocket` | Push listener, auto-reconnect with exponential backoff |
| `models` | Pydantic v2 models, tolerant of firmware quirks, `extra` preserved |
| `status` | Unified parser for the three NXT status formats + `StateTracker` |
| `const` | Module types, icon IDs, actions as `IntEnum` |
| `exceptions` | `DobissError` → `DobissConnectionError` / `DobissAuthError` / `DobissApiError` |

Developed and validated against real NXT hardware, firmware 4.30.
Quality gates: 35 tests (including a fake NXT server), `mypy --strict`,
ruff, CI on Python 3.12 & 3.13.

## License

MIT
