#!/usr/bin/env python3
"""WATTSON structural vault digest.

Commits user (phone/desktop) changes as `sync:` when a digest is requested,
then writes a structural digest note and commits it as `agent:`.
Agent-made vault changes must be committed by the agent itself with an
`agent:` prefix before a digest runs; anything left uncommitted at digest
time is attributed to the user.
"""
import argparse
import datetime
import fcntl
import os
import subprocess
import sys
import tempfile
from pathlib import Path

AGENT_IDENTITY = ("WATTSON Agent", "agent@wattson.local")
USER_IDENTITY = ("John Osullivan", "john.osullivan42@gmail.com")
REQ_DIR = Path("99_Machine/digest/requests")
OUT_DIR = Path("99_Machine/digest")
INBOX_DIR = Path("00_Inbox")
LOCK = "/tmp/wattson-vault-digest.lock"


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
    out = git(vault, "log", "--grep", r"^agent: digest [0-9]", "--format=%H", "-n", "1")
    return out or None


def render_digest(vault, stamp, trigger, sync_sha, added, modified, deleted, renamed,
                  agent_commits, since_label, inbox):
    now = datetime.datetime.now().astimezone()
    lines = [
        "---",
        "type: wattson-digest",
        f"created: {now.strftime('%Y-%m-%d %H:%M')}",
        f"trigger: {trigger}",
        f"since: {since_label}",
        "digest-version: 0",
        "---",
        "",
        f"# Digest — {stamp}",
        "",
        f"## You {f'(`sync: {sync_sha}`)' if sync_sha else '(no uncommitted changes at trigger time)'}",
        "",
    ]
    total = len(added) + len(modified) + len(deleted) + len(renamed)
    lines.append(f"{total} path(s) changed since {since_label}.")
    lines.append("")

    def heading(title, items):
        lines.append(f"### {title} ({len(items)})")
        if not items:
            lines.extend(["(none)", ""])
            return
        groups = group_by_folder(items)
        for folder in sorted(groups):
            names = groups[folder]
            if len(names) == 1 and folder == "(vault root)":
                lines.append(f"- `{names[0]}`")
            else:
                lines.append(f"- **{folder}** ({len(names)})")
                lines.extend([f"  - `{n}`" for n in names])
        lines.append("")

    heading("Added", added)
    heading("Modified", modified)
    heading("Deleted", deleted)
    heading("Renamed", renamed)

    lines += ["## Agent since last digest", ""]
    if not agent_commits:
        lines += ["(none)", ""]
    for c in agent_commits:
        lines.append(f"- `{c['sha']}` {c['subject']}")
        lines += [f"  - `{p}`" for p in c["paths"]]
    if agent_commits:
        lines.append("")

    lines += [f"## Unfiled Inbox ({len(inbox)})", ""]
    if inbox:
        lines += [f"- `{p}`" for p in inbox]
    else:
        lines.append("(none)")
    lines.append("")

    lines += ["## Proposals", "", "(none — v0 digest is read-only on your content)", ""]
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser(description="Run a structural WATTSON vault digest.")
    ap.add_argument("--vault", default="spike/obsidian/vault-data")
    ap.add_argument("--request", help="marker filename (without .md); default: newest pending marker")
    ap.add_argument("--quiet", action="store_true", help="exit silently when no marker is pending")
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
    since_commit = last_digest_commit(vault) or git(vault, "rev-list", "--max-parents=0", "HEAD")
    since_label = "baseline" if since_commit == git(vault, "rev-list", "--max-parents=0", "HEAD") else f"digest {git(vault, 'log', '-1', '--format=%s', since_commit)}"

    status = git(vault, "status", "--porcelain")
    sync_sha = None
    if status:
        n = len(status.splitlines())
        git(vault, "add", "-A")
        git(vault, "commit", "-m", f"sync: checkpoint {stamp} ({n} paths)", identity=USER_IDENTITY)
        sync_sha = git(vault, "rev-parse", "--short", "HEAD")

    head = git(vault, "rev-parse", "HEAD")
    added, modified, deleted, renamed = section_changes(vault, since_commit, head)
    agent_commits = list_agent_commits(vault, since_commit, head)
    inbox = inbox_files(vault)

    note = vault / OUT_DIR / f"{stamp}.md"
    note.parent.mkdir(parents=True, exist_ok=True)
    note.write_text(render_digest(vault, stamp, trigger, sync_sha, added, modified,
                                  deleted, renamed, agent_commits, since_label, inbox))

    if marker is not None:
        processed = marker.parent / "processed"
        processed.mkdir(exist_ok=True)
        marker.rename(processed / marker.name)

    git(vault, "add", "-A")
    git(vault, "commit", "-m", f"agent: digest {stamp}", identity=AGENT_IDENTITY)
    print(f"digest {stamp}: {len(added)} added, {len(modified)} modified, "
          f"{len(deleted)} deleted, {len(renamed)} renamed; agent commits: {len(agent_commits)}; "
          f"inbox: {len(inbox)}; note: {note.relative_to(vault)}")


if __name__ == "__main__":
    main()
