# agent-core/wattson/flows.py
from __future__ import annotations
from autogen import GroupChat, GroupChatManager
from agent_core.wattson.agents_autogen import triage, relate, prb, orchestrator
from agent_core.wattson import tools
from agent_core.wattson.ontology_utils import list_area_tags
import frontmatter, json

def relationship_round(note_path: str, apply_th=0.75, suggest_th=0.4):
    # Load note and deterministic baseline
    note = frontmatter.load(note_path)
    text = f"{note.content}\n" + " ".join(map(str, (note.metadata or {}).values()))
    onto = tools.load_ontology()
    base = tools.deterministic_candidates(text, onto)
    avail = available_area_tags(onto)

    # Kick off relate agent with a single message that **includes** the baseline + available list.
    relate.init_chat()
    msg = {
        "role": "user",
        "content": json.dumps({
            "note_excerpt": text[:6000],
            "deterministic_candidates": base,
            "available_tags": avail,
            "apply_threshold": apply_th,
            "suggest_threshold": suggest_th,
            "max_expansions": 3
        })
    }
    out = relate.generate_reply(messages=[msg])  # Autogen will allow function calls if needed
    # Expect strict JSON back
    data = json.loads(out.msg if hasattr(out, "msg") else out)
    apply = [(r["tag"], float(r.get("score",1.0))) for r in data.get("apply", []) if r["tag"] in avail]
    suggest = [(r["tag"], float(r.get("score",0))) for r in data.get("suggest", []) if r["tag"] in avail]
    # Ensure deterministic recall survives (failsafe)
    seen = {t for t,_ in apply+suggest}
    for t in base:
        if t not in seen:
            apply.append((t, 0.8))
    # Sort by score desc
    apply.sort(key=lambda x: -x[1]); suggest.sort(key=lambda x: -x[1])
    return apply, suggest

def full_tagging_pr_flow(note_path: str, diff_lines: int, diff_hunks: int):
    group = GroupChat(agents=[orchestrator, triage, relate, prb], messages=[], max_round=8)
    manager = GroupChatManager(groupchat=group, llm_config=triage.llm_config)

    # Seed with a structured instruction the orchestrator can route
    seed = {
        "task": "tag_and_pr",
        "note_path": note_path,
        "diff_lines": diff_lines,
        "diff_hunks": diff_hunks,
        "policy": {"max_lines": 200, "max_hunks": 50}
    }
    reply = orchestrator.initiate_chat(manager, message=json.dumps(seed))
    return reply  # final PR body should appear before max_round
