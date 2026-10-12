"""Semantic pass: model call + deterministic validation of its output.

The model proposes; code decides. Anything that is not an established tag,
not verbatim, or not confident enough is rejected or parked for review.
"""
import json
import re

from . import config

RELATION_TYPES = {"supports", "contradicts", "cites", "applies-to", "derived-from", "related"}
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def existing_tags(text: str):
    """Tags already in a note's frontmatter (axis/value strings)."""
    tags = []
    if text.startswith("---\n"):
        end = text.find("\n---", 4)
        if end == -1:
            return tags
        in_tags = False
        for line in text[4:end].splitlines():
            if re.match(r"^tags:\s*$", line):
                in_tags = True
                continue
            if in_tags:
                m = re.match(r'^\s*-\s*"?([^"\n]+)"?\s*$', line)
                if m:
                    t = m.group(1).lstrip("#")
                    tags.append(t)
                    continue
                in_tags = False
    return tags


def note_title(text: str, fallback: str) -> str:
    m = re.search(r"^#\s+(.+)$", text, re.MULTILINE)
    return m.group(1).strip() if m else fallback


def is_etk_note(text: str) -> bool:
    return any(t.startswith("type/") for t in existing_tags(text))


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def verbatim_body(body: str, note_text: str):
    """Return the body to store (verbatim; whitespace-normalized if needed)
    or None when the body is not a passage of the note."""
    if body and body in note_text:
        return body.strip()
    nb, nt = _norm(body), _norm(note_text)
    if nb and nb in nt:
        return nb
    return None


def _title_exists(title: str, existing_titles) -> bool:
    t = title.lower().strip()
    slug = re.sub(r"\W+", "-", t).strip("-")
    return t in existing_titles or (slug and slug in existing_titles)


def build_prompt(tag_list, note_path, note_text, is_etk):
    axis_rule = (
        "- For this note only area/* and context/* tags are allowed (no type/, status/, maturity/, horizon/)."
        if not is_etk
        else "- Any axis tag from the list is allowed."
    )
    return f"""You are processing the vault note "{note_path}".

Note content:
<<<NOTE
{note_text[: config.NOTE_CHAR_LIMIT]}
NOTE>>>

JOB 1 - TAGS: choose 0-3 tags describing what this note is ABOUT, copied exactly from this established list (invent nothing):
{json.dumps(tag_list, indent=0)}
Rules:
- Prefer the most specific (longest) area tag that fits.
{axis_rule}
- Only include tags you are confident about; if you are torn between two, pick one and add a "review" entry with both options.

JOB 2 - ATOM EXTRACTIONS: an atom is one self-contained, durable idea from the note that deserves to exist as its own concept note.
- Propose 0-2. Most notes deserve 0.
- "body" MUST be an exact copy of a passage from the note content above (whitespace may be normalized, nothing else). Never paraphrase, summarize, or add words.
- "title": a short concept name, at most 8 words.
- "tags": 1-3 established tags for the atom (area/* preferred).

Reply with ONLY a JSON object, no markdown fences, exactly this shape:
{{"tags": [{{"tag": "area/...", "reason": "...", "confidence": 0.0, "needs_review": false}}],
  "extractions": [{{"title": "...", "tags": ["area/..."], "body": "...", "reason": "..."}}],
  "summary": "one sentence on what this note covers",
  "review": [{{"topic": "...", "options": ["area/...", "area/..."], "note": "why ambiguous"}}]}}"""


def validate_output(raw, note_text, note_path, established, existing, existing_titles):
    """Deterministically screen model output. Never raises on bad model data."""
    res = {
        "summary": "",
        "applied": [],     # [tag] safe to write
        "review_tags": [],  # [{tag, reason}]
        "rejected_tags": [],
        "extractions": [],  # ready-to-accept proposal payloads
        "skipped_extractions": [],  # [{title, why}]
        "review": [],
    }
    if not isinstance(raw, dict):
        res["error"] = "model reply was not a JSON object"
        return res

    summary = raw.get("summary")
    res["summary"] = summary.strip()[:300] if isinstance(summary, str) else ""

    for t in raw.get("tags") or []:
        if not isinstance(t, dict):
            continue
        tag = t.get("tag")
        reason = str(t.get("reason") or "")[:200]
        if not isinstance(tag, str) or tag.lstrip("#") not in established:
            res["rejected_tags"].append({"tag": str(tag), "why": "not an established tag"})
            continue
        tag = tag.lstrip("#")
        if tag in existing:
            continue
        if tag.startswith(("type/", "status/", "maturity/", "horizon/")) and not is_etk_note(note_text):
            res["rejected_tags"].append({"tag": tag, "why": "axis not allowed on non-ETK notes"})
            continue
        conf = t.get("confidence")
        try:
            conf = float(conf)
        except (TypeError, ValueError):
            conf = 0.0
        if t.get("needs_review") is True or conf < config.APPLY_CONFIDENCE:
            res["review_tags"].append({"tag": tag, "reason": reason or f"confidence {conf:.2f}"})
        else:
            res["applied"].append({"tag": tag, "reason": reason})

    for r in raw.get("review") or []:
        if isinstance(r, dict) and r.get("topic"):
            opts = [str(o) for o in (r.get("options") or [])][:5]
            res["review"].append({"topic": str(r["topic"])[:200], "options": opts, "note": str(r.get("note") or "")[:300]})

    for e in raw.get("extractions") or []:
        if not isinstance(e, dict):
            continue
        title = str(e.get("title") or "").strip()
        body = verbatim_body(str(e.get("body") or ""), note_text)
        why = None
        if not (1 <= len(title) <= 120):
            why = "bad title"
        elif body is None:
            why = "body is not a verbatim passage of the note"
        elif _title_exists(title, existing_titles):
            why = "a note with this title already exists"
        else:
            tags = [str(x).lstrip("#") for x in (e.get("tags") or []) if str(x).lstrip("#") in established]
            res["extractions"].append({
                "title": title,
                "body": body,
                "tags": tags,
                "reason": str(e.get("reason") or "")[:300],
            })
            continue
        res["skipped_extractions"].append({"title": title[:120] or "(untitled)", "why": why or "unknown"})

    return res


def call_and_validate(cfg, note_path, note_text, established, existing, existing_titles):
    """Model call + validation. Returns (result, error_string_or_None)."""
    prompt = build_prompt(sorted(established), note_path, note_text, is_etk_note(note_text))
    raw, err = config.chat_completion(cfg, prompt)
    if err:
        return None, f"model call failed: {err}"
    return validate_output(raw, note_text, note_path, established, existing, existing_titles), None
