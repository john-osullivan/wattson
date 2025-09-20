#!/usr/bin/env bash
set -euo pipefail

# Validate changed markdown files against schema and enforce diff budget

MAX_LINES=${MAX_LINES:-200}
MAX_HUNKS=${MAX_HUNKS:-50}

# 1) Schema validation on staged *.md (adjust to your staging flow)
changed=$(git diff --cached --name-only -- '*.md' || true)
if [[ -n "$changed" ]]; then
  echo "Validating schema for:"
  echo "$changed"
  python - <<'PY'
import sys, pathlib
from agent_core.wattson.governance.validate import validate_note
errs=[]
for p in sys.stdin.read().strip().splitlines():
    if not p: continue
    if not p.endswith(".md"): continue
    for e in validate_note(pathlib.Path(p)):
        errs.append(e)
if errs:
    print("\n".join(errs))
    sys.exit(1)
PY
fi <<< "$changed"

# 2) Diff budget on staged changes
stats=$(git diff --cached --unified=0 | sed 's/\r$//')
lines=$(( $(grep -cE '^\+|^\-' <<<"$stats" || true) ))
hunks=$(( $(grep -cE '^@@ ' <<<"$stats" || true) ))

echo "Diff budget: ${lines} lines / ${hunks} hunks (limits ${MAX_LINES}/${MAX_HUNKS})"
if (( lines > MAX_LINES || hunks > MAX_HUNKS )); then
  echo "Diff budget exceeded. Split into smaller PRs."
  exit 2
fi

echo "Validation OK."
