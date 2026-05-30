# syntax=docker/dockerfile:1

# ---- base : image uv officielle sur Python 3.12 slim ----
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS base

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH="/opt/venv/bin:$PATH"

WORKDIR /app

# ---- deps : couche cache séparée pour les dépendances ----
FROM base AS deps
# On copie seulement les manifestes pour profiter du cache Docker.
COPY pyproject.toml ./
COPY README.md ./
# Pas de uv.lock encore généré au premier build : --no-install-project
# installe seulement les dépendances déclarées dans pyproject.toml.
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --no-install-project --no-dev

# ---- dev : image complète avec deps de dev (tests) ----
FROM deps AS dev
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --no-install-project
COPY . .
RUN --mount=type=cache,target=/root/.cache/uv uv sync
ENTRYPOINT []
CMD ["pytest"]

# ---- runtime : image finale minimale (serveur MCP) ----
FROM deps AS runtime
COPY src ./src
COPY pyproject.toml README.md ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --no-dev

# stdio par défaut (Claude Desktop / Code). Pour le mode hosted
# (sse / streamable-http), override la commande ; l'hôte 0.0.0.0 rend le port
# joignable via -p (sans effet en stdio).
ENV INFINIDEX_URL=http://host.docker.internal:58000 \
    INFINIDEX_MCP_TRANSPORT=stdio \
    INFINIDEX_MCP_HOST=0.0.0.0

ENTRYPOINT ["infinidex-mcp"]
