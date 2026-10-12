# WATTSON

An AI-augmented personal knowledge and task system built around Obsidian and
the Emergent Task & Knowledge (ETK) information model. WATTSON is a cognitive
maintenance layer over a durable Markdown knowledge graph: capture stays
low-friction (Daily Notes), and the system performs the semantic work of
turning raw material into structured, linked, tagged knowledge.

**Status: Phase 2 in progress.** The ETK contracts are frozen and
deterministic Knap rendering is proven end-to-end; the vault digest and the
extraction-proposal lifecycle (tagging + atom proposals, structured
JSON + Knap-rendered Markdown) are implemented. The design baseline, the
Phase 0 vault runtime (ADR 0001), and Phases 1–2 live in this repo.

## Design baseline

`wattson-handoff/` is the authoritative design pack:

- `wattson-handoff/README.md` — how to use the pack
- `wattson-handoff/01-executive-system-design.md` — product and architecture definition
- `wattson-handoff/02-phased-implementation-plan.md` — phased plan with exit criteria
- `wattson-handoff/reference/` — ETK information model, contracts/rendering,
  Olares/vault runtime, processing pipelines, agent responsibilities,
  settled decisions and open questions

Treat the pack as the design baseline, not a claim about repository state.

## Durable content

`schemas/etk/` — the human-editable ETK source schema, transcribed from the
handoff reference documents:

- `ontology.yaml` — ontology axes, seed Area tree, deterministic alias index
- `note-types.yaml` — note roles (fleeting, atom, evergreen, project, source, hub)
- `relations.yaml` — typed-relation vocabulary and encoding policy
- `notes.yaml` — the structured note contract (discriminated union, per D2/D3)
- `proposal.yaml` — the proposal envelope (per D6)

These are the only hand-edited schema sources. Generated contracts (JSON
Schema, TypeScript, Zod, Pydantic) derive from them; regenerate with
`just generate`, verify with `just check-generated`.

## Quickstart (Phase 1)

Prereqs: Node 20+, `just`, `python3`. The Python side uses an isolated venv
(`just py-setup` creates `py/.venv`).

```sh
just generate      # YAML -> JSON Schema + TS types + Zod + Pydantic
just test          # node:test (golden+invalid+schema) + python tests
just typecheck     # tsc --noEmit
just render test/golden/atom-minimal.json        # M1 command, prints Markdown
just render test/golden/source-full.json -o /tmp/n.md   # write to a file
just render-doc <ctx.json> --template digest     # render a machine doc (no ETK validation)
just digest        # vault digest: structural pass + semantic pipeline (model)
just digest-structural   # structural digest only (no model calls)
just proposal list                 # pending extraction proposals
just proposal show <id>            # rendered Markdown (--json for the raw envelope)
just proposal accept <id>          # render the atom, link the source, commit `agent:`
just proposal reject <id>
```

The M1 command validates the note (Zod, fail-closed) then renders it through
the matching Knap template. Invalid notes are rejected before anything is
written — `just render` prints the structured issue and exits non-zero.

Machine documents (vault digest, proposal envelopes) are structured JSON
rendered through `templates/digest.knap.md` / `templates/proposal.knap.md`
via `etk render-doc` — the same deterministic Knap engine, no hand-written
Markdown. The digest writes both artifacts to the vault:
`99_Machine/digest/<stamp>.json` (source of truth) and
`99_Machine/digest/<stamp>.md` (rendered).

## Repository state

The legacy scaffold (AutoGen multi-agent prototype, micro-PR tooling,
Docker Compose infra) was removed on 2026-09-21 and is preserved at git tag
`archive/legacy-scaffold` for reference only. Do not build on it; it
implements the pre-handoff architecture that the design pack supersedes.

## Next steps

Per the phased plan:

- **Phase 0** — DONE. Olares development/runtime foundation + vault runtime
  (full Obsidian in a container, `vault-runtime/`; decision ADR 0001).
- **Phase 1** — DONE. ETK contracts frozen and deterministic Knap rendering
  proven (ADR 0002).
- **Phase 2** — IN PROGRESS. Processing pipeline + proposal lifecycle done:
  semantic digest (established-tag tagging, atom extraction proposals),
  durable sidecar state, proposal review CLI, Knap-rendered digest.
  Remaining: live model pass against the real vault and durable Olares
  operation (app image, worker, chat).

See `wattson-handoff/02-phased-implementation-plan.md` for work items and
exit criteria, and `docs/plans/phase-1-etk-contracts.md` for the Phase 1 plan.
Each phase exists to resolve one uncertainty; do not start a later phase
before the preceding exit criteria are met.
