"""Fixtures partagées : settings de test pointant sur un InfiniDex fictif.

Aucun test ne touche un InfiniDex live — tout le HTTP est mocké via `respx`
(fixture `respx_mock` fournie par le plugin pytest de respx).
"""

from __future__ import annotations

import pytest
from pydantic import HttpUrl

from infinidex_mcp.config import Settings

BASE_URL = "http://infinidex.test"


@pytest.fixture
def settings() -> Settings:
    """Settings de test : InfiniDex fictif, pas de clé, timeout court."""
    return Settings(
        url=HttpUrl(BASE_URL),
        api_key=None,
        mcp_transport="stdio",
        http_timeout=2.0,
    )
