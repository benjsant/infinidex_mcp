# Workflow Docker d'InfiniDex MCP.
#
# Les builds forcent --network=host : sur certains hosts (DNS IPv6-only),
# le réseau bridge de Docker n'atteint pas pypi.org pendant le build.

IMAGE        := infinidex-mcp:latest
DEV_IMAGE    := infinidex-mcp-dev:latest
INFINIDEX_URL ?= http://host.docker.internal:58000

.PHONY: build build-dev test check run-sse smoke clean

## Build de l'image runtime (serveur MCP).
build:
	docker build --network=host --target runtime -t $(IMAGE) .

## Build de l'image dev (inclut les deps de test).
build-dev:
	docker build --network=host --target dev -t $(DEV_IMAGE) .

## Lance la suite de tests (monte src/ et tests/ pour itérer sans rebuild).
test: build-dev
	docker run --rm \
		-v "$(PWD)/src:/app/src" -v "$(PWD)/tests:/app/tests" \
		$(DEV_IMAGE) pytest

## Vérifie la connexion à un InfiniDex local.
check: build
	docker run --rm --add-host host.docker.internal:host-gateway \
		-e INFINIDEX_URL=$(INFINIDEX_URL) $(IMAGE) --check

## Démarre le serveur en transport SSE (port 3000).
run-sse: build
	docker run --rm -p 3000:3000 --add-host host.docker.internal:host-gateway \
		-e INFINIDEX_URL=$(INFINIDEX_URL) \
		-e INFINIDEX_MCP_TRANSPORT=sse \
		$(IMAGE) --transport sse

## Smoke test : liste les tools exposés par le serveur.
smoke: build
	docker run --rm --entrypoint python $(IMAGE) -c \
		"import asyncio; from infinidex_mcp.server import build_server; from infinidex_mcp.config import Settings; \
		print(sorted(t.name for t in asyncio.run(build_server(Settings()).list_tools())))"

## Supprime les images construites.
clean:
	-docker rmi $(IMAGE) $(DEV_IMAGE)
