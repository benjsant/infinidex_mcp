"""Tests des tools Pokémon, de bout en bout via FastMCP (schéma + HTTP mocké).

Endpoints réels : GET /pokemon/{id}, GET /pokemon/search?q=, GET /pokemon/?limit&offset.
"""

from __future__ import annotations

import json

import httpx
import pytest

from infinidex_mcp.server import build_server

from .conftest import BASE_URL

# Réponse type de GET /pokemon/{id} (forme PokemonDetail : stats à plat).
PIKACHU_DETAIL = {
    "id": 25,
    "national_id": 25,
    "name_en": "Pikachu",
    "name_fr": "Pikachu",
    "generation_id": 1,
    "hp": 35,
    "attack": 55,
    "defense": 40,
    "sp_attack": 50,
    "sp_defense": 50,
    "speed": 90,
    "bst": 320,
    "base_experience": 112,
    "is_hoenn_only": False,
    "sprite_path": "25.png",
    "pokepedia_url": None,
    "types": [{"slot": 1, "name_en": "Electric", "name_fr": "Électrik"}],
    "abilities": [{"slot": 1, "is_hidden": False, "name_en": "Static", "name_fr": "Statik"}],
}

# Réponse type de GET /pokemon/search (forme PokemonListItem).
PIKACHU_LIST_ITEM = {
    "id": 25,
    "national_id": 25,
    "name_en": "Pikachu",
    "name_fr": "Pikachu",
    "types": [{"slot": 1, "name_en": "Electric", "name_fr": "Électrik"}],
    "sprite_path": "25.png",
    "is_hoenn_only": False,
    "bst": 320,
}


async def call_tool(mcp, name: str, arguments: dict):
    """Appelle un tool et retourne son résultat structuré (dict).

    Tolère les deux signatures de `FastMCP.call_tool` selon la version du SDK.
    """
    result = await mcp.call_tool(name, arguments)
    content, structured = result if isinstance(result, tuple) else (result, None)
    if structured is not None:
        return structured
    return json.loads(content[0].text)


async def test_get_pokemon_by_id(settings, respx_mock):
    respx_mock.get(f"{BASE_URL}/pokemon/25").mock(
        return_value=httpx.Response(200, json=PIKACHU_DETAIL)
    )
    mcp = build_server(settings)
    out = await call_tool(mcp, "get_pokemon", {"name_or_id": 25})
    assert out["name_en"] == "Pikachu"
    assert out["hp"] == 35 and out["speed"] == 90
    assert out["types"][0]["name_en"] == "Electric"
    assert out["abilities"][0]["is_hidden"] is False


async def test_get_pokemon_by_name_resolves_via_search(settings, respx_mock):
    # Nom → /search → fetch détaillé sur l'id résolu.
    respx_mock.get(f"{BASE_URL}/pokemon/search").mock(
        return_value=httpx.Response(200, json=[PIKACHU_LIST_ITEM])
    )
    respx_mock.get(f"{BASE_URL}/pokemon/25").mock(
        return_value=httpx.Response(200, json=PIKACHU_DETAIL)
    )
    mcp = build_server(settings)
    out = await call_tool(mcp, "get_pokemon", {"name_or_id": "Pikachu"})
    assert out["id"] == 25
    assert out["bst"] == 320


async def test_get_pokemon_unknown_name_raises(settings, respx_mock):
    respx_mock.get(f"{BASE_URL}/pokemon/search").mock(return_value=httpx.Response(200, json=[]))
    mcp = build_server(settings)
    with pytest.raises(Exception):
        await call_tool(mcp, "get_pokemon", {"name_or_id": "Nopemon"})


async def test_search_pokemon(settings, respx_mock):
    route = respx_mock.get(f"{BASE_URL}/pokemon/search").mock(
        return_value=httpx.Response(200, json=[PIKACHU_LIST_ITEM])
    )
    mcp = build_server(settings)
    out = await call_tool(mcp, "search_pokemon", {"name": "pika"})
    assert out["count"] == 1
    assert out["results"][0]["id"] == 25
    # Le paramètre est bien passé en ?q=
    assert route.calls.last.request.url.params["q"] == "pika"


async def test_list_pokemon_with_total(settings, respx_mock):
    respx_mock.get(f"{BASE_URL}/pokemon/").mock(
        return_value=httpx.Response(200, json=[PIKACHU_LIST_ITEM])
    )
    respx_mock.get(f"{BASE_URL}/pokemon/count").mock(return_value=httpx.Response(200, json=572))
    mcp = build_server(settings)
    out = await call_tool(mcp, "list_pokemon", {"limit": 10, "offset": 0})
    assert out["count"] == 1
    assert out["total"] == 572


async def test_list_pokemon_passes_filters(settings, respx_mock):
    list_route = respx_mock.get(f"{BASE_URL}/pokemon/").mock(
        return_value=httpx.Response(200, json=[PIKACHU_LIST_ITEM])
    )
    count_route = respx_mock.get(f"{BASE_URL}/pokemon/count").mock(
        return_value=httpx.Response(200, json=51)
    )
    mcp = build_server(settings)
    out = await call_tool(
        mcp, "list_pokemon", {"type_id": 4, "min_bst": 400, "sort_by": "bst_desc"}
    )
    assert out["total"] == 51
    lp = list_route.calls.last.request.url.params
    assert lp["type_id"] == "4" and lp["min_bst"] == "400" and lp["sort_by"] == "bst_desc"
    # count ne reçoit que les filtres (pas limit/offset/sort_by).
    cp = count_route.calls.last.request.url.params
    assert cp["type_id"] == "4" and "sort_by" not in cp and "limit" not in cp


async def test_get_pokemon_404_raises(settings, respx_mock):
    respx_mock.get(f"{BASE_URL}/pokemon/99999").mock(return_value=httpx.Response(404))
    mcp = build_server(settings)
    with pytest.raises(Exception):
        await call_tool(mcp, "get_pokemon", {"name_or_id": 99999})
