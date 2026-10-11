import json
from pathlib import Path

import pytest
from pydantic import TypeAdapter, ValidationError

from wattson.etk.generated.models import EtkNote, EtkProposalEnvelope

REPO_ROOT = Path(__file__).resolve().parents[2]
GOLDEN_DIR = REPO_ROOT / "test" / "golden"
INVALID_DIR = REPO_ROOT / "test" / "invalid"
PROPOSAL_DIR = REPO_ROOT / "test" / "proposal"

note_adapter = TypeAdapter(EtkNote)
proposal_adapter = TypeAdapter(EtkProposalEnvelope)


def _golden_files():
    return sorted(GOLDEN_DIR.glob("*.json"))


def _invalid_files():
    return sorted(INVALID_DIR.glob("*.json"))


@pytest.mark.parametrize("path", _golden_files(), ids=lambda p: p.name)
def test_golden_fixture_roundtrips(path: Path):
    data = json.loads(path.read_text())
    note = note_adapter.validate_python(data)
    assert note.noteType == data["noteType"]
    assert note.title == data["title"]
    assert note.body == data["body"]
    # Round-trip: dump the model and re-validate the dumped form.
    again = note_adapter.validate_python(note.model_dump())
    assert again.model_dump() == note.model_dump()


@pytest.mark.parametrize("path", _invalid_files(), ids=lambda p: p.name)
def test_invalid_fixture_rejected(path: Path):
    data = json.loads(path.read_text())
    with pytest.raises(ValidationError):
        note_adapter.validate_python(data)


def test_proposal_envelope_accepted():
    data = json.loads((PROPOSAL_DIR / "envelope-valid.json").read_text())
    envelope = proposal_adapter.validate_python(data)
    assert len(envelope.proposals) == 2
    assert envelope.proposals[0].status == "pending_review"
    assert envelope.proposals[0].note.noteType == "atom"
    assert envelope.proposals[1].note.kind == "video"


def test_proposal_envelope_invalid_rejected():
    data = json.loads((PROPOSAL_DIR / "envelope-invalid.json").read_text())
    with pytest.raises(ValidationError):
        proposal_adapter.validate_python(data)
