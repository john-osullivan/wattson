from __future__ import annotations
import re, yaml, pathlib, frontmatter
from dataclasses import dataclass

ONTO = pathlib.Path(__file__).resolve().parents[2] / "ontology"

@dataclass
class TagProposal:
    path: str
    add_tags: list[str]

def _canonical(term: str, normalize: dict[str,str]) -> str|None:
    t = re.sub(r"[^a-z0-9]+", " ", term.lower()).strip()
    return normalize.get(t)

def propose_tags(path: str) -> TagProposal:
    with open(ONTO / "alias-index.yaml", "r", encoding="utf-8") as f:
        alias = yaml.safe_load(f)["normalize"]
    with open(ONTO / "tag-lexicon.yaml", "r", encoding="utf-8") as f:
        tmap = yaml.safe_load(f)["tag_map"]

    note = frontmatter.load(path)
    text = (note.content or "") + " " + " ".join(map(str, (note.metadata or {}).values()))
    candidates = set(re.findall(r"[A-Za-z][A-Za-z0-9\-\s]{2,}", text))
    tokens = filter(None, (_canonical(c, alias) for c in candidates))
    tags = set()
    for tok in tokens:
        tags.update(tmap.get(tok, []))
    return TagProposal(path=path, add_tags=sorted(tags))
