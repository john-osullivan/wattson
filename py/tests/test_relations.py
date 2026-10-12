"""Relations pass tests: atom corpus loading, prompt screening, envelope
lifecycle, and accept/reject behavior."""
import json
import subprocess
from pathlib import Path

import pytest

from wattson.pipeline import apply, relations

ATOM_A = """---
tags:
  - "area/tech/programming"
  - "type/atom"
created: "2026-10-12"
---

# Gall's Law

You can't start with the final, working version of something. You have to start with something that doesn't work.

### Links
- [[Quotes]]

### Relations
derived-from:: [[Quotes]]
"""

ATOM_B = """---
tags:
  - "area/tech/fintech"
  - "type/atom"
created: "2026-10-12"
---

# API Learning Loop

Short build-measure-learn cycles are the fastest way to learn an API.
"""

ATOM_C = """---
tags:
  - "area/tech/ai"
  - "type/atom"
created: "2026-10-12"
---

# Eval-First AI

Write the eval before the model; the eval is the spec.
"""


def git(vault, *args, identity=("T", "t@t.local")):
    cmd = ["git", "-C", str(vault)]
    if identity:
        cmd += ["-c", f"user.name={identity[0]}", "-c", f"user.email={identity[1]}"]
    cmd += [str(a) for a in args]
    r = subprocess.run(cmd, capture_output=True, text=True)
    assert r.returncode == 0, f"git {' '.join(args)}: {r.stderr}"
    return r.stdout.strip()


@pytest.fixture
def vault(tmp_path):
    v = tmp_path / "vault"
    v.mkdir()
    (v / ".git").mkdir()
    git(v, "init", "-q", "-b", "main")
    git(v, "config", "user.name", "T")
    git(v, "config", "user.email", "t@t.local")
    return v


def add_atom(vault, rel, text):
    p = vault / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text)
    return p


def test_load_atoms_parses_title_tags_body(vault):
    add_atom(vault, "30_Knowledge/Atoms/galls-law.md", ATOM_A)
    add_atom(vault, "30_Knowledge/Atoms/api-learning-loop.md", ATOM_B)
    atoms = relations.load_atoms(vault)
    assert [a["title"] for a in atoms] == ["API Learning Loop", "Gall's Law"]
    a = atoms[1]
    assert "type/atom" in a["tags"] and "area/tech/programming" in a["tags"]
    assert a["body"].startswith("You can't start")
    assert "### Links" not in a["body"]


def test_validate_screens_model_output(vault):
    add_atom(vault, "30_Knowledge/Atoms/galls-law.md", ATOM_A)
    add_atom(vault, "30_Knowledge/Atoms/api-learning-loop.md", ATOM_B)
    add_atom(vault, "30_Knowledge/Atoms/eval-first-ai.md", ATOM_C)
    corpus = ["Gall's Law", "API Learning Loop", "Eval-First AI"]
    batch = ["Gall's Law", "API Learning Loop"]
    raw = {"relations": [
        {"source": "Gall's Law", "target": "Eval-First AI", "type": "related", "reason": "r"},
        {"source": "Gall's Law", "target": "No Such Atom", "type": "related", "reason": "r"},
        {"source": "Gall's Law", "target": "Gall's Law", "type": "related", "reason": "r"},
        {"source": "Gall's Law", "target": "Eval-First AI", "type": "vibes", "reason": "r"},
        {"source": "Not In Batch", "target": "Eval-First AI", "type": "related", "reason": "r"},
        {"source": "API Learning Loop", "target": "Gall's Law", "type": "applies-to", "reason": "r"},
        {"source": "Gall's Law", "target": "Eval-First AI", "type": "related", "reason": "dup"},
    ]}
    props, skips = relations.validate(raw, batch, corpus, set())
    assert [(p["source"], p["target"], p["type"]) for p in props] == [
        ("Gall's Law", "Eval-First AI", "related"),
        ("API Learning Loop", "Gall's Law", "applies-to"),
    ]
    assert len(skips) == 5
    assert any("not an accepted atom" in s["why"] for s in skips)
    assert any("self relation" in s["why"] for s in skips)
    assert any("unknown relation type" in s["why"] for s in skips)
    assert any("not in this batch" in s["why"] for s in skips)
    assert any("duplicate" in s["why"] for s in skips)


def test_validate_enforces_existing_and_per_source_cap():
    corpus = ["A", "B", "C", "D", "E"]
    raw = {"relations": [
        {"source": "A", "target": "B", "type": "related", "reason": "already"},
        {"source": "A", "target": "C", "type": "related", "reason": "ok1"},
        {"source": "A", "target": "D", "type": "related", "reason": "ok2"},
        {"source": "A", "target": "E", "type": "related", "reason": "ok3"},
        {"source": "A", "target": "C", "type": "supports", "reason": "over cap"},
    ]}
    props, skips = relations.validate(raw, ["A"], corpus, {("A", "B", "related")})
    assert [p["target"] for p in props] == ["C", "D", "E"]
    assert any("already on record" in s["why"] for s in skips)
    assert any("more than 3" in s["why"] for s in skips)


