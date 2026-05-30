"""Tools attaques : search_move, get_move, get_move_tutors.

Schémas calés sur l'API réelle :
  - GET /moves/search?q=        -> list[MoveListItem]
  - GET /moves/{move_id}        -> MoveDetail (descriptions + infos TM)
  - GET /moves/{move_id}/tutors -> list[MoveTutorOut]  (tuteurs classiques)
"""

from __future__ import annotations

from typing import Annotated

from mcp.server.fastmcp import FastMCP
from mcp.shared.exceptions import McpError
from mcp.types import INVALID_PARAMS, ErrorData
from pydantic import Field

from ..client import InfiniDexClient
from ._base import OutBase, _best_match, is_id


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


class TMLocationOut(OutBase):
    location_id: int | None = None
    location_name_en: str | None = None
    location_name_fr: str | None = None
    notes: str | None = None


class TMInfoOut(OutBase):
    """Infos CT/TM si l'attaque en est une."""

    number: int = Field(description="Numéro de la TM (1 = TM01)")
    location_summary: str | None = None
    locations: list[TMLocationOut] = Field(default_factory=list)


class MoveDetailOut(MoveSummary):
    """Détail complet d'une attaque (mappe `MoveDetail`)."""

    description_en: str | None = None
    description_fr: str | None = None
    source: str | None = Field(default=None, description="base | infinite_fusion")
    tm: TMInfoOut | None = Field(default=None, description="Infos TM, null si l'attaque n'est pas une TM")


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


async def _resolve_move_id(client: InfiniDexClient, name_or_id: str | int) -> int:
    """Résout un nom d'attaque (EN/FR) ou un id vers un id de move."""
    if is_id(name_or_id):
        return int(name_or_id)
    needle = str(name_or_id).strip()
    matches = await client.get("/moves/search", params={"q": needle})
    if not matches:
        raise McpError(
            ErrorData(code=INVALID_PARAMS, message=f"No move matching name '{needle}'")
        )
    return int(_best_match(matches, needle)["id"])


def register(mcp: FastMCP, client: InfiniDexClient) -> None:
    """Enregistre les tools d'attaques sur le serveur MCP."""

    @mcp.tool(
        description=(
            "Search moves by name (English or French, accent-insensitive). Returns "
            "lightweight matches with type, category, power, accuracy and PP (no "
            "description). Use to find a move's id, then get_move for full detail."
        )
    )
    async def search_move(
        name: Annotated[str, Field(description="Full or partial move name", min_length=1)],
    ) -> MoveList:
        data = await client.get("/moves/search", params={"q": name})
        return MoveList(count=len(data), results=data)

    @mcp.tool(
        description=(
            "Get the full detail of a move by id OR name (EN/FR): type, category, "
            "power, accuracy, PP, in-game description (EN/FR), and TM info (number "
            "and where to find it) if the move is a TM. Use when the user asks what "
            "a move does."
        )
    )
    async def get_move(
        move: Annotated[str | int, Field(description="Move id or name (EN/FR)")],
    ) -> MoveDetailOut:
        move_id = await _resolve_move_id(client, move)
        data = await client.get(f"/moves/{move_id}")
        return MoveDetailOut.model_validate(data)

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
        move_id = await _resolve_move_id(client, move)
        data = await client.get(f"/moves/{move_id}/tutors")
        return MoveTutorsOut(move_id=move_id, count=len(data), tutors=data)
