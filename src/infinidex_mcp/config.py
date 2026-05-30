"""Configuration du serveur, lue depuis les variables d'environnement.

Toutes les options sont préfixées `INFINIDEX_` (cf. CLAUDE.md). Aucune valeur
n'est requise : le serveur fonctionne out-of-the-box contre un InfiniDex local.
"""

from __future__ import annotations

from typing import Literal

from pydantic import Field, HttpUrl
from pydantic_settings import BaseSettings, SettingsConfigDict

# stdio : clients locaux (Claude Desktop/Code). streamable-http : mode hosted
# moderne (recommandé). sse : ancien transport hosted, conservé pour compat.
Transport = Literal["stdio", "sse", "streamable-http"]


class Settings(BaseSettings):
    """Paramètres runtime du serveur MCP InfiniDex."""

    model_config = SettingsConfigDict(
        env_prefix="INFINIDEX_",
        env_file=".env",
        extra="ignore",
    )

    # URL de base de l'API InfiniDex (sans slash final).
    url: HttpUrl = Field(default=HttpUrl("http://localhost:58000"))

    # Clé interne optionnelle — envoyée en header X-Internal-Key si présente.
    api_key: str | None = Field(default=None)

    # Transport MCP. Note : le préfixe `INFINIDEX_` s'applique, donc la var
    # d'env est INFINIDEX_MCP_TRANSPORT.
    mcp_transport: Transport = Field(default="stdio")

    # Hôte et port d'écoute (transports hosted : sse / streamable-http).
    # En conteneur, mettre l'hôte à 0.0.0.0 pour être joignable via -p.
    mcp_host: str = Field(default="127.0.0.1")
    mcp_port: int = Field(default=3000, ge=1, le=65535)

    # Timeout (secondes) des requêtes HTTP vers InfiniDex.
    http_timeout: float = Field(default=10.0, gt=0)

    # Nombre de tentatives supplémentaires sur erreur transitoire (timeout/5xx).
    http_retries: int = Field(default=2, ge=0, le=5)

    # Délai de base du backoff exponentiel entre tentatives (secondes).
    http_backoff: float = Field(default=0.2, ge=0)

    @property
    def base_url(self) -> str:
        """URL de base normalisée, sans slash final."""
        return str(self.url).rstrip("/")


def load_settings() -> Settings:
    """Charge les settings depuis l'environnement (point d'entrée unique)."""
    return Settings()
