"""Deterministic vault edits. Every write re-verifies the source fingerprint
immediately before writing so a concurrent user edit is never clobbered.
"""
import json
import re
import subprocess
import tempfile
from pathlib import Path

from . import config, state


class StaleError(RuntimeError):
    pass


def _read_checked(vault: Path, rel: str, expected_fp: str) -> str:
    p = vault / rel
    data = p.read_bytes()
    if state.fingerprint(data) != expected_fp:
        raise StaleError(f"changed on disk since analysis: {rel}")
    return data.decode("utf-8", "replace")


def _write(vault: Path, rel: str, content: str) -> None:
    (vault / rel).write_text(content, encoding="utf-8")


def _tags_block(text: str):
    """Locate the frontmatter tags list.

    Returns (end, existing, tags_idx, last_item_idx): `end` indexes the '\\n'
    that opens the closing '---' line; `existing` is the set of tags present;
    `tags_idx` the index of the 'tags:' key within the frontmatter (between
    the delimiters) or -1; `last_item_idx` the index of the block's last line
    (-1 when the key has no items). None when there is no frontmatter.
    """
    if not text.startswith("---\n"):
        return None
    end = text.find("\n---", 4)
    if end == -1:
        return None
    fm = text[4:end].splitlines()
    existing = set()
    tags_idx = -1
    last_item = -1
    in_tags = False
    for i, line in enumerate(fm):
        if re.match(r"^tags:\s*$", line):
            in_tags = True
            if tags_idx == -1:
                tags_idx = i
            last_item = i
            continue
        if in_tags:
            m = re.match(r'^\s+-\s*"?([^"\n]+?)"?\s*$', line)
            if m:
                existing.add(m.group(1).lstrip("#"))
                last_item = i
                continue
            in_tags = False
    return end, existing, tags_idx, last_item


def apply_tags(text: str, new_tags):
    """Add tags to the frontmatter (additive only). Returns new text or None
    when nothing new would be added. New items always land inside the
    frontmatter: appended to the existing tags block, or in a fresh block
    inserted before the closing delimiter."""
    new_tags = [t for t in new_tags if t]
    if not new_tags:
        return None
    block = _tags_block(text)
    if block is None:
        items = "\n".join(f'  - "{t}"' for t in new_tags)
        return f"---\ntags:\n{items}\n---\n\n" + text
    end, existing, tags_idx, last_item = block
    todo = list(dict.fromkeys(t for t in new_tags if t not in existing))
    if not todo:
        return None
    head, rest = text[:end + 4], text[end + 4:]
    lines = head.splitlines()  # last element is the closing '---'
    items = [f'  - "{t}"' for t in todo]
    if tags_idx == -1:
        lines[len(lines) - 1:len(lines) - 1] = ["tags:"] + items
    else:
        # fm index -> lines index shifts by 1 for the opening '---'
        lines[last_item + 2:last_item + 2] = items
    return "\n".join(lines) + rest


def apply_tags_checked(vault: Path, rel: str, fp: str, new_tags) -> bool:
    """Apply tags with fingerprint re-check. Returns True when the file changed."""
    text = _read_checked(vault, rel, fp)
    new_text = apply_tags(text, new_tags)
    if new_text is None:
        return False
    _write(vault, rel, new_text)
    return True


def append_extracted_section(vault: Path, rel: str, fp: str, atom_title: str) -> bool:
    """Append the reciprocal link for an accepted extraction (idempotent)."""
    text = _read_checked(vault, rel, fp)
    line = f"- [[{atom_title}]]"
    if line in text:
        return False
    if re.search(r"^## Extracted\s*$", text, re.MULTILINE):
        if not text.endswith("\n"):
            text += "\n"
        new_text = text + line + "\n"
    else:
        if not text.endswith("\n"):
            text += "\n"
        new_text = text + "\n## Extracted\n" + line + "\n"
    _write(vault, rel, new_text)
    return True


def render_atom_markdown(note: dict, out_path: Path) -> None:
    """Render an ETK atom note to markdown via the deterministic Knap renderer."""
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
        json.dump(note, f)
        tmp = f.name
    try:
        r = subprocess.run(
            config.RENDER_CMD + [tmp, "-o", str(out_path)],
            capture_output=True, text=True, cwd=str(config.REPO_ROOT),
        )
        if r.returncode != 0:
            raise RuntimeError(f"etk render failed: {r.stderr.strip()[:300]}")
    finally:
        Path(tmp).unlink(missing_ok=True)


def find_atom_dir(vault: Path) -> str:
    """Existing atom folder if any, else the conventional home (created on write)."""
    conv = vault / "30_Knowledge" / "Atoms"
    if conv.is_dir():
        return conv.relative_to(vault).as_posix()
    for d in sorted(vault.rglob("*")):
        if d.is_dir() and re.search(r"atom", d.name, re.IGNORECASE):
            rel = d.relative_to(vault).as_posix()
            if not any(rel.startswith(p + "/") or rel == p for p in config.SKIP_PREFIXES):
                return rel
    return "30_Knowledge/Atoms"


def slugify(s: str) -> str:
    s = re.sub(r"[^\w\s-]", "", s, flags=re.UNICODE).strip().lower()
    return re.sub(r"[\s_-]+", "-", s)[:60] or "atom"
