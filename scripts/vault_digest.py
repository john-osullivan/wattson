#!/usr/bin/env python3
"""WATTSON vault digest (structural + intelligent semantic pass).

Commits user (phone/desktop) changes as `sync:` when a digest is requested,
then runs the semantic pipeline (established-tag tagging + atom extraction
proposals) on changed notes, writes a digest note, and commits it as
`agent:`. Agent-made vault changes must be committed by the agent itself with
an `agent:` prefix before a digest runs; anything left uncommitted at digest
time is attributed to the user.
"""
import argparse
import datetime
import fcntl
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "py"))
from wattson.pipeline import run as pipeline_run  # noqa: E402

AGENT_IDENTITY = ("WATTSON Agent", "agent@wattson.local")
USER_IDENTITY = ("John Osullivan", "john.osullivan42@gmail.com")
REQ_DIR = Path("99_Machine/digest/requests")
OUT_DIR = Path("99_Machine/digest")
INBOX_DIR = Path("00_Inbox")
LOCK = os.environ.get("WATTSON_DIGEST_LOCK", "/tmp/wattson-vault-digest.lock")


def git(vault, *args, identity=None):
    cmd = ["git", "-C", str(vault)]
    if identity:
        cmd += ["-c", f"user.name={identity[0]}", "-c", f"user.email={identity[1]}"]
    cmd += [str(a) for a in args]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"git {' '.join(map(str, args))} failed: {r.stderr.strip()}")
    return r.stdout.strip()


def find_marker(vault, request):
    if request:
        name = request if request.endswith(".md") else request + ".md"
        for d in (REQ_DIR, REQ_DIR / "processed"):
            p = vault / d / name
            if p.exists():
                return p
        sys.exit(f"marker not found: {name}")
    if not (vault / REQ_DIR).is_dir():
        return None
    pending = sorted(p for p in (vault / REQ_DIR).iterdir() if p.is_file())
    return pending[-1] if pending else None


def inbox_files(vault):
    root = vault / INBOX_DIR
    if not root.is_dir():
        return []
    return sorted(str(p.relative_to(vault)) for p in root.rglob("*") if p.is_file())


def section_changes(vault, prev, head):
    out = git(vault, "diff", "--name-status", "-M", f"{prev}..{head}")
    added, modified, deleted, renamed = [], [], [], []
    for line in out.splitlines():
        parts = line.split("\t")
        if len(parts) < 2:
            continue
        status, *names = parts
        if status.startswith("A"):
            added.append(names[-1])
        elif status.startswith("M"):
            modified.append(names[-1])
        elif status.startswith("D"):
            deleted.append(names[-1])
        elif status.startswith("R"):
            renamed.append(f"{names[0]} -> {names[1]}")
    return added, modified, deleted, renamed


def group_by_folder(paths):
    groups = {}
    for p in paths:
        top = p.split("/", 1)[0] if "/" in p else "(vault root)"
        groups.setdefault(top, []).append(p)
    return groups


def list_agent_commits(vault, prev, head):
    out = git(vault, "log", f"{prev}..{head}", "--name-status", "--pretty=format:@@@%h %s")
    commits = []
    cur = None
    for line in out.splitlines():
        if line.startswith("@@@"):
            cur = {"sha": line[3:].split(" ", 1)[0], "subject": line[3:].split(" ", 1)[1], "paths": []}
            commits.append(cur)
        elif cur is not None and line.strip():
            cur["paths"].append(line.split("\t")[-1])
    return [c for c in commits if c["subject"].startswith("agent:")]


def last_digest_commit(vault):
    # final digest-note commit only: "agent: digest <stamp>" (the "changes"
    # commits carry a trailing "changes (...)" and must not match)
    out = git(vault, "log", "-E", "--grep", r"^agent: digest [^ ]+$", "--format=%H", "-n", "1")
    return out or None


def last_sync_checkpoint(vault):
    out = git(vault, "log", "--grep", r"^sync: checkpoint", "--format=%H", "-n", "1")
    return out or None


def filter_user_changes(added, modified, deleted, renamed):
    """Drop agent-owned machine paths (99_Machine/) from the user-facing change
    lists; they are covered by the 'Agent since last digest' section."""
    drop = lambda lst: [p for p in lst if not p.startswith("99_Machine/")]
    return drop(added), drop(modified), drop(deleted), \
        [r for r in renamed if "99_Machine/" not in r]


def user_change_paths(vault, prev, head):
    """Paths changed by non-agent commits in prev..head — the user's sync state.
    Paths touched only by `agent:` commits are excluded (they are reported in
    the 'Agent since last digest' section instead)."""
    out = git(vault, "log", f"{prev}..{head}", "--name-only", "--pretty=format:@@@%s")
    paths, in_agent = set(), False
    for line in out.splitlines():
        if line.startswith("@@@"):
            in_agent = line[3:].startswith("agent:")
        elif line.strip() and not in_agent:
            paths.add(line)
    return paths


