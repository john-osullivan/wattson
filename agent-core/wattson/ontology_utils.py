# Utilities for working with ontology/ontology.yaml
from __future__ import annotations
from typing import Dict, Iterable, List, Set, Tuple
from agent_core.wattson import tools  # re-use your single source of truth

def list_area_tags() -> List[str]:
    """All ETK area tags present anywhere in the ontology terms."""
    onto = tools.load_ontology()
    tags: Set[str] = set()
    for term in onto.get("terms", {}).values():
        tags.update(term.get("tags", []))
    return sorted(tags)

def list_terms() -> List[str]:
    """Canonical term keys as defined in ontology.yaml."""
    onto = tools.load_ontology()
    return sorted(onto.get("terms", {}).keys())

def aliases_by_term() -> Dict[str, List[str]]:
    """term -> aliases[] mapping (already normalized in file; no extra processing)."""
    onto = tools.load_ontology()
    out: Dict[str, List[str]] = {}
    for k, spec in (onto.get("terms", {}) or {}).items():
        out[k] = list(spec.get("aliases", []))
    return out

def invert_alias_index() -> Dict[str, List[str]]:
    """alias phrase -> [terms...] so one alias can trigger multiple terms."""
    idx: Dict[str, List[str]] = {}
    for term, aliases in aliases_by_term().items():
        for a in aliases:
            idx.setdefault(a.lower(), []).append(term)
    return idx

def validate_ontology(strict: bool = False) -> Tuple[bool, List[str]]:
    """Light checks: terms have aliases and tags; tags look like '#area/...'.
    Returns (ok, problems)."""
    problems: List[str] = []
    onto = tools.load_ontology()
    for term, spec in (onto.get("terms", {}) or {}).items():
        if not spec.get("aliases"):
            problems.append(f"term '{term}' has no aliases")
        t = spec.get("tags", [])
        if not t:
            problems.append(f"term '{term}' has no tags")
        for tag in t:
            if not tag.startswith("#area/"):
                problems.append(f"term '{term}' has non-area tag: {tag}")
    return (len(problems) == 0, problems)
