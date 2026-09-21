# WATTSON — Executive System Design

## 1. Purpose

WATTSON is an AI-augmented personal knowledge and task system built around Obsidian and the Emergent Task & Knowledge (ETK) information model.

Its primary purpose is to reduce the **executive-function cost** of maintaining a useful personal knowledge system. Capture should remain low-friction; WATTSON should perform much of the later semantic work required to turn raw material into structured knowledge and actionable commitments.

The system is designed around several durable goals:

- make capture cheap enough to use continuously;
- move classification, tagging, linking, and structural maintenance out of the user's working memory;
- combine task/action management with long-term knowledge development rather than maintaining separate systems;
- preserve a legible, local-first corpus made primarily of Markdown;
- use AI where semantic judgment is useful while keeping deterministic operations deterministic;
- keep the user in control of material transformations;
- allow the model, agent framework, UI, and hosting implementation to change without invalidating the knowledge base.

WATTSON is therefore best understood as a **cognitive maintenance layer over a durable Obsidian/Markdown knowledge graph**, not as an agent framework or a replacement notes application.

---

## 2. Core Product Model

Three layers should remain conceptually separate.

### WATTSON product layer

Defines what the system should accomplish:

- reduce organizational friction;
- preserve context;
- surface commitments;
- build useful connections;
- convert raw capture into durable knowledge;
- keep the vault trustworthy and understandable.

### ETK information layer

Defines the durable data model:

- note roles and lifecycle;
- hierarchical ontology;
- explicit links and relationships;
- projects and tasks;
- queryable metadata;
- hubs as views over the corpus.

This is the layer most worth protecting over time.

### Replaceable machinery

Includes:

- specific LLMs;
- agent frameworks;
- vector stores;
- review interfaces;
- Kubernetes topology;
- Git workflow;
- scheduling;
- embedding models;
- coding agents.

These should be introduced only when they solve a demonstrated problem.

---

## 3. Primary User Experience

The MVP should not require the user to launch WATTSON or point a CLI at a file.

The existing Obsidian **Daily Note is the primary capture surface**.

The normal flow should be:

```text
Phone / desktop Obsidian
        ↓
write into today's Daily Note
        ↓
Obsidian Sync
        ↓
WATTSON runtime on Olares
        ↓
semantic processing
        ↓
reviewable ETK proposals
        ↓
accepted ETK corpus
```

This preserves the lowest-friction behavior already in use: opening today's note and writing.

The exact approval UI is intentionally not foundational. The first review surface should be the simplest Obsidian-native or browser-accessible mechanism that permits quick inspection and editing. A custom review application is not required to prove the core system.

---

## 4. Execution Environment

### Olares One is both the development host and production host

Development should happen on the Olares box so it is available through a browser from any client.

Recommended human development surfaces:

- **Code Server**: primary browser IDE and interactive terminal.
- **OpenCode**: coding-agent environment operating on the same repository.
- **Control Hub**: deployment, container logs, container shells, Kubernetes inspection, and host administration.

The WATTSON monorepo should live in an explicitly shared user-data location such as:

```text
Home/Code/wattson
```

Applications that need repository access should receive explicit Olares `userData` permission to that location.

### Runtime

WATTSON should eventually be packaged as a private Olares Application Chart (OAC). Its application definition controls permissions, persistent storage, entrances, workload definitions, and connectivity; its container image controls which binaries and libraries are actually installed.

The first production runtime can remain one small WATTSON application rather than decomposing the system into many services.

---

## 5. Model Architecture

WATTSON should depend on a narrow model-provider abstraction.

Current default:

```text
Local inference → Qwen3.8-27B on Olares
```

Optional fallback or evaluation path:

```text
Remote inference → OpenAI API
```

The rest of WATTSON should not depend on a particular model name.

Different semantic jobs may eventually route to different local or remote models, but routing should be added after measurements demonstrate a need.

---

## 6. Core Data Pipeline

The preferred write path is:

```text
source content
      ↓
LLM semantic judgment
      ↓
ETK-typed structured data
      ↓
JSON Schema validation
      ↓
Knap template rendering
      ↓
Markdown / Obsidian operation
```

The division of responsibility is deliberate:

- **LLM**: meaning, decomposition, classification, tagging, relationship judgment.
- **JSON Schema**: valid structure.
- **Knap**: deterministic conversion from structured data to Markdown/YAML.
- **Obsidian**: vault semantics, navigation, links, metadata cache, and sync where available.
- **WATTSON**: orchestration, state, policy, and semantic workflows.

The LLM should not be responsible for reliably serializing YAML, inventing formatting conventions, or reproducing boilerplate that a template can render deterministically.

---

## 7. Vault Runtime Boundary

There are two plausible server-side Obsidian architectures. The rest of WATTSON should be insulated from this choice behind a small **Vault Runtime** interface.

### Candidate A — Full Obsidian runtime

Run the Linux desktop application inside the WATTSON environment using a virtual display such as Xvfb.

Advantages:

