# WATTSON Core Design Handoff

This pack captures the current design of WATTSON after revisiting the original WATTSON and ETK specifications in light of:

- the existing Obsidian vault and heavy use of Daily Notes;
- an Olares One as the primary development and runtime environment;
- a locally hosted inference backend, currently Qwen3.8-27B with 24 GB VRAM available on the server;
- Obsidian's newer CLI and Headless Sync tooling;
- Obsidian's Knap template language;
- the maturation of agent frameworks;
- and the explicit goal of reducing speculative architecture in favor of a small vertical slice that proves value.

These documents intentionally separate **durable product and information-model decisions** from **replaceable implementation machinery**.

## Documents

### 1. Executive system design

[`01-executive-system-design.md`](01-executive-system-design.md)

The concise product and architecture definition: what WATTSON is, what it is not, major components, execution environment, and the architectural boundaries intended to survive implementation changes.

### 2. Phased implementation plan

[`02-phased-implementation-plan.md`](02-phased-implementation-plan.md)

A milestone-driven implementation sequence. Each phase has a concrete exit criterion intended to prevent the project from expanding before the preceding uncertainty has been resolved.

### 3. Reference documents

- [`reference/01-etk-information-model.md`](reference/01-etk-information-model.md) — durable information architecture, note types, ontology axes, links, relationships, and tag evolution.
- [`reference/02-contracts-and-rendering.md`](reference/02-contracts-and-rendering.md) — ETK schema → JSON Schema → generated language types; structured LLM output; Knap rendering.
- [`reference/03-olares-and-vault-runtime.md`](reference/03-olares-and-vault-runtime.md) — Olares development/runtime model and the full-Obsidian-vs-Headless architectural spike.
- [`reference/04-processing-pipelines.md`](reference/04-processing-pipelines.md) — Bootstrapper, Daily Note ingestion, enrichment, and ontology-emergence flows.
- [`reference/05-agent-responsibilities.md`](reference/05-agent-responsibilities.md) — semantic responsibilities of each intelligent component, independent of agent framework.
- [`reference/06-decisions-open-questions.md`](reference/06-decisions-open-questions.md) — settled decisions, deliberate non-decisions, and early implementation questions.

## How to use this pack

Treat these files as the **design baseline**, not as a claim about the current state of either the `WATTSON` or `bigrock.dev` repositories.

The next useful step is to review this pack, then compare it against those repositories and produce a short implementation-state delta:

1. What already exists?
2. What conflicts with this design?
3. What can be reused?
4. What should be deleted or deferred?
5. What is the smallest first milestone from the current code state?

The repositories should inform implementation sequencing without accidentally redefining the product around unfinished experiments.
