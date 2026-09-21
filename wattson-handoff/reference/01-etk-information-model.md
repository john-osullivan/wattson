# Reference — ETK Information Model

## 1. Purpose

Emergent Task & Knowledge (ETK) resolves a conflict found in many personal-management systems: information is simultaneously relevant to **action** and **knowledge**.

A note should not have to live in one conceptual silo.

ETK therefore separates the atomic unit of information—the note—from its contextual roles and uses metadata, links, and dynamic views to present different perspectives over the same corpus.

Conceptually:

- GTD contributes management of commitments, projects, contexts, and strategic horizons.
- Zettelkasten/Evergreen practice contributes atomic ideas, dense linking, synthesis, and emergent knowledge.
- ETK combines these without requiring a single folder/category to encode every role.

---

## 2. Durable Note Roles

### Fleeting Note

Low-friction raw capture.

Properties:

- minimal or no required semantic structure;
- may be transient;
- commonly originates in Daily Notes or inbox capture;
- intended to be clarified later.

### Atom

The fundamental durable knowledge unit.

Properties:

- expresses one meaningful concept;
- has a declarative title where practical;
- is independently linkable;
- preserves the user's idea rather than expanding it into unrelated synthesis.

An Atom is not required to be tiny. Atomicity is conceptual rather than a word-count rule.

### Evergreen

A durable synthesis.

Properties:

- expresses an integrative idea rather than merely summarizing one source fragment;
- generally draws on multiple Atoms or pieces of evidence;
- contains meaningful original synthesis;
- should be created conservatively.

Large notes are not automatically Evergreens.

### Project

A desired outcome requiring multiple actions.

Properties can include:

- status;
- due date;
- Area relationship;
- tasks / next actions;
- relevant knowledge links.

### Source

Represents external source material separately from the user's durable ideas.

Examples:

- article;
- book;
- PDF;
- video;
- website;
- paper.

A Source note can preserve bibliographic information, excerpts, summary, and reflections while Atoms represent ideas extracted from it.

### Hub

An intentional navigation or dashboard note.

A Hub is not a folder.

It provides a useful entry point into a major Area, subject, project family, or knowledge cluster using links and dynamic queries.

Existing Hubs should generally be stable. If routine AI editing is necessary to keep a Hub working, the query design should be inspected before adding an agent to maintain it.

---

## 3. Minimal Folder Model

The original ETK design uses a deliberately sparse folder hierarchy:

```text
00_Inbox/
10_Areas/
20_Projects/
30_Knowledge/
    Atoms/
    Evergreens/
    Sources/
99_Assets/
Meta/
```

The exact physical folder layout is less important than maintaining the conceptual boundary:

- folders provide broad operational organization;
- links and metadata encode richer meaning.

A staging/review folder may be added for WATTSON proposals without changing ETK semantics.

---

## 4. Ontology Axes

The original ontology defines several independent hierarchical axes.

### `#type`

```text
#type/hub
#type/project
#type/atom
#type/evergreen
#type/source
```

### `#status`

```text
#status/active
#status/someday
#status/incubating
#status/done
#status/dropped
```

### `#maturity`

```text
#maturity/seed
#maturity/budding
#maturity/stable
```

### `#horizon`

```text
#horizon/5-purpose-principles
#horizon/4-vision-goals
#horizon/3-areas-of-focus
#horizon/2-projects
#horizon/1-current-actions
```

### `#context`

Original seed contexts:

```text
#context/work
#context/home
#context/computer
#context/phone
```

Contexts can evolve if real task behavior demonstrates a useful distinction.

### `#area`

The original seed Area tree includes:

