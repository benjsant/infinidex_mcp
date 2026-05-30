"""Tools Pokémon : get_pokemon, search_pokemon, list_pokemon.

Schémas calés sur l'API réelle InfiniDex :
  - GET /pokemon/{id}          -> PokemonDetail (stats à plat, types/abilities objets)
  - GET /pokemon/search?q=     -> list[PokemonListItem]  (q : min 2 caractères)
  - GET /pokemon/?limit&offset&filtres -> list[PokemonListItem]
  - GET /pokemon/count?filtres -> int
"""

from __future__ import annotations

from typing import Annotated, Literal

from mcp.server.fastmcp import FastMCP
from pydantic import Field

from ..client import InfiniDexClient
from ._base import OutBase, is_id, resolve_pokemon_id

SortBy = Literal["id", "id_desc", "name_asc", "name_desc", "bst_asc", "bst_desc"]


class TypeRef(OutBase):
    """Type d'un Pokémon (slot 1 ou 2)."""

    slot: int
    name_en: str
    name_fr: str | None = None


class AbilityRef(OutBase):
    """Talent d'un Pokémon."""

    slot: int
    is_hidden: bool
    name_en: str
    name_fr: str | None = None


class PokemonOut(OutBase):
    """Fiche détaillée d'un Pokémon InfiniDex (mappe `PokemonDetail`)."""

    id: int = Field(description="InfiniDex (Infinite Fusion) id — distinct du national_id")
    national_id: int | None = Field(default=None, description="Numéro du Pokédex national")
    name_en: str
    name_fr: str | None = None
    generation_id: int | None = None
    hp: int | None = None
    attack: int | None = None
    defense: int | None = None
    sp_attack: int | None = None
    sp_defense: int | None = None
    speed: int | None = None
    bst: int | None = Field(default=None, description="Base stat total")
    base_experience: int | None = None
    is_hoenn_only: bool | None = None
    sprite_path: str | None = None
    pokepedia_url: str | None = None
    types: list[TypeRef] = Field(default_factory=list)
    abilities: list[AbilityRef] = Field(default_factory=list)


class PokemonListItem(OutBase):
    """Entrée légère d'une liste/recherche (mappe `PokemonListItem`)."""

    id: int
    national_id: int | None = None
    name_en: str
    name_fr: str | None = None
    types: list[TypeRef] = Field(default_factory=list)
    sprite_path: str | None = None
    is_hoenn_only: bool | None = None
    bst: int | None = None


class PokemonList(OutBase):
    """Page de résultats Pokémon."""

    count: int = Field(description="Nombre d'éléments sur cette page")
    total: int | None = Field(default=None, description="Total correspondant aux filtres (toutes pages)")
    results: list[PokemonListItem] = Field(default_factory=list)


def register(mcp: FastMCP, client: InfiniDexClient) -> None:
    """Enregistre les tools Pokémon sur le serveur MCP."""

    @mcp.tool(
        description=(
            "Look up the full Pokédex entry for a single Infinite Fusion Pokémon "
            "by Infinite Fusion id (not national dex id) OR by name (English or "
            "French). Returns base stats, types, abilities (incl. hidden), BST and "
            "sprite. Always call this first for any question about a specific Pokémon."
        )
    )
    async def get_pokemon(
        name_or_id: Annotated[
            str | int,
            Field(description="IF id (e.g. 25) or name EN/FR (e.g. 'Pikachu')"),
        ],
    ) -> PokemonOut:
        pokemon_id = name_or_id if is_id(name_or_id) else await resolve_pokemon_id(
            client, name_or_id
        )
        data = await client.get(f"/pokemon/{int(pokemon_id)}")
        return PokemonOut.model_validate(data)

    @mcp.tool(
        description=(
            "Search Pokémon by full or partial name (English or French, "
            "accent-insensitive). Returns lightweight matches (id, names, types, "
            "BST). Use to disambiguate before get_pokemon. Query needs >= 2 chars."
        )
    )
    async def search_pokemon(
        name: Annotated[
            str, Field(description="Name or partial name (min 2 chars)", min_length=2)
        ],
    ) -> PokemonList:
        data = await client.get("/pokemon/search", params={"q": name})
        return PokemonList(count=len(data), total=len(data), results=data)

    @mcp.tool(
        description=(
            "List Pokémon with pagination and optional filters. `total` gives the "
            "full count matching the filters (all pages). Filter by type, "
            "generation (1=Kanto, 3=Hoenn) and BST range; sort by id/name/bst. "
            "Use to browse the dex or answer 'how many … ' questions."
        )
    )
    async def list_pokemon(
        limit: Annotated[int, Field(description="Max items per page", ge=1, le=1000)] = 20,
        offset: Annotated[int, Field(description="Items to skip (pagination)", ge=0)] = 0,
        type_id: Annotated[int | None, Field(description="Filter by type id", ge=1)] = None,
        generation_id: Annotated[
            int | None, Field(description="Filter by generation (1=Kanto, 3=Hoenn)", ge=1)
        ] = None,
        min_bst: Annotated[int | None, Field(description="Minimum BST", ge=0)] = None,
        max_bst: Annotated[int | None, Field(description="Maximum BST", ge=0)] = None,
        sort_by: Annotated[SortBy, Field(description="Sort order")] = "id",
    ) -> PokemonList:
        filters = {
            k: v
            for k, v in (
                ("type_id", type_id),
                ("generation_id", generation_id),
                ("min_bst", min_bst),
                ("max_bst", max_bst),
            )
            if v is not None
        }
        data = await client.get(
            "/pokemon/", params={"limit": limit, "offset": offset, "sort_by": sort_by, **filters}
        )
        total = await client.get("/pokemon/count", params=filters)
        return PokemonList(count=len(data), total=total, results=data)
