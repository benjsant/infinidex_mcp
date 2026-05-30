"""Helpers communs aux modules de tools.

- `OutBase` : base Pydantic v2 partagée par tous les schémas de sortie.
- `client_for` : context manager qui ouvre un `InfiniDexClient` pour la durée
  d'un appel de tool (pas de cache, pas d'état partagé — cf. CLAUDE.md).
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

from mcp.shared.exceptions import McpError
from mcp.types import INVALID_PARAMS, ErrorData
from pydantic import BaseModel, ConfigDict

from ..client import InfiniDexClient
from ..config import Settings


class OutBase(BaseModel):
    """Base des schémas de sortie : ignore les champs amont inconnus.

    InfiniDex peut enrichir ses réponses ; on reste tolérant en entrée tout en
    exposant un contrat stable et typé au client MCP.
    """

    model_config = ConfigDict(extra="ignore")


@asynccontextmanager
async def client_for(settings: Settings) -> AsyncIterator[InfiniDexClient]:
    """Ouvre un client HTTP InfiniDex le temps d'un appel de tool."""
    async with InfiniDexClient(settings) as client:
        yield client


def is_id(value: str | int) -> bool:
    """True si `value` est un id (entier ou chaîne purement numérique)."""
    return isinstance(value, int) or (isinstance(value, str) and value.isdigit())


async def resolve_pokemon_id(client: InfiniDexClient, name_or_id: str | int) -> int:
    """Résout un nom (EN/FR) ou un id vers un id Pokémon InfiniDex.

    Les ids passent tels quels ; les noms sont résolus via /pokemon/search
    (correspondance exacte EN/FR prioritaire, sinon premier résultat). Lève une
    `McpError(INVALID_PARAMS)` si aucun Pokémon ne correspond.
    """
    if is_id(name_or_id):
        return int(name_or_id)
    needle = str(name_or_id).strip()
    matches = await client.get("/pokemon/search", params={"q": needle})
    if not matches:
        raise McpError(
            ErrorData(code=INVALID_PARAMS, message=f"No Pokémon matching name '{needle}'")
        )
    low = needle.lower()
    best = next(
        (
            m
            for m in matches
            if (m.get("name_en") or "").lower() == low
            or (m.get("name_fr") or "").lower() == low
        ),
        matches[0],
    )
    return int(best["id"])
