"""Orchestrate one intelligent digest pass over the changed notes of a vault."""
from datetime import datetime, timezone

from . import apply, config, detect, proposals, semantics, state


class Report:
    """Everything the digest note and stdout need to say about this run."""

    def __init__(self):
        self.skipped = False
        self.skip_reason = ""
        self.examined = 0
        self.notes = []        # per-note entries (changed notes only)
        self.tagged = 0
        self.atoms_proposed = 0
        self.failures = []     # [{path, error}]
        self.deleted = []
        self.state_errors = []

    def to_dict(self):
        return {
            "skipped": self.skipped,
            "skip_reason": self.skip_reason,
            "examined": self.examined,
            "tagged": self.tagged,
            "atoms_proposed": self.atoms_proposed,
            "notes": self.notes,
            "failures": self.failures,
            "deleted": self.deleted,
            "state_errors": self.state_errors,
        }


def _existing_titles(vault):
    titles = set()
    for p in vault.rglob("*.md"):
        rel = p.relative_to(vault).as_posix()
        if any(rel.startswith(pref + "/") or rel == pref for pref in config.SKIP_PREFIXES):
            continue
        titles.add(p.stem.lower())
        try:
            head = p.read_text(encoding="utf-8", errors="replace")[:2000]
            t = semantics.note_title(head, "")
            if t:
                titles.add(t.lower())
        except OSError:
            pass
    return titles


def run_intelligent_digest(vault, model=None, skip=False, skip_reason=""):
    """Run the semantic pass. `model` overrides the model call (tests).

    model(note_path, note_text, established, existing, existing_titles) -> (result, err)
    Writes tag edits and proposal envelopes; updates sidecar state.
    """
    rep = Report()
    if skip:
        rep.skipped = True
        rep.skip_reason = skip_reason or "skipped"
        return rep

    cfg = config.load_config()
    established = config.established_tags()
    st = state.load_state(vault)
    changed = detect.classify(vault, st)
    rep.examined = changed["scan_count"]
    rep.deleted = changed["deleted"]
    for rel in changed["deleted"]:
        state.record_deleted(st, rel)

    if model is None:
        model = lambda path, text, est, ex, titles: semantics.call_and_validate(
            cfg, path, text, est, ex, titles)

    existing_titles = _existing_titles(vault)
    call_count = 0

    for item in changed["added"] + changed["modified"]:
        rel, fp, text = item["path"], item["fingerprint"], item["text"]
        entry = state.note_entry(st, rel)
        existing = semantics.existing_tags(text)
        res, err = model(rel, text, established, existing, existing_titles)
        call_count += 1
        note_rec = {
            "path": rel,
            "append_only": item.get("append_only", False),
            "summary": "",
            "applied": [],
            "review_tags": [],
            "rejected_tags": [],
            "extractions": [],
            "skipped_extractions": [],
            "review": [],
            "error": "",
        }
        rep.notes.append(note_rec)
        if err or res is None:
            note_rec["error"] = err or "no result"
            rep.failures.append({"path": rel, "error": note_rec["error"]})
            state.record_failed(st, rel, fp, text, note_rec["error"])
            continue

        note_rec.update({
            "summary": res.get("summary", ""),
            # copy the model's lists: note_rec["extractions"] is appended to
            # below, and it must not mutate the list the loop iterates over
            "applied": list(res.get("applied", [])),
            "review_tags": list(res.get("review_tags", [])),
            "rejected_tags": list(res.get("rejected_tags", [])),
            "extractions": list(res.get("extractions", [])),
            "skipped_extractions": list(res.get("skipped_extractions", [])),
            "review": list(res.get("review", [])),
        })

        tags_to_apply = [t["tag"] for t in res.get("applied", [])]
        if tags_to_apply:
            try:
                if apply.apply_tags_checked(vault, rel, fp, tags_to_apply):
                    rep.tagged += 1
                    # our own edit changed the note on disk: track the new
                    # fingerprint/text so the next run sees it as processed
                    data = (vault / rel).read_bytes()
                    fp = state.fingerprint(data)
                    text = data.decode("utf-8", "replace")
            except apply.StaleError as e:
                note_rec["error"] = str(e)
                rep.failures.append({"path": rel, "error": str(e)})
                state.record_failed(st, rel, fp, text, str(e))
                continue
            except OSError as e:
                note_rec["error"] = f"write failed: {e}"
                rep.failures.append({"path": rel, "error": note_rec["error"]})
                state.record_failed(st, rel, fp, text, note_rec["error"])
                continue

        source_title = semantics.note_title(text, rel.rsplit("/", 1)[-1].removesuffix(".md"))
        for ext in res.get("extractions", []):
            pid = proposals.proposal_id(ext["title"], ext["body"])
            env = proposals.make_envelope(pid, rel, fp, ext, source_title)
            existing_env = proposals.envelope_path(vault, pid)
            if existing_env.exists():
                prev = None
                try:
                    prev = proposals.load_envelope(vault, pid)
                except (OSError, ValueError):
                    prev = None
                if prev and prev["proposals"][0]["status"] == "pending_review" \
                        and prev["source"]["fingerprint"] == fp:
                    continue  # identical pending proposal already on file
                # stale or resolved duplicate: refresh under a fresh id
                pid = proposals.proposal_id(ext["title"], ext["body"] + datetime.now(timezone.utc).isoformat())
                env = proposals.make_envelope(pid, rel, fp, ext, source_title)
            proposals.save_envelope(vault, env)
            rep.atoms_proposed += 1
            note_rec["extractions"].append({**ext, "proposalId": pid, "source": rel})

        state.record_processed(st, rel, fp, text)

    try:
        state.save_state(vault, st)
    except OSError as e:
        rep.state_errors.append(f"state save failed: {e}")

    rep.model_calls = call_count
    return rep
