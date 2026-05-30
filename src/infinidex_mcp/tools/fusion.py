"""Tools fusion : get_fusion, get_triple_fusion.

Schémas calés sur l'API réelle :
  - GET /fusion/{head_id}/{body_id}/full -> FusionFullOut {fusion, moves, expert_moves}
  - GET /triple-fusions/{id}             -> TripleFusionDetail
"""

from __future__ import annotations

from typing import Annotated

from mcp.server.fastmcp import FastMCP
from pydantic import Field

from ..config import Settings
from ._base import OutBase, client_for, resolve_pokemon_id


class TypeRef(OutBase):
    """Type (mappe `TypeOut`)."""

    id: int | None = None
    name_en: str
    name_fr: str | None = None
    is_triple_fusion_type: bool | None = None


class ExpertMoveOut(OutBase):
    """Attaque enseignable à la fusion par un Move Expert (Knot / Boon Island)."""

    move_id: int
    name_en: str
    name_fr: str | None = None
    category: str | None = None
    power: int | None = None
    type: TypeRef | None = None
    locations: list[str] = Field(default_factory=list)
    prices_heart_scales: dict[str, int] = Field(default_factory=dict)


class FusionOut(OutBase):
    """Résultat d'une fusion head × body (cœur de `FusionResult` + extras)."""

    head_id: int
    body_id: int
    head_name_en: str | None = None
    head_name_fr: str | None = None
    body_name_en: str | None = None
    body_name_fr: str | None = None
    hp: int | None = None
    attack: int | None = None
    defense: int | None = None
    sp_attack: int | None = None
    sp_defense: int | None = None
    speed: int | None = None
    type1: TypeRef | None = None
    type2: TypeRef | None = None
    sprite_path: str | None = Field(default=None, description="Sprite : '{head_id}.{body_id}.png'")
    move_count: int = Field(default=0, description="Nombre total d'attaques du moveset fusionné")
    expert_moves: list[ExpertMoveOut] = Field(default_factory=list)


class TripleComponent(OutBase):
    """Un des trois Pokémon composant une triple fusion."""

    position: int
    pokemon_id: int
    national_id: int | None = None
    name_en: str | None = None
    name_fr: str | None = None


class TripleTypeRef(OutBase):
    slot: int
    name_en: str
    name_fr: str | None = None
    is_triple_fusion_type: bool | None = None


class TripleAbilityRef(OutBase):
    slot: int
    is_hidden: bool
    name_en: str
    name_fr: str | None = None


class TripleFusionOut(OutBase):
    """Détail d'une triple fusion (mappe `TripleFusionDetail`)."""

    id: int
    name_en: str | None = None
    name_fr: str | None = None
    sprite_path: str | None = None
    hp: int | None = None
    attack: int | None = None
    defense: int | None = None
    sp_attack: int | None = None
    sp_defense: int | None = None
    speed: int | None = None
    evolves_from_id: int | None = None
    evolution_level: int | None = None
    steps_to_hatch: int | None = None
    types: list[TripleTypeRef] = Field(default_factory=list)
    components: list[TripleComponent] = Field(default_factory=list)
    abilities: list[TripleAbilityRef] = Field(default_factory=list)


def register(mcp: FastMCP, settings: Settings) -> None:
    """Enregistre les tools de fusion sur le serveur MCP."""

    @mcp.tool(
        description=(
            "Compute the head × body fusion (Infinite Fusion): combined stats, "
            "types, sprite, and the moves teachable by Move Experts with their "
            "Heart Scale prices. head and body accept an IF id OR a name (EN/FR). "
            "Use when the user asks about fusing two Pokémon (e.g. 'Pikachu fused "
            "with Mime Jr')."
        )
    )
    async def get_fusion(
        head: Annotated[str | int, Field(description="Head Pokémon: IF id or name EN/FR")],
        body: Annotated[str | int, Field(description="Body Pokémon: IF id or name EN/FR")],
    ) -> FusionOut:
        async with client_for(settings) as client:
            head_id = await resolve_pokemon_id(client, head)
            body_id = await resolve_pokemon_id(client, body)
            data = await client.get(f"/fusion/{head_id}/{body_id}/full")
        fusion = data.get("fusion", {})
        return FusionOut.model_validate(
            {
                **fusion,
                "move_count": len(data.get("moves", [])),
                "expert_moves": data.get("expert_moves", []),
            }
        )

    @mcp.tool(
        description=(
            "Get a Triple Fusion (legendary three-Pokémon fusion, post-game only) "
            "by its id (1–23). Returns its 3 components, types (incl. IF-exclusive "
            "types), stats, evolution and abilities."
        )
    )
    async def get_triple_fusion(
        triple_fusion_id: Annotated[
            int, Field(description="Id of the triple fusion (1–23)", ge=1)
        ],
    ) -> TripleFusionOut:
        async with client_for(settings) as client:
            data = await client.get(f"/triple-fusions/{triple_fusion_id}")
        return TripleFusionOut.model_validate(data)
