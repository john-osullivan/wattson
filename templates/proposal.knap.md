# Proposals — `{{ source.path }}`

- source fingerprint: `{{ source.fingerprint }}`

{% for p in proposals %}## {{ p.proposalId }}

- status: `{{ p.status }}`
- note: {{ p.note.noteType }}
- created: {{ p.note.created }}

### {{ p.note.title }}

- tags: {{ p.note.tags | map:item => "`${item}`" | join:", " ?? "(untyped)" }}

{{ p.note.body | trim }}
{% if p.note.links %}

### Links
{% for l in p.note.links %}- {{ l | wikilink }}
{% endfor %}
{% endif %}{% if p.note.relations %}

### Relations
{% for r in p.note.relations %}{{ r.type }}:: {{ r.target | wikilink }}
{% endfor %}
{% endif %}
- accept: `just proposal accept {{ p.proposalId }}`
- reject: `just proposal reject {{ p.proposalId }}`

{% endfor %}
