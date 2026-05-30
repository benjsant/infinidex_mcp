"""Tests du tool lieux (GET /pokemon/{id}/locations)."""

from __future__ import annotations

from infinidex_mcp.server import build_server

from .conftest import BASE_URL
from .test_tools_pokemon import PIKACHU_LIST_ITEM, call_tool

import httpx

LOCATIONS = [
    {"location_id": 5, "location_name": "Viridian Forest", "method": "wild", "notes": "rate:10% | lv:3-5"},
    {"location_id": 9, "location_name": "Power Plant", "method": "static", "notes": "lv:25"},
]


async def test_get_pokemon_locations_by_id(settings, respx_mock):
    respx_mock.get(f"{BASE_URL}/pokemon/25/locations").mock(
        return_value=httpx.Response(200, json=LOCATIONS)
    )
    mcp = build_server(settings)
    out = await call_tool(mcp, "get_pokemon_locations", {"name_or_id": 25})
    assert out["pokemon_id"] == 25
    assert out["count"] == 2
    assert out["locations"][0]["location_name"] == "Viridian Forest"
    assert out["locations"][0]["method"] == "wild"


async def test_get_pokemon_locations_by_name(settings, respx_mock):
    respx_mock.get(f"{BASE_URL}/pokemon/search").mock(
        return_value=httpx.Response(200, json=[PIKACHU_LIST_ITEM])
    )
    respx_mock.get(f"{BASE_URL}/pokemon/25/locations").mock(
        return_value=httpx.Response(200, json=LOCATIONS)
    )
    mcp = build_server(settings)
    out = await call_tool(mcp, "get_pokemon_locations", {"name_or_id": "Pikachu"})
    assert out["pokemon_id"] == 25 and out["count"] == 2
