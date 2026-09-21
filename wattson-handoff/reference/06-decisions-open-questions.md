# Reference — Decisions, Non-Decisions, and Open Questions

## 1. Settled Design Decisions

### Obsidian remains the user-facing knowledge environment

WATTSON enriches the vault rather than replacing Obsidian.

### Daily Notes are the primary MVP capture surface

The system must operate without a manual processing command.

### ETK is the durable conceptual model

The note lifecycle, multi-axis ontology, links, Projects, Sources, and Hubs remain foundational.

### Local-first inference

Olares-hosted Qwen is the default inference path.

OpenAI can remain a configurable fallback/evaluation provider.

### Olares is the default development and runtime host

Browser access should be sufficient for ordinary development and operation.

### Knap is the deterministic Markdown renderer

Structured data should precede Markdown generation.

### JSON Schema is the language-neutral generated contract

ETK human-readable schema → JSON Schema → TS/Zod/Python.

### `[[wikilinks]]` are canonical entity references

Do not create opaque entity IDs without a demonstrated need.

### Typed relations are visible

Prefer readable inline fields over hidden comments or novel syntax.

### Tagging is comprehensive

The enrichment process must search for all relevant established tags.

### Ontology evolution is conservative

A new tag needs at least three meaningful members and a distinct informational contribution.

### Existing Hubs should normally be self-updating

The Hub Scout finds new structure rather than continuously repairing static lists.

### Bootstrapper fragmentation is semantic

Do not assume legacy headings/dividers accurately encode idea boundaries.

### Frameworks are replaceable

Agent-framework selection does not define the architecture.

---

# 2. Explicitly Deferred Decisions

These decisions should be made only after the relevant vertical slice exists.

### Review interface

Possibilities include:

- Obsidian-native staging;
- terminal/TUI;
- small browser UI;
- custom Obsidian plugin.

Do not build a custom UI simply because it can be designed.

### Git governance for ongoing agent edits

The original WATTSON design used branch/worktree/PR-style proposal governance.

That remains an option for higher-risk autonomous operation, but it is not required for Bootstrapper work or the first Daily Note vertical slice.

### Vector database

Do not select one yet.

First determine whether vault search, direct graph context, and model context are inadequate.

### Embedding/reranking models

Same rule: introduce after a measured retrieval failure.

### Agent framework

AutoGen was the original selected framework.

Given ecosystem changes and the goal of minimizing architecture, reconsider it when orchestration becomes nontrivial.

### Voice capture

Daily Notes already provide the initial capture interface.

Voice is an enhancement.

### Mobile review UX

The system must be usable from a phone, but the exact review interaction should follow observed usage.

---

# 3. Immediate Open Question — Full Obsidian vs Headless Sync

This is the only architectural fork that should be resolved before substantial vault tooling is written.

### Full Obsidian hypothesis

Running Obsidian desktop inside WATTSON with a virtual display could give the system:

- full CLI;
- MetadataCache;
- link resolution;
- Daily Note semantics;
- rename/link-update behavior;
- plugin/API access through `eval`.

### Headless fallback

`obsidian-headless` provides supported continuous Sync but not full vault operations.

### Required action

Build a short Phase-0 runtime spike and make the decision from observed stability.

---

# 4. Immediate Schema Question — Tags vs Explicit Frontmatter Properties

The original ETK design uses hierarchical tags for the ontology axes.

Some later design sketches duplicated these ideas as explicit fields such as:

```text
type
area
maturity
status
horizon
context
```

Before freezing the generated schema, choose a single canonical representation or a deliberate synchronization policy.

Avoid accidental dual sources of truth.

---

# 5. Daily Note Incrementality

The worker needs an idempotent way to recognize newly captured material.

Recommended initial behavior:

- maintain sidecar SQLite state;
- fast-path append-only changes;
- debounce Sync activity;
- conservative fallback on edits.

Do not add invisible markers to Daily Notes merely to simplify implementation unless sidecar state proves inadequate.

---

# 6. Proposal Lifecycle

A minimal state machine is useful even before selecting a UI.

Conceptually:

```text
generated
   ↓
pending_review
   ├── accepted
   ├── accepted_with_edits
   ├── rejected
   └── deferred
```

Finalization writes durable ETK notes.

The exact representation of this state is not yet fixed.

---

# 7. Repository Boundaries

There are at least two relevant repositories:

- `WATTSON`
- `bigrock.dev` (Olares/server work)

Their current contents were not part of this design handoff.

Before implementation planning continues, compare both repositories to this baseline.

Questions:

- Which repo should own Olares Application Chart definitions?
- Which repo should own reusable home-server deployment patterns?
- Which WATTSON code already exists?
- Is there a monorepo structure already worth preserving?
- Which experiments should be archived instead of integrated?

Avoid moving code until that state review exists.

---

# 8. Criteria for Adding Complexity

A new component is justified when all three are true:

1. a working vertical slice exposes a repeated limitation;
2. the component directly addresses that limitation;
3. a simpler change to schema/prompt/tooling is inadequate.

This rule applies especially to:

- agents;
- services;
- databases;
- queues;
- custom UIs;
- autonomous execution;
- orchestration frameworks.

---

# 9. Current Technical Facts to Re-verify During Implementation

External tools are changing rapidly.

Before depending on specifics, verify current versions and APIs for:

- Olares manifest/OAC specification;
- full Obsidian CLI;
- Obsidian Headless;
- Knap;
- the installed local inference backend;
- Code Server/OpenCode Olares filesystem permissions.

Current reference entry points:

- https://obsidian.md/help/cli
- https://obsidian.md/help/sync/headless
- https://github.com/obsidianmd/knap
- https://www.olares.com/docs/developer/develop/
- https://www.olares.com/docs/developer/develop/package/manifest
