"""Pipeline tests: detection, frontmatter edits, semantic screening,
end-to-end digest run with a mocked model, and the proposal lifecycle."""
import json
import subprocess
from pathlib import Path

import pytest

from wattson.pipeline import apply, detect, proposals, run, semantics, state

DAILY = """---
created: 2026-10-10
---
# Sat, Oct 10

## Journal
- A loud voice is not a well-sourced one. I keep seeing this in the feed.

## TODOs
- [ ] buy celery
"""

DAILY_TAGGED = """---
created: 2026-10-10
tags:
  - "area/personal/journaling"
---
# Sat, Oct 10

## Journal
- b
"""

PLAIN = "No frontmatter here.\n\nJust prose about disinformation campaigns.\n"


def git(vault, *args, identity=("T", "t@t.local")):
    cmd = ["git", "-C", str(vault)]
    if identity:
        cmd += ["-c", f"user.name={identity[0]}", "-c", f"user.email={identity[1]}"]
    cmd += [str(a) for a in args]
    r = subprocess.run(cmd, capture_output=True, text=True)
    assert r.returncode == 0, f"git {' '.join(args)}: {r.stderr}"
    return r.stdout.strip()


@pytest.fixture
def vault(tmp_path):
    v = tmp_path / "vault"
    v.mkdir()
    (v / ".git").mkdir()
    git(v, "init", "-q", "-b", "main")
    git(v, "config", "user.name", "T")
    git(v, "config", "user.email", "t@t.local")
    return v


def add_note(vault, rel, text):
    p = vault / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text)
    return p


def mock_model(canned):
    """Returns (model_fn, calls_counter)."""
    calls = {"n": 0}

    def model(rel, text, established, existing, existing_titles):
        calls["n"] += 1
        if callable(canned):
            return canned(rel, text)
        if rel in canned:
            return canned[rel], None
        return {"summary": "", "applied": [], "review_tags": [], "rejected_tags": [],
                "extractions": [], "skipped_extractions": [], "review": []}, None

    return model, calls


def test_detect_added_modified_deleted_append_only(vault):
    p = add_note(vault, "10_Journaling/a.md", DAILY)
    st = state.load_state(vault)
    c1 = detect.classify(vault, st)
    assert [n["path"] for n in c1["added"]] == ["10_Journaling/a.md"]
    state.record_processed(st, "10_Journaling/a.md", c1["added"][0]["fingerprint"], DAILY)

    c2 = detect.classify(vault, st)
    assert not c2["added"] and not c2["modified"] and not c2["deleted"]

    p.write_text(DAILY + "## More\n- appended\n")
    c3 = detect.classify(vault, st)
    assert len(c3["modified"]) == 1 and c3["modified"][0]["append_only"] is True

    p.write_text(DAILY.replace("- A loud voice", "- A LOUD voice"))
    c4 = detect.classify(vault, st)
    assert len(c4["modified"]) == 1 and c4["modified"][0]["append_only"] is False

    p.unlink()
    c5 = detect.classify(vault, st)
    assert c5["deleted"] == ["10_Journaling/a.md"]


def test_skipped_dirs_not_scanned(vault):
    add_note(vault, ".obsidian/x.md", "hidden")
    add_note(vault, "99_Machine/wattson/state.json", "{}")
    add_note(vault, "99_Machine/digest/2026.md", "machine")
    add_note(vault, "10_Journaling/a.md", "user")
    scan = detect.scan_vault(vault)
    assert list(scan) == ["10_Journaling/a.md"]


def test_apply_tags_existing_frontmatter(vault):
    text = DAILY_TAGGED
    out = apply.apply_tags(text, ["area/society/disinformation", "area/personal/journaling"])
    assert out is not None
    assert '- "area/society/disinformation"' in out
    # duplicate existing tag not re-added
    assert out.count('"area/personal/journaling"') == 1
    # body untouched, original tag kept
    assert out.endswith(text.split("---", 2)[2])
    assert "- b" in out


def test_apply_tags_no_frontmatter(vault):
    out = apply.apply_tags(PLAIN, ["area/society/disinformation"])
    assert out.startswith('---\ntags:\n  - "area/society/disinformation"\n---\n\n')
    assert out.endswith(PLAIN)


