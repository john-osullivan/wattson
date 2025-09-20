from __future__ import annotations
from dataclasses import dataclass
import pathlib, frontmatter

@dataclass
class Proposal:
    path: str
    changes: dict  # frontmatter fields to set/update

class IntakeTriage:
    """Classify new notes, seed minimal frontmatter, extract tasks (non-prose)."""

    def run(self, path: str) -> Proposal:
        p = pathlib.Path(path)
        fm = frontmatter.load(p)
        meta = fm.metadata or {}
        if "type" not in meta:
            meta["type"] = "fleeting"
        # Add other safe fields, never edit body
        return Proposal(path=str(p), changes=meta)
