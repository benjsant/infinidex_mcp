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


async def test_check_ok(settings, respx_mock):
    respx_mock.get(f"{BASE_URL}/pokemon/count").mock(return_value=httpx.Response(200, json=572))
    async with InfiniDexClient(settings) as client:
        assert await client.check() == "ok"


async def test_check_unauthorized(settings, respx_mock):
    # 403 = joignable mais clé manquante/invalide (et non « injoignable »).
    respx_mock.get(f"{BASE_URL}/pokemon/count").mock(return_value=httpx.Response(403))
    async with InfiniDexClient(settings) as client:
        assert await client.check() == "unauthorized"


async def test_check_unreachable(settings, respx_mock):
    respx_mock.get(f"{BASE_URL}/pokemon/count").mock(side_effect=httpx.ConnectError("down"))
    async with InfiniDexClient(settings) as client:
        assert await client.check() == "unreachable"


async def test_get_retries_then_succeeds(respx_mock):
    # 1er essai timeout, 2e essai 500, 3e essai OK -> doit réussir.
    s = Settings(url=HttpUrl(BASE_URL), http_retries=2, http_backoff=0.0)
    respx_mock.get(f"{BASE_URL}/pokemon/1").mock(
        side_effect=[
            httpx.TimeoutException("slow"),
            httpx.Response(500),
            httpx.Response(200, json={"id": 1}),
        ]
    )
    async with InfiniDexClient(s) as client:
        assert await client.get("/pokemon/1") == {"id": 1}


async def test_get_retries_exhausted(respx_mock):
    s = Settings(url=HttpUrl(BASE_URL), http_retries=1, http_backoff=0.0)
    respx_mock.get(f"{BASE_URL}/pokemon/1").mock(return_value=httpx.Response(503))
    async with InfiniDexClient(s) as client:
        with pytest.raises(McpError) as exc:
            await client.get("/pokemon/1")
    assert exc.value.error.code == INTERNAL_ERROR
