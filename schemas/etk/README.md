# ETK schema sources

Human-editable YAML — the only hand-edited schemas in WATTSON. Phase 1
generates JSON Schema, TypeScript types, Zod validators, and Pydantic
models from these files (`just generate`); generated artifacts carry
do-not-edit banners and are never modified by hand.

| File | Feeds |
|---|---|
| `ontology.yaml` | tag enum (axes + Area tree), alias index |
| `note-types.yaml` | role definitions (human reference; not machine-consumed in v1) |
| `relations.yaml` | relation-type enum |
| `notes.yaml` | structured note contract — the model's output unit |
| `proposal.yaml` | proposal envelope — review-workflow container |

## Field dialect

A *named type* is any top-level mapping except `version`. Named types may
reference each other across files in this directory.

```yaml
typeName:
  description: one or more lines
  fields:                    # plain object
    fieldName:
      type: <type>
      required: true | false
      description: ...
      # + constraints (below)
```

### Types

| `type` | meaning |
|---|---|
| `string` | text |
| `date` | text, `YYYY-MM-DD` (pattern-checked, not calendar-validated) |
| `uri` | text, `http://` or `https://` URL |
| `boolean` | `true` / `false` |
| `enum` | one of `values` |
| `string_list` | array of non-empty strings |
| `tags` | array of established ontology tags (enum derived from `ontology.yaml`) |
| `links` | array of bare wikilink targets (no `[[`/`]]` brackets) |
| `relations` | array of `{type, target}`; `type` from `relations.yaml` |
| `tasks` | array of `{text, done}` |
| `list` | array; element type named by `item` |
| `<name>` | reference to another named type (any file in this directory) |

### Constraints

- `string`: `min_length`, `max_length`, `pattern` (ECMAScript regex)
- `date`, `uri`: `pattern` only
- list types (`string_list`, `tags`, `links`, `relations`, `tasks`, `list`):
  `min_items`, `max_items`, `unique_items`, `item_pattern` (regex applied to
  each string element), `item`
- `tags` only: `include_tag` (a required tag; `{noteType}` is resolved per
  union member), `sort_items` (render-time canonical ordering)
- `enum`: `values`

### `render` (notes.yaml only)

`render: frontmatter | body` tells the template where the field lives.
Frontmatter fields are assembled in code into one type-checked `fm` object
in declaration order; the template serializes it with Knap's `yaml` filter
— no YAML or Markdown formatting is hand-rolled in application code.

### Discriminated unions

```yaml
note:
  discriminator: noteType
  base_fields: { ... }
  members:
    atom:    { description: ..., fields: {} }
    project: { description: ..., fields: { due: ..., tasks: ... } }
```

Union members are the `members` keys. Each member's schema is its
`base_fields` plus its own `fields`, plus the discriminator added
automatically as a required enum. The generator emits one JSON Schema /
Zod / Pydantic union per discriminated type.
