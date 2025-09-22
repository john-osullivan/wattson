from __future__ import annotations
import pathlib
from autogen import ConversableAgent, register_function
from agent_core.wattson.autogen_cfg import llm_cfg
from agent_core.wattson import tools

PROMPTS_DIR = pathlib.Path(__file__).resolve().parents[0] / "prompts"

def _read(name: str) -> str:
    return (PROMPTS_DIR / name).read_text(encoding="utf-8")

def make_agents():
    triage = ConversableAgent(
        "IntakeTriageAgent",
        system_message=_read("intake_triage.md"),
        llm_config=llm_cfg,
    )
    relate = ConversableAgent(
        "RelationshipTaggingAgent",
        system_message=_read("relationship_tagging.md"),
        llm_config=llm_cfg,
    )
    prb = ConversableAgent(
        "PRButlerAgent",
        system_message=_read("pr_butler.md"),
        llm_config=llm_cfg,
    )
    orchestrator = ConversableAgent(
        "Orchestrator",
        system_message=_read("orchestrator.md"),
        llm_config=llm_cfg,
    )

    # Register deterministic tools for both LLM tool-calls and Python execution
    for agent in (triage, relate, prb, orchestrator):
        register_function(tools.load_ontology, caller=agent, executor=agent)
        register_function(tools.normalize_text, caller=agent, executor=agent)
        register_function(tools.deterministic_candidates, caller=agent, executor=agent)
        register_function(tools.schema_validate_frontmatter, caller=agent, executor=agent)
        register_function(tools.diff_budget, caller=agent, executor=agent)

    return triage, relate, prb, orchestrator
