"""Client HTTP async vers l'API InfiniDex.

Toute la communication réseau passe par ici — aucun `httpx` dans `tools/`
(cf. règles CLAUDE.md). Les erreurs HTTP (4xx/5xx), timeouts et erreurs de
connexion sont traduites en `McpError` propres, jamais propagées en exception
brute vers le client MCP.

Le client est conçu pour être *partagé* sur la durée de vie du serveur : il
maintient un pool de connexions chaud (pas de handshake TLS par appel). Les
erreurs transitoires (timeout, erreur réseau, 5xx) sont retentées avec un
backoff exponentiel borné.
"""

from __future__ import annotations

import asyncio
from types import TracebackType
from typing import Any, Literal

import httpx
from mcp.shared.exceptions import McpError
from mcp.types import INTERNAL_ERROR, INVALID_PARAMS, ErrorData

from .config import Settings

# Résultat de `check()` : OK / joignable mais clé refusée / injoignable.
CheckStatus = Literal["ok", "unauthorized", "unreachable"]


def _mcp_error(code: int, message: str) -> McpError:
    """Construit une McpError avec le code et message donnés."""
    return McpError(ErrorData(code=code, message=message))


class InfiniDexClient:
    """Wrapper fin et typé autour de `httpx.AsyncClient` pour InfiniDex.

    S'utilise comme client partagé (créé une fois au démarrage du serveur) ou
    comme context manager async pour un usage ponctuel (tests, `--check`) :

        async with InfiniDexClient(settings) as client:
            data = await client.get("/pokemon/1")
    """

    def __init__(self, settings: Settings, *, client: httpx.AsyncClient | None = None):
        self._settings = settings
        self._retries = settings.http_retries
        self._backoff = settings.http_backoff
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

        Retente sur erreur transitoire (timeout, réseau, 5xx) jusqu'à
        `http_retries` fois avec backoff exponentiel. Traduit l'échec final en
        `McpError` :
          - 404            -> INVALID_PARAMS ("ressource introuvable")
          - autres 4xx/5xx -> INTERNAL_ERROR (avec le code amont)
          - timeout/réseau -> INTERNAL_ERROR
        """
        last_error_message = ""
        for attempt in range(self._retries + 1):
            try:
                response = await self._client.get(path, params=params)
            except httpx.TimeoutException:
                last_error_message = f"InfiniDex timed out after {self._settings.http_timeout}s"
            except httpx.HTTPError as exc:
                last_error_message = (
                    f"Could not reach InfiniDex at {self._settings.base_url}: {exc}"
                )
            else:
                # 5xx = transitoire (le backend redémarre, etc.) -> on retente.
                if response.status_code >= 500:
                    last_error_message = (
                        f"InfiniDex returned HTTP {response.status_code} for {path}"
                    )
                else:
                    return self._decode(response, path)

            if attempt < self._retries:
                await asyncio.sleep(self._backoff * (2**attempt))

        raise _mcp_error(INTERNAL_ERROR, last_error_message)

    @staticmethod
    def _decode(response: httpx.Response, path: str) -> Any:
        """Traduit une réponse non-5xx en JSON ou en `McpError`."""
        if response.status_code == 404:
            raise _mcp_error(INVALID_PARAMS, f"Not found in InfiniDex: {path}")
        if response.is_error:
            raise _mcp_error(
                INTERNAL_ERROR, f"InfiniDex returned HTTP {response.status_code} for {path}"
            )
        try:
            return response.json()
        except ValueError as exc:
            raise _mcp_error(
                INTERNAL_ERROR, f"InfiniDex returned a non-JSON response for {path}"
            ) from exc

    async def check(self) -> CheckStatus:
        """Vérifie la connexion *et l'authentification* (utilisé par `--check`).

        Tape un endpoint authentifié (`/pokemon/count`) plutôt que `/health` ou
        `/`, afin de distinguer un 403 (clé manquante/invalide) d'une vraie
        indisponibilité — sinon un mauvais `INFINIDEX_API_KEY` passerait inaperçu.
        """
        try:
            response = await self._client.get("/pokemon/count")
        except httpx.HTTPError:
            return "unreachable"
        if response.status_code in (401, 403):
            return "unauthorized"
        if response.status_code >= 500:
            return "unreachable"
        return "ok"
