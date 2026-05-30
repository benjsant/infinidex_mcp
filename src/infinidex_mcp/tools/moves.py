"""Tools attaques : search_move, get_move_tutors.

Schémas calés sur l'API réelle :
  - GET /moves/search?q=        -> list[MoveListItem]
  - GET /moves/{move_id}/tutors -> list[MoveTutorOut]  (tuteurs classiques)
"""

from __future__ import annotations

from typing import Annotated

from mcp.server.fastmcp import FastMCP
from mcp.shared.exceptions import McpError
from mcp.types import INVALID_PARAMS, ErrorData
from pydantic import Field

from ..config import Settings
from ._base import OutBase, client_for, is_id


class TypeRef(OutBase):
    id: int | None = None
    name_en: str
    name_fr: str | None = None
    is_triple_fusion_type: bool | None = None


class MoveSummary(OutBase):
    """Entrée d'une attaque (mappe `MoveListItem`)."""

    id: int
    name_en: str
    name_fr: str | None = None
    category: str | None = Field(default=None, description="Physical / Special / Status")
    power: int | None = None
    accuracy: int | None = None
    pp: int | None = None
    type: TypeRef | None = None


class MoveList(OutBase):
    """Liste de résultats d'attaques."""

    count: int
    results: list[MoveSummary] = Field(default_factory=list)


class MoveTutorOut(OutBase):
    """Tuteur classique enseignant une attaque (mappe `MoveTutorOut`)."""

    id: int | None = None
    move_id: int | None = None
    move_name_en: str | None = None
    move_name_fr: str | None = None
    location_id: int | None = None
    location_name_en: str | None = None
    location_name_fr: str | None = None
    price: int | None = None
    currency: str | None = None
    npc_description: str | None = None


class MoveTutorsOut(OutBase):
    """Ensemble des tuteurs disponibles pour une attaque donnée."""

    move_id: int = Field(description="Id de l'attaque interrogée")
    count: int
    tutors: list[MoveTutorOut] = Field(default_factory=list)


async def _resolve_move_id(client, name_or_id: str | int) -> int:
    """Résout un nom d'attaque (EN/FR) ou un id vers un id de move."""
    if is_id(name_or_id):
        return int(name_or_id)
    needle = str(name_or_id).strip()
    matches = await client.get("/moves/search", params={"q": needle})
    if not matches:
        raise McpError(
            ErrorData(code=INVALID_PARAMS, message=f"No move matching name '{needle}'")
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


def register(mcp: FastMCP, settings: Settings) -> None:
    """Enregistre les tools d'attaques sur le serveur MCP."""

    @mcp.tool(
        description=(
            "Search moves by name (English or French, accent-insensitive). Returns "
            "lightweight matches with type, category, power, accuracy and PP. Use "
            "to find a move's id or basic data. Query needs at least 1 char."
        )
    )
    async def search_move(
        name: Annotated[str, Field(description="Full or partial move name", min_length=1)],
    ) -> MoveList:
        async with client_for(settings) as client:
            data = await client.get("/moves/search", params={"q": name})
        return MoveList(count=len(data), results=data)

    @mcp.tool(
        description=(
            "List the classic Move Tutors (NPCs) that teach a given move, with "
            "location and price. The move accepts an id OR a name (EN/FR). Does not "
            "cover Move Experts (fusion-only) — those are returned by get_fusion."
        )
    )
    async def get_move_tutors(
        move: Annotated[str | int, Field(description="Move id or name (EN/FR)")],
    ) -> MoveTutorsOut:
        async with client_for(settings) as client:
            move_id = await _resolve_move_id(client, move)
            data = await client.get(f"/moves/{move_id}/tutors")
        return MoveTutorsOut(move_id=move_id, count=len(data), tutors=data)
