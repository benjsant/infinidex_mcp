"""InfiniDex MCP — serveur Model Context Protocol pour les données InfiniDex."""

from __future__ import annotations

__version__ = "0.1.0"

from .server import build_server, run

__all__ = ["build_server", "run", "__version__"]
