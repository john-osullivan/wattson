# WATTSON — Phased Implementation Plan

## Planning rule

Each phase exists to resolve a specific uncertainty. Do not substantially implement a later phase until the preceding phase's exit criteria have been met.

The project previously accumulated design faster than working software. This plan deliberately biases toward **vertical slices and empirical decisions**.

---

# Phase 0 — Establish the Olares development/runtime foundation

## Objective

Prove that WATTSON can be developed comfortably on Olares and settle the one architectural question that materially affects vault implementation: full Obsidian runtime versus official Headless Sync.

## Work

### Development workspace

Establish:

- repository under `Home/Code/wattson`;
- Code Server with access to that directory;
- OpenCode with access to the same directory;
- Git credentials/workflow;
- Python and TypeScript toolchains;
- `just`, `jq`, container-build tooling, and tests;
- access to the existing local Qwen inference endpoint.

### Olares application skeleton

Create the smallest private Olares Application Chart that can:

- launch a test container;
- persist application data;
- reach the local inference backend;
- expose logs and a shell through Control Hub.

Do not build a user-facing WATTSON web UI.

### Vault-runtime spike

Prototype full Linux Obsidian in a container using a virtual X display.

Verify:

- app launches reliably;
- target test vault opens;
- Obsidian CLI registers and works;
- `obsidian tags`, `links`, `backlinks`, `tasks`, property operations, file creation, rename/move, and `eval` work;
- Sync can run reliably;
- process survives restarts;
- behavior remains stable for several days.

In parallel, confirm the fallback path using `obsidian-headless`:

- login;
- `sync-setup`;
- `sync --continuous`;
- persistent credentials/configuration;
- phone ↔ Olares round trip.

## Milestone M0 — Runtime decision

A short architecture decision record chooses:

- **Full Obsidian Runtime**, or
- **Headless Sync + WATTSON vault library**.

The choice is backed by an actual container test rather than preference.

### Exit criteria

- Browser-based development environment is comfortable enough for normal work.
- Local Qwen can be called from repo code.
- A WATTSON test application can run on Olares.
- Obsidian Sync round-trip works.
- Vault-runtime path is chosen.

---

# Phase 1 — Freeze ETK contracts and deterministic rendering

## Objective

Establish one typed boundary between semantic AI output and durable Markdown.

## Work

### Human-readable ETK schema

Extract the authoritative ontology and note-role rules into editable ETK schema files.

Do not independently maintain JSON Schema, TypeScript, Zod, and Python definitions.

### Generation pipeline

Implement:

```text
ETK source schema
     ↓
JSON Schema
     ├── TypeScript types
     ├── Zod validators
     └── Pydantic/Python types
```

Expose regeneration through `just`.

### Knap templates

Create minimal templates for:

- Atom;
- Evergreen;
- Project;
- Source;
- Hub;
- proposal/review representation if needed.

Templates own YAML/Markdown formatting.

### Golden tests

Given known structured JSON, render exact Markdown fixtures.

## Milestone M1 — Typed ETK write pipeline

A command can take a valid ETK JSON object and deterministically produce schema-valid, expected Markdown.

### Exit criteria

- ETK source is the only hand-edited schema.
- Generated contracts are reproducible.
- Invalid structured output fails before touching the vault.
- Knap rendering is deterministic and covered by fixtures.

---

# Phase 2 — Bootstrapper vertical slice

## Objective

Prove that local inference can successfully reorganize the notes that actually exist.

## Scope

Process **one source note at a time**.

The source can be:

- a sparse stub;
- a long Daily Note;
- an over-broad topic note;
- a note whose formatting does not reliably signal semantic boundaries.

## Semantic pipeline

The model:

1. reads the complete source note;
2. identifies semantic fragments;
3. determines whether each fragment should become an Atom, Project, Source, rare Evergreen, or remain unconverted;
4. proposes declarative titles;
5. performs a full established-tag pass;
6. proposes useful links and typed relations;
7. returns structured ETK objects.

Code:

8. validates objects;
9. renders them through Knap;
10. presents proposed files for human review;
11. writes only accepted/edited output.

Content preservation is mandatory. Provenance tracking is optional because the migration is intended to create a new durable corpus rather than preserve a historical transformation chain.

## Review

Do not build a sophisticated review UI in this phase.

Use the simplest review workflow that allows rapid:

- inspect;
- edit;
- accept;
- reject.

Batch size may control how many candidate outputs from one source note are reviewed at once, beginning at one.

## Evaluation set

Run the workflow against a deliberately varied set of real notes rather than fabricated examples.

Track qualitative failures such as:

- fragment boundaries too broad/narrow;
- content loss;
- unnecessary rewriting;
- wrong note type;
- missing tags;
- over-tagging;
- duplicate concepts;
- poor titles;
- hallucinated link targets.

