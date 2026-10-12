#!/usr/bin/env python3
"""Run the consolidation pass: propose typed relations between accepted atoms.

Batches the atom corpus, asks the model for connections, screens every
proposal deterministically, and writes pending relation envelopes. The
model proposes; code decides; a human accepts. Re-runs are idempotent:
proposals already on record (in atom files or as envelopes) are skipped.
"""
import fcntl
import os
import sys
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "py"))
sys.path.insert(0, str(REPO_ROOT / "scripts"))
from wattson.pipeline import config, relations  # noqa: E402
from vault_digest import AGENT_IDENTITY, git, push_backup  # noqa: E402

LOCK = os.environ.get("WATTSON_DIGEST_LOCK", "/tmp/wattson-vault-digest.lock")


def main():
    import argparse
    ap = argparse.ArgumentParser(description="WATTSON consolidation pass.")
    ap.add_argument("--vault", default="vault-runtime/vault-data")
    args = ap.parse_args()
    vault = Path(args.vault).expanduser().resolve()
    if not (vault / ".git").is_dir():
        sys.exit(f"not a git repo: {vault}")

    lock_fd = open(LOCK, "w")
    try:
        fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        sys.exit("another digest is running; try again shortly")

    cfg = config.load_config()
    atoms = relations.load_atoms(vault)
    if len(atoms) < 2:
        sys.exit(f"need at least 2 atoms, found {len(atoms)}")
    corpus_titles = [a["title"] for a in atoms]
    existing = relations.recorded_relations(vault)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")

    proposed = skipped = failed_batches = 0
    for i in range(0, len(atoms), relations.BATCH_SIZE):
        batch = atoms[i:i + relations.BATCH_SIZE]
        batch_titles = [a["title"] for a in batch]
        prompt = relations.build_prompt(batch, corpus_titles)
        raw, err = config.chat_completion(cfg, prompt, max_tokens=4000, retries=1)
        if err or raw is None:
            failed_batches += 1
            print(f"batch {i // relations.BATCH_SIZE + 1} failed: {err}", file=sys.stderr)
            continue
        props, skips = relations.validate(raw, batch_titles, corpus_titles, existing)
        skipped += len(skips)
        for s in skips:
            print(f"  skip: {s.get('source')} -> {s.get('target')} [{s.get('type')}]: {s.get('why')}")
        for prop in props:
            rid = relations.relation_id(prop["source"], prop["target"], prop["type"])
            if relations.envelope_path(vault, rid).exists():
                skipped += 1
                continue
            relations.save_envelope(vault, relations.make_envelope(rid, prop, batch_titles))
            existing.add((prop["source"], prop["target"], prop["type"]))
            proposed += 1
        print(f"batch {i // relations.BATCH_SIZE + 1}: {len(props)} proposed "
              f"({i + len(batch)}/{len(atoms)} atoms)", file=sys.stderr)

    if proposed:
        git(vault, "add", "-A")
        git(vault, "commit", "-m",
            f"agent: relations {stamp} ({proposed} proposed)", identity=AGENT_IDENTITY)
        backup = push_backup(vault)
    print(f"atoms: {len(atoms)}; proposed: {proposed}; skipped: {skipped}; "
          f"failed batches: {failed_batches}{'; backup: ' + backup if proposed and backup else ''}")


if __name__ == "__main__":
    main()
