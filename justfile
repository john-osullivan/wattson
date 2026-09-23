# WATTSON task runner. https://just.systems
set shell := ["bash", "-c"]

default:
    @just --list

# --- Phase 0: model provider --------------------------------------------------

model-test:  # verify Qwen endpoint: connectivity, completion, structured JSON
    python3 scripts/model_test.py

# --- Phase 0: Obsidian vault-runtime spike ------------------------------------

spike-build:  # build the Obsidian-in-container spike image
    docker build --network=host -t wattson-spike-obsidian:latest spike/obsidian

spike-up:  # run spike container (noVNC :6080, test vault mounted, profile persisted)
    # --network=host: bridge egress is filtered (400 on apt AND Obsidian's sync API)
    docker rm -f wattson-spike-obsidian 2>/dev/null || true
    docker run -d --name wattson-spike-obsidian \
        --network=host \
        -v "{{justfile_directory()}}/spike/obsidian/vault-data:/data/vault" \
        -v wattson-spike-state:/data/state \
        -v wattson-spike-profile:/home/ubuntu/.config/obsidian \
        wattson-spike-obsidian:latest

spike-logs:  # tail spike container logs
    docker logs --tail 120 wattson-spike-obsidian

spike-shell:  # shell inside the spike container
    docker exec -it wattson-spike-obsidian bash

# --- Phase 0: Obsidian CLI -------------------------------------------------------
# The CLI is the Electron binary itself; the app-side "command line interface"
# toggle must be enabled (socket: ~/.obsidian-cli.sock). --no-sandbox is required:
# this container blocks unprivileged namespaces, so Chromium's zygote crashes
# without it (the GUI gets the same flag from entrypoint.sh).

spike-cli *args:  # run the Obsidian CLI: just spike-cli sync:status (avoid single quotes in args)
	docker exec -e CLI_ARGS='{{args}}' -u ubuntu -e DISPLAY=:99 wattson-spike-obsidian bash -c 'obsidian --no-sandbox --disable-gpu --disable-dev-shm-usage $CLI_ARGS'

spike-down:  # stop and remove the spike container
    docker rm -f wattson-spike-obsidian || true

# --- Phase 0: vault digest (structural, marker-triggered) ----------------------

digest:  # run vault digest now (newest pending marker, or manual stamp)
	python3 scripts/vault_digest.py --vault {{justfile_directory()}}/spike/obsidian/vault-data

digest-watch:  # start background 30s poller; runs a digest when a marker note appears in 99_Machine/digest/requests/
	@if [ -f /tmp/wattson-digest-watch.pid ] && kill -0 "$(cat /tmp/wattson-digest-watch.pid)" 2>/dev/null; then echo "digest watcher already running (pid $(cat /tmp/wattson-digest-watch.pid))"; else nohup bash -c 'while true; do python3 "{{justfile_directory()}}/scripts/vault_digest.py" --vault "{{justfile_directory()}}/spike/obsidian/vault-data" --quiet; sleep 30; done' >> "{{justfile_directory()}}/spike/obsidian/digest-watch.log" 2>&1 & echo $! > /tmp/wattson-digest-watch.pid; echo "digest watcher started (pid $(cat /tmp/wattson-digest-watch.pid), log: spike/obsidian/digest-watch.log)"; fi

digest-stop:  # stop the digest watcher
	@pid=$(cat /tmp/wattson-digest-watch.pid 2>/dev/null); if [ -n "$pid" ] && kill "$pid" 2>/dev/null; then echo "digest watcher stopped"; fi; rm -f /tmp/wattson-digest-watch.pid

# --- Phase 1 (planned) ----------------------------------------------------------
# schemas:         # ETK YAML -> JSON Schema -> TS/Zod/Pydantic
# types:           # regenerate language contracts
# check-generated: # fail if committed generated contracts are stale
