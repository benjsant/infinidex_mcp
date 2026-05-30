"""Tests de l'entrée CLI (`--check`, override transport)."""

from __future__ import annotations

import httpx

from infinidex_mcp.__main__ import main

from .conftest import BASE_URL


def test_check_ok(monkeypatch, respx_mock):
    monkeypatch.setenv("INFINIDEX_URL", BASE_URL)
    respx_mock.get(f"{BASE_URL}/").mock(return_value=httpx.Response(200))
    assert main(["--check"]) == 0


def test_check_failure(monkeypatch, respx_mock):
    monkeypatch.setenv("INFINIDEX_URL", BASE_URL)
    respx_mock.get(f"{BASE_URL}/").mock(side_effect=httpx.ConnectError("down"))
    assert main(["--check"]) == 1


def test_run_invoked_with_transport_override(monkeypatch):
    captured = {}

    def fake_run(settings):
        captured["transport"] = settings.mcp_transport

    monkeypatch.setattr("infinidex_mcp.__main__.run", fake_run)
    assert main(["--transport", "sse"]) == 0
    assert captured["transport"] == "sse"
