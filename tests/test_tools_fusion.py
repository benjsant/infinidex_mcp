"""Tests des tools de fusion.

Endpoints réels : GET /fusion/{h}/{b}/full, GET /triple-fusions/{id}.
"""

from __future__ import annotations

import httpx

from infinidex_mcp.server import build_server

from .conftest import BASE_URL
from .test_tools_pokemon import call_tool

# Forme FusionFullOut = {fusion: FusionResult, moves: [...], expert_moves: [...]}.
FUSION_FULL = {
    "fusion": {
        "head_id": 439,
        "body_id": 25,
        "head_name_en": "Mime Jr.",
        "head_name_fr": "Mime Jr.",
        "body_name_en": "Pikachu",
        "body_name_fr": "Pikachu",
        "hp": 40,
        "attack": 45,
        "defense": 45,
        "sp_attack": 70,
        "sp_defense": 80,
        "speed": 80,
        "type1": {"id": 14, "name_en": "Psychic", "name_fr": "Psy", "is_triple_fusion_type": False},
        "type2": {"id": 13, "name_en": "Electric", "name_fr": "Électrik", "is_triple_fusion_type": False},
        "sprite_path": "439.25.png",
    },
    "moves": [{"move_id": 1}, {"move_id": 2}, {"move_id": 3}],
    "expert_moves": [
        {
            "move_id": 85,
            "name_en": "Thunderbolt",
            "category": "Special",
            "power": 90,
            "type": {"id": 13, "name_en": "Electric"},
            "locations": ["knot_island"],
            "prices_heart_scales": {"knot_island": 2},
        }
    ],
}


async def test_get_fusion_by_id(settings, respx_mock):
    respx_mock.get(f"{BASE_URL}/fusion/439/25/full").mock(
        return_value=httpx.Response(200, json=FUSION_FULL)
    )
    mcp = build_server(settings)
    out = await call_tool(mcp, "get_fusion", {"head": 439, "body": 25})
    assert out["head_id"] == 439 and out["body_id"] == 25
    assert out["type1"]["name_en"] == "Psychic"
    assert out["type2"]["name_en"] == "Electric"
    assert out["move_count"] == 3
    assert out["expert_moves"][0]["name_en"] == "Thunderbolt"


async def test_get_fusion_resolves_names(settings, respx_mock):
    # 'Mime Jr.' et 'Pikachu' résolus via /pokemon/search avant l'appel fusion.
    respx_mock.get(f"{BASE_URL}/pokemon/search", params={"q": "Mime Jr."}).mock(
        return_value=httpx.Response(200, json=[{"id": 439, "name_en": "Mime Jr."}])
    )
    respx_mock.get(f"{BASE_URL}/pokemon/search", params={"q": "Pikachu"}).mock(
        return_value=httpx.Response(200, json=[{"id": 25, "name_en": "Pikachu"}])
    )
    respx_mock.get(f"{BASE_URL}/fusion/439/25/full").mock(
        return_value=httpx.Response(200, json=FUSION_FULL)
    )
    mcp = build_server(settings)
    out = await call_tool(mcp, "get_fusion", {"head": "Mime Jr.", "body": "Pikachu"})
    assert out["sprite_path"] == "439.25.png"


async def test_get_triple_fusion(settings, respx_mock):
    respx_mock.get(f"{BASE_URL}/triple-fusions/1").mock(
        return_value=httpx.Response(
            200,
            json={
                "id": 1,
                "name_en": "Zapmolcuno",
                "name_fr": "Zapmolcuno",
                "hp": 90,
                "attack": 90,
                "types": [
                    {"slot": 1, "name_en": "Electric", "is_triple_fusion_type": False},
                ],
                "components": [
                    {"position": 1, "pokemon_id": 144, "national_id": 144, "name_en": "Articuno"},
                    {"position": 2, "pokemon_id": 145, "national_id": 145, "name_en": "Zapdos"},
                    {"position": 3, "pokemon_id": 146, "national_id": 146, "name_en": "Moltres"},
                ],
                "abilities": [{"slot": 1, "is_hidden": False, "name_en": "Pressure"}],
            },
        )
    )
    mcp = build_server(settings)
    out = await call_tool(mcp, "get_triple_fusion", {"triple_fusion_id": 1})
    assert out["name_en"] == "Zapmolcuno"
    assert [c["pokemon_id"] for c in out["components"]] == [144, 145, 146]