- access to the full `obsidian` CLI;
- Obsidian-native tag, task, link, backlink, rename, search, template, and property behavior;
- `obsidian eval` can access the running application's JavaScript API and metadata cache;
- Obsidian itself becomes the primary vault abstraction.

Risks:

- Electron in a headless/container environment is not an officially documented server mode;
- lifecycle and Sync stability must be tested;
- desktop Sync and Headless Sync must not operate concurrently on the same vault.

### Candidate B — Official Headless Sync runtime

Use `obsidian-headless` (`ob`) for continuous synchronization and implement only the vault semantics WATTSON actually needs.

Advantages:

- officially intended for agents and automation;
- materially simpler runtime;
- no virtual GUI requirements.

Costs:

- `ob` is a synchronization CLI, not the full vault-management CLI;
- WATTSON must own more parsing/indexing/link-resolution behavior.

### Decision rule

Do not settle this by speculation. Phase 0 contains a short spike that tests the full Obsidian option. If stable and operationally reasonable, prefer it for the semantic leverage of the full CLI/API. Otherwise fall back to Headless Sync without changing ETK, model contracts, or Knap rendering.

---

## 8. Initial Intelligent Workflows

Only a few semantic workflows are required before WATTSON can demonstrate value.

### Bootstrapper

Migrates existing unstructured or weakly structured notes into ETK.

The model performs semantic fragmentation rather than relying on headings or divider characters, because existing notes are inconsistent.

Each source note can yield multiple proposed notes.

The user reviews proposed outputs before they enter the durable corpus.

### Daily Note Intake

Continuously watches today's Daily Note and recognizes newly captured material after Sync delivers it to Olares.

It proposes ETK structures without requiring an explicit command from the user.

### Relationship & Tagging Enricher

Given an ETK note, performs a thorough semantic pass:

- applies all relevant established tags;
- identifies useful `[[wikilinks]]`;
- adds typed relationships when the relation itself is meaningful;
- normalizes structural metadata.

### Hub & Ontology Scout

Runs infrequently.

It looks for emergent clusters that justify:

- a new Hub;
- a new tag.

A new tag must aggregate at least three notes in a human-sensible way and add a genuinely new dimension rather than reproduce the same coverage as an existing tag.

---

## 9. Deterministic Supporting Infrastructure

The first version should use as little infrastructure as possible.

Required:

- human-editable ETK schema definitions;
- generated JSON Schemas;
- generated TypeScript types;
- generated Zod validators;
- generated Python/Pydantic types;
- Knap templates;
- local state for idempotency and processing status, likely SQLite;
- filesystem/vault watcher;
- model-provider interface;
- logging and simple diagnostics.

Deferred until demonstrated necessary:

- dedicated vector database;
- complex event bus;
- multi-agent chat topology;
- custom mobile review UI;
- Git PR machinery for every operation;
- cloud deployment;
- voice capture pipeline;
- elaborate autonomous scheduling.

---

## 10. Engineering Principles

### Legible logic

Prefer explicit workflows and named stages over clever abstraction.

### Strong typing

Define shared data once and generate language-specific representations.

### Human-readable source of truth

ETK remains the human-editable conceptual schema. Generated artifacts are not independently edited.

### Deterministic tools before LLM calls

Parsing that is genuinely semantic belongs to the model. Validation, rendering, state transitions, file naming rules, and schema checks should be ordinary code.

### Framework independence

Agent responsibilities are architectural; agent frameworks are replaceable.

AutoGen or another framework may eventually be useful, but WATTSON should not require a large agent framework to execute a simple semantic pipeline.

### Vertical slices before platform work

The system should earn new infrastructure by exposing a concrete limitation in a working workflow.

---

## 11. MVP Success Definition

The first meaningful WATTSON release is successful when all of the following are true:

1. WATTSON runs continuously on Olares.
2. A note written into today's Daily Note from a phone reaches the Olares vault automatically.
3. WATTSON detects new capture without a manual CLI invocation.
4. Local inference can turn that material into useful, schema-valid ETK proposals.
5. Proposed notes preserve the user's content and apply plausible tags/links.
6. The user can inspect and edit those proposals without excessive friction.
7. Accepted output becomes normal Obsidian Markdown and participates naturally in Obsidian links, search, queries, and plugins.
8. Repeated processing is idempotent enough not to generate duplicate notes continuously.

Everything beyond that is an enhancement rather than a prerequisite for beginning.

---

## 12. Current External References

These external implementation facts were current when this handoff was written:

- Obsidian CLI requires a running Obsidian desktop application:
  https://obsidian.md/help/cli
- Obsidian Headless provides the `ob` CLI and continuous Sync for automation:
  https://obsidian.md/help/sync/headless
- Knap repository and CLI/library documentation:
  https://github.com/obsidianmd/knap
- Olares application development:
  https://www.olares.com/docs/developer/develop/
- Olares Application Chart structure:
  https://www.olares.com/docs/developer/develop/package/chart
- Olares manifest and permission model:
  https://www.olares.com/docs/developer/develop/package/manifest
- Olares container inspection:
  https://www.olares.com/docs/manual/olares/controlhub/manage-container
