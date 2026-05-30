"""Tests de la configuration (lecture env vars valides / invalides)."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from infinidex_mcp.config import Settings, load_settings


def test_defaults():
    s = Settings()
    assert s.base_url == "http://localhost:58000"
    assert s.mcp_transport == "stdio"
    assert s.mcp_port == 3000
    assert s.api_key is None


def test_env_override(monkeypatch):
    monkeypatch.setenv("INFINIDEX_URL", "http://example.org:9000/")
    monkeypatch.setenv("INFINIDEX_API_KEY", "secret")
    monkeypatch.setenv("INFINIDEX_MCP_TRANSPORT", "sse")
    monkeypatch.setenv("INFINIDEX_MCP_PORT", "4242")
    s = load_settings()
    # base_url enlève le slash final.
    assert s.base_url == "http://example.org:9000"
    assert s.api_key == "secret"
    assert s.mcp_transport == "sse"
    assert s.mcp_port == 4242


def test_invalid_transport(monkeypatch):
    monkeypatch.setenv("INFINIDEX_MCP_TRANSPORT", "carrier-pigeon")
    with pytest.raises(ValidationError):
        load_settings()


def test_invalid_port(monkeypatch):
    monkeypatch.setenv("INFINIDEX_MCP_PORT", "70000")
    with pytest.raises(ValidationError):
        load_settings()