## Milestone M2 — Bootstrapper is worth using

At least a representative sample of legacy notes can be converted with substantially less effort than manual ETK refactoring.

### Exit criteria

- No known content-loss failure.
- User routinely accepts the majority of proposed structure after modest edits.
- Model output contracts are stable enough for continued use.
- Failure patterns have produced prompt/schema/tool improvements rather than more architecture.

---

# Phase 3 — Ambient Daily Note ingestion

## Objective

Make WATTSON useful during ordinary life without requiring the user to launch it.

## Work

### Daily Note resolver

Determine today's Daily Note using the chosen vault runtime and Obsidian conventions/configuration.

Avoid hard-coding a filename format when Obsidian can provide the configured Daily Note.

### Continuous processing

Run an always-on WATTSON worker in the Olares application.

The worker:

1. receives/senses Sync updates;
2. identifies changes to today's Daily Note;
3. waits for a short quiet period to avoid processing every keystroke;
4. determines what content is new or changed;
5. invokes the semantic pipeline;
6. creates reviewable proposals.

### Processing state

Use sidecar state, likely SQLite, rather than embedding invisible operational markers into user notes.

At minimum track:

- source path;
- source content hash;
- processed ranges/fragments when practical;
- proposal identifiers;
- output identifiers;
- status.

Optimize first for append-heavy Daily Note behavior. If the existing note remains an exact prefix, process only the appended tail. On arbitrary edits, fall back conservatively rather than pretending diff interpretation is perfect.

### Review surface

Use the simplest mechanism that is available from normal Obsidian clients.

A dedicated in-vault proposal/staging area is a strong default because it is immediately available on phone and desktop. Exact approval interaction remains replaceable.

## Milestone M3 — Phone-to-WATTSON loop

The user can add meaningful content to today's Daily Note from a phone, do nothing else, and later see useful ETK proposals generated on Olares.

### Exit criteria

- No manual processing command is required.
- Changes arrive promptly enough for ordinary use.
- Repeated Sync events do not create duplicate proposal storms.
- Failure does not modify or lose Daily Note content.
- Review can occur from an ordinary Obsidian client.

---

# Phase 4 — Relationship & Tagging Enricher

## Objective

Prove that WATTSON can maintain structure after notes exist rather than only create it during migration.

## Work

For a new or changed ETK note:

1. collect relevant vault context;
2. perform a comprehensive pass over existing tags;
3. resolve likely note/entity references against canonical `[[linked]]` notes;
4. propose missing plain links;
5. propose typed relationships only when relation semantics add value;
6. normalize metadata against ETK schema.

Use deterministic vault queries first; semantic retrieval is an enhancement.

Do not add a vector database merely because one was in an old architecture drawing.

## Milestone M4 — Corpus improves with use

A newly created note becomes meaningfully better connected and tagged with minimal manual curation.

### Exit criteria

- Established-tag recall is good enough that manual tag hunting is uncommon.
- Hallucinated/nonexistent link targets are rare or prevented structurally.
- Enrichment is idempotent.
- Changes remain understandable to the user.

---

# Phase 5 — Emergent ontology and Hub scouting

## Objective

Allow the information architecture to grow with the corpus without tag proliferation.

## Work

Periodically analyze the corpus for candidate clusters.

### New tag rule

A proposed new tag must:

- apply meaningfully to at least three notes;
- describe a human-sensible concept;
- add a new dimension of organization;
- not merely reproduce the exact or near-exact membership of an existing tag.

### New Hub rule

A Hub candidate should correspond to a cluster worth navigating as an intentional entry point, not merely any semantic cluster.

The Scout proposes; it does not silently expand the ontology.

## Milestone M5 — Ontology evolves conservatively

The system occasionally surfaces genuinely useful structural concepts without accumulating one-note tags.

---

# Phase 6 — Add infrastructure only where measured friction warrants it

Potential additions include:

- embeddings and vector retrieval;
- specialized reranker;
- multi-model routing;
- AutoGen or another orchestration framework;
- Git/worktree proposal governance;
- richer browser/mobile review UI;
- voice capture;
- scheduled planning/review agents;
- additional agent roles.

Every addition should identify the concrete bottleneck it solves and a simpler alternative that proved insufficient.

---

# Cross-phase non-goals

Until demonstrated necessary, do not spend significant implementation effort on:

- cloud GPU deployment;
- custom synchronization;
- bespoke graph database;
- generalized workflow engine;
- microservice decomposition;
- complex event infrastructure;
- fully autonomous edits to the durable vault;
- perfect mobile review UX;
- elaborate voice interfaces;
- a universal personal assistant.

The first goal is narrower: make the existing Obsidian capture behavior produce a progressively better ETK corpus with very little maintenance effort.
