---
{{ fm | yaml }}
---

# {{ title | trim }}

{{ body | trim }}
{% if tasks %}

### Tasks
{% for t in tasks %}- {% if t.done %}[x]{% else %}[ ]{% endif %} {{ t.text }}
{% endfor %}
{% endif %}{% if links %}

### Links
{% for l in links %}- {{ l | wikilink }}
{% endfor %}
{% endif %}{% if relations %}

### Relations
{% for r in relations %}{{ r.type }}:: {{ r.target | wikilink }}
{% endfor %}
{% endif %}
