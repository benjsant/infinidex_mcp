"""Tool objets : get_item.

Schéma calé sur l'API réelle :
  - GET /items/{id} -> ItemOut {effect, price_buy, price_sell, locations[]}
"""

from __future__ import annotations

from typing import Annotated

from mcp.server.fastmcp import FastMCP
from pydantic import Field

from ..client import InfiniDexClient
from ._base import OutBase


class ItemLocationOut(OutBase):
    """Lieu d'obtention d'un objet."""

    id: int | None = None
    location_name: str | None = None
    method: str | None = Field(default=None, description="'shop' | 'found' | 'wild' | 'other'")
    notes: str | None = None


class ItemOut(OutBase):
    """Objet du jeu (mappe `ItemOut`)."""

    id: int
    name_en: str
    name_fr: str | None = None
    category: str | None = Field(default=None, description="'fusion' | 'evolution' | 'valuable'")
    effect: str | None = Field(default=None, description="Effet en jeu")
    price_buy: int | None = Field(default=None, description="Prix d'achat (Pokédollars), null si non vendu")
    price_sell: int | None = Field(default=None, description="Prix de revente, null si non vendable")
    locations: list[ItemLocationOut] = Field(default_factory=list)


def register(mcp: FastMCP, client: InfiniDexClient) -> None:
    """Enregistre le tool objets sur le serveur MCP."""

    @mcp.tool(
        description=(
            "Look up a single item by its InfiniDex id. Returns names, category, "
            "in-game effect, buy/sell prices and obtention locations. Scope: fusion "
            "/ evolution / valuable items."
        )
    )
    async def get_item(
        item_id: Annotated[int, Field(description="InfiniDex id of the item", ge=1)],
    ) -> ItemOut:
        data = await client.get(f"/items/{item_id}")
        return ItemOut.model_validate(data)