def test_apply_tags_frontmatter_without_tags_key(vault):
    text = "---\ncreated: 2026-10-10\n---\n\n# X\n"
    out = apply.apply_tags(text, ["context/home"])
    assert out is not None
    # the tags block must land INSIDE the frontmatter, before the closing ---
    fm = out.split("\n---\n", 2)[0]
    assert "tags:\n  - \"context/home\"" in fm
    # and the body is untouched
    assert out.endswith("\n---\n\n# X\n")
    # re-adding the same tag is a no-op
    assert apply.apply_tags(out, ["context/home"]) is None


def test_apply_tags_inserts_inside_frontmatter(vault):
    # regression: tags were once appended AFTER the closing --- (orphan block)
    out = apply.apply_tags(DAILY, ["area/society/disinformation"])
    assert out is not None
    parts = out.split("\n---\n")
    fm, body = parts[0], parts[1]
    assert fm.count("tags:") == 1
    assert '- "area/society/disinformation"' in fm
    assert body.startswith("# Sat, Oct 10")
    assert "tags:" not in body


def test_apply_tags_extends_mid_frontmatter_block(vault):
    text = "---\ntags:\n  - \"area/personal/journaling\"\ncreated: 2026-10-10\n---\nbody\n"
    out = apply.apply_tags(text, ["context/home"])
    assert out is not None
    fm = out.split("\n---\n", 2)[0]
    assert fm.count("tags:") == 1
    assert fm.index("- \"area/personal/journaling\"") < fm.index("- \"context/home\"")
    assert fm.index("- \"context/home\"") < fm.index("created: 2026-10-10")


def test_apply_tags_noop_returns_none(vault):
    assert apply.apply_tags(DAILY_TAGGED, ["area/personal/journaling"]) is None
    assert apply.apply_tags(DAILY, []) is None


def test_apply_tags_dedupes_within_new_tags(vault):
    # regression: the model may echo a tag twice; it must land once
    out = apply.apply_tags(DAILY, ["context/home", "context/home", "area/tech/ai"])
    fm = out.split("\n---\n")[0]
    assert fm.count('"context/home"') == 1
    assert fm.count('"area/tech/ai"') == 1


def test_apply_tags_checked_stale_fingerprint(vault):
    p = add_note(vault, "10_Journaling/a.md", DAILY)
    fp = state.fingerprint(p.read_bytes())
    p.write_text(DAILY + "changed after analysis\n")
    with pytest.raises(apply.StaleError):
        apply.apply_tags_checked(vault, "10_Journaling/a.md", fp, ["area/tech/ai"])
    assert "area/tech/ai" not in p.read_text()


def test_semantics_screening(vault):
    est = {"area/society/disinformation", "area/tech/ai", "type/atom", "context/work"}
    raw = {
        "tags": [
            {"tag": "area/society/disinformation", "reason": "r", "confidence": 0.9, "needs_review": False},
            {"tag": "made/up/tag", "reason": "x", "confidence": 0.9, "needs_review": False},
            {"tag": "context/work", "reason": "x", "confidence": 0.4, "needs_review": False},
            {"tag": "area/tech/ai", "reason": "x", "confidence": 0.9, "needs_review": True},
        ],
        "extractions": [
            {"title": "Loud voice", "tags": ["area/society/disinformation"],
             "body": "A loud voice is not a well-sourced one.", "reason": "core idea"},
            {"title": "Paraphrase", "tags": ["area/tech/ai"],
             "body": "Loud voices are often poorly sourced.", "reason": "no"},
            {"title": "buy celery", "tags": ["area/personal"],
             "body": "buy celery", "reason": "exists"},
        ],
        "summary": "s",
    }
    res = semantics.validate_output(raw, DAILY, "10_Journaling/a.md", est, [], {"buy-celery"})
    assert [t["tag"] for t in res["applied"]] == ["area/society/disinformation"]
    assert {t["tag"] for t in res["rejected_tags"]} == {"made/up/tag"}
    assert {t["tag"] for t in res["review_tags"]} == {"context/work", "area/tech/ai"}
    assert len(res["extractions"]) == 1
    assert res["extractions"][0]["title"] == "Loud voice"
    assert {e["title"] for e in res["skipped_extractions"]} == {"Paraphrase", "buy celery"}


def test_semantics_existing_tag_not_reapplied(vault):
    est = {"area/personal/journaling"}
    raw = {"tags": [{"tag": "area/personal/journaling", "reason": "r",
                     "confidence": 0.9, "needs_review": False}]}
    res = semantics.validate_output(raw, DAILY_TAGGED, "x.md", est,
                                    ["area/personal/journaling"], set())
    assert res["applied"] == []


