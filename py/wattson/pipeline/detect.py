"""Vault scanning and change classification against sidecar state."""
from pathlib import Path

from . import config, state


def scan_vault(vault: Path) -> dict:
    """Map relpath (posix) -> (bytes, fingerprint) for processable notes."""
    out = {}
    for p in sorted(vault.rglob("*.md")):
        rel = p.relative_to(vault).as_posix()
        if any(rel == pref or rel.startswith(pref + "/") for pref in config.SKIP_PREFIXES):
            continue
        try:
            data = p.read_bytes()
        except OSError:
            continue
        out[rel] = (data, state.fingerprint(data))
    return out


def classify(vault: Path, st: dict) -> dict:
    """Split scanned notes into added / modified / deleted vs state.

    modified entries carry `append_only` (true when the new text is the old
    text with content appended to the end) and `text`.
    """
    scan = scan_vault(vault)
    notes = st.get("notes", {})
    added, modified, deleted = [], [], []
    for rel, (data, fp) in scan.items():
        entry = notes.get(rel)
        if entry is None:
            added.append({"path": rel, "fingerprint": fp, "text": data.decode("utf-8", "replace")})
        elif entry.get("fingerprint") != fp:
            old_text = entry.get("last_text", "")
            text = data.decode("utf-8", "replace")
            append_only = (not entry.get("truncated")) and bool(old_text) and text.startswith(old_text)
            modified.append({"path": rel, "fingerprint": fp, "text": text, "append_only": append_only})
    for rel in notes:
        if rel not in scan:
            deleted.append(rel)
    return {
        "scan_count": len(scan),
        "added": sorted(added, key=lambda n: n["path"]),
        "modified": sorted(modified, key=lambda n: n["path"]),
        "deleted": sorted(deleted),
    }
