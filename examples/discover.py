"""First real-world test: discover the whole DOBISS installation.

Usage (Git Bash):

    export DOBISS_HOST="192.168.x.x"          # IP or dobiss.local
    export DOBISS_SECRET="<secret from Global settings -> API>"
    python examples/discover.py

The secret comes from environment variables so it never ends up in the
code or in Git. The raw JSON payload is saved to ``discovery_raw.json``
(next to this script) so we can inspect the real fields and refine the
models afterwards.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path

from aiohttp import ClientSession

from pydobiss_nxt.auth import DobissAuth
from pydobiss_nxt.client import DobissClient
from pydobiss_nxt.exceptions import DobissAuthError, DobissConnectionError


async def main() -> int:
    host = os.environ.get("DOBISS_HOST")
    secret = os.environ.get("DOBISS_SECRET")
    if not host or not secret:
        print("Définis d'abord DOBISS_HOST et DOBISS_SECRET (voir docstring).")
        return 1

    auth = DobissAuth(host, secret)
    async with ClientSession() as session:
        client = DobissClient(auth, session)

        # --- raw payload, kept verbatim for model refinement ---------
        raw = await client._request("GET", "discover")  # noqa: SLF001
        out = Path(__file__).parent / "discovery_raw.json"
        out.write_text(json.dumps(raw, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"Payload brut sauvé dans {out}\n")

        # --- parsed view ---------------------------------------------
        discovery = await client.discover()
        subjects = discovery.all_subjects()
        print(f"{len(discovery.groups)} groupes, {len(subjects)} sorties\n")

        for group in discovery.groups:
            print(f"── {group.group.name or f'Groupe {group.group.id}'}")
            for s in group.subjects:
                kind = getattr(s.type, "name", s.type)
                icon = getattr(s.icons_id, "name", s.icons_id)
                dim = " [dimmable]" if s.dimmable else ""
                virt = " [virtuel]" if s.is_virtual else ""
                print(f"   {s.key:>7}  {s.name:<30} type={kind} icône={icon}{dim}{virt}")

        if discovery.temp_calendars:
            print("\nCalendriers thermostat:")
            for cal in discovery.temp_calendars:
                print(f"   {cal.id}: {cal.name}")

    return 0


if __name__ == "__main__":
    try:
        sys.exit(asyncio.run(main()))
    except DobissAuthError as err:
        print(f"❌ Authentification refusée: {err}")
        print("→ Vérifie le secret (Global settings → API) et que l'API est activée.")
        sys.exit(2)
    except DobissConnectionError as err:
        print(f"❌ NXT injoignable: {err}")
        print("→ Vérifie l'adresse IP et que tu es sur le même réseau.")
        sys.exit(3)