def test_semantics_whitespace_normalized_body(vault):
    est = {"area/tech/ai"}
    raw = {"extractions": [
        {"title": "Multi line", "tags": ["area/tech/ai"],
         "body": "line one   line two", "reason": "r"}]}
    text = "line one\n\nline two\n"
    res = semantics.validate_output(raw, text, "x.md", est, [], set())
    assert len(res["extractions"]) == 1
    assert res["extractions"][0]["body"] == "line one line two"


def test_run_end_to_end_and_idempotent(vault):
    add_note(vault, "10_Journaling/2026-10-10.md", DAILY)
    git(vault, "add", "-A"); git(vault, "commit", "-q", "-m", "init")

    model, calls = mock_model({
        "10_Journaling/2026-10-10.md": {
            "summary": "journal with a media idea",
            "applied": [{"tag": "area/society/disinformation", "reason": "r"}],
            "review_tags": [], "rejected_tags": [],
            "extractions": [{"title": "Loud voice", "tags": ["area/society/disinformation"],
                             "body": "A loud voice is not a well-sourced one.", "reason": "core idea"}],
            "skipped_extractions": [], "review": [],
        }})
    rep = run.run_intelligent_digest(vault, model=model)
    assert rep.tagged == 1 and rep.atoms_proposed == 1 and not rep.failures

    note = (vault / "10_Journaling/2026-10-10.md").read_text()
    assert '- "area/society/disinformation"' in note
    # user prose untouched
    assert note.count("buy celery") == 1
    assert "## Extracted" not in note  # extraction is proposal-only until accepted

    st = state.load_state(vault)
    assert st["notes"]["10_Journaling/2026-10-10.md"]["status"] == "processed"

    props = proposals.list_proposals(vault)
    assert len(props) == 1 and props[0]["status"] == "pending_review"
    pid = props[0]["id"]
    env = proposals.load_envelope(vault, pid)
    assert env["source"]["path"] == "10_Journaling/2026-10-10.md"
    assert env["proposals"][0]["note"]["tags"][0] == "type/atom"

    # second run: nothing changed -> no model calls, no duplicates
    rep2 = run.run_intelligent_digest(vault, model=model)
    assert calls["n"] == 1
    assert rep2.tagged == 0 and rep2.atoms_proposed == 0
    assert len(proposals.list_proposals(vault)) == 1


def test_max_notes_bounded_and_resumable(vault):
    add_note(vault, "10_Journaling/a.md", DAILY)
    add_note(vault, "10_Journaling/b.md", PLAIN)
    model, calls = mock_model({
        "10_Journaling/a.md": {"summary": "s", "applied": [{"tag": "area/tech/ai", "reason": "r"}],
                               "review_tags": [], "rejected_tags": [], "extractions": [],
                               "skipped_extractions": [], "review": []},
        "10_Journaling/b.md": {"summary": "s", "applied": [{"tag": "area/tech/ai", "reason": "r"}],
                               "review_tags": [], "rejected_tags": [], "extractions": [],
                               "skipped_extractions": [], "review": []},
    })
    rep1 = run.run_intelligent_digest(vault, model=model, max_notes=1)
    assert rep1.truncated is True and calls["n"] == 1 and rep1.tagged == 1
    # state persisted per-note: exactly one note processed so far
    st = state.load_state(vault)
    done = [p for p, e in st["notes"].items() if e["status"] == "processed"]
    assert len(done) == 1

    rep2 = run.run_intelligent_digest(vault, model=model, max_notes=1)
    assert rep2.truncated is False and calls["n"] == 2 and rep2.tagged == 1
    assert all(e["status"] == "processed"
               for e in state.load_state(vault)["notes"].values())


