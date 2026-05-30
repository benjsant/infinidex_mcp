"""Helpers communs aux modules de tools.

- `OutBase` : base Pydantic v2 partagée par tous les schémas de sortie.
- `is_id` / `resolve_pokemon_id` : résolution nom (EN/FR) ou id vers un id.

Le client HTTP est désormais *partagé* (créé au démarrage du serveur et injecté
dans chaque `register`) : les tools l'utilisent directement, sans ouvrir de
connexion par appel.
"""

from __future__ import annotations

from mcp.shared.exceptions import McpError
from mcp.types import INVALID_PARAMS, ErrorData
from pydantic import BaseModel, ConfigDict

from ..client import InfiniDexClient


class OutBase(BaseModel):
    """Base des schémas de sortie : ignore les champs amont inconnus.

    InfiniDex peut enrichir ses réponses ; on reste tolérant en entrée tout en
    exposant un contrat stable et typé au client MCP.
    """

    model_config = ConfigDict(extra="ignore")


def is_id(value: str | int) -> bool:
    """True si `value` est un id (entier ou chaîne purement numérique)."""
    return isinstance(value, int) or (isinstance(value, str) and value.isdigit())


def _best_match(matches: list[dict], needle: str) -> dict:
    """Choisit la meilleure correspondance : nom EN/FR exact, sinon le premier."""
    low = needle.lower()
    return next(
        (
            m
            for m in matches
            if (m.get("name_en") or "").lower() == low
            or (m.get("name_fr") or "").lower() == low
        ),
        matches[0],
    )


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
    return int(_best_match(matches, needle)["id"])
