"""Durable sidecar state: per-note fingerprints and processing status.

Stored in the vault at 99_Machine/wattson/state.json (machine-owned, committed
like any other agent output). A note counts as processed only after its
fingerprint is persisted here.
"""
import hashlib
import json
import os
import tempfile
from pathlib import Path

from . import config

STATE_VERSION = 1


def fingerprint(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def empty_state():
    return {"version": STATE_VERSION, "notes": {}}


def load_state(vault: Path) -> dict:
    p = vault / config.STATE_FILE
    if not p.exists():
        return empty_state()
    try:
        with open(p) as f:
            state = json.load(f)
    except (json.JSONDecodeError, OSError):
        return empty_state()
    if not isinstance(state, dict) or "notes" not in state:
        return empty_state()
    return state


def save_state(vault: Path, state: dict) -> None:
    p = vault / config.STATE_FILE
    p.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(p.parent), prefix=".state-", suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(state, f, indent=1, sort_keys=True)
            f.write("\n")
        os.replace(tmp, p)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def note_entry(state: dict, path: str) -> dict:
    return state["notes"].get(path, {})


def record_processed(state: dict, path: str, fp: str, text: str) -> None:
    state["notes"][path] = {
        "fingerprint": fp,
        "last_text": text if len(text) <= config.LAST_TEXT_LIMIT else "",
        "truncated": len(text) > config.LAST_TEXT_LIMIT,
        "status": "processed",
    }


def record_failed(state: dict, path: str, fp: str, text: str, error: str) -> None:
    e = state["notes"].get(path, {})
    state["notes"][path] = {
        "fingerprint": e.get("fingerprint"),  # keep old fp: retry next run
        "last_text": e.get("last_text", ""),
        "truncated": e.get("truncated", False),
        "status": "failed",
        "last_error": error[:500],
    }


def record_deleted(state: dict, path: str) -> None:
    state["notes"].pop(path, None)
