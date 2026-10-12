"""Consolidation pass: typed relations between existing atoms.

The model proposes; code decides. A relation is only recorded when both
endpoints are accepted atoms, the type is an established relation type,
and the same relation is not already on record. Proposals live in their
own envelope dir (99_Machine/wattson/relations) and go through the same
explicit accept/reject workflow as atom extractions.
"""
import hashlib
import json
import re
from pathlib import Path

from . import apply, config
from .semantics import RELATION_TYPES, existing_tags, note_title

RELATION_DIR = "99_Machine/wattson/relations"
BATCH_SIZE = 20
BODY_LIMIT = 400
MAX_PER_SOURCE = 3

RELATION_LINE_RE = re.compile(r"^([a-z-]+):: \[\[(.+?)\]\]\s*$")
RELATION_ID_RE = re.compile(r"^rel-[a-z0-9-]+-[0-9a-f]{8}$")


class RelationError(Exception):
    pass


def load_atoms(vault: Path):
    """All accepted atoms: [{title, path, tags, body}] in stable path order."""
    atom_dir = apply.find_atom_dir(vault)
    root = vault / atom_dir
    if not root.is_dir():
        return []
    out = []
    for p in sorted(root.rglob("*.md")):
        text = p.read_text(encoding="utf-8")
        m = re.search(r"^#\s+(.+)$", text, re.MULTILINE)
        if not m:
            continue
        title = m.group(1).strip()
        body = text[m.end():]
        body = body.split("\n### ")[0].strip()[:BODY_LIMIT]
        out.append({
            "title": title,
            "path": p.relative_to(vault).as_posix(),
            "tags": existing_tags(text),
            "body": body,
        })
    return out


def recorded_relations(vault: Path):
    """(source_title, target_title, type) triples already written in atom files."""
    out = set()
    atom_dir = apply.find_atom_dir(vault)
    root = vault / atom_dir
    if not root.is_dir():
        return out
    for p in sorted(root.rglob("*.md")):
        text = p.read_text(encoding="utf-8")
        m = re.search(r"^#\s+(.+)$", text, re.MULTILINE)
        if not m:
            continue
        title = m.group(1).strip()
        sec = re.search(r"^### Relations\s*$", text, re.MULTILINE)
        if not sec:
            continue
        nxt = re.search(r"^### ", text[sec.end():], re.MULTILINE)
        section = text[sec.end():sec.end() + (nxt.start() if nxt else len(text))]
        for line in section.splitlines():
            r = RELATION_LINE_RE.match(line.strip())
            if not r:
                continue
            raw = r.group(2)
            target = raw.split("|", 1)[1] if "|" in raw else raw
            out.add((title, target.strip(), r.group(1)))
    return out


def relation_id(source: str, target: str, rtype: str) -> str:
    h = hashlib.sha1(f"{source}|{target}|{rtype}".encode("utf-8", "replace")).hexdigest()[:8]
    return f"rel-{apply.slugify(source)}-{apply.slugify(target)}-{rtype}-{h}"


def envelope_path(vault: Path, rid: str) -> Path:
    return vault / RELATION_DIR / f"{rid}.json"


def make_envelope(rid, relation, batch) -> dict:
    return {
        "source": {"kind": "relations", "batch": batch},
        "proposals": [{
            "proposalId": rid,
            "status": "pending_review",
            "relation": {
                "source": relation["source"],
                "target": relation["target"],
                "type": relation["type"],
                "reason": relation["reason"],
            },
        }],
    }


def validate_envelope(env: dict) -> None:
    if not isinstance(env, dict) or env.get("source", {}).get("kind") != "relations":
        raise ValueError("malformed relation envelope")
    for p in env.get("proposals") or []:
        if not RELATION_ID_RE.match(p.get("proposalId", "")):
            raise ValueError("bad relation proposalId")
        r = p.get("relation") or {}
        if not r.get("source") or not r.get("target"):
            raise ValueError("relation needs source and target")
        if r.get("type") not in RELATION_TYPES:
            raise ValueError(f"bad relation type: {r.get('type')!r}")


def save_envelope(vault: Path, env: dict) -> None:
    validate_envelope(env)
    p = envelope_path(vault, env["proposals"][0]["proposalId"])
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(env, indent=1) + "\n", encoding="utf-8")


def load_envelope(vault: Path, rid: str) -> dict:
    p = envelope_path(vault, rid)
    if not p.exists():
        raise FileNotFoundError(f"unknown relation proposal: {rid}")
    return json.loads(p.read_text(encoding="utf-8"))


def list_relations(vault: Path) -> list:
    rows = []
    d = vault / RELATION_DIR
    if not d.is_dir():
        return rows
    for p in sorted(d.glob("*.json")):
        try:
            env = json.loads(p.read_text(encoding="utf-8"))
            validate_envelope(env)
        except (ValueError, json.JSONDecodeError):
            continue
        for prop in env.get("proposals") or []:
            r = prop.get("relation") or {}
            rows.append({
                "id": prop.get("proposalId"),
                "status": prop.get("status"),
                "source": r.get("source", ""),
                "target": r.get("target", ""),
                "type": r.get("type", ""),
            })
    return rows


