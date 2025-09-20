#!/usr/bin/env bash
set -euo pipefail

TS="$(date +%Y%m%d-%H%M%S)"
WT="../worktree-$TS"
BASE_REF="origin/main"
BRANCH="ai-proposal/$TS"

git fetch origin main
git worktree add "$WT" "$BASE_REF"

(
  cd "$WT"
  git switch -c "$BRANCH"
  # Place or modify files here before committing (CI will validate schema + budget)
  git add -A
  git commit -m "triage: capture $TS"
  git push -u origin "$BRANCH"
)

git worktree remove "$WT" --force
echo "Opened branch $BRANCH (worktree removed)."
