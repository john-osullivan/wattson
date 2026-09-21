# Reference — Contracts, Type Generation, and Knap Rendering

## 1. Principle

AI should return **meaning**, not hand-crafted Markdown formatting.

WATTSON should establish a typed contract between semantic reasoning and durable files.

```text
ETK source schema
       ↓
generated JSON Schema
       ↓
structured model output
       ↓
runtime validation
       ↓
Knap
       ↓
Markdown
```

---

## 2. Schema Source of Truth

The human-maintained ETK schema should be compact and legible.

Suggested repository shape:

```text
schemas/
  etk/
    ontology.yaml
    note-types.yaml
    relations.yaml
    workflows.yaml
  generated/
    json-schema/
```

The exact YAML dialect is an implementation detail. It should optimize for easy human editing rather than mirror every JSON Schema keyword.

A generator compiles the ETK schema into full JSON Schema documents.

Generated JSON Schema is a build artifact, not an independently edited source.

---

## 3. Generated Language Contracts

JSON Schema feeds both application languages.

```text
JSON Schema
  ├── TypeScript static types
  ├── Zod runtime validators
  └── Python / Pydantic models
```

The repository should expose one `just` recipe that regenerates everything.

Example conceptual commands:

```text
just schemas
just types
just check-generated
```

CI should fail when committed generated contracts are stale.

---

## 4. Why JSON Schema Is the Interchange Boundary

It works naturally for:

- OpenAI structured outputs;
- local model JSON generation;
- TypeScript;
- Python;
- Zod/Pydantic validation;
- CLI stdin/stdout;
- `jq`;
- persisted proposal records;
- API payloads if a UI is later added.

Protocol Buffers are not required unless WATTSON later develops RPC/streaming constraints that JSON does not satisfy.

---

## 5. CLI / Language Boundary

Python and TypeScript components should exchange JSON through ordinary process boundaries unless a long-running service is genuinely useful.

Canonical pattern:

```text
TypeScript process
      ↓ JSON stdin
Python command
      ↓ JSON stdout
jq / schema validation
      ↓
TypeScript
```

`jq` is useful for:

- debugging payloads;
- projections;
- assertions in shell scripts;
- readable diagnostics;
- stable composition in `just` recipes.

Do not make `jq` the business-logic layer.

---

## 6. Semantic Output Contract

An LLM response should contain structured proposals rather than final Markdown.

Conceptually:

```json
{
  "source": {
    "path": "Daily Notes/2026-09-21.md",
    "sourceFingerprint": "..."
  },
  "proposals": [
    {
      "proposalId": "...",
      "noteType": "atom",
      "title": "Costly signals discourage low-effort abuse",
      "body": "...",
      "ontology": {
        "tags": [
          "area/society/media",
          "area/brasstax/product/abuse-prevention",
          "type/atom",
          "maturity/seed"
        ]
      },
      "relations": [
        {
          "type": "supports",
          "target": "Identity systems benefit from costly signals"
        }
      ],
      "links": [
        "Online community moderation"
      ]
    }
  ]
}
```

The final concrete schema should be generated from ETK rather than copied from this example.

---

## 7. Structured Output Requirements

Model output should be constrained enough that invalid generations fail closed.

Prefer, in order:

1. API-native structured outputs / JSON Schema;
2. constrained local decoding when the inference backend supports it;
3. JSON-only prompt plus strict validation/retry.

The model should never be trusted merely because its response looks JSON-like.

On invalid output:

1. retain the source unchanged;
2. log the validation problem;
3. retry with the validation error if policy allows;
4. otherwise surface a failed proposal.

---

## 8. Knap's Role

Knap owns the transformation from validated structured data to Obsidian Markdown.

Use it for:

- YAML/frontmatter serialization;
- note layout;
- links and embeds;
- optional sections;
- lists;
- repeated structures;
- filename-related formatting when appropriate.

Do not ask the model to reproduce boilerplate that belongs in a Knap template.

Example conceptual Atom template:

```knap
---
{{ frontmatter | yaml }}
---

# {{ title | trim }}

{{ body | trim }}

{% if relations %}
### Relations

{% for relation in relations %}
{{ relation.type }}:: [[{{ relation.target }}]]
{% endfor %}
{% endif %}
```

Exact Knap syntax should be tested against the installed version rather than copied blindly from this conceptual example.

---

## 9. Knap Features Worth Leveraging

Current Knap releases support useful features for WATTSON including:

- CLI rendering;
- JSON/stdin data input;
- batch rendering;
- template validation;
- safe YAML formatting;
- typed values preserved through filter chains;
- collection filtering/mapping;
- execution limits;
- a TypeScript library API.

Prefer the TypeScript library API inside long-running WATTSON application code; keep the CLI available for:

- manual debugging;
- golden tests;
- `just` recipes;
- container inspection.

Reference:
https://github.com/obsidianmd/knap

---

## 10. Proposed Template Set

Keep templates small.

Initial set:

```text
templates/
  atom.knap.md
  evergreen.knap.md
  project.knap.md
  source.knap.md
  hub.knap.md
```

If WATTSON uses in-vault staged proposals, a separate template can render proposal-only review metadata without contaminating final note templates.

---

## 11. Testing Strategy

### Contract fixtures

Store representative valid and invalid structured objects.

### Rendering golden files

For each template:

```text
fixture.json → Knap → expected.md
```

Use exact comparisons after normalized line endings.

### Round-trip semantics

When practical, parse rendered metadata back and verify semantic equality with source structured data.

### Model contract tests

Model integration tests should validate:

- valid schema;
- no unknown ontology values;
- no nonexistent link targets when a target is required to preexist;
- no content disappearance in Bootstrapper proposals.

---

## 12. OpenAI and Local Models

The contract layer should be identical for both.

### OpenAI

Use current Structured Outputs / JSON Schema capabilities where supported by the selected API/model.

### Local Qwen

Use the inference server's OpenAI-compatible or native structured-output mechanism if available.

If constrained decoding is supported, prefer schema-constrained generation over prompt-only JSON.

WATTSON's orchestration code should hide these differences behind a model-provider interface.