def build_prompt(batch, corpus_titles) -> str:
    atom_blocks = []
    for a in batch:
        atom_blocks.append(
            f"--- ATOM: {a['title']} ---\n"
            f"tags: {', '.join(a['tags']) or '(none)'}\n"
            f"{a['body']}\n--- END ---"
        )
    return f"""You are consolidating a vault of concept atoms into a knowledge graph.

CORPUS (all accepted atom titles; relation targets MUST be an exact match from this list):
{json.dumps(corpus_titles, indent=0)}

BATCH (the atoms you are relating; each "source" below must be one of these, exactly):
{chr(10).join(atom_blocks)}

JOB: propose typed relations FROM batch atoms TO any atom in the corpus.
- "type" must be one of: {", ".join(sorted(RELATION_TYPES))}
  (supports, contradicts, applies-to and derived-from are directional; "cites" means the source atom quotes/references the target; "related" is a weak catch-all and should be rare)
- 0-{MAX_PER_SOURCE} relations per batch atom. Most batch atoms have 0 or 1.
- Only propose a relation when the connection is clear from the atom content. Never invent content.
- "source" and "target" are atom titles, exactly as listed. Never relate an atom to itself.

Reply with ONLY a JSON object, no markdown fences:
{{"relations": [{{"source": "...", "target": "...", "type": "...", "reason": "one sentence"}}],
  "summary": "one sentence on the connections found in this batch"}}"""


def validate(raw, batch_titles, corpus_titles, existing) -> tuple:
    """Deterministically screen model output. Returns (proposals, skipped)."""
    props, skipped, seen, per_source = [], [], set(), {}
    if not isinstance(raw, dict):
        return props, [{"why": "model reply was not a JSON object"}]
    for r in raw.get("relations") or []:
        if not isinstance(r, dict):
            continue
        src = str(r.get("source", "")).strip()
        tgt = str(r.get("target", "")).strip()
        rtype = str(r.get("type", "")).strip()
        reason = str(r.get("reason") or "")[:200]
        why = None
        if src not in batch_titles:
            why = f"source {src!r} is not in this batch"
        elif tgt not in corpus_titles:
            why = f"target {tgt!r} is not an accepted atom"
        elif src == tgt:
            why = "self relation"
        elif rtype not in RELATION_TYPES:
            why = f"unknown relation type {rtype!r}"
        elif (src, tgt, rtype) in existing:
            why = "relation already on record"
        elif (src, tgt, rtype) in seen:
            why = "duplicate in this reply"
        elif per_source.get(src, 0) >= MAX_PER_SOURCE:
            why = f"more than {MAX_PER_SOURCE} relations for this source"
        else:
            seen.add((src, tgt, rtype))
            per_source[src] = per_source.get(src, 0) + 1
            props.append({"source": src, "target": tgt, "type": rtype, "reason": reason})
        if why:
            skipped.append({"source": src, "target": tgt, "type": rtype, "why": why})
    return props, skipped


def atom_file(vault: Path, atoms_by_title, title: str) -> Path:
    a = atoms_by_title.get(title)
    if not a:
        raise RelationError(f"atom not found: {title}")
    return vault / a["path"]


def _append_relation_line(text: str, line: str) -> str:
    m = re.search(r"^### Relations\s*$", text, re.MULTILINE)
    if not m:
        return text.rstrip("\n") + "\n\n### Relations\n" + line + "\n"
    nxt = re.search(r"^### ", text[m.end():], re.MULTILINE)
    if nxt:  # not the last section: insert at the end of the section
        pos = m.end() + nxt.start()
        while pos > m.end() and text[pos - 1] == "\n":
            pos -= 1
        return text[:pos] + "\n" + line + text[pos:]
    return text.rstrip("\n") + "\n" + line + "\n"


def accept(vault: Path, rid: str) -> dict:
    """Accept a pending relation: record it in the source atom's Relations
    section. Returns {atom_path, line}."""
    env = load_envelope(vault, rid)
    prop = env["proposals"][0]
    if prop["status"] != "pending_review":
        raise RelationError(f"relation {rid} is {prop['status']}, not pending_review")
    rel = prop["relation"]
    atoms = load_atoms(vault)
    by_title = {a["title"]: a for a in atoms}
    src_p = atom_file(vault, by_title, rel["source"])
    tgt_p = atom_file(vault, by_title, rel["target"])
    line = f"{rel['type']}:: [[{apply.slugify(rel['target'])}|{rel['target']}]]"
    text = src_p.read_text(encoding="utf-8")
    if line in text:
        raise RelationError(f"relation already recorded: {line}")
    src_p.write_text(_append_relation_line(text, line), encoding="utf-8")
    prop["status"] = "accepted"
    save_envelope(vault, env)
    return {"atom_path": src_p.relative_to(vault).as_posix(),
            "target_path": tgt_p.relative_to(vault).as_posix(), "line": line}


def reject(vault: Path, rid: str) -> None:
    env = load_envelope(vault, rid)
    prop = env["proposals"][0]
    if prop["status"] != "pending_review":
        raise RelationError(f"relation {rid} is {prop['status']}, not pending_review")
    prop["status"] = "rejected"
    save_envelope(vault, env)