def test_repropose_same_body_does_not_duplicate(vault):
    add_note(vault, "10_Journaling/a.md", PLAIN)
    calls = {"n": 0}

    def flaky(rel, text, established, existing, titles):
        # the model is non-deterministic: same atom body, different title each run
        calls["n"] += 1
        title = "Same Atom" if calls["n"] == 1 else "Same Atom, retitled"
        return {"summary": "s", "applied": [], "review_tags": [], "rejected_tags": [],
                "extractions": [{"title": title, "body": "one body", "tags": [], "reason": "r"}],
                "skipped_extractions": [], "review": []}, None

    run.run_intelligent_digest(vault, model=flaky)

    # crash simulation: state lost, note re-processed, model non-deterministic
    (vault / "99_Machine/wattson/state.json").unlink()
    rep2 = run.run_intelligent_digest(vault, model=flaky)
    envs = list((vault / "99_Machine/wattson/proposals").glob("*.json"))
    assert len(envs) == 1  # duplicate suppressed (same source + body)
    assert rep2.atoms_proposed == 0
    assert rep2.notes[0]["extractions"][0]["deduped"] is True

    # user edits the source note: the pending proposal is refreshed in place
    (vault / "10_Journaling/a.md").write_text(PLAIN + "\nNew line.\n")
    rep3 = run.run_intelligent_digest(vault, model=flaky)
    envs = list((vault / "99_Machine/wattson/proposals").glob("*.json"))
    assert len(envs) == 1
    env = json.loads(envs[0].read_text())
    assert env["source"]["fingerprint"] == \
        state.fingerprint((vault / "10_Journaling/a.md").read_bytes())
    assert rep3.notes[0]["extractions"][0]["refreshed"] is True


def test_run_model_failure_is_durable_and_retried(vault):
    add_note(vault, "10_Journaling/a.md", DAILY)
    flaky = {"n": 0}

    def model(rel, text, established, existing, titles):
        flaky["n"] += 1
        if flaky["n"] == 1:
            return None, "model call failed: boom"
        return {"summary": "s", "applied": [], "review_tags": [], "rejected_tags": [],
                "extractions": [], "skipped_extractions": [], "review": []}, None

    rep1 = run.run_intelligent_digest(vault, model=model)
    assert len(rep1.failures) == 1
    st = state.load_state(vault)
    e = st["notes"]["10_Journaling/a.md"]
    assert e["status"] == "failed" and "boom" in e["last_error"]
    assert e["fingerprint"] is None  # old fp kept: retried next run

    rep2 = run.run_intelligent_digest(vault, model=model)
    assert not rep2.failures and flaky["n"] == 2
    assert state.load_state(vault)["notes"]["10_Journaling/a.md"]["status"] == "processed"


def test_accept_proposal_writes_atom_and_link(vault, tmp_path):
    add_note(vault, "10_Journaling/2026-10-10.md", DAILY)
    st = state.load_state(vault)
    c = detect.classify(vault, st)
    fp = c["added"][0]["fingerprint"]
    pid = proposals.proposal_id("Loud voice", "A loud voice is not a well-sourced one.")
    env = proposals.make_envelope(pid, "10_Journaling/2026-10-10.md", fp,
                                  {"title": "Loud voice",
                                   "body": "A loud voice is not a well-sourced one.",
                                   "tags": ["area/society/disinformation"], "reason": "r"},
                                  "Sat, Oct 10")
    proposals.save_envelope(vault, env)

    rendered = {}

    def fake_render(note, out_path):
        rendered["note"] = note
        out_path.write_text("---\ntags:\n  - \"type/atom\"\n---\n\n# Loud voice\n\nbody\n")

    out = proposals.accept(vault, pid, render_fn=fake_render)
    assert (vault / out["atom_path"]).exists()
    assert rendered["note"]["relations"] == [{"type": "derived-from", "target": "Sat, Oct 10"}]

    src = (vault / "10_Journaling/2026-10-10.md").read_text()
    assert "## Extracted" in src and "- [[Loud voice]]" in src

    assert proposals.load_envelope(vault, pid)["proposals"][0]["status"] == "accepted"
    with pytest.raises(proposals.ProposalError):
        proposals.accept(vault, pid, render_fn=fake_render)


def test_accept_rejects_stale_source(vault):
    p = add_note(vault, "10_Journaling/2026-10-10.md", DAILY)
    fp = state.fingerprint(p.read_bytes())
    pid = proposals.proposal_id("Loud voice", "A loud voice is not a well-sourced one.")
    proposals.save_envelope(vault, proposals.make_envelope(
        pid, "10_Journaling/2026-10-10.md", fp,
        {"title": "Loud voice", "body": "A loud voice is not a well-sourced one.",
         "tags": ["area/society/disinformation"], "reason": "r"},
        "Sat, Oct 10"))
    # user rewrite removes the quoted passage -> the extraction is no longer faithful
    p.write_text(DAILY.replace("A loud voice is not a well-sourced one.", "rewritten entirely"))
    with pytest.raises(proposals.ProposalError, match="source changed"):
        proposals.accept(vault, pid, render_fn=lambda n, p: None)


