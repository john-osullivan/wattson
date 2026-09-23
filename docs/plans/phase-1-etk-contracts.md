# Phase 1 Implementation Plan — Freeze ETK Contracts and Deterministic Rendering

Status: proposed, pending user sign-off
Date: 2026-09-23
Resolves: `wattson-handoff/02-phased-implementation-plan.md` Phase 1 / Milestone M1

## 1. Objective

Establish one typed boundary between semantic AI output and durable Markdown:

```
ETK source schema (hand-edited YAML)
      ↓ generate
JSON Schema (interchange boundary: model structured outputs, jq, CLI, proposal records)
      ↓ generate
TypeScript types + Zod validators        Pydantic/Python models
      ↓
Knap templates → deterministic Markdown (golden-tested)
```

M1: a command takes a valid ETK JSON object and deterministically produces
schema-valid, expected Markdown. No model calls, no vault writes, no review UI
— those are Phase 2+.

## 2. Current state (verified 2026-09-23)

- Hand-edited ETK sources exist: `schemas/etk/{ontology,note-types,relations}.yaml`
  (transcribed in Phase 0; tag-vs-frontmatter normalization already decided in
  the `ontology.yaml` header: hierarchical tags canonical for ontology
  membership, frontmatter for property-like values).
- Phase 0 exit criteria met: dev environment, Qwen endpoint
  (`scripts/model_test.py`), Obsidian runtime + CLI (ADR 0001), Sync round-trip.
- Toolchain on this host: Node 24.18 / npm 11, Python 3.12, just 1.43, jq.
  Default Python env has no PyYAML/pydantic → project venv needed for the
  Python side (already gitignored: `.venv/`).
- **Knap verified against npm `knap@0.6.0`** (obsidianmd/knap, MIT, Node 20+):
  - library: `createEngine({ filters: standardFilters })`,
    `await engine.renderOrThrow(template, { variables })` → markdown string;
  - CLI: `knap render|batch|validate`, offline `knap help filters|tags`;
  - standard filters include `yaml`, `wikilink`, `list`, `join`, `date`,
    `where`, `map` — enough for all five templates (probe-verified:
    frontmatter `yaml` dump, `{% for %}` loops, `wikilink`).
  - No `frontmatter` filter; frontmatter is assembled in code and passed as
    one variable (`{{ fm | yaml }}`).

## 3. Decisions

Defaults below are recommended; each is small to change before implementation.

- **D1 — Tag validation is a closed enum.** The generator emits the full list
  of currently valid tags (all axis values + every node/leaf of the Area tree)
  as a JSON Schema `enum` / `z.enum` / Python `Literal`. Unknown tags fail
  validation (fail-closed). Adding a tag means editing `ontology.yaml` (the
  Phase 5 Scout proposes exactly that edit). Seed ontology has ~120 tags; enum
  size is not a concern. *New-tag tracking (a way for model output to propose
  tags not yet in the ontology) is deliberately deferred — if Phase 2's
  Bootstrapper shows the need, it lands on the proposal envelope
  (`proposed_tags`), never on the note contract.*
- **D2 — Note contract is a discriminated union** of the five durable roles
  (`atom | evergreen | project | source | hub`), per `note-types.yaml`.
  `fleeting` stays a capture role and has no render contract.
- **D3 — Common fields + thin per-type extras:**
  - all notes: `noteType`, `title`, `body` (Markdown), `tags` (enum list,
    must include `type/<noteType>`), `links` (string[] of `[[wikilink]]`
    targets, plain adjacency), `relations` (`{type, target}` with `type` from
    `relations.yaml`), `aliases` (string[]), `created` (YYYY-MM-DD);
  - `project`: `due?` (date), `tasks?` (`{text, done}`);
  - `source`: `kind` (article|book|pdf|video|website|paper), `author?`,
    `url?`, `published?` (date), `excerpt?`;
  - `evergreen`, `hub`: no extras in v1 (synthesis / navigation live in
    `body` + `links`).
- **D4 — Frontmatter is assembled in code as a type-checked object, then
  serialized by Knap — never by hand-rolled string formatting.** `render.ts`
  does no string manipulation: it validates (Zod) and passes a type-checked
  variables object to the engine, including an `fm` object built in a fixed
  key order (`tags` sorted, then `aliases`, `created`, then type-specific
  keys). Knap 0.6.0 has **no file partials/includes** (verified: the
  `template` filter is an inline `${property}` mini-template, not a sub-file
  mechanism; syntax reference confirms only variables/filters/if/for/set), so
  each note template owns its own 3-line frontmatter block
  (`--- {{ fm | yaml }} ---`). With five templates this duplication is
  trivial, and each template stays self-contained and readable. Templates own
  layout; the `yaml` filter owns serialization.
