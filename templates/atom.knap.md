---
{{ fm | yaml }}
---

# {{ title | trim }}

{{ body | trim }}
{% if links %}

### Links
{% for l in links %}- {{ l | wikilink }}
{% endfor %}
{% endif %}{% if relations %}

### Relations
{% for r in relations %}{{ r.type }}:: {{ r.target | wikilink }}
{% endfor %}
{% endif %}
