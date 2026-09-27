# ADR 0002 — ETK Contracts: One Typed Boundary, Deterministic Knap Rendering

Status: **Accepted**
Date: 2026-09-23
Deciders: WATTSON Phase 1 (Milestone M1)

## Context

Phase 1's job is to freeze the contract between semantic AI output and the
durable Markdown vault, and to prove that a command turns a *valid* ETK JSON
object into *expected* Markdown deterministically. The design
(`wattson-handoff/reference/02-contracts-and-rendering.md`) and the plan
(`docs/plans/phase-1-etk-contracts.md`) leave seven small decisions open.
This ADR records them so Phase 2+ builds on a frozen boundary. Scope is
deliberately narrow: no model calls, no vault writes, no review UI (those are
Phase 2+).

The pipeline is: hand-edited YAML (`schemas/etk/`) → a TypeScript generator
(`tools/generate/`) → JSON Schema (interchange) → TypeScript types + Zod
validators + Pydantic models → Knap templates → Markdown.

## Decisions

- **D1 — Tag validation is a closed enum.** The generator emits the full set
  of currently-valid tags (axis values `axis/value` + every node and leaf of
  the Area tree `area/<path>`) as a JSON Schema `enum` / `z.enum` / Python
  `Literal`. Unknown tags fail closed. Adding a tag means editing
  `ontology.yaml`; new-tag *proposal* (a way for model output to propose tags
  not yet in the ontology) is deferred to the Phase 2 proposal envelope
  (`proposed_tags`), never the note contract. Seed ontology ≈ 86 tags; enum
  size is not a concern.
- **D2 — The note contract is a discriminated union** of the five durable
  roles (`atom | evergreen | project | source | hub`), keyed on `noteType`,
  per `note-types.yaml`. `fleeting` is a capture role and has no render
  contract, so it is not a union member.
- **D3 — Common fields + thin per-type extras.** All notes: `noteType`,
  `title`, `body` (Markdown), `tags` (enum list, must include
  `type/<noteType>`), `links?` (plain wikilink targets, adjacency only),
  `relations?` (`{type, target}` from `relations.yaml`), `aliases?`, `created`
  (YYYY-MM-DD). `project`: `due?`, `tasks?` (`{text, done}`). `source`:
  `kind` (article|book|pdf|video|website|paper), `author?`, `url?`,
  `published?`, `excerpt?`. `evergreen`/`hub`: no extras in v1.
- **D4 — Frontmatter is assembled in code, serialized by Knap.** `render.ts`
  does no string manipulation: it Zod-validates, then passes a type-checked
  variables object to the engine including an `fm` object built in a fixed key
  order (`tags` sorted, then `aliases`, `created`, then type-specific keys).
  Knap 0.6.0 has **no file partials/includes** (verified), so each of the five
  templates owns its own `--- {{ fm | yaml }} ---` block. Templates own
  layout; the `yaml` filter owns serialization.
- **D5 — Generator is TypeScript, run via `tsx`, one module per concern.**
  Knap + Zod + the M1 command already make Node the runtime language, so one
  toolchain; emitting Pydantic is plain code-generation. `tools/generate/` is
  split into legible modules (`sources`, `dialect`, one `emit*` per artifact,
  `common`, `index`). A Python generator was rejected to avoid a second
  language for generators and to keep Phase 0's stdlib-only Python scripts
  dependency-free.
- **D6 — Proposal envelope schema now; proposal template later.**
  `proposal.yaml` freezes the envelope shape (`source {path, fingerprint}`,
  `proposals [{proposalId, status, note}]`, lifecycle states from
  `reference/06` §6) so Phase 2 builds on a frozen contract. Rendering
  proposal/staging notes belongs to the Phase 2 review workflow.
- **D7 — Flat repo layout.** No npm workspaces / monorepo tooling. Layout:
  `schemas/etk/` (hand-edited), `schemas/generated/json-schema/`,
  `tools/generate/`, `src/generated/` + `src/render.ts` + `src/cli.ts`,
  `templates/*.knap.md`, `test/`, `py/wattson/etk/generated/`.

## Rationale (summary)

One typed boundary (Zod at runtime, JSON Schema at the interchange edge,
Pydantic on the Python side) means model output is validated *before* it can
touch the vault, and the same source YAML regenerates all three. Knap is used
only as a template/serialization engine — deterministic and version-pinned —
not as a vault tool. Fail-closed tag validation is intentional: a stale
ontology rejects new tags loudly rather than letting them leak into the
graph.

## Consequences

- `just check-generated && just test && just typecheck` must stay green from a
  clean clone; `just render <fixture>` matches the golden file byte-for-byte.
- Tag growth is a `schemas/etk/ontology.yaml` edit followed by `just generate`
  + `just check-generated` — the enum, types, Zod, Pydantic, and JSON Schema
  all update together.
- The emitted JSON Schema is the interchange boundary Phase 2 feeds to model
  structured outputs; the runtime Zod validator and the schema are kept honest
  by the same golden fixtures (`test/schema.test.ts` cross-checks via Ajv).
- Knap whitespace quirks are pinned by golden fixtures + the `knap@0.6.0`
  lock; if a 0.6.x change shifts whitespace, fixtures are re-blessed
  deliberately, never silently.
