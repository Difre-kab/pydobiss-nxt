"""Listen to real-time updates from the NXT.

Usage (same env vars as discover.py):

    export DOBISS_HOST="192.168.x.x"
    export DOBISS_SECRET="<secret>"
    python examples/listen.py

Then walk around the house and flip some wall switches: every state
change pushed by the NXT is printed and appended (raw) to
``ws_captures.jsonl`` for later analysis. Stop with Ctrl+C.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from aiohttp import ClientSession

from pydobiss_nxt.auth import DobissAuth
from pydobiss_nxt.websocket import DobissWebSocket

CAPTURE_FILE = Path(__file__).parent / "ws_captures.jsonl"


def on_update(update: dict[str, Any]) -> None:
    stamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{stamp}] {json.dumps(update, ensure_ascii=False)}")
    with CAPTURE_FILE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(update, ensure_ascii=False) + "\n")


async def main() -> int:
    host = os.environ.get("DOBISS_HOST")
    secret = os.environ.get("DOBISS_SECRET")
    if not host or not secret:
        print("Définis d'abord DOBISS_HOST et DOBISS_SECRET.")
        return 1

    auth = DobissAuth(host, secret)
    async with ClientSession() as session:
        ws = DobissWebSocket(auth, session)
        ws.start(on_update)
        print(f"🔌 Connecté à {auth.ws_url}")
        print("Va appuyer sur des interrupteurs ! (Ctrl+C pour arrêter)\n")
        try:
            while True:
                await asyncio.sleep(3600)
        except (KeyboardInterrupt, asyncio.CancelledError):
            pass
        finally:
            await ws.stop()
            print(f"\nCaptures sauvées dans {CAPTURE_FILE}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(asyncio.run(main()))
    except KeyboardInterrupt:
        sys.exit(0)
