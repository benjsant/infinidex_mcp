"""Modules de tools MCP, un fichier par domaine (SOLID).

`register_all` enregistre tous les domaines sur une instance FastMCP, en leur
injectant le client HTTP partagé.
"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from ..client import InfiniDexClient
from . import fusion, items, locations, moves, pokemon

_MODULES = (pokemon, fusion, moves, items, locations)


def register_all(mcp: FastMCP, client: InfiniDexClient) -> None:
    """Enregistre tous les tools de tous les domaines sur le serveur."""
    for module in _MODULES:
        module.register(mcp, client)


__all__ = ["register_all"]
