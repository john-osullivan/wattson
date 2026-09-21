# WATTSON

An AI-augmented personal knowledge and task system built around Obsidian and
the Emergent Task & Knowledge (ETK) information model. WATTSON is a cognitive
maintenance layer over a durable Markdown knowledge graph: capture stays
low-friction (Daily Notes), and the system performs the semantic work of
turning raw material into structured, linked, tagged knowledge.

**Status: design baseline only. No implementation exists yet.**

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

These are the only hand-edited schema sources. Generated contracts (JSON
Schema, TypeScript, Zod, Pydantic) will derive from them in Phase 1.

## Repository state

The legacy scaffold (AutoGen multi-agent prototype, micro-PR tooling,
Docker Compose infra) was removed on 2026-09-21 and is preserved at git tag
`archive/legacy-scaffold` for reference only. Do not build on it; it
implements the pre-handoff architecture that the design pack supersedes.

## Next steps

Per the phased plan, implementation starts at:

- **Phase 0** — Olares development/runtime foundation + vault-runtime spike
  (full Obsidian in a container vs `obsidian-headless`; decision M0)
- **Phase 1** — freeze ETK contracts and deterministic Knap rendering (M1)

See `wattson-handoff/02-phased-implementation-plan.md` for work items and
exit criteria. Each phase exists to resolve one uncertainty; do not start a
later phase before the preceding exit criteria are met.
