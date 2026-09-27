import json
from pathlib import Path

import pytest
from pydantic import TypeAdapter, ValidationError

from wattson.etk.generated.models import EtkNote

REPO_ROOT = Path(__file__).resolve().parents[2]
GOLDEN_DIR = REPO_ROOT / "test" / "golden"
INVALID_DIR = REPO_ROOT / "test" / "invalid"

note_adapter = TypeAdapter(EtkNote)


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
