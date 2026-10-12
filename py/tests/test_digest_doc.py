"""The digest document is pure structured data: build_digest_doc must be a
deterministic, I/O-free transformation, and render_digest must round-trip
through the Knap renderer."""
import importlib
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts"))
vault_digest = importlib.import_module("vault_digest")


def _report():
    r = vault_digest.pipeline_run.Report()
    r.examined = 3
    r.tagged = 1
    r.atoms_proposed = 1
    r.notes = [{
        "path": "10_Journaling/a.md",
        "append_only": False,
        "summary": "journal with an idea",
        "applied": [{"tag": "area/society/disinformation", "reason": "r"}],
        "review_tags": [],
        "rejected_tags": [],
        "extractions": [{"title": "Loud voice", "tags": ["type/atom"],
                         "body": "b", "reason": "core idea",
                         "proposalId": "atom-loud-voice-00000000", "source": "10_Journaling/a.md"}],
        "skipped_extractions": [],
        "review": [],
        "error": "",
    }]
    return r


def test_build_digest_doc_is_pure_and_deterministic():
    kw = dict(
        stamp="20261012-120000", trigger="99_Machine/digest/requests/x.md",
        created="2026-10-12 12:00", sync_sha="ab12cd3",
        added=["10_Daily/a.md", "README-extra.md", "00_Inbox/b.md"],
        modified=["10_Daily/c.md"], deleted=[], renamed=[],
        agent_commits=[{"sha": "deadbe1", "subject": "agent: digest x changes", "paths": ["10_Daily/a.md"]}],
        since_label="baseline", inbox=["00_Inbox/b.md"],
    )
    d1 = vault_digest.build_digest_doc(semantic=_report(), backup="pushed to origin", **kw)
    d2 = vault_digest.build_digest_doc(semantic=_report(), backup="pushed to origin", **kw)
    assert d1 == d2
    assert d1["changed_total"] == 4
    assert d1["sync_sha"] == "ab12cd3"
    assert [c["title"] for c in d1["changes"]] == ["Added", "Modified", "Deleted", "Renamed"]
    added = d1["changes"][0]
    assert added["count"] == 3
    assert {g["folder"] for g in added["groups"]} == {"10_Daily", "(vault root)", "00_Inbox"}
    root = [g for g in added["groups"] if g["folder"] == "(vault root)"][0]
    assert root["root_single"] is True and root["paths"] == ["README-extra.md"]
    # semantic: Report -> plain dict, proposals lifted from note extractions
    assert d1["semantic"]["proposals"][0]["proposalId"] == "atom-loud-voice-00000000"
    assert d1["backup"] == "pushed to origin"


def test_build_digest_doc_semantic_none_and_empty():
    d = vault_digest.build_digest_doc(backup="",
                                      stamp="s", trigger="t", created="c", sync_sha=None,
                                      added=[], modified=[], deleted=[], renamed=[],
                                      agent_commits=[], since_label="baseline", inbox=[])
    assert d["semantic"] is None
    assert d["changed_total"] == 0
    assert all(c["count"] == 0 and c["groups"] == [] for c in d["changes"])


def test_render_digest_roundtrip_via_knap():
    doc = vault_digest.build_digest_doc(backup="no remote configured",
                                        stamp="s", trigger="t", created="c", sync_sha=None,
                                        added=["10_Daily/a.md"], modified=[], deleted=[], renamed=[],
                                        agent_commits=[], since_label="baseline", inbox=[])
    md = vault_digest.render_doc_markdown(doc, template="digest")
    assert md.startswith("---\ntype: wattson-digest\n")
    assert "# Digest — s" in md
    assert "### Added (1)" in md and "`10_Daily/a.md`" in md
    assert "(none)" in md  # empty sections render their placeholder
    assert "## Backup" in md and "no remote configured" in md
    assert "## Semantic review (WATTSON)" in md and "(not run)" in md
