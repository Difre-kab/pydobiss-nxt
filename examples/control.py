"""First real control test: blink one light from Python.

Usage (same env vars as the other examples):

    export DOBISS_HOST="192.168.129.0"
    export DOBISS_SECRET="<secret>"
    python examples/control.py            # blinks Lampe ATELIER (1_3)
    python examples/control.py 2 0        # or any address/channel you pass

The script reads the current state first, blinks the output twice
(on 1 s / off 1 s), then restores the initial state. Nothing is left
in a different state than it was found.
"""

from __future__ import annotations

import asyncio
import os
import sys

from aiohttp import ClientSession

from pydobiss_nxt.auth import DobissAuth
from pydobiss_nxt.client import DobissClient
from pydobiss_nxt.status import parse_status_update

DEFAULT_ADDRESS = 1  # Lampe ATELIER
DEFAULT_CHANNEL = 3


async def main() -> int:
    host = os.environ.get("DOBISS_HOST")
    secret = os.environ.get("DOBISS_SECRET")
    if not host or not secret:
        print("Définis d'abord DOBISS_HOST et DOBISS_SECRET.")
        return 1

    address = int(sys.argv[1]) if len(sys.argv) > 2 else DEFAULT_ADDRESS
    channel = int(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_CHANNEL
    key = f"{address}_{channel}"

    auth = DobissAuth(host, secret)
    async with ClientSession() as session:
        client = DobissClient(auth, session)

        # remember the initial state to restore it afterwards
        # NB: /status for a single channel returns a bare value, while a
        # module-wide query returns the usual per-module structure.
        raw = await client.get_status(address=address, channel=channel)
        status = raw.get("status", raw) if isinstance(raw, dict) else raw
        if isinstance(status, dict):
            initial = parse_status_update(status).get(key, 0)
        elif isinstance(status, list):
            initial = int(status[channel]) if channel < len(status) else 0
        else:
            initial = int(status or 0)
        print(f"État initial de {key}: {initial}")

        print("✨ Clignotement...")
        for _ in range(2):
            await client.turn_on(address, channel)
            await asyncio.sleep(1)
            await client.turn_off(address, channel)
            await asyncio.sleep(1)

        if initial:
            await client.turn_on(address, channel)
        print(f"État restauré ({initial}). La maison obéit à ton code. 🏠")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
