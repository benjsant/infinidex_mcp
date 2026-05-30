"""Client HTTP async vers l'API InfiniDex.

Toute la communication réseau passe par ici — aucun `httpx` dans `tools/`
(cf. règles CLAUDE.md). Les erreurs HTTP (4xx/5xx), timeouts et erreurs de
connexion sont traduites en `McpError` propres, jamais propagées en exception
brute vers le client MCP.
"""

from __future__ import annotations

from types import TracebackType
from typing import Any

import httpx
from mcp.shared.exceptions import McpError
from mcp.types import INTERNAL_ERROR, INVALID_PARAMS, ErrorData

from .config import Settings


def _mcp_error(code: int, message: str) -> McpError:
    """Construit une McpError avec le code et message donnés."""
    return McpError(ErrorData(code=code, message=message))


class InfiniDexClient:
    """Wrapper fin et typé autour de `httpx.AsyncClient` pour InfiniDex.

    S'utilise comme context manager async :

        async with InfiniDexClient(settings) as client:
            data = await client.get("/pokemon/1")
    """

    def __init__(self, settings: Settings, *, client: httpx.AsyncClient | None = None):
        self._settings = settings
        headers: dict[str, str] = {"Accept": "application/json"}
        if settings.api_key:
            headers["X-Internal-Key"] = settings.api_key
        # `client` injectable pour les tests (respx monte sur une vraie instance).
        self._client = client or httpx.AsyncClient(
            base_url=settings.base_url,
            headers=headers,
            timeout=settings.http_timeout,
        )

    async def __aenter__(self) -> InfiniDexClient:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        await self._client.aclose()

    async def get(self, path: str, *, params: dict[str, Any] | None = None) -> Any:
        """GET `path` et retourne le JSON décodé.

        Traduit toute erreur en `McpError` :
          - 404            -> INVALID_PARAMS ("ressource introuvable")
          - autres 4xx/5xx -> INTERNAL_ERROR (avec le code amont)
          - timeout/réseau -> INTERNAL_ERROR
        """
        try:
            response = await self._client.get(path, params=params)
        except httpx.TimeoutException as exc:
            raise _mcp_error(
                INTERNAL_ERROR, f"InfiniDex timed out after {self._settings.http_timeout}s"
            ) from exc
        except httpx.HTTPError as exc:
            raise _mcp_error(
                INTERNAL_ERROR, f"Could not reach InfiniDex at {self._settings.base_url}: {exc}"
            ) from exc

        if response.status_code == 404:
            raise _mcp_error(INVALID_PARAMS, f"Not found in InfiniDex: {path}")
        if response.is_error:
            raise _mcp_error(
                INTERNAL_ERROR,
                f"InfiniDex returned HTTP {response.status_code} for {path}",
            )

        try:
            return response.json()
        except ValueError as exc:
            raise _mcp_error(
                INTERNAL_ERROR, f"InfiniDex returned a non-JSON response for {path}"
            ) from exc

    async def ping(self) -> bool:
        """Vérifie la joignabilité d'InfiniDex (utilisé par `--check`)."""
        try:
            response = await self._client.get("/")
        except httpx.HTTPError:
            return False
        return response.status_code < 500