def _change_section(title, items):
    groups = group_by_folder(items)
    group_list = []
    for folder in sorted(groups):
        names = groups[folder]
        group_list.append({
            "folder": folder,
            "count": len(names),
            "root_single": len(names) == 1 and folder == "(vault root)",
            # Obsidian internals: report the count, not the file list
            "paths": [] if folder == ".obsidian" else names,
        })
    return {"title": title, "count": len(items), "groups": group_list}


def _semantic_doc(semantic):
    if semantic is None:
        return None
    d = semantic.to_dict()
    d["proposals"] = [e for n in d["notes"] for e in n["extractions"] if e.get("proposalId")]
    return d


def build_digest_doc(stamp, trigger, created, sync_sha, added, modified, deleted, renamed,
                     agent_commits, since_label, inbox, semantic=None, backup="", obsidian=""):
    """Pure: build the structured digest document (a dict). No I/O, deterministic."""
    return {
        "type": "wattson-digest",
        "digest-version": 1,
        "stamp": stamp,
        "created": created,
        "trigger": trigger,
        "since": since_label,
        "sync_sha": sync_sha,
        "changed_total": len(added) + len(modified) + len(deleted) + len(renamed),
        "changes": [
            _change_section("Added", added),
            _change_section("Modified", modified),
            _change_section("Deleted", deleted),
            _change_section("Renamed", renamed),
        ],
        "agent_commits": agent_commits,
        "inbox": inbox,
        "semantic": _semantic_doc(semantic),
        "backup": backup,
        "obsidian": obsidian,
    }


def render_doc_markdown(doc, template="digest"):
    """Render a machine document dict to Markdown via the deterministic Knap renderer."""
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
        json.dump(doc, f)
        tmp = f.name
    try:
        r = subprocess.run(
            ["npx", "tsx", "src/cli.ts", "render-doc", tmp, "--template", template],
            capture_output=True, text=True, cwd=str(REPO_ROOT),
        )
        if r.returncode != 0:
            raise RuntimeError(f"etk render-doc failed: {r.stderr.strip()[:300]}")
        return r.stdout
    finally:
        Path(tmp).unlink(missing_ok=True)


def obsidian_sync_status():
    """Best-effort one-line Obsidian sync status from the vault CLI.

    Returns '' when the vault container is down or the CLI errors — never raises,
    so a digest can never fail because of it.
    """
    try:
        r = subprocess.run(
            ["docker", "ps", "--format", "{{.Names}}", "--filter", "name=wattson-vault-obsidian"],
            capture_output=True, text=True, timeout=5,
        )
        if "wattson-vault-obsidian" not in r.stdout:
            return ""
        r = subprocess.run(
            ["just", "vault-cli", "sync:status"],
            capture_output=True, text=True, timeout=15, cwd=str(REPO_ROOT),
        )
        if r.returncode != 0:
            return ""
        lines = [l for l in (r.stdout or "").strip().splitlines() if l.strip()]
        return lines[-1] if lines else ""
    except (subprocess.SubprocessError, OSError):
        return ""


def render_digest(stamp, trigger, sync_sha, added, modified, deleted, renamed,
                  agent_commits, since_label, inbox, semantic=None, backup="", obsidian=""):
    created = datetime.datetime.now().astimezone().strftime("%Y-%m-%d %H:%M")
    doc = build_digest_doc(stamp, trigger, created, sync_sha, added, modified, deleted, renamed,
                           agent_commits, since_label, inbox, semantic=semantic,
                           backup=backup, obsidian=obsidian)
    return render_doc_markdown(doc), doc


def push_backup(vault):
    """Push to the configured vault remote (if any). Returns a one-line status."""
    r = subprocess.run(["git", "-C", str(vault), "remote"], capture_output=True, text=True)
    remotes = [x for x in r.stdout.split() if x]
    if not remotes:
        return "no remote configured — local commits only (set one with `git remote add origin <url>`)"
    remote = remotes[0]
    r = subprocess.run(["git", "-C", str(vault), "push"], capture_output=True, text=True)
    if r.returncode == 0:
        return f"pushed to {remote}"
    return f"PUSH FAILED to {remote}: {(r.stderr or r.stdout).strip()[:300]}"


