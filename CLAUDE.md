# CLAUDE.md

## Contexte

Tu travailles sur le projet InfiniDex MCP (nom de travail).

InfiniDex MCP est un serveur Model Context Protocol (MCP) en Python qui
expose les outils structurés du projet InfiniDex
(https://github.com/benjsant/InfiniDex) à n'importe quel client compatible
MCP — Claude Desktop, Claude Code, Cursor, Windsurf, etc.

Pourquoi ce projet existe : InfiniDex expose ses données via HTTP REST,
consommé par son frontend Next.js et son agent LLM interne. MCP est le
protocole émergent qui permet à un assistant comme Claude Code d'utiliser
des outils tiers de façon standard. Ce serveur fait le pont entre les deux.

Cas d'usage : un utilisateur de Claude Code tape "donne-moi les stats de
Mime Jr fusionné avec Pikachu" — Claude appelle automatiquement
get_fusion via ce serveur MCP, sans que l'utilisateur ouvre le site
InfiniDex.

Le code doit être minimal, sans dépendance sur le runtime InfiniDex
(juste son API HTTP), et distribuable en `pip install infinidex-mcp`.

---

# Stack technique

- Python 3.12+
- `mcp` (SDK officiel Anthropic — https://github.com/modelcontextprotocol/python-sdk)
- `httpx` pour le client HTTP async vers InfiniDex
- `pydantic` v2 pour la validation des schémas tools
- `uv` pour la gestion des dépendances et le packaging
- Aucune dépendance sur InfiniDex côté code — seulement son URL HTTP

---

# Architecture

Structure :

infinidex-mcp/

  pyproject.toml
  README.md
  LICENSE                          # MIT

  src/
    infinidex_mcp/
      __init__.py
      __main__.py                  # entrée python -m infinidex_mcp
      server.py                    # création du serveur MCP + binding tools
      config.py                    # lecture env vars (INFINIDEX_URL, API_KEY)
      client.py                    # client httpx vers l'API InfiniDex

      tools/
        __init__.py
        _base.py                   # helpers communs aux tools
        pokemon.py                 # get_pokemon, search_pokemon, list_pokemon
        fusion.py                  # get_fusion, get_triple_fusion
        moves.py                   # search_move, get_move_tutors
        items.py                   # get_item
        locations.py               # search_pokemon_locations

  tests/
    test_client.py
    test_tools_pokemon.py
    ...
    conftest.py                    # mock InfiniDex HTTP via respx

  examples/
    claude_desktop_config.json     # exemple de config Claude Desktop
    claude_code_config.json        # exemple Claude Code
    cursor_config.json             # exemple Cursor

---

# Règles de développement

- Respecter les principes SOLID : un fichier `tools/X.py` par domaine.
- Chaque tool MCP a son propre schéma Pydantic (validation entrée/sortie).
- Toute la logique HTTP passe par `client.py` — pas de `httpx` dans `tools/`.
- Erreurs HTTP InfiniDex (4xx, 5xx) traduites en `McpError` propre, jamais loggées en `Exception` brute.
- Pas de cache local — c'est le rôle du serveur InfiniDex.
- Stdio mode par défaut (Claude Desktop / Code) — SSE mode pour plus tard.
- Tests sans dépendance sur InfiniDex live (mock httpx via `respx`).
- Le serveur ne doit JAMAIS appeler search_web — c'est InfiniDex qui décide d'aller sur le web côté agent. MCP expose uniquement les données structurées.

---

# Interface CLI

Commande unique :

  infinidex-mcp                    # démarre le serveur stdio
  infinidex-mcp --transport sse    # démarre le serveur SSE (port configurable)
  infinidex-mcp --check            # vérifie la connexion à InfiniDex et exit

Variables d'environnement :

  INFINIDEX_URL=http://localhost:58000      # défaut
  INFINIDEX_API_KEY=<optionnel>             # si InfiniDex a INTERNAL_API_KEY
  INFINIDEX_MCP_TRANSPORT=stdio             # stdio | sse
  INFINIDEX_MCP_PORT=3000                   # uniquement si transport=sse

---

# Fonctionnalités MVP

## Tools exposés (8 minimum)

| Tool | Wrapper sur InfiniDex |
|---|---|
| `get_pokemon` | GET /pokemon/{id} ou /pokemon/by-name/{name} |
| `search_pokemon` | GET /pokemon/?name=... |
| `list_pokemon` | GET /pokemon/?limit=...&offset=... |
| `get_fusion` | GET /fusion/{head_id}/{body_id}/full |
| `get_triple_fusion` | GET /triple-fusions/{id} |
| `search_move` | GET /moves/?name=... |
| `get_item` | GET /items/{id} |
| `get_move_tutors` | GET /tutors/by-move/{move_id} |

## Schémas Pydantic

Chaque tool a un schéma input strict :

  class GetPokemonInput(BaseModel):
      pokemon_id: int = Field(..., description="IF id of the Pokémon (not national_id)")

Et l'output est typé :

  class PokemonOut(BaseModel):
      id: int
      name_en: str
      name_fr: str | None
      types: list[str]
      stats: dict[str, int]
      ...

## Documentation des tools

Chaque tool a une `description` accessible aux LLM clients via la spec MCP.
Cette description guide le LLM sur quand et comment l'utiliser.

Exemple :

  description = (
      "Lookup full data for a single Pokémon by its Infinite Fusion id "
      "(not national dex id). Returns stats, types, abilities, location. "
      "Use when the user asks about a specific Pokémon by name or id."
  )

---

# Fonctionnalités futures

Prévoir l'architecture pour :

## Transport SSE

Mode serveur hosted pour usage à distance (cas : équipe qui veut un serveur
MCP partagé). Activé par `--transport sse`, exposable via reverse proxy.

## Cache local optionnel

Cache LRU bornée des réponses InfiniDex (clé = URL+params). Activé par
`--cache-size N`. Utile si latence réseau vers InfiniDex est élevée.

## Authentification

Si InfiniDex tourne en prod avec `INTERNAL_API_KEY`, le serveur MCP passe
la clé en header `X-Internal-Key` pour chaque requête.

## Métriques

Compteurs par tool (nombre d'appels, latence p50/p95, erreurs). Exposés via
`infinidex-mcp --metrics` ou endpoint Prometheus si transport=sse.

## Publication PyPI + Homebrew

  pip install infinidex-mcp
  uvx infinidex-mcp
  brew install benjsant/tap/infinidex-mcp

---

# Tests

Créer des tests pour :

- chaque tool (schéma validation + appel HTTP mocké)
- le client (gestion 200, 404, 500, timeout)
- la config (env vars valides / invalides)
- le serveur MCP (handshake protocole via mcp[cli] test harness)

Objectifs :

- couverture > 75%
- tests purs unitaires sans serveur InfiniDex live (mock via respx)
- 1 test d'intégration optionnel qui pinge un InfiniDex local si dispo

---

# Distribution

PyPI :

  uv build
  uv publish

Install end-user :

  pip install infinidex-mcp
  # ou directement sans install
  uvx infinidex-mcp

Config Claude Desktop :

  {
    "mcpServers": {
      "infinidex": {
        "command": "uvx",
        "args": ["infinidex-mcp"],
        "env": {
          "INFINIDEX_URL": "http://localhost:58000"
        }
      }
    }
  }

---

# Priorité

Toujours privilégier :

1. simplicité
2. lisibilité
3. compatibilité maximale avec le standard MCP (suivre la spec à la lettre)

avant toute fonctionnalité custom.

---

# Pitch portfolio (rappel)

Ce projet n'est pas un projet jouet — il démontre une compréhension du
standard tool-calling émergent en 2026 :

  "InfiniDex expose un agent LLM via HTTP pour son frontend. Mais qu'est-ce
   qui se passe si tu veux que Claude Code, Cursor ou un autre IDE puisse
   l'interroger directement ? J'ai construit le serveur MCP qui sert
   exactement ça — n'importe quel client MCP peut désormais interroger
   InfiniDex sans toucher au site."

Bonus pour entretien : tu peux démontrer en live pendant la conversation
en tapant une question dans Claude Code et en montrant les tool calls qui
arrivent au serveur MCP en temps réel.

Cible recruteur : AI Engineer / LLM Engineer junior-mid qui suit
l'écosystème MCP (Anthropic, OpenAI, Cursor, Microsoft tous adoptent).

