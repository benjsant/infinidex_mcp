"""Création du serveur MCP InfiniDex et binding des tools.

On s'appuie sur `FastMCP` (API haut niveau du SDK officiel) qui gère le
handshake protocole, la génération des JSON Schemas depuis les annotations
Pydantic, et les transports stdio / SSE.
"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from .config import Settings, load_settings
from .tools import register_all


def build_server(settings: Settings | None = None) -> FastMCP:
    """Construit le serveur MCP avec tous les tools enregistrés.

    `settings` est injectable pour les tests ; sinon lu depuis l'environnement.
    """
    settings = settings or load_settings()
    mcp = FastMCP(
        name="infinidex",
        instructions=(
            "Structured access to InfiniDex (Pokémon Infinite Fusion) data: "
            "Pokémon, fusions, moves and items. Prefer these tools over guessing; "
            "ids are InfiniDex ids, not national dex ids."
        ),
        port=settings.mcp_port,
    )
    register_all(mcp, settings)
    return mcp


def run(settings: Settings | None = None) -> None:
    """Démarre le serveur sur le transport configuré (stdio par défaut)."""
    settings = settings or load_settings()
    mcp = build_server(settings)
    mcp.run(transport=settings.mcp_transport)
