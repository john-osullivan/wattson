from __future__ import annotations
import argparse, json, sys, pathlib
from rich import print as rprint

# These modules are the ones we've been building toward.
# If you haven't pasted them yet, stub or adjust imports accordingly.
try:
    from agent_core.wattson.flows import relationship_round
except Exception as e:
    def relationship_round(note_path: str, apply_th=0.75, suggest_th=0.4):
        raise SystemExit(f"[CLI] flows.relationship_round not available: {e}")

def main():
    p = argparse.ArgumentParser(prog="wattson-agent", description="Run WATTSON Autogen interactions")
    sub = p.add_subparsers(dest="cmd", required=True)

    r = sub.add_parser("relate", help="Run RelationshipTagging on a note and print JSON result")
    r.add_argument("note_path", type=pathlib.Path)
    r.add_argument("--apply", type=float, default=0.75, dest="apply_th")
    r.add_argument("--suggest", type=float, default=0.40, dest="suggest_th")

    args = p.parse_args()

    if args.cmd == "relate":
        apply_list, suggest_list = relationship_round(str(args.note_path), args.apply_th, args.suggest_th)
        out = {
            "apply": [{"tag": t, "score": s} for t, s in apply_list],
            "suggest": [{"tag": t, "score": s} for t, s in suggest_list],
        }
        rprint(json.dumps(out, indent=2))
        return 0

    p.print_help()
    return 1

if __name__ == "__main__":
    sys.exit(main())