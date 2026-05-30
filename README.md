# InfiniDex MCP

Serveur [Model Context Protocol](https://modelcontextprotocol.io) qui expose les
données structurées d'[InfiniDex](https://github.com/benjsant/InfiniDex)
(Pokémon Infinite Fusion) à n'importe quel client MCP — Claude Desktop, Claude
Code, Cursor, Windsurf…

> *« InfiniDex expose un agent LLM via HTTP pour son frontend. Mais si tu veux
> que Claude Code ou Cursor l'interroge directement ? J'ai construit le serveur
> MCP qui sert exactement ça. »*

Le serveur fait le pont entre un client MCP et l'API HTTP REST d'InfiniDex. Il
n'a **aucune dépendance** sur le runtime InfiniDex — juste son URL.

## Tools exposés

| Tool | Wrapper InfiniDex |
|---|---|
| `get_pokemon` | `GET /pokemon/{id}` |
| `get_pokemon_by_name` | `GET /pokemon/by-name/{name}` |
| `search_pokemon` | `GET /pokemon/?name=…` |
| `list_pokemon` | `GET /pokemon/?limit=…&offset=…` |
| `get_fusion` | `GET /fusion/{head_id}/{body_id}/full` |
| `get_triple_fusion` | `GET /triple-fusions/{id}` |
| `search_move` | `GET /moves/?name=…` |
| `get_move_tutors` | `GET /tutors/by-move/{move_id}` |
| `get_item` | `GET /items/{id}` |

Chaque tool a un schéma d'entrée/sortie Pydantic v2 strict et une `description`
exploitée par le LLM client.

## Workflow Docker (recommandé)

Tout tourne en conteneur — aucune installation Python/`uv` sur ta machine. Le
`Makefile` encapsule les commandes :

```bash
make build      # image runtime (serveur MCP), taguée infinidex-mcp:latest
make test       # build dev + suite de tests
make check      # vérifie la connexion à un InfiniDex local
make run-sse    # serveur en transport SSE sur :3000
make smoke      # liste les tools exposés
```

> **Note réseau :** les `make build*` forcent `--network=host`. Sur un host dont
> le DNS ne résout `pypi.org` qu'en IPv6, le réseau bridge de Docker n'atteint
> pas pypi pendant le build ; `--network=host` contourne ça. Si ton DNS expose
> de l'IPv4, `docker compose build` fonctionne aussi.

`docker-compose.yml` est également fourni pour les runs (`test`, `check`, `sse`).

## Brancher un client MCP

Voir [`examples/`](examples/). Exemple Claude Desktop / Code :

```json
{
  "mcpServers": {
    "infinidex": {
      "command": "docker",
      "args": [
        "run", "--rm", "-i",
        "--add-host", "host.docker.internal:host-gateway",
        "-e", "INFINIDEX_URL=http://host.docker.internal:58000",
        "infinidex-mcp:latest"
      ]
    }
  }
}
```

> `host.docker.internal` permet au conteneur d'atteindre un InfiniDex qui tourne
> sur ton host (port 58000 par défaut).
>
> ⚠️ Si ton InfiniDex définit `INTERNAL_API_KEY`, le backend renvoie **403** aux
> requêtes sans la clé. Renseigne alors `INFINIDEX_API_KEY` avec la même valeur —
> le MCP l'envoie en header `X-Internal-Key`.

## Configuration

| Variable | Défaut | Rôle |
|---|---|---|
| `INFINIDEX_URL` | `http://localhost:58000` | URL de base de l'API InfiniDex |
| `INFINIDEX_API_KEY` | *(vide)* | Envoyée en header `X-Internal-Key` si InfiniDex l'exige |
| `INFINIDEX_MCP_TRANSPORT` | `stdio` | `stdio` (clients locaux) ou `sse` (hosted) |
| `INFINIDEX_MCP_PORT` | `3000` | Port d'écoute SSE |

## CLI

```bash
infinidex-mcp                  # serveur stdio (défaut)
infinidex-mcp --transport sse  # serveur SSE
infinidex-mcp --check          # teste la connexion à InfiniDex puis exit
```

## Stack

Python 3.12+ · [`mcp`](https://github.com/modelcontextprotocol/python-sdk) ·
`httpx` (async) · `pydantic` v2 · `uv` · Docker.

## Licence

MIT — voir [LICENSE](LICENSE).
