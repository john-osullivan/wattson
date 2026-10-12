# WATTSON task runner. https://just.systems
set shell := ["bash", "-c"]

default:
    @just --list

# --- Phase 0: model provider --------------------------------------------------

model-test:  # verify Qwen endpoint: connectivity, completion, structured JSON
    python3 scripts/model_test.py

# --- Vault runtime: full Obsidian in a container (ADR 0001) ---------------------

vault-build:  # build the vault-runtime image
    docker build --network=host -t wattson-vault-obsidian:latest vault-runtime

vault-up:  # run the vault-runtime container (noVNC :6080, vault mounted, profile persisted)
    # --network=host: bridge egress is filtered (400 on apt AND Obsidian's sync API)
    docker rm -f wattson-vault-obsidian 2>/dev/null || true
    docker run -d --name wattson-vault-obsidian \
        --network=host \
        -v "{{justfile_directory()}}/vault-runtime/vault-data:/data/vault" \
        -v wattson-vault-state:/data/state \
        -v wattson-vault-profile:/home/ubuntu/.config/obsidian \
        wattson-vault-obsidian:latest

vault-logs:  # tail vault-runtime container logs
    docker logs --tail 120 wattson-vault-obsidian

vault-shell:  # shell inside the vault-runtime container
    docker exec -it wattson-vault-obsidian bash

# --- Vault runtime: Obsidian CLI -------------------------------------------------
# The CLI is the Electron binary itself; the app-side "command line interface"
# toggle must be enabled (socket: ~/.obsidian-cli.sock). --no-sandbox is required:
# this container blocks unprivileged namespaces, so Chromium's zygote crashes
# without it (the GUI gets the same flag from entrypoint.sh).

vault-cli *args:  # run the Obsidian CLI: just vault-cli sync:status (avoid single quotes in args)
	docker exec -e CLI_ARGS='{{args}}' -u ubuntu -e DISPLAY=:99 wattson-vault-obsidian bash -c 'obsidian --no-sandbox --disable-gpu --disable-dev-shm-usage $CLI_ARGS'

vault-down:  # stop and remove the vault-runtime container
    docker rm -f wattson-vault-obsidian || true

# --- Phase 0: vault digest (structural, marker-triggered) ----------------------

digest:  # run vault digest now (newest pending marker, or manual stamp)
	python3 scripts/vault_digest.py --vault {{justfile_directory()}}/vault-runtime/vault-data

digest-structural:  # structural digest only, no model calls
	python3 scripts/vault_digest.py --vault {{justfile_directory()}}/vault-runtime/vault-data --skip-semantic

proposal *args:  # extraction proposals: just proposal list | show <id> | accept <id> | reject <id>
	python3 scripts/vault_proposal.py --vault {{justfile_directory()}}/vault-runtime/vault-data {{args}}

digest-watch:  # start background 30s poller; runs a digest when a marker note appears in 99_Machine/digest/requests/
	@if [ -f /tmp/wattson-digest-watch.pid ] && kill -0 "$(cat /tmp/wattson-digest-watch.pid)" 2>/dev/null; then echo "digest watcher already running (pid $(cat /tmp/wattson-digest-watch.pid))"; else nohup bash -c 'while true; do python3 "{{justfile_directory()}}/scripts/vault_digest.py" --vault "{{justfile_directory()}}/vault-runtime/vault-data" --quiet; sleep 30; done' >> "{{justfile_directory()}}/vault-runtime/digest-watch.log" 2>&1 & echo $! > /tmp/wattson-digest-watch.pid; echo "digest watcher started (pid $(cat /tmp/wattson-digest-watch.pid), log: vault-runtime/digest-watch.log)"; fi

digest-stop:  # stop the digest watcher
	@pid=$(cat /tmp/wattson-digest-watch.pid 2>/dev/null); if [ -n "$pid" ] && kill "$pid" 2>/dev/null; then echo "digest watcher stopped"; fi; rm -f /tmp/wattson-digest-watch.pid

# --- Phase 1: ETK contracts + deterministic rendering -------------------------

generate:  # ETK YAML -> all generated contracts (JSON Schema + TS/Zod/Pydantic)
	@npm run generate

schemas:  # regenerate JSON Schema only
	@npm run generate -- --only schemas

types:  # regenerate language contracts (TS/Zod/Pydantic) only
	@npm run generate -- --only types

check-generated:  # fail if committed generated contracts are stale
	@npm run check-generated

typecheck:  # tsc --noEmit
	@npm run typecheck

test:  # node:test (golden+invalid+schema) + python tests
	@just test-node
	@just test-py

test-node:  # node:test golden + invalid + schema cross-check
	@npm test

test-py:  # python (pydantic) tests under py/.venv
	@just py-setup-ensure
	cd py && ./.venv/bin/python -m pytest tests -q

py-setup:  # (re)create py/.venv + install dev deps
	rm -rf py/.venv
	python3 -m venv py/.venv
	py/.venv/bin/python -m pip install --upgrade pip
	py/.venv/bin/python -m pip install -e "py[dev]"

py-setup-ensure:  # no-op if py/.venv exists, else run just py-setup
	@if [ -x py/.venv/bin/python ]; then echo "py/.venv present"; else just py-setup; fi

render *args:  # M1 command: just render <note.json> [-o out.md]
	@npx tsx src/cli.ts render {{args}}

render-doc *args:  # render a machine document: just render-doc <context.json> --template <name> [-o out.md]
	@npx tsx src/cli.ts render-doc {{args}}
