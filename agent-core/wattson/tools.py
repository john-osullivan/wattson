# agent-core/wattson/tools.py
from __future__ import annotations
import re, yaml, pathlib, frontmatter, json
from jsonschema import validate as js_validate, ValidationError

ONTO = pathlib.Path(__file__).resolve().parents[1] / "ontology" / "ontology.yaml"
SCHEMA = pathlib.Path(__file__).resolve().parents[1] / "schema" / "etk.schema.json"

def load_ontology() -> dict:
    """Return parsed ontology file."""
    return yaml.safe_load(ONTO.read_text(encoding="utf-8"))

def normalize_text(s: str) -> str:
    """Lowercase, strip punctuation to spaces, collapse."""
    return re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()

def deterministic_candidates(note_text: str, ontology: dict) -> list[str]:
    """Return union of tags for any term whose alias is a substring in note_text."""
    hay = normalize_text(note_text)
    tags = set()
    for _token, spec in ontology.get("terms", {}).items():
        aliases = [normalize_text(a) for a in spec.get("aliases", [])]
        if any(a in hay for a in aliases):
            tags.update(spec.get("tags", []))
    return sorted(tags)

def schema_validate_frontmatter(md_path: str) -> list[str]:
    """Validate a single Markdown note's frontmatter against ETK schema; return error list."""
    sch = json.loads(SCHEMA.read_text(encoding="utf-8"))
    note = frontmatter.load(md_path)
    try:
        js_validate(instance=note.metadata or {}, schema=sch)
        return []
    except ValidationError as e:
        return [f"{md_path}: {e.message}"]

def diff_budget(lines_changed: int, hunks: int, max_lines=200, max_hunks=50) -> bool:
    """Return True if within budget."""
    return (lines_changed <= max_lines) and (hunks <= max_hunks)