```text
#area/brasstax
  #area/brasstax/product
    #area/brasstax/product/credibility-models
    #area/brasstax/product/ux-design
    #area/brasstax/product/abuse-prevention
  #area/brasstax/market
    #area/brasstax/market/disinformation
    #area/brasstax/market/media-analysis
    #area/brasstax/market/research
  #area/brasstax/strategy
    #area/brasstax/strategy/gtm
    #area/brasstax/strategy/economics
    #area/brasstax/strategy/naming
  #area/brasstax/philosophy
    #area/brasstax/philosophy/epistemology
    #area/brasstax/philosophy/ethics

#area/business
  #area/business/startups
  #area/business/economics
  #area/business/product-management
  #area/business/venture-capital

#area/career
  #area/career/job-search
  #area/career/management
  #area/career/professional-development

#area/comedy
  #area/comedy/dark
  #area/comedy/programming
  #area/comedy/business
  #area/comedy/satire

#area/creative
  #area/creative/writing
  #area/creative/design

#area/personal
  #area/personal/family
  #area/personal/friends
  #area/personal/journaling
  #area/personal/relationships
  #area/personal/travel

#area/projects
  #area/projects/chick-fil-gay
  #area/projects/johno-dev

#area/society
  #area/society/disinformation
  #area/society/journalism
  #area/society/media
  #area/society/politics
  #area/society/sociology

#area/tech
  #area/tech/ai
  #area/tech/blockchain
  #area/tech/cybersecurity
  #area/tech/fintech
  #area/tech/programming
```

This tree is a **seed ontology**, not a declaration that future information must fit only these branches.

---

## 5. Tagging Policy

A central WATTSON requirement is a **comprehensive established-tag pass**.

Given a note, the semantic agent should search the entire currently valid ontology and identify all tags that materially apply, not merely choose the single most obvious category.

The system should optimize against two opposite failures:

### Under-tagging

A relevant note becomes hard to surface in a legitimate context because the agent applied only its primary topic.

### Tag proliferation

The ontology accumulates increasingly specific tags with one note each, turning tagging into disguised filing.

### New-tag criterion

The Hub/Ontology Scout may propose a new tag only when:

1. at least three existing notes fit it meaningfully;
2. the grouping is intelligible to a human;
3. the tag adds a new useful distinction;
4. its membership is not merely a duplicate of another tag's membership.

The threshold is a minimum, not sufficient proof. Three coincidentally similar notes do not require a tag.

---

## 6. Canonical Entities and Links

Do not create an opaque entity-ID system unless a demonstrated problem requires one.

Use Obsidian's existing identity primitive:

```markdown
[[Canonical Note]]
```

Aliases belong on the canonical note.

Examples of canonical linked entities can include:

- people;
- organizations;
- products;
- technologies;
- projects;
- concepts.

This keeps identity human-readable and allows Obsidian to participate directly in resolution.

---

## 7. Relationship Encoding

Ordinary `[[wikilinks]]` are sufficient for broad semantic adjacency.

Typed relationships are useful only when the relation itself carries information.

Use visible, human-editable inline fields rather than hidden comments or novel bracket syntax.

Example:

```markdown
### Relations

supports:: [[Identity systems benefit from costly signals]]
contradicts:: [[Friction always damages conversion]]
cites:: [[Exit, Voice, and Loyalty]]
applies-to:: [[BrassTax]]
related:: [[Online community moderation]]
```

Relationship vocabulary should remain deliberately small and should evolve only when repeated use justifies another relation type.

Initial candidates:

- `supports`
- `contradicts`
- `cites`
- `applies-to`
- `derived-from`
- `related`

---

## 8. Hubs and GTD Horizons

### Command Center

Supports:

- current actions;
- active projects;
- Areas of Focus;
- recently matured knowledge.

### Area Hub

Represents a durable Area of Focus/Responsibility.

Useful views can include:

- mission or standard;
- active projects;
- tasks;
- relevant knowledge;
- recent activity.

### Knowledge Hub

Supports exploration and synthesis.

Useful views can include:

- stable principles;
- idea incubator;
- related Atoms and Evergreens;
- orphaned or weakly connected notes.

Dynamic views should derive from repeatable ontology structure rather than hard-coded note lists whenever practical.

---

## 9. Physical Metadata Encoding — One Deliberate Normalization Remains

The original ETK design uses hierarchical tags heavily while some later WATTSON design sketches also represented `type`, `area`, `status`, `maturity`, `horizon`, and `context` as explicit frontmatter properties.

Do not blindly maintain both representations.

Before implementation, normalize this into one canonical encoding and generate queries/templates around it.

A reasonable default to evaluate is:

- keep hierarchical ETK tags canonical for ontology membership;
- use frontmatter for values that are naturally properties rather than taxonomy, such as dates, aliases, bibliographic fields, or WATTSON workflow state.

If explicit scalar properties materially improve Obsidian Bases/query ergonomics, add them intentionally with a defined synchronization rule.

This is an implementation-schema decision; the conceptual ontology above is already stable.
