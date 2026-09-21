# Reference — Semantic Agent Responsibilities

## 1. Framework Independence

These are **responsibilities**, not a requirement for one process/object/class per agent.

A future implementation can express them through:

- plain functions and model calls;
- AutoGen;
- another agent framework;
- scheduled jobs;
- a single orchestrator with typed tools.

Do not create a multi-agent topology merely to match this document.

---

# 2. Bootstrapper

## Mission

Convert one pre-ETK note into a complete set of reviewable ETK note proposals without losing meaningful source content.

## Semantic responsibilities

- understand the complete input note;
- segment it semantically;
- classify each useful fragment;
- generate appropriate declarative titles;
- distinguish Atom from genuine Evergreen synthesis;
- identify project/task/source material;
- apply all relevant established ontology tags;
- identify useful existing-note relationships.

## Constraints

- user reviews every generated note;
- preserve source meaning;
- avoid unnecessary prose rewriting;
- never silently discard content;
- do not create new ontology tags as part of ordinary migration.

---

# 3. Intake / Daily Note Processor

## Mission

Turn low-friction Daily Note capture into structured proposals.

## Responsibilities

- distinguish actionable capture, durable knowledge, source material, and transient text;
- use enough surrounding Daily Note context to interpret abbreviated capture;
- produce typed proposal(s);
- route the proposal through the same ETK contract/render pipeline as the Bootstrapper.

## Constraints

- do not require the user to invoke processing manually;
- do not erase source Daily Note text;
- do not interpret repeated Sync events as new ideas.

This responsibility may share most implementation code with the Bootstrapper.

---

# 4. Relationship & Tagging Enricher

## Mission

Ensure a durable note is as discoverable and connected as its content warrants.

## Responsibilities

### Tagging

Perform a thorough pass over the existing ontology.

Apply every materially relevant tag, not merely one primary category.

### Linking

Identify meaningful references to canonical linked notes.

Prefer real existing targets.

### Typed relationships

Identify relationships such as:

- support;
- contradiction;
- citation;
- application;
- derivation.

Use typed relationships only when the type adds useful information.

### Metadata normalization

Bring note metadata into schema compliance.

## Constraints

- no opaque entity-ID layer;
- no hidden relation comments;
- no casual invention of new tags;
- no unnecessary prose rewriting.

---

# 5. Hub & Ontology Scout

## Mission

Detect higher-level organization that has emerged from the corpus.

## Hub responsibility

Propose new Hubs for durable, navigationally useful clusters.

Do not act as a continuous Hub query repair process.

## Tag-evolution responsibility

Propose new tags only when:

- at least three notes support the category;
- the concept makes sense to a human;
- the cluster is distinct from existing tag coverage;
- the distinction has likely future utility.

## Constraints

- ontology expansion is proposal-only;
- conservative cadence;
- explain closest existing concepts and why they are insufficient.

---

# 6. Governance / Validation

The old design called this a "PR Butler."

Most of this should now be deterministic infrastructure, not an LLM agent.

Responsibilities include:

- JSON Schema validation;
- generated-type freshness;
- Knap template validation;
- file/path safety;
- idempotency checks;
- output-size limits;
- link-target checks where deterministic;
- failure logging;
- Git/versioning mechanics if enabled.

Use an LLM only when the governance decision genuinely requires semantic judgment.

---

# 7. Optional Future Semantic Roles

Do not implement these by default.

Possible later roles include:

- planning/next-action agent;
- weekly review synthesizer;
- project health agent;
- source-ingestion agent;
- duplicate/concept-merger;
- maturity reviewer for Atoms/Evergreens.

Each should be justified by repeated manual work that the existing roles cannot absorb cleanly.

---

# 8. Tool Design

Give semantic agents narrow typed tools.

Potential examples:

```text
vault.read_note
vault.search
vault.resolve_link
vault.backlinks
vault.tags
vault.move_note
vault.create_note

ontology.list_tags
ontology.describe_tag

render.note

model.embed
model.rerank
```

Agents should not receive a raw shell merely because the framework makes tool registration easy.

The agent chooses **what should happen**.

Typed application tools decide **how it happens safely**.
