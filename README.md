# wattson
WATTSON automates the thoughtful synthesis of notes.  Schema-first knowledge & task agents operating on an Obsidian vault via micro-PRs.

## Quick start

1) Copy `.env.example` → `.env` and set `WATTSON_VAULT` to your local Obsidian vault path.
2) `just up` (or `docker compose -f infra/compose.yaml up -d`) to bring up agent-core + API.
3) Drop a note into `00_Inbox` (in your real vault). The Intake/Triage flow should propose a micro-PR.

### Repo structure

- `schema/` — JSON Schema & enums (validation; slow-changing “grammar”)
- `ontology/` — alias index, tag lexicon, entities (fast-changing “vocabulary”)
- `agent-core/` — Python agents + governance tools
- `api/` — thin service used by review UI to open/merge PRs
- `infra/` — Dockerfiles and Compose
- `scripts/` — small utilities (PR open, validate, etc.)

Vault is **not** in this repo. The path is read from `WATTSON_VAULT` at runtime and mounted in containers.

### Diff budget policy (human-scannable PRs)

- Default budget: ≤200 changed lines and ≤50 hunks per PR.
- Agents split work automatically when exceeding the budget.
- Metadata-only agents never touch prose.

