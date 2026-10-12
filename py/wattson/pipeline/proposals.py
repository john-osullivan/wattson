"""Extraction proposals: durable, reviewable, explicit-accept workflow.

One JSON envelope per proposal at 99_Machine/wattson/proposals/<id>.json.
Accepting re-verifies the source fingerprint, renders the atom with the
deterministic Knap renderer, and adds the reciprocal link in the source note.
"""
import hashlib
import json
import re
from datetime import date
from pathlib import Path

from . import apply, config, semantics, state

PROPOSAL_ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")


def proposal_id(title: str, body: str) -> str:
    h = hashlib.sha1(body.encode("utf-8", "replace")).hexdigest()[:8]
    pid = f"atom-{apply.slugify(title)}-{h}"
    pid = pid[:64]
    assert PROPOSAL_ID_RE.match(pid), pid
    return pid


def envelope_path(vault: Path, pid: str) -> Path:
    return vault / config.PROPOSAL_DIR / f"{pid}.json"


def make_envelope(pid, source_path, source_fp, extraction, source_title) -> dict:
    tags = ["type/atom"] + [t for t in extraction["tags"] if t != "type/atom"][:3]
    note = {
        "noteType": "atom",
        "title": extraction["title"],
        "body": extraction["body"],
        "tags": tags,
        "links": [source_title],
        "relations": [{"type": "derived-from", "target": source_title}],
        "created": date.today().isoformat(),
    }
    return {
        "source": {"path": source_path, "fingerprint": source_fp},
        "proposals": [
            {
                "proposalId": pid,
                "status": "pending_review",
                "note": note,
            }
        ],
    }


def validate_envelope(env: dict) -> None:
    if not isinstance(env, dict) or "source" not in env or "proposals" not in env:
        raise ValueError("malformed proposal envelope")
    src = env["source"]
    if not isinstance(src.get("fingerprint"), str) or not re.match(r"^[0-9a-f]{16,64}$", src["fingerprint"]):
        raise ValueError("bad source fingerprint")
    for p in env["proposals"]:
        if not PROPOSAL_ID_RE.match(p.get("proposalId", "")):
            raise ValueError("bad proposalId")
        n = p["note"]
        if n.get("noteType") != "atom" or not n.get("title") or not n.get("body"):
            raise ValueError("bad atom note")
        if not n.get("tags") or "type/atom" not in n["tags"]:
            raise ValueError("atom note must carry type/atom")
        if not re.match(r"^\d{4}-\d{2}-\d{2}$", n.get("created", "")):
            raise ValueError("bad created date")


def save_envelope(vault: Path, env: dict) -> None:
    validate_envelope(env)
    p = envelope_path(vault, env["proposals"][0]["proposalId"])
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(env, indent=1) + "\n", encoding="utf-8")


def load_envelope(vault: Path, pid: str) -> dict:
    p = envelope_path(vault, pid)
    if not p.exists():
        raise FileNotFoundError(f"unknown proposal: {pid}")
    return json.loads(p.read_text(encoding="utf-8"))


def list_proposals(vault: Path) -> list:
    d = vault / config.PROPOSAL_DIR
    if not d.is_dir():
        return []
    out = []
    for p in sorted(d.glob("*.json")):
        try:
            env = json.loads(p.read_text(encoding="utf-8"))
            for prop in env["proposals"]:
                out.append({
                    "id": prop["proposalId"],
                    "status": prop["status"],
                    "title": prop["note"]["title"],
                    "source": env["source"]["path"],
                })
        except (json.JSONDecodeError, KeyError):
            continue
    return out


def accept(vault: Path, pid: str, render_fn=None) -> dict:
    """Accept a pending proposal. Returns {atom_path, source_path}. Never raises
    on stale source: raises ProposalError with a clear message instead."""
    render_fn = render_fn or apply.render_atom_markdown
    env = load_envelope(vault, pid)
    prop = env["proposals"][0]
    if prop["status"] != "pending_review":
        raise ProposalError(f"proposal {pid} is {prop['status']}, not pending_review")
    src = env["source"]
    src_p = vault / src["path"]
    if not src_p.exists():
        raise ProposalError(f"source note no longer exists: {src['path']}")
    fp = state.fingerprint(src_p.read_bytes())
    if fp != src["fingerprint"]:
        raise ProposalError(
            f"source changed since the proposal was made ({src['path']}); "
            "reject this proposal and re-run the digest"
        )
    note = prop["note"]
    atom_dir = apply.find_atom_dir(vault)
    atom_name = apply.slugify(note["title"]) + ".md"
    atom_rel = f"{atom_dir}/{atom_name}"
    atom_p = vault / atom_rel
    if atom_p.exists():
        raise ProposalError(f"atom file already exists: {atom_rel}")
    atom_p.parent.mkdir(parents=True, exist_ok=True)
    render_fn(note, atom_p)
    changed = apply.append_extracted_section(vault, src["path"], fp, note["title"])
    prop["status"] = "accepted"
    save_envelope(vault, env)
    return {"atom_path": atom_rel, "source_path": src["path"], "source_changed": changed}


def reject(vault: Path, pid: str) -> None:
    env = load_envelope(vault, pid)
    prop = env["proposals"][0]
    if prop["status"] not in ("pending_review", "generated"):
        raise ProposalError(f"proposal {pid} is {prop['status']}, not pending_review")
    prop["status"] = "rejected"
    save_envelope(vault, env)


class ProposalError(RuntimeError):
    pass