def test_accept_reanchors_superficial_source_change(vault, tmp_path):
    # regression: our own tag append (or a sibling '## Extracted' backlink)
    # changes the source fingerprint but leaves the quoted body intact ->
    # the proposal must be re-anchored, not rejected
    p = add_note(vault, "10_Journaling/2026-10-10.md", DAILY)
    fp = state.fingerprint(p.read_bytes())
    pid = proposals.proposal_id("Loud voice", "A loud voice is not a well-sourced one.")
    env = proposals.make_envelope(
        pid, "10_Journaling/2026-10-10.md", fp,
        {"title": "Loud voice", "body": "A loud voice is not a well-sourced one.",
         "tags": ["area/society/disinformation"], "reason": "r"},
        "Sat, Oct 10")
    proposals.save_envelope(vault, env)
    apply.apply_tags_checked(vault, "10_Journaling/2026-10-10.md", fp,
                             ["area/society/disinformation"])

    rendered = {}

    def fake_render(note, out_path):
        rendered["note"] = note
        out_path.write_text("---\ntags:\n  - \"type/atom\"\n---\n\n# Loud voice\n\nbody\n")

    out = proposals.accept(vault, pid, render_fn=fake_render)
    assert (vault / out["atom_path"]).exists()
    # envelope re-anchored to the post-tag-append fingerprint (accept then
    # appends the '## Extracted' backlink, so strip it to compare)
    env2 = proposals.load_envelope(vault, pid)
    pre_backlink = p.read_text().replace("\n## Extracted\n- [[Loud voice]]\n", "")
    assert env2["source"]["fingerprint"] == state.fingerprint(pre_backlink.encode("utf-8"))
    assert env2["source"]["fingerprint"] != fp  # actually re-anchored, not original
    assert env2["proposals"][0]["status"] == "accepted"


def test_reject_proposal(vault):
    pid = proposals.proposal_id("X", "body")
    proposals.save_envelope(vault, proposals.make_envelope(
        pid, "a.md", "a" * 64,
        {"title": "X", "body": "body", "tags": ["area/tech/ai"], "reason": "r"}, "T"))
    proposals.reject(vault, pid)
    assert proposals.load_envelope(vault, pid)["proposals"][0]["status"] == "rejected"
    with pytest.raises(proposals.ProposalError):
        proposals.reject(vault, pid)


def test_make_envelope_sanitizes_bracketed_source_title(vault):
    # regression: Obsidian headings can carry brackets (e.g. status markers),
    # which are invalid as ETK wikilink targets
    pid = proposals.proposal_id("Flow theory", "verbatim body text")
    env = proposals.make_envelope(
        pid, "a.md", "a" * 64,
        {"title": "Flow theory", "body": "verbatim body text",
         "tags": ["area/tech/ai"], "reason": "r"},
        "**[shipped] Practice Stripe via API worksheets**")
    proposals.save_envelope(vault, env)
    n = proposals.load_envelope(vault, pid)["proposals"][0]["note"]
    assert n["links"] == ["**shipped Practice Stripe via API worksheets**"]
    assert n["relations"] == [{"type": "derived-from",
                               "target": "**shipped Practice Stripe via API worksheets**"}]


def test_save_envelope_rejects_bracketed_link_target(vault):
    env = {
        "source": {"path": "a.md", "fingerprint": "a" * 64},
        "proposals": [{
            "proposalId": "atom-x-deadbeef",
            "status": "pending_review",
            "note": {
                "noteType": "atom", "title": "X", "body": "b",
                "tags": ["type/atom"], "links": ["bad [target]"],
                "relations": [], "created": "2026-10-12",
            },
        }],
    }
    with pytest.raises(ValueError, match="brackets not allowed"):
        proposals.save_envelope(vault, env)


def test_state_save_load_roundtrip_and_corruption(tmp_path):
    st = state.empty_state()
    state.record_processed(st, "a/b.md", "f" * 64, "text")
    state.record_failed(st, "c.md", None, "t", "err")
    state.record_deleted(st, "c.md")
    state.save_state(tmp_path, st)
    st2 = state.load_state(tmp_path)
    assert st2["notes"]["a/b.md"]["fingerprint"] == "f" * 64
    assert "c.md" not in st2["notes"]
    (tmp_path / "99_Machine/wattson/state.json").write_text("{corrupt")
    assert state.load_state(tmp_path) == state.empty_state()
