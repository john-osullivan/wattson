"""Integration: full structural digest runs against a temp vault.

Proves the 'You' section attributes only user (non-agent) changes, agent
edits land in the 'Agent since last digest' section, and 99_Machine/ bookkeeping
never leaks into either.
"""
import json
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "vault_digest.py"

USER = ("John Osullivan", "john.osullivan42@gmail.com")
AGENT = ("WATTSON Agent", "agent@wattson.local")


def git(vault, *args, identity=USER):
    cmd = ["git", "-C", str(vault)]
    if identity:
        cmd += ["-c", f"user.name={identity[0]}", "-c", f"user.email={identity[1]}"]
    cmd += [str(a) for a in args]
    r = subprocess.run(cmd, capture_output=True, text=True)
    assert r.returncode == 0, f"git {' '.join(args)}: {r.stderr}"
    return r.stdout.strip()


def run_digest(vault, tmp_path, *extra):
    env = dict(os.environ, WATTSON_DIGEST_LOCK=str(tmp_path / "digest.lock"))
    r = subprocess.run([sys.executable, str(SCRIPT), "--vault", str(vault), *extra],
                       capture_output=True, text=True, env=env, cwd=str(REPO_ROOT))
    assert r.returncode == 0, f"digest failed: {r.stderr}\n{r.stdout}"
    return r.stdout


def latest_doc(vault):
    d = vault / "99_Machine" / "digest"
    latest = sorted(d.glob("*.json"))[-1]
    return json.loads(latest.read_text(encoding="utf-8"))


def section(doc, title):
    for s in doc["changes"]:
        if s["title"] == title:
            return [p for g in s["groups"] for p in g["paths"]]
    raise KeyError(title)


def test_you_section_excludes_agent_edits(tmp_path):
    v = tmp_path / "vault"
    v.mkdir()
    (v / ".git").mkdir()
    git(v, "init", "-q", "-b", "main")
    git(v, "config", "user.name", USER[0])
    git(v, "config", "user.email", USER[1])
    # a baseline commit so the repo has a HEAD (a real vault always does)
    (v / "README.md").write_text("vault\n")
    git(v, "add", "-A"); git(v, "commit", "-q", "-m", "init")

    (v / "00_Inbox").mkdir()
    (v / "00_Inbox/a.md").write_text("hello world\n")
    # left uncommitted: this is the fresh sync state the first digest checkpoints

    # digest 1 (baseline: no checkpoint yet -> everything is new user content)
    run_digest(v, tmp_path, "--skip-semantic")
    doc1 = latest_doc(v)
    assert "00_Inbox/a.md" in section(doc1, "Added")
    assert doc1["since"] == "baseline"

    # agent tags a note and commits it as an agent change
    (v / "00_Inbox/a.md").write_text("---\ntags:\n  - \"area/x\"\n---\nhello world\n")
    git(v, "add", "-A"); git(v, "commit", "-q",
                             "-m", "agent: digest manual-20261012-000000 changes (1 tagged, 0 proposals)",
                             identity=AGENT)

    # user adds another note (uncommitted = fresh sync state)
    (v / "00_Inbox/b.md").write_text("new note\n")

    # digest 2: 'You' must show only the user's new note
    run_digest(v, tmp_path, "--skip-semantic")
    doc2 = latest_doc(v)
    added, modified = section(doc2, "Added"), section(doc2, "Modified")
    assert "00_Inbox/b.md" in added
    assert "00_Inbox/a.md" not in added and "00_Inbox/a.md" not in modified
    all_paths = [p for s in doc2["changes"] for g in s["groups"] for p in g["paths"]]
    assert not any(p.startswith("99_Machine/") for p in all_paths)
    # agent edit reported in the agent section
    assert len(doc2["agent_commits"]) == 1
    assert "00_Inbox/a.md" in doc2["agent_commits"][0]["paths"]

    # digest 3: nothing new -> empty 'You', no agent commits since last digest
    run_digest(v, tmp_path, "--skip-semantic")
    doc3 = latest_doc(v)
    assert doc3["changed_total"] == 0
    assert doc3["agent_commits"] == []
