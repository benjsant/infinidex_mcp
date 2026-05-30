"""Tests du client HTTP : 200, 404, 500, timeout, JSON invalide, header clé."""

from __future__ import annotations

import httpx
import pytest
import respx
from mcp.shared.exceptions import McpError
from mcp.types import INTERNAL_ERROR, INVALID_PARAMS
from pydantic import HttpUrl

from infinidex_mcp.client import InfiniDexClient
from infinidex_mcp.config import Settings

from .conftest import BASE_URL


async def test_get_ok(settings, respx_mock):
    respx_mock.get(f"{BASE_URL}/pokemon/1").mock(
        return_value=httpx.Response(200, json={"id": 1, "name_en": "Bulbasaur"})
    )
    async with InfiniDexClient(settings) as client:
        data = await client.get("/pokemon/1")
    assert data == {"id": 1, "name_en": "Bulbasaur"}


async def test_get_404_is_invalid_params(settings, respx_mock):
    respx_mock.get(f"{BASE_URL}/pokemon/99999").mock(return_value=httpx.Response(404))
    async with InfiniDexClient(settings) as client:
        with pytest.raises(McpError) as exc:
            await client.get("/pokemon/99999")
    assert exc.value.error.code == INVALID_PARAMS


async def test_get_500_is_internal_error(settings, respx_mock):
    respx_mock.get(f"{BASE_URL}/pokemon/1").mock(return_value=httpx.Response(500))
    async with InfiniDexClient(settings) as client:
        with pytest.raises(McpError) as exc:
            await client.get("/pokemon/1")
    assert exc.value.error.code == INTERNAL_ERROR


async def test_get_timeout(settings, respx_mock):
    respx_mock.get(f"{BASE_URL}/pokemon/1").mock(side_effect=httpx.TimeoutException("slow"))
    async with InfiniDexClient(settings) as client:
        with pytest.raises(McpError) as exc:
            await client.get("/pokemon/1")
    assert exc.value.error.code == INTERNAL_ERROR
    assert "timed out" in exc.value.error.message


async def test_get_connect_error(settings, respx_mock):
    respx_mock.get(f"{BASE_URL}/pokemon/1").mock(
        side_effect=httpx.ConnectError("refused")
    )
    async with InfiniDexClient(settings) as client:
        with pytest.raises(McpError) as exc:
            await client.get("/pokemon/1")
    assert exc.value.error.code == INTERNAL_ERROR


async def test_get_non_json(settings, respx_mock):
    respx_mock.get(f"{BASE_URL}/pokemon/1").mock(
        return_value=httpx.Response(200, text="<html>nope</html>")
    )
    async with InfiniDexClient(settings) as client:
        with pytest.raises(McpError) as exc:
            await client.get("/pokemon/1")
    assert "non-JSON" in exc.value.error.message


async def test_api_key_header_sent(respx_mock):
    s = Settings(url=HttpUrl(BASE_URL), api_key="topsecret")
    route = respx_mock.get(f"{BASE_URL}/pokemon/1").mock(
        return_value=httpx.Response(200, json={"id": 1})
    )
    async with InfiniDexClient(s) as client:
        await client.get("/pokemon/1")
    assert route.calls.last.request.headers["X-Internal-Key"] == "topsecret"


async def test_ping_ok(settings, respx_mock):
    respx_mock.get(f"{BASE_URL}/").mock(return_value=httpx.Response(200))
    async with InfiniDexClient(settings) as client:
        assert await client.ping() is True


async def test_ping_unreachable(settings, respx_mock):
    respx_mock.get(f"{BASE_URL}/").mock(side_effect=httpx.ConnectError("down"))
    async with InfiniDexClient(settings) as client:
        assert await client.ping() is False
