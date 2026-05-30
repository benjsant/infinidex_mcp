"""Tool lieux : get_pokemon_locations.

Schéma calé sur l'API réelle :
  - GET /pokemon/{id}/locations -> list[LocationOut]

Note : InfiniDex n'expose pas d'endpoint HTTP de *recherche globale* de lieux
(par condition/méthode) — ça n'existe qu'en interne côté agent DB. On fournit
donc la variante faisable : les lieux d'un Pokémon donné (nom ou id).
"""

from __future__ import annotations

from typing import Annotated

from mcp.server.fastmcp import FastMCP
from pydantic import Field

from ..client import InfiniDexClient
from ._base import OutBase, is_id, resolve_pokemon_id


class LocationOut(OutBase):
    """Un lieu de rencontre pour un Pokémon (mappe `LocationOut`)."""

    location_id: int | None = None
    location_name: str | None = None
    method: str | None = Field(
        default=None, description="wild | static | gift | trade | fishing | headbutt | …"
    )
    notes: str | None = Field(default=None, description="Niveau, taux de rencontre, conditions…")


class PokemonLocationsOut(OutBase):
    """Ensemble des lieux où trouver un Pokémon."""

    pokemon_id: int = Field(description="Id InfiniDex du Pokémon interrogé")
    count: int
    locations: list[LocationOut] = Field(default_factory=list)


def register(mcp: FastMCP, client: InfiniDexClient) -> None:
    """Enregistre le tool lieux sur le serveur MCP."""

    @mcp.tool(
        description=(
            "List the in-game encounter locations of a Pokémon (where to find it): "
            "method (wild, static, gift, trade, fishing…) and notes (level, rate, "
            "conditions). The Pokémon accepts an IF id OR a name (EN/FR). Use when "
            "the user asks where to catch or obtain a specific Pokémon."
        )
    )
    async def get_pokemon_locations(
        name_or_id: Annotated[
            str | int, Field(description="IF id or name EN/FR of the Pokémon")
        ],
    ) -> PokemonLocationsOut:
        pokemon_id = name_or_id if is_id(name_or_id) else await resolve_pokemon_id(
            client, name_or_id
        )
        pokemon_id = int(pokemon_id)
        data = await client.get(f"/pokemon/{pokemon_id}/locations")
        return PokemonLocationsOut(pokemon_id=pokemon_id, count=len(data), locations=data)
