---
type: wattson-digest
created: {{ created }}
trigger: {{ trigger }}
since: {{ since }}
digest-version: 1
---

# Digest — {{ stamp }}

## You ({% if sync_sha %}`sync: {{ sync_sha }}`{% else %}no uncommitted changes at trigger time{% endif %})

{{ changed_total }} path(s) changed since {{ since }}.

{% for c in changes %}### {{ c.title }} ({{ c.count }})
{% if c.count %}{% for g in c.groups %}{% if g.root_single %}- `{{ g.paths[0] }}`
{% else %}- **{{ g.folder }}** ({{ g.count }})
{% for p in g.paths %}  - `{{ p }}`
{% endfor %}{% endif %}{% endfor %}{% else %}(none)
{% endif %}

{% endfor %}## Agent since last digest

{% if agent_commits %}{% for a in agent_commits %}- `{{ a.sha }}` {{ a.subject }}
{% for p in a.paths %}  - `{{ p }}`
{% endfor %}{% endfor %}{% else %}(none)
{% endif %}

## Unfiled Inbox ({{ inbox | length }})

{% if inbox %}{% for p in inbox %}- `{{ p }}`
{% endfor %}{% else %}(none)
{% endif %}

## Semantic review (WATTSON)

{% if not semantic %}(not run)
{% else %}{% if semantic.skipped %}(skipped: {{ semantic.skip_reason }})
{% else %}{{ semantic.examined }} note(s) examined; {{ semantic.notes | length }} changed since last digest; {{ semantic.tagged }} tagged; {{ semantic.atoms_proposed }} extraction proposal(s).
{% if semantic.truncated %}- **partial run**: this digest processed only a bounded batch; the remaining changed notes carry over to the next digest.

{% endif %}

{% if not semantic.notes %}(no changed notes — nothing to review)

{% else %}{% for n in semantic.notes %}### `{{ n.path }}` ({% if n.append_only %}append-only edit{% else %}edited{% endif %})
{% if n.summary %}- summary: {{ n.summary }}
{% endif %}{% if n.applied %}- tags applied:
{% for t in n.applied %}  - `{{ t.tag }}` — {{ t.reason }}
{% endfor %}{% endif %}{% if n.review_tags %}- tag suggestions (not applied — needs review):
{% for t in n.review_tags %}  - `{{ t.tag }}` — {{ t.reason }}
{% endfor %}{% endif %}{% if n.rejected_tags %}- tags rejected (not established):
{% for t in n.rejected_tags %}  - `{{ t.tag }}` — {{ t.why }}
{% endfor %}{% endif %}{% if n.review %}- ambiguous topics:
{% for r in n.review %}  - {{ r.topic }}: {{ r.options | map:item => "`${item}`" | join:" | " ?? "(none)" }} — {{ r.note }}
{% endfor %}{% endif %}{% if n.skipped_extractions %}- extractions skipped:
{% for e in n.skipped_extractions %}  - {{ e.title }} — {{ e.why }}
{% endfor %}{% endif %}{% if n.error %}- **error**: {{ n.error }}
{% endif %}

{% endfor %}{% endif %}{% if semantic.deleted %}Notes removed from state (no longer present): {{ semantic.deleted | map:item => "`${item}`" | join:", " }}

{% endif %}## Extraction proposals (pending review) ({{ semantic.atoms_proposed }})
{% if semantic.proposals %}{% for e in semantic.proposals %}- `{{ e.proposalId }}` — **{{ e.title }}** ({{ e.tags | map:item => "`${item}`" | join:", " ?? "(untyped)" }}) ← `{{ e.source }}`
  - {{ e.reason }}
  - accept: `just proposal accept {{ e.proposalId }}` · reject: `just proposal reject {{ e.proposalId }}`
{% endfor %}{% else %}(none)

{% endif %}

{% if semantic.failures or semantic.state_errors %}## Failures

{% for f in semantic.failures %}- `{{ f.path }}`: {{ f.error }}
{% endfor %}{% for e in semantic.state_errors %}- state: {{ e }}
{% endfor %}

{% endif %}{% endif %}{% endif %}{% if backup %}## Backup

- {{ backup }}
{% endif %}{% if obsidian %}## Obsidian

- {{ obsidian }}
{% endif %}
