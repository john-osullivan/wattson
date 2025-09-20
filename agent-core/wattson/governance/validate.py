from __future__ import annotations
import frontmatter, json, jsonschema, pathlib

SCHEMA_PATH = pathlib.Path(__file__).resolve().parents[2] / "schema" / "etk.schema.json"
ENUMS_PATH  = pathlib.Path(__file__).resolve().parents[2] / "schema" / "enums.json"

def load_schema():
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        schema = json.load(f)
    # inline $refs to local enums (simple loader)
    with open(ENUMS_PATH, "r", encoding="utf-8") as f:
        enums = json.load(f)["properties"]
    # patch refs (kept minimal)
    schema["properties"]["type"]     = enums["type"]
    schema["properties"]["status"]   = enums["status"]
    schema["properties"]["maturity"] = enums["maturity"]
    schema["properties"]["horizon"]  = enums["horizon"]
    schema["properties"]["context"]  = enums["context"]
    return schema

def validate_note(path: pathlib.Path) -> list[str]:
    note = frontmatter.load(path)
    data = note.metadata or {}
    schema = load_schema()
    try:
        jsonschema.validate(instance=data, schema=schema)
        return []
    except jsonschema.ValidationError as e:
        return [f"{path}: {e.message}"]
