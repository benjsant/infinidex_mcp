"""Tests des tools attaques et objets.

Endpoints réels : GET /moves/search?q=, GET /moves/{id}/tutors, GET /items/{id}.
"""

from __future__ import annotations

import httpx

from infinidex_mcp.server import build_server

from .conftest import BASE_URL
from .test_tools_pokemon import call_tool

MOVE_ITEM = {
    "id": 85,
    "name_en": "Thunderbolt",
    "name_fr": "Tonnerre",
    "category": "Special",
    "power": 90,
    "accuracy": 100,
    "pp": 15,
    "type": {"id": 13, "name_en": "Electric", "name_fr": "Électrik"},
}


async def test_search_move(settings, respx_mock):
    route = respx_mock.get(f"{BASE_URL}/moves/search").mock(
        return_value=httpx.Response(200, json=[MOVE_ITEM])
    )
    mcp = build_server(settings)
    out = await call_tool(mcp, "search_move", {"name": "thunder"})
    assert out["count"] == 1
    assert out["results"][0]["power"] == 90
    assert out["results"][0]["type"]["name_en"] == "Electric"
    assert route.calls.last.request.url.params["q"] == "thunder"


async def test_get_move_tutors_by_id(settings, respx_mock):
    respx_mock.get(f"{BASE_URL}/moves/85/tutors").mock(
        return_value=httpx.Response(
            200,
            json=[
                {
                    "id": 1,
                    "move_id": 85,
                    "move_name_en": "Thunderbolt",
                    "location_id": 3,
                    "location_name_en": "Saffron City",
                    "price": 0,
                    "currency": "free",
                    "npc_description": "Move Tutor",
                }
            ],
        )
    )
    mcp = build_server(settings)
    out = await call_tool(mcp, "get_move_tutors", {"move": 85})
    assert out["move_id"] == 85
    assert out["count"] == 1
    assert out["tutors"][0]["location_name_en"] == "Saffron City"


async def test_get_move_tutors_by_name(settings, respx_mock):
    respx_mock.get(f"{BASE_URL}/moves/search").mock(
        return_value=httpx.Response(200, json=[MOVE_ITEM])
    )
    respx_mock.get(f"{BASE_URL}/moves/85/tutors").mock(
        return_value=httpx.Response(200, json=[])
    )
    mcp = build_server(settings)
    out = await call_tool(mcp, "get_move_tutors", {"move": "Thunderbolt"})
    assert out["move_id"] == 85
    assert out["count"] == 0


async def test_get_item(settings, respx_mock):
    respx_mock.get(f"{BASE_URL}/items/3").mock(
        return_value=httpx.Response(
            200,
            json={
                "id": 3,
                "name_en": "Fire Stone",
                "name_fr": "Pierre Feu",
                "category": "evolution",
                "effect": "Evolves certain Pokémon.",
                "price_buy": 3000,
                "price_sell": 1500,
                "locations": [
                    {"id": 1, "location_name": "Celadon Dept.", "method": "shop", "notes": None}
                ],
            },
        )
    )
    mcp = build_server(settings)
    out = await call_tool(mcp, "get_item", {"item_id": 3})
    assert out["name_en"] == "Fire Stone"
    assert out["price_buy"] == 3000 and out["price_sell"] == 1500
    assert out["locations"][0]["method"] == "shop"
