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
    docker rm -f wattson-spike-obsidian 2>/dev/null || true
    docker run -d --name wattson-spike-obsidian \
        -p 6080:6080 \
        -v "{{justfile_directory()}}/spike/obsidian/test_vault:/data/vault" \
        -v wattson-spike-state:/data/state \
        -v wattson-spike-profile:/root/.config/obsidian \
        wattson-spike-obsidian:latest

spike-logs:  # tail spike container logs
    docker logs --tail 120 wattson-spike-obsidian

spike-shell:  # shell inside the spike container
    docker exec -it wattson-spike-obsidian bash

spike-cli:  # obsidian CLI help inside the spike container
    docker exec wattson-spike-obsidian bash -lc 'obsidian --help'

spike-down:  # stop and remove the spike container
    docker rm -f wattson-spike-obsidian || true

# --- Phase 1 (planned) ----------------------------------------------------------
# schemas:         # ETK YAML -> JSON Schema -> TS/Zod/Pydantic
# types:           # regenerate language contracts
# check-generated: # fail if committed generated contracts are stale