- **D5 — Generator is TypeScript**, run via `tsx`, single file
  (`tools/generate.ts`). Rationale: Knap + Zod + the M1 command already make
  Node the runtime language; one toolchain; emitting Pydantic/Python is plain
  code-generation. (Alternative: Python generator — rejected to avoid a
  second language with generators, and to keep Phase 0's stdlib-only Python
  scripts dependency-free.)
- **D6 — Proposal envelope schema is included in Phase 1; the proposal
  template is not.** `proposal.yaml` freezes the envelope shape
  (`source {path, fingerprint}`, `proposals [{proposalId, status, note}]` with
  the lifecycle states from `reference/06` §6) so Phase 2 builds on a frozen
  contract. Rendering proposal/staging notes happens with Phase 2's review
  workflow.
- **D7 — Flat repo layout** (no npm workspaces, no monorepo tooling):

```
package.json tsconfig.json        # root = the TS project (private)
schemas/etk/*.yaml                # hand-edited sources (only these)
schemas/etk/README.md             # field dialect reference
schemas/generated/json-schema/    # etk-note, etk-proposal, etk-tag schemas
tools/generate.ts                 # the generator (yaml → everything)
src/generated/                    # types.ts, zod.ts (GENERATED)
src/render.ts src/cli.ts          # type-checked vars + template dispatch, M1 cmd
templates/*.knap.md               # atom evergreen project source hub
test/                             # golden + invalid fixtures, node:test
py/wattson/etk/generated/models.py# GENERATED Pydantic
py/tests/ py/pyproject.toml       # Python-side checks (venv: py/.venv)
```

## 4. Work items

### W1 — Complete the ETK source schemas (design step, user review) — DONE

- Added `schemas/etk/notes.yaml`: the structured note contract per D2/D3
  (discriminated union; base fields title/body/tags/links/relations/aliases/
  created; project: due/tasks; source: kind/author/url/published/excerpt),
  including per-field `render: frontmatter|body` placement and all
  constraints the generator needs.
- Added `schemas/etk/proposal.yaml`: the proposal envelope per D6
  (`proposal_source {path, fingerprint}`, `proposal {proposalId, status,
  note}`, `proposal_envelope {source, proposals[]}`; lifecycle states from
  `reference/06` §6).
- Added `schemas/etk/README.md`: the closed field dialect (types,
  constraints, `render`, discriminated unions) that the generator consumes.
- Left the three existing files untouched. All five parse cleanly.

### W2 — Contract generator

`tools/generate.ts` (deps: `yaml` for parsing; no other generator libraries):

- reads the five `schemas/etk/*.yaml`;
- derives the tag enum: axis values → `axis/value`; Area tree walk →
  `area/<path>` for every node and leaf;
- emits, with `GENERATED — do not edit` banners and fixed key order:
  - `schemas/generated/json-schema/{etk-note,etk-proposal,etk-tag}.schema.json`
    (draft 2020-12);
  - `src/generated/types.ts`, `src/generated/zod.ts` (discriminated unions,
    `extra: "forbid"` / `strict`);
  - `py/wattson/etk/generated/models.py` (Pydantic v2, discriminated union,
    `model_config = ConfigDict(extra="forbid")`);
- flags: `--out <dir>` (redirect all output; used by `--check`), `--check`
  (regenerate to temp, diff, exit 1 on drift);
- deterministic output: stable key order, 2-space indent, trailing newline,
  no timestamps.

### W3 — Knap templates (hand-written, own all Markdown/YAML formatting)

`templates/{atom,evergreen,project,source,hub}.knap.md`. Shape (atom example):

```
---
{{ fm | yaml }}
---

# {{ title | trim }}

{{ body | trim }}

{% if links %}### Links

{% for l in links %}- {{ l | wikilink }}
{% endfor %}
{% endif %}
{% if relations %}### Relations

{% for r in relations %}{{ r.type }}:: {{ r.target | wikilink }}
{% endfor %}
{% endif %}
```

- every template carries its own `--- {{ fm | yaml }} ---` block (D4: no
  partials in Knap 0.6.0; `fm` is a type-checked object from `render.ts`);
