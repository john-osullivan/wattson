# Reference — WATTSON Processing Pipelines

## 1. General Pattern

Semantic workflows should share a common shape:

```text
trigger
  ↓
collect source + relevant context
  ↓
LLM semantic operation
  ↓
typed proposal JSON
  ↓
schema validation
  ↓
deterministic rendering / vault operation
  ↓
human review where required
  ↓
durable state
```

Keep semantic reasoning and deterministic mutation separate.

---

# 2. Bootstrapper

## Purpose

Convert pre-WATTSON notes into ETK.

The existing corpus is not assumed to have consistent formatting.

Typical examples include:

- Daily Notes containing many unrelated captures;
- long category notes separated by inconsistent dividers;
- one-line category stubs;
- mixed tasks, sources, observations, and ideas.

## Input unit

One existing note.

A single input note may produce many output notes.

## Fragmentation

**LLM-controlled.**

Formatting provides evidence but does not define boundaries.

The model reads the complete source and identifies semantic units based on meaning.

Do not use a heading/divider regex as the primary fragmenter.

## Semantic transformation

For each fragment, propose:

- output note role;
- declarative title;
- preserved body content;
- established ontology tags;
- relevant links;
- typed relationships;
- source/project metadata where appropriate.

Create Evergreens conservatively.

If the source contains ideas but not actual synthesis, create Atoms and leave synthesis for later.

## Review

The user reviews every proposed output.

Start with one proposal visible at a time.

Allow a configurable review batch size later when results prove trustworthy.

The user may:

- accept;
- edit then accept;
- reject;
- defer.

No original note is considered fully consumed until every meaningful source fragment has an explicit disposition.

## Content-loss invariant

Every meaningful part of the source must be:

- represented in accepted output;
- deliberately rejected by the user;
- or explicitly deferred.

The Bootstrapper must never silently drop text because the model labeled it "other."

## Git

Git is useful as ordinary project/vault backup but is not part of the Bootstrapper's human-in-loop protocol.

The user is already reviewing each conversion.

---

# 3. Daily Note Intake

## Purpose

Make WATTSON ambient.

The user writes normally into today's Daily Note from any Obsidian client.

WATTSON notices and processes the capture automatically.

## Trigger

Daily Note file changes after Sync reaches Olares.

Avoid running on every filesystem write.

Use a debounce/quiet period.

## Daily Note location

Prefer Obsidian's configured daily-note behavior if the selected Vault Runtime can expose it.

Do not unnecessarily hard-code filenames such as `YYYY-MM-DD.md`.

## Incremental state

Maintain a sidecar processing record outside user-authored Markdown.

For example:

```text
daily_note_path
last_seen_hash
last_processed_hash
last_processed_prefix_length
proposal ids
timestamps
```

### Fast path

If the previously processed Daily Note text is an exact prefix of the current text, treat the appended tail as new input.

### Edit path

If earlier content changed, use a conservative file-diff/reconciliation path.

Avoid repeatedly creating outputs for unchanged material.

## Result

Create reviewable ETK proposal(s).

Do not destructively remove Daily Note text in the initial implementation.

The Daily Note remains the capture log even after its ideas become durable notes.

---

# 4. Relationship & Tagging Enrichment

## Purpose

Improve a note's participation in the wider vault.

## Inputs

- target note;
- current ETK ontology;
- existing canonical note titles/aliases;
- direct links/backlinks if available;
- relevant search results;
- optional semantic retrieval later.

## Tagging pass

Evaluate **all currently valid tags** that could materially apply.

The task is not "choose a tag."

It is "identify the complete useful set without adding irrelevant labels."

## Link pass

Prefer existing canonical notes.

Do not invent a link target that does not exist unless the workflow explicitly supports proposing a new Atom/entity as a separate operation.

## Relationship pass

Use a small typed-relation vocabulary only when the relationship carries information beyond adjacency.

## Mutation

Enrichment proposals should remain reviewable until empirical trust justifies narrower classes of automatic mutation.

---

# 5. Hub & Ontology Scouting

## Purpose

Find durable structure that has emerged from actual content.

Runs infrequently.

## Candidate tag detection

Search for a semantic cluster with at least three meaningful members.

Compare membership against existing tags.

Reject a candidate if it merely renames an existing grouping.

Propose:

- tag;
- parent in hierarchy;
- concise semantic definition;
- notes that justify it;
- distinction from closest existing tags.

## Candidate Hub detection

Search for clusters large or important enough to merit a navigational entry point.

A Hub proposal should explain:

- why this is a durable navigational concept;
- which note types participate;
- what dynamic views should expose it.

The agent should not continuously rewrite existing Hub query code.

---

# 6. Model Failure Handling

Semantic failure must not become data loss.

On:

- timeout;
- invalid structured output;
- schema violation;
- missing link target;
- Knap failure;
- vault mutation failure;

WATTSON should:

1. preserve source content;
2. retain enough state for retry;
3. record a useful error;
4. avoid partially finalizing the proposal.

Use retry limits rather than infinite autonomous loops.

---

# 7. Idempotency

Each semantic job should have a stable identity based on:

- workflow type;
- source;
- relevant source content hash;
- schema/prompt version where material.

A repeated event for identical input should reuse/ignore the existing result rather than create another copy.

Generated note titles alone are not an idempotency key.

---

# 8. Human Feedback

Rejected or heavily edited proposals are useful evaluation data.

Initially, retain structured review outcomes such as:

```text
accepted
accepted_with_edits
rejected
deferred
```

Do not automatically fine-tune or mutate prompts based on every isolated correction.

Periodically inspect repeated failure patterns and convert them into:

- schema changes;
- clearer prompt rules;
- deterministic checks;
- ontology updates;
- model-routing changes.

This avoids teaching the system contradictory rules from one-off preferences.
