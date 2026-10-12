#!/usr/bin/env python3
"""Manage WATTSON extraction proposals (list / show / accept / reject).

`show` renders the proposal envelope as Markdown with the deterministic Knap
renderer (pass --json for the raw envelope). Accepting a proposal renders the
atom note with the deterministic ETK renderer, writes it to the vault, adds the
reciprocal link to the source note, and commits everything as `agent:`.
"""
import argparse
import fcntl
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "py"))
sys.path.insert(0, str(REPO_ROOT / "scripts"))
from wattson.pipeline import apply, proposals, relations, state  # noqa: E402
from vault_digest import push_if_stale, render_doc_markdown  # noqa: E402

AGENT_IDENTITY = ("WATTSON Agent", "agent@wattson.local")
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


def commit_and_push(vault, msg):
    """Commit as the agent and push if the remote has gone stale."""
    git(vault, "add", "-A")
    git(vault, "commit", "-m", msg, identity=AGENT_IDENTITY)
    status = push_if_stale(vault)
    if status:
        print(status)


def main():
    ap = argparse.ArgumentParser(description="WATTSON extraction proposals.")
    ap.add_argument("--vault", default="vault-runtime/vault-data")
    ap.add_argument("command", choices=["list", "show", "accept", "reject"],
                    help="list all | show <id> | accept <id> | reject <id>")
    ap.add_argument("proposal_id", nargs="?", help="proposal id (for show/accept/reject)")
    ap.add_argument("--json", dest="as_json", action="store_true",
                    help="show: print the raw envelope JSON instead of rendered Markdown")
    args = ap.parse_args()

    vault = Path(args.vault).expanduser().resolve()
    if not (vault / ".git").is_dir():
        sys.exit(f"not a git repo: {vault}")

    if args.command == "list":
        rows = proposals.list_proposals(vault)
        if not rows:
            print("(no proposals)")
        else:
            for r in rows:
                print(f"{r['status']:<16} {r['id']}  {r['title']}  <- {r['source']}")
        rels = relations.list_relations(vault)
        if rels:
            if rows:
                print()
            for r in rels:
                print(f"{r['status']:<16} {r['id']}  {r['source']}  --[{r['type']}]-->  {r['target']}")
        if not rows and not rels:
            print("(no relation proposals)")
        return

    if not args.proposal_id:
        sys.exit(f"usage: vault_proposal.py --vault <v> {args.command} <id>")

    is_relation = args.proposal_id.startswith("rel-")

    lock_fd = open(LOCK, "w")
    try:
        fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        sys.exit("another digest is running; try again shortly")

    if args.command == "show":
        if is_relation:
            env = relations.load_envelope(vault, args.proposal_id)
            r = env["proposals"][0]["relation"]
            if args.as_json:
                print(json.dumps(env, indent=2))
            else:
                print(f"{r['source']}  --[{r['type']}]-->  {r['target']}\n{r['reason']}")
            return
        env = proposals.load_envelope(vault, args.proposal_id)
        if args.as_json:
            print(json.dumps(env, indent=2))
        else:
            print(render_doc_markdown(env, template="proposal"), end="")
        return

    if args.command == "reject":
        if is_relation:
            relations.reject(vault, args.proposal_id)
        else:
            proposals.reject(vault, args.proposal_id)
        commit_and_push(vault, f"agent: reject proposal {args.proposal_id}")
        print(f"rejected {args.proposal_id}")
        return

    # accept
    if is_relation:
        try:
            out = relations.accept(vault, args.proposal_id)
        except (relations.RelationError, FileNotFoundError, ValueError, OSError) as e:
            sys.exit(f"cannot accept {args.proposal_id}: {e}")
        commit_and_push(vault, f"agent: accept proposal {args.proposal_id} (relation in {out['atom_path']})")
        print(f"accepted {args.proposal_id}: {out['line']}")
        return
    try:
        out = proposals.accept(vault, args.proposal_id)
    except (proposals.ProposalError, FileNotFoundError, ValueError, OSError) as e:
        sys.exit(f"cannot accept {args.proposal_id}: {e}")
    commit_and_push(vault, f"agent: accept proposal {args.proposal_id} (atom: {out['atom_path']})")
    print(f"accepted {args.proposal_id}: wrote {out['atom_path']}; "
          f"source linked: {out['source_path']}")


if __name__ == "__main__":
    main()