- `project` adds a `### Tasks` section (`- [ ]` / `- [x]` via `{% if t.done %}`);
- `source` adds a `### Excerpt` blockquote section;
- whitespace/blank-line behavior is whatever Knap 0.6.0 actually produces —
  golden fixtures (W5) pin it, and the `knap` version is pinned in
  `package.json` + lockfile.

### W4 — M1 command + renderer

- `src/render.ts`: `renderNote(json: unknown): { markdown, note }`
  → Zod-validate (structured error on failure, nothing rendered) → select
  template by `noteType` → build the type-checked variables object
  (incl. the `fm` frontmatter object, D4 — no string manipulation) → Knap
  `renderOrThrow` → markdown.
- `src/cli.ts`: `etk render <note.json> [-o out.md]` and
  `etk validate <note.json>` (M1 command; later phases wrap this).
- Root `package.json`: deps `knap@0.6.0`, `zod`; devDeps `typescript`, `tsx`,
  `@types/node`, `yaml`, `ajv` (schema cross-check).

### W5 — Golden + validation tests (node:test + tsx, no test framework dep)

- `test/golden/*.json` → `test/golden/expected/*.md`, one fixture per note
  type exercising: minimal fields, all optional fields, multiple
  relations/links, long body. Exact compare after CRLF normalization + single
  trailing newline.
- `test/invalid/*.json` — each must fail validation: unknown tag, missing
  `type/<noteType>` tag, bad relation type, empty title, non-due date,
  unknown noteType, extra fields. Assert the Zod error, not just a throw.
- `test/schema.test.ts` — every golden fixture also validates against the
  emitted JSON Schema via `ajv` (keeps the interchange boundary honest with
  the runtime validator).
- `py/tests/test_models.py` — import generated Pydantic models; parse every
  golden fixture; assert round-trip of key fields; assert an invalid fixture
  raises. Run under `py/.venv` (pydantic v2, pytest).

### W6 — just recipes (replaces the commented Phase 1 block)

```
just generate         # yaml → JSON Schema → TS/Zod/Pydantic (all)
just schemas          # JSON Schema only
just types            # TS/Zod/Pydantic only
just check-generated  # fail if committed generated contracts are stale
just test             # node:test (golden+invalid+schema) + python tests
just typecheck        # tsc --noEmit
just render <FILE>    # M1 command
just py-setup         # create py/.venv + install
```

### W7 — Docs

- ADR `docs/decisions/0002-etk-contracts.md`: records D1–D7 with rationale
  (this is the "freeze" the phase is named for).
- README: status update, quickstart (`just generate && just test &&
  just render test/golden/atom-minimal.json`).

## 5. Verification — exit criteria mapping

| Exit criterion | How it is verified |
|---|---|
| ETK source is the only hand-edited schema | generator reads only `schemas/etk/`; all emitted files carry do-not-edit banners |
| Generated contracts are reproducible | deterministic emitter + `just check-generated` (temp regen + diff) |
| Invalid structured output fails before touching the vault | `renderNote` validates before any rendering; invalid-fixture tests assert specific Zod errors; JSON Schema available for Phase 2 structured outputs |
| Knap rendering is deterministic and covered by fixtures | exact-match golden tests for all five templates; knap version pinned |

Definition of done: `just check-generated && just test && just typecheck`
all green from a clean clone; `just render <fixture>` output matches the
golden file byte-for-byte.

## 6. Explicitly out of scope (Phase 1)

No model calls, no prompt work, no vault writes, no proposal review workflow
or template, no SQLite state, no OAC/chart changes, no daily-note logic.
The Obsidian spike keeps running per ADR 0001 conditions (multi-day
stability + Sync are still open gates on that decision).

## 7. Risks / watch-items

- **Knap output quirks** (filter quoting, loop newline handling): pinned by
  golden fixtures + version lock; if 0.6.x changes whitespace, fixtures are
  re-blessed deliberately, never silently.
- **Pydantic v2 discriminated-union emit**: generated code is tested in W5;
  if the emitter is fiddly, fallback is `Annotated[Union[...],
  Field(discriminator="noteType")]` which is already the plan.
- **Tag enum staleness**: if Phase 2/5 add tags without regenerating,
  validation rejects them by design — that is the intended fail-closed
  behavior, surfaced as a clear "unknown tag" error.

## 8. Sequencing estimate

W1 (half session, incl. review) → W2 → W3+W4 → W5 → W6+W7. Each step ends
with a green `just test` slice; W2 is the only step that gates the rest.
