"""Point d'entrée CLI : `infinidex-mcp` et `python -m infinidex_mcp`.

  infinidex-mcp                 # serveur stdio (défaut)
  infinidex-mcp --transport sse # serveur SSE
  infinidex-mcp --check         # teste la connexion à InfiniDex puis exit
"""

from __future__ import annotations

import argparse
import asyncio
import sys

from .client import InfiniDexClient
from .config import load_settings
from .server import run


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="infinidex-mcp",
        description="MCP server exposing InfiniDex (Pokémon Infinite Fusion) data.",
    )
    parser.add_argument(
        "--transport",
        choices=("stdio", "sse"),
        default=None,
        help="Transport MCP (override INFINIDEX_MCP_TRANSPORT ; défaut stdio).",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Vérifie la connexion à InfiniDex et quitte (exit 0 si OK).",
    )
    return parser


async def _check(settings) -> int:
    async with InfiniDexClient(settings) as client:
        ok = await client.ping()
    target = settings.base_url
    if ok:
        print(f"OK: InfiniDex reachable at {target}", file=sys.stderr)
        return 0
    print(f"ERROR: InfiniDex unreachable at {target}", file=sys.stderr)
    return 1


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    settings = load_settings()

    if args.transport:
        settings.mcp_transport = args.transport

    if args.check:
        return asyncio.run(_check(settings))

    run(settings)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
