"""Paths, model config, and the OpenAI-compatible client for the pipeline."""
import json
import os
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
ENV_FILE = REPO_ROOT / "wattson.env"
SCHEMA_FILE = REPO_ROOT / "schemas" / "generated" / "json-schema" / "etk-note.schema.json"

MACHINE_DIR = "99_Machine/wattson"
STATE_FILE = "99_Machine/wattson/state.json"
PROPOSAL_DIR = "99_Machine/wattson/proposals"

# Directories never processed semantically.
SKIP_PREFIXES = (".obsidian", "99_Machine", "91_Attachments", "img_import", ".trash")

DEFAULTS = {
    "WATTSON_MODEL_BASE_URL": "https://366ada1d.app.on.bigrock.dev/v1",
    "WATTSON_MODEL_NAME": "unsloth/Qwen3.8-27B-GGUF:UD-Q4_K_XL",
}
TIMEOUT = int(os.environ.get("WATTSON_MODEL_TIMEOUT", "180"))
NOTE_CHAR_LIMIT = 16000
LAST_TEXT_LIMIT = 65536
APPLY_CONFIDENCE = 0.7

# Render an ETK note JSON to markdown with the deterministic Knap renderer.
RENDER_CMD = ["npx", "tsx", "src/cli.ts", "render"]


def load_config():
    cfg = dict(DEFAULTS)
    if ENV_FILE.exists():
        with open(ENV_FILE) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                cfg[k.strip()] = v.strip()
    for k in list(DEFAULTS) + ["WATTSON_MODEL_API_KEY"]:
        if os.environ.get(k):
            cfg[k] = os.environ[k]
    cfg["WATTSON_MODEL_BASE_URL"] = cfg["WATTSON_MODEL_BASE_URL"].rstrip("/")
    return cfg


def established_tags():
    """Closed tag enum from the generated JSON Schema (source: ontology.yaml)."""
    with open(SCHEMA_FILE) as f:
        schema = json.load(f)
    return set(schema["$defs"]["tag"]["enum"])


def http_json(url, payload=None, api_key=None, timeout=TIMEOUT):
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(url, data=data, method="POST" if data else "GET")
    req.add_header("Content-Type", "application/json")
    if api_key:
        req.add_header("Authorization", f"Bearer {api_key}")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


def chat_completion(cfg, prompt, max_tokens=2000, retries=1):
    """One chat completion, parsed as JSON. Returns (obj, error_string)."""
    payload = {
        "model": cfg["WATTSON_MODEL_NAME"],
        "temperature": 0,
        "max_tokens": max_tokens,
        "chat_template_kwargs": {"enable_thinking": False},
        "messages": [
            {"role": "system", "content": "You are WATTSON, a personal knowledge vault assistant. You always reply with a single JSON object and nothing else."},
            {"role": "user", "content": prompt},
        ],
    }
    key = cfg.get("WATTSON_MODEL_API_KEY")
    last_err = ""
    for _ in range(retries + 1):
        try:
            d = http_json(f"{cfg['WATTSON_MODEL_BASE_URL']}/chat/completions", payload, api_key=key)
            content = (d["choices"][0]["message"].get("content") or "").strip()
            if content.startswith("```"):
                lines = content.splitlines()
                if lines and lines[0].startswith("```"):
                    lines = lines[1:]
                if lines and lines[-1].strip() == "```":
                    lines = lines[:-1]
                content = "\n".join(lines)
            return json.loads(content), None
        except Exception as e:
            last_err = str(e)
    return None, last_err
