"""Tests serveur : les 8 tools du MVP sont bien enregistrés et exposés."""

from __future__ import annotations

from infinidex_mcp.server import build_server

EXPECTED_TOOLS = {
    "get_pokemon",
    "search_pokemon",
    "list_pokemon",
    "get_fusion",
    "get_triple_fusion",
    "search_move",
    "get_move",
    "get_move_tutors",
    "get_item",
}


async def test_all_tools_registered(settings):
    mcp = build_server(settings)
    tools = await mcp.list_tools()
    names = {t.name for t in tools}
    assert EXPECTED_TOOLS <= names, f"missing: {EXPECTED_TOOLS - names}"
    # Au moins les 8 tools du MVP.
    assert len(names) >= 8


async def test_tools_have_descriptions(settings):
    mcp = build_server(settings)
    tools = await mcp.list_tools()
    for tool in tools:
        assert tool.description, f"{tool.name} has no description"


async def test_tools_expose_input_schema(settings):
    mcp = build_server(settings)
    tools = await mcp.list_tools()
    by_name = {t.name: t for t in tools}
    schema = by_name["get_pokemon"].inputSchema
    assert "name_or_id" in schema["properties"]