def test_relation_id_stable_and_unique():
    i1 = relations.relation_id("Gall's Law", "Eval-First AI", "related")
    i2 = relations.relation_id("Gall's Law", "Eval-First AI", "related")
    i3 = relations.relation_id("Gall's Law", "Eval-First AI", "supports")
    assert i1 == i2 and i1 != i3
    assert i1.startswith("rel-") and relations.RELATION_ID_RE.match(i1)


def _pending(vault, src, tgt, rtype="related"):
    rid = relations.relation_id(src, tgt, rtype)
    relations.save_envelope(vault, relations.make_envelope(
        rid, {"source": src, "target": tgt, "type": rtype, "reason": "test"}, [src]))
    return rid


def test_accept_appends_relation_line(vault):
    add_atom(vault, "30_Knowledge/Atoms/galls-law.md", ATOM_A)
    add_atom(vault, "30_Knowledge/Atoms/eval-first-ai.md", ATOM_C)
    rid = _pending(vault, "Gall's Law", "Eval-First AI", "supports")
    out = relations.accept(vault, rid)
    text = (vault / out["atom_path"]).read_text()
    line = "supports:: [[eval-first-ai|Eval-First AI]]"
    assert line in text
    # line lands inside the Relations section, after the existing derived-from
    rel_section = text.split("### Relations", 1)[1]
    assert rel_section.index("derived-from::") < rel_section.index(line)
    assert relations.load_envelope(vault, rid)["proposals"][0]["status"] == "accepted"
    with pytest.raises(relations.RelationError):
        relations.accept(vault, rid)


def test_accept_creates_relations_section_when_missing(vault):
    add_atom(vault, "30_Knowledge/Atoms/api-learning-loop.md", ATOM_B)
    add_atom(vault, "30_Knowledge/Atoms/galls-law.md", ATOM_A)
    rid = _pending(vault, "API Learning Loop", "Gall's Law", "derived-from")
    out = relations.accept(vault, rid)
    text = (vault / out["atom_path"]).read_text()
    assert text.rstrip().endswith("derived-from:: [[galls-law|Gall's Law]]")
    assert "### Relations" in text


def test_accept_rejects_duplicate_line_and_missing_atoms(vault):
    add_atom(vault, "30_Knowledge/Atoms/galls-law.md", ATOM_A)
    add_atom(vault, "30_Knowledge/Atoms/eval-first-ai.md", ATOM_C)
    rid = _pending(vault, "Gall's Law", "Eval-First AI")
    # simulate the line already being on record
    p = vault / "30_Knowledge/Atoms/galls-law.md"
    p.write_text(p.read_text() + "\nrelated:: [[eval-first-ai|Eval-First AI]]\n")
    with pytest.raises(relations.RelationError, match="already recorded"):
        relations.accept(vault, rid)

    rid2 = _pending(vault, "Gall's Law", "Missing Atom")
    with pytest.raises(relations.RelationError, match="not found"):
        relations.accept(vault, rid2)


def test_recorded_relations_parses_alias_links(vault):
    add_atom(vault, "30_Knowledge/Atoms/galls-law.md",
             ATOM_A + "related:: [[eval-first-ai|Eval-First AI]]\n")
    add_atom(vault, "30_Knowledge/Atoms/api-learning-loop.md", ATOM_B)
    rec = relations.recorded_relations(vault)
    assert ("Gall's Law", "Quotes", "derived-from") in rec
    assert ("Gall's Law", "Eval-First AI", "related") in rec
    assert not any(t == "API Learning Loop" for (_, t, _) in rec)


def test_envelope_reject_and_list(vault):
    add_atom(vault, "30_Knowledge/Atoms/galls-law.md", ATOM_A)
    add_atom(vault, "30_Knowledge/Atoms/eval-first-ai.md", ATOM_C)
    rid = _pending(vault, "Gall's Law", "Eval-First AI")
    rows = relations.list_relations(vault)
    assert rows[0]["id"] == rid and rows[0]["status"] == "pending_review"
    relations.reject(vault, rid)
    assert relations.load_envelope(vault, rid)["proposals"][0]["status"] == "rejected"
    with pytest.raises(relations.RelationError):
        relations.reject(vault, rid)
    rows = relations.list_relations(vault)
    assert rows[0]["status"] == "rejected"


def test_validate_envelope_rejects_bad_types(vault):
    env = relations.make_envelope(
        relations.relation_id("A", "B", "vibes"),
        {"source": "A", "target": "B", "type": "vibes", "reason": "x"}, ["A"])
    with pytest.raises(ValueError):
        relations.save_envelope(vault, env)
