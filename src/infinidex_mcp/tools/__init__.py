"""Modules de tools MCP, un fichier par domaine (SOLID).

`register_all` enregistre tous les domaines sur une instance FastMCP.
"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from ..config import Settings
from . import fusion, items, moves, pokemon

_MODULES = (pokemon, fusion, moves, items)


def register_all(mcp: FastMCP, settings: Settings) -> None:
    """Enregistre tous les tools de tous les domaines sur le serveur."""
    for module in _MODULES:
        module.register(mcp, settings)


__all__ = ["register_all"]