def main():
    ap = argparse.ArgumentParser(description="Run a WATTSON vault digest (structural + semantic).")
    ap.add_argument("--vault", default="vault-runtime/vault-data")
    ap.add_argument("--request", help="marker filename (without .md); default: newest pending marker")
    ap.add_argument("--quiet", action="store_true", help="exit silently when no marker is pending")
    ap.add_argument("--skip-semantic", action="store_true", help="run structural digest only (no model calls)")
    ap.add_argument("--max-notes", type=int, default=0, metavar="N",
                    help="process at most N changed notes semantically this run (0 = all); the rest carry over")
    args = ap.parse_args()

    vault = Path(args.vault).expanduser().resolve()
    if not (vault / ".git").is_dir():
        sys.exit(f"not a git repo: {vault}")

    lock_fd = open(LOCK, "w")
    try:
        fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        return

    marker = find_marker(vault, args.request)
    if marker is None:
        if args.quiet or args.request:
            return
        stamp = "manual-" + datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        trigger = "manual (terminal)"
    else:
        stamp = marker.stem
        trigger = str(marker.relative_to(vault))

    prev = git(vault, "rev-parse", "HEAD")
    root = git(vault, "rev-list", "--max-parents=0", "HEAD")
    # 'Agent since last digest' range starts at the previous agent digest commit
    digest_ref = last_digest_commit(vault) or root
    since_label = "baseline" if digest_ref == root \
        else f"digest {git(vault, 'log', '-1', '--format=%s', digest_ref)}"
    # 'You' range: consecutive sync checkpoints; without a previous checkpoint
    # the root commit is the baseline (first run shows everything as new)
    user_prev = last_sync_checkpoint(vault) or root

    status = git(vault, "status", "--porcelain")
    sync_sha = None
    if status:
        n = len(status.splitlines())
        git(vault, "add", "-A")
        git(vault, "commit", "-m", f"sync: checkpoint {stamp} ({n} paths)", identity=USER_IDENTITY)
        sync_sha = git(vault, "rev-parse", "--short", "HEAD")
        user_head = git(vault, "rev-parse", "HEAD")
    else:
        user_head = user_prev  # nothing new from the user this run

    head = git(vault, "rev-parse", "HEAD")
    if user_head != user_prev:
        added, modified, deleted, renamed = section_changes(vault, user_prev, user_head)
        user_paths = user_change_paths(vault, user_prev, user_head)
        added = [p for p in added if p in user_paths]
        modified = [p for p in modified if p in user_paths]
        deleted = [p for p in deleted if p in user_paths]
        renamed = [r for r in renamed
                   if user_paths & {r.split(" -> ")[0], r.split(" -> ")[-1]}]
        added, modified, deleted, renamed = filter_user_changes(added, modified, deleted, renamed)
    else:
        added, modified, deleted, renamed = [], [], [], []
    agent_commits = list_agent_commits(vault, digest_ref, head)
    inbox = inbox_files(vault)

    semantic = None
    if args.skip_semantic:
        semantic = pipeline_run.Report()
        semantic.skipped = True
        semantic.skip_reason = "--skip-semantic"
    else:
        try:
            semantic = pipeline_run.run_intelligent_digest(vault, max_notes=args.max_notes)
        except Exception as e:  # structural digest must still work if the model is down
            semantic = pipeline_run.Report()
            semantic.skipped = True
            semantic.skip_reason = f"semantic pass crashed: {str(e)[:200]}"

    if semantic is not None and not semantic.skipped:
        if git(vault, "status", "--porcelain"):
            git(vault, "add", "-A")
            git(vault, "commit", "-m",
                f"agent: digest {stamp} changes ({semantic.tagged} tagged, {semantic.atoms_proposed} proposals)",
                identity=AGENT_IDENTITY)

    backup = push_backup(vault) if semantic is not None and not semantic.skipped else ""
    obsidian = obsidian_sync_status()

    note = vault / OUT_DIR / f"{stamp}.md"
    note.parent.mkdir(parents=True, exist_ok=True)
    md, doc = render_digest(stamp, trigger, sync_sha, added, modified,
                            deleted, renamed, agent_commits, since_label, inbox,
                            semantic=semantic, backup=backup, obsidian=obsidian)
    note.write_text(md)
    (vault / OUT_DIR / f"{stamp}.json").write_text(json.dumps(doc, indent=2), encoding="utf-8")

    if marker is not None:
        processed = marker.parent / "processed"
        processed.mkdir(exist_ok=True)
        marker.rename(processed / marker.name)

    git(vault, "add", "-A")
    git(vault, "commit", "-m", f"agent: digest {stamp}", identity=AGENT_IDENTITY)
    if semantic is not None and not semantic.skipped:
        backup2 = push_backup(vault)
        if backup2.startswith("PUSH FAILED"):
            print(f"warning: {backup2}", file=sys.stderr)
    sem_summary = ""
    if semantic is not None and not semantic.skipped:
        sem_summary = (f"; semantic: {len(semantic.notes)} changed, {semantic.tagged} tagged, "
                       f"{semantic.atoms_proposed} proposals, {len(semantic.failures)} failures")
    print(f"digest {stamp}: {len(added)} added, {len(modified)} modified, "
          f"{len(deleted)} deleted, {len(renamed)} renamed; agent commits: {len(agent_commits)}; "
          f"inbox: {len(inbox)}; backup: {backup}; note: {note.relative_to(vault)}{sem_summary}")


if __name__ == "__main__":
    main()
