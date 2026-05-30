# InfiniDex MCP

Serveur [Model Context Protocol](https://modelcontextprotocol.io) qui expose les
données structurées d'[InfiniDex](https://github.com/benjsant/InfiniDex)
(Pokémon Infinite Fusion) à n'importe quel client MCP — Claude Desktop, Claude
Code, Cursor, Windsurf…

> *« InfiniDex expose un agent LLM via HTTP pour son frontend. Mais si tu veux
> que Claude Code ou Cursor l'interroge directement ? J'ai construit le serveur
> MCP qui sert exactement ça : n'importe quel client MCP peut désormais
> interroger InfiniDex sans toucher au site. »*

Le serveur fait le **pont** entre un client MCP et l'API HTTP REST d'InfiniDex.
Il n'a **aucune dépendance** sur le runtime InfiniDex — seulement son URL.

```
Client MCP (Claude Code / Desktop, Cursor…)
   │  protocole MCP (stdio ou HTTP)
   ▼
infinidex-mcp  ──►  API HTTP InfiniDex (FastAPI)  ──►  PostgreSQL
   (ce repo)         http://localhost:58000
```

**100 % local** : tout tourne sur ta machine, en Docker. Aucune publication, aucun
service externe.

---

## Sommaire

- [Tools exposés](#tools-exposés)
- [Démarrage rapide](#démarrage-rapide)
- [Brancher un client MCP](#brancher-un-client-mcp)
- [Configuration](#configuration)
- [Interface CLI](#interface-cli)
- [Transports](#transports)
- [Développement](#développement)
- [Structure du projet](#structure-du-projet)
- [Limites connues](#limites-connues)
- [Stack & licence](#stack--licence)

---

## Tools exposés

10 tools, un fichier par domaine (principe SOLID). Chaque tool a un schéma
d'entrée/sortie **Pydantic v2** strict et une `description` exploitée par le LLM
client. Les `id` sont des **ids InfiniDex** (Infinite Fusion), distincts du
numéro de Pokédex national.

| Tool | Rôle | Endpoint InfiniDex |
|---|---|---|
| `get_pokemon` | Fiche complète d'un Pokémon (stats, types, talents) | `GET /pokemon/{id}` (nom EN/FR résolu via `/pokemon/search`) |
| `search_pokemon` | Recherche par nom partiel (EN/FR) | `GET /pokemon/search?q=…` |
| `list_pokemon` | Liste paginée + filtres (type/génération/BST) + total | `GET /pokemon/` + `GET /pokemon/count` |
| `get_fusion` | Fusion head × body : stats, types, sprite, Move Experts | `GET /fusion/{head_id}/{body_id}/full` |
| `get_triple_fusion` | Triple fusion légendaire (1–23) | `GET /triple-fusions/{id}` |
| `search_move` | Recherche d'attaques par nom | `GET /moves/search?q=…` |
| `get_move` | Détail d'une attaque (descriptions EN/FR + infos TM) | `GET /moves/{id}` |
| `get_move_tutors` | Tuteurs classiques enseignant une attaque | `GET /moves/{id}/tutors` |
| `get_item` | Détail d'un objet (effet, prix, lieux) | `GET /items/{id}` |
| `get_pokemon_locations` | Où trouver un Pokémon (méthode, niveau, taux) | `GET /pokemon/{id}/locations` |

`get_pokemon`, `get_fusion`, `get_move`, `get_move_tutors` et
`get_pokemon_locations` acceptent un **id ou un nom** (EN/FR) — le nom est résolu
via l'endpoint `/search` correspondant.

---

## Démarrage rapide

Pré-requis : **Docker + Docker Compose**. (Aucune installation Python/`uv` sur ton
host : tout vit dans les conteneurs.)

```bash
git clone https://github.com/benjsant/infinidex_mcp.git
cd infinidex_mcp

# 1. Build de l'image runtime (serveur MCP), taguée infinidex-mcp:latest
make build

# 2. (optionnel) Vérifier la connexion à un InfiniDex qui tourne en local
make check

# 3. (optionnel) Lancer les tests
make test
```

> **InfiniDex doit tourner à part** (par défaut sur `http://localhost:58000`).
> Voir le dépôt [InfiniDex](https://github.com/benjsant/InfiniDex) : `docker
> compose up -d`.

> **⚠️ Note réseau (build).** Les `make build*` forcent `--network=host`. Sur un
> host dont le DNS ne résout `pypi.org` qu'en IPv6, le réseau bridge de Docker
> n'atteint pas pypi pendant le build ; `--network=host` contourne ça. Si ton DNS
> expose de l'IPv4, `docker compose build` fonctionne aussi.

---

## Brancher un client MCP

Le mode **stdio** (défaut) est piloté par le client : il lance le conteneur
lui-même. Exemples prêts à l'emploi dans [`examples/`](examples/).

### Claude Desktop / Claude Code

`claude_desktop_config.json` (ou l'équivalent Claude Code) :

```json
{
  "mcpServers": {
    "infinidex": {
      "command": "docker",
      "args": [
        "run", "--rm", "-i",
        "--add-host", "host.docker.internal:host-gateway",
        "-e", "INFINIDEX_URL=http://host.docker.internal:58000",
        "-e", "INFINIDEX_API_KEY=<votre INTERNAL_API_KEY, si InfiniDex l'exige>",
        "infinidex-mcp:latest"
      ]
    }
  }
}
```

> `host.docker.internal` permet au conteneur d'atteindre un InfiniDex qui tourne
> sur ton host (port 58000 par défaut).
>
> **⚠️ Clé interne.** Si ton InfiniDex définit `INTERNAL_API_KEY`, le backend
> renvoie **403** aux requêtes sans la clé. Renseigne alors `INFINIDEX_API_KEY`
> avec la même valeur — le MCP l'envoie en header `X-Internal-Key`.

Une fois branché, tu peux demander en langage naturel : *« donne-moi les stats de
Mime Jr fusionné avec Pikachu »* → le client appelle `get_fusion` via ce serveur,
et chaque appel de tool est visible en temps réel.

---

## Configuration

Tout passe par des variables d'environnement préfixées `INFINIDEX_`. Aucune
n'est requise : le serveur fonctionne out-of-the-box contre un InfiniDex local.

| Variable | Défaut | Rôle |
|---|---|---|
| `INFINIDEX_URL` | `http://localhost:58000` | URL de base de l'API InfiniDex |
| `INFINIDEX_API_KEY` | *(vide)* | Envoyée en header `X-Internal-Key` si InfiniDex l'exige |
| `INFINIDEX_MCP_TRANSPORT` | `stdio` | `stdio` (local) · `streamable-http` (hosted, recommandé) · `sse` (hosted, ancien) |
| `INFINIDEX_MCP_HOST` | `127.0.0.1` | Hôte d'écoute en mode hosted (mettre `0.0.0.0` en conteneur) |
| `INFINIDEX_MCP_PORT` | `3000` | Port d'écoute en mode hosted |
| `INFINIDEX_HTTP_TIMEOUT` | `10.0` | Timeout (s) des requêtes vers InfiniDex |
| `INFINIDEX_HTTP_RETRIES` | `2` | Tentatives supplémentaires sur erreur transitoire (timeout/réseau/5xx) |
| `INFINIDEX_HTTP_BACKOFF` | `0.2` | Délai de base (s) du backoff exponentiel entre tentatives |

---

## Interface CLI

```bash
infinidex-mcp                              # serveur stdio (défaut)
infinidex-mcp --transport streamable-http  # serveur hosted (recommandé)
infinidex-mcp --transport sse              # serveur hosted (ancien transport)
infinidex-mcp --check                      # teste connexion + authentification, puis exit
```

`--check` valide la **connexion ET l'authentification** (il interroge un endpoint
authentifié, pas seulement `/health`) et distingue trois cas :

- ✅ `OK` (exit 0) — joignable et authentifié
- ⛔ `403` (exit 1) — joignable mais clé manquante/invalide (`INFINIDEX_API_KEY`)
- ❌ injoignable (exit 1)

---

## Transports

| Transport | Usage | Commande |
|---|---|---|
| `stdio` | Clients locaux (Claude Desktop/Code, Cursor). **Défaut.** | `infinidex-mcp` |
| `streamable-http` | Serveur hosted moderne (recommandé), exposable via reverse proxy. | `make run-http` |
| `sse` | Serveur hosted, transport historique (conservé pour compat). | `make run-sse` |

En conteneur, le mode hosted écoute sur `0.0.0.0:3000` (réglé par l'image) pour
être joignable via `-p`. Endpoint MCP : `http://<host>:3000/mcp`.

```bash
make run-http      # streamable-http sur :3000
# handshake :
curl -s -X POST http://localhost:3000/mcp \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"x","version":"0"}}}'
```

---

## Développement

Workflow 100 % conteneurisé via le `Makefile` :

| Cible | Effet |
|---|---|
| `make build` | Image runtime (serveur MCP), taguée `infinidex-mcp:latest` |
| `make build-dev` | Image dev (inclut les deps de test) |
| `make test` | Build dev + suite `pytest` (couverture incluse) |
| `make check` | Vérifie connexion + auth à un InfiniDex local |
| `make run-http` | Serveur hosted streamable-http sur `:3000` |
| `make run-sse` | Serveur hosted SSE sur `:3000` |
| `make smoke` | Liste les tools exposés par le serveur |
| `make clean` | Supprime les images construites |

Les tests sont **purement unitaires** : aucune dépendance à un InfiniDex live, tout
le HTTP est mocké via [`respx`](https://lundberg.github.io/respx/). Le code source
et les tests sont montés en volume dans l'image dev → itération sans rebuild.

```bash
make test    # 41 tests, ~98 % de couverture
```

`docker-compose.yml` fournit aussi des services pour les runs (`test`, `check`,
`http`, `sse`).

### Principes de conception

- Un fichier `tools/<domaine>.py` par domaine métier (SOLID).
- Toute la logique HTTP est centralisée dans `client.py` — aucun `httpx` dans
  `tools/`.
- Le client HTTP est **partagé** sur la durée de vie du serveur (pool de
  connexions chaud), avec retry + backoff sur erreurs transitoires.
- Les erreurs HTTP InfiniDex (4xx/5xx, timeout) sont traduites en `McpError`
  propres, jamais propagées en exception brute.
- Pas de cache de données local — c'est le rôle du serveur InfiniDex.
- Schémas de sortie tolérants (`extra="ignore"`) pour rester compatibles si
  InfiniDex enrichit ses réponses.

---

## Structure du projet

```
infinidex_mcp/
├── Dockerfile                # image multi-stage (deps / dev / runtime) sur uv
├── docker-compose.yml        # services test / check / http / sse
├── Makefile                  # workflow Docker
├── pyproject.toml            # packaging uv + config pytest/coverage
├── src/infinidex_mcp/
│   ├── __main__.py           # entrée CLI (--transport, --check)
│   ├── server.py             # build du serveur FastMCP + lifespan client
│   ├── config.py             # settings via env (pydantic-settings)
│   ├── client.py             # client httpx async partagé (retry, erreurs→McpError)
│   ├── py.typed              # marqueur PEP 561 (lib typée)
│   └── tools/
│       ├── _base.py          # OutBase + résolution nom→id
│       ├── pokemon.py        # get_pokemon, search_pokemon, list_pokemon
│       ├── fusion.py         # get_fusion, get_triple_fusion
│       ├── moves.py          # search_move, get_move, get_move_tutors
│       ├── items.py          # get_item
│       └── locations.py      # get_pokemon_locations
├── tests/                    # pytest + respx (HTTP mocké)
└── examples/                 # configs Claude Desktop / Code / Cursor
```

---

## Limites connues

- **Recherche globale de lieux non exposée.** InfiniDex n'a pas d'endpoint HTTP de
  recherche de lieux par condition/méthode (c'est interne à son agent, côté DB) :
  on fournit donc `get_pokemon_locations` (lieux *d'un* Pokémon), pas une
  recherche globale type *« tous les légendaires »*.
- **`get_item` / `get_triple_fusion` dépendent de l'ETL InfiniDex.** Si l'ETL n'a
  pas chargé items/triple-fusions, ces endpoints renvoient 404 (le MCP traduit
  proprement en erreur).
- **Distribution locale uniquement.** Pas de publication PyPI/Homebrew : l'image
  Docker `infinidex-mcp:latest` se construit localement via `make build`.

---

## Stack & licence

Python 3.12+ · [`mcp`](https://github.com/modelcontextprotocol/python-sdk)
(FastMCP) · `httpx` (async) · `pydantic` v2 · `pydantic-settings` · `uv` · Docker.
Tests : `pytest` + `respx`.

Licence **MIT** — voir [LICENSE](LICENSE).
