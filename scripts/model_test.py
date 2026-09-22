#!/usr/bin/env python3
"""Verify the WATTSON model provider (OpenAI-compatible /v1 endpoint).

Checks, in order:
  1. endpoint reachable and the configured model is listed
  2. plain chat completion returns content (thinking disabled)
  3. structured output: model returns exactly the requested JSON shape

Config comes from environment variables or wattson.env at the repo root.
Exits non-zero on any failure. Stdlib only.
"""

import json
import os
import sys
import time
import urllib.request

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENV_FILE = os.path.join(REPO_ROOT, "wattson.env")
DEFAULTS = {
    "WATTSON_MODEL_BASE_URL": "https://366ada1d.app.on.bigrock.dev/v1",
    "WATTSON_MODEL_NAME": "unsloth/Qwen3.8-27B-GGUF:UD-Q4_K_XL",
}
TIMEOUT = 180


def load_config():
    cfg = dict(DEFAULTS)
    if os.path.exists(ENV_FILE):
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


def http_json(url, payload=None, api_key=None, timeout=TIMEOUT):
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(url, data=data, method="POST" if data else "GET")
    req.add_header("Content-Type", "application/json")
    if api_key:
        req.add_header("Authorization", f"Bearer {api_key}")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


def main():
    cfg = load_config()
    base = cfg["WATTSON_MODEL_BASE_URL"]
    model = cfg["WATTSON_MODEL_NAME"]
    key = cfg.get("WATTSON_MODEL_API_KEY")
    results = []

    def record(name, ok, detail=""):
        results.append((name, ok))
        print(f"{'PASS' if ok else 'FAIL'}  {name}" + (f"  ({detail})" if detail else ""))

    # 1. model listed
    try:
        t0 = time.time()
        listing = http_json(f"{base}/models", api_key=key)
        ids = [m.get("id") for m in listing.get("data", [])]
        record("model-listed", model in ids,
               f"{len(ids)} model(s) in {time.time() - t0:.1f}s")
    except Exception as e:
        record("model-listed", False, str(e))
        finish(results)

    common = {
        "model": model,
        "temperature": 0,
        "chat_template_kwargs": {"enable_thinking": False},
    }

    # 2. plain completion
    try:
        t0 = time.time()
        d = http_json(
            f"{base}/chat/completions",
            {**common,
             "messages": [{"role": "user", "content": "Reply with exactly: PONG"}],
             "max_tokens": 60},
            api_key=key)
        msg = d["choices"][0]["message"]
        content = (msg.get("content") or "").strip()
        usage = d.get("usage", {})
        record("plain-completion", "PONG" in content.upper(),
               f"{usage.get('completion_tokens')} tok in {time.time() - t0:.1f}s")
    except Exception as e:
        record("plain-completion", False, str(e))

    # 3. structured JSON output (one retry on bad shape)
    schema_prompt = (
        "Return ONLY a JSON object with exactly these fields: "
        '"noteType" (string, must be "atom"), '
        '"title" (non-empty string), '
        '"tags" (array of exactly 2 strings), '
        '"ok" (boolean, must be true).'
    )
    ok = False
    detail = ""
    for attempt in (1, 2):
        try:
            t0 = time.time()
            d = http_json(
                f"{base}/chat/completions",
                {**common, "messages": [{"role": "user", "content": schema_prompt}],
                 "max_tokens": 400},
                api_key=key)
            content = (d["choices"][0]["message"].get("content") or "").strip()
            obj = json.loads(content)
            good = (
                obj.get("noteType") == "atom"
                and isinstance(obj.get("title"), str) and obj["title"]
                and isinstance(obj.get("tags"), list) and len(obj["tags"]) == 2
                and all(isinstance(t, str) for t in obj["tags"])
                and obj.get("ok") is True
            )
            detail = f"attempt {attempt}, {time.time() - t0:.1f}s, {content[:80]!r}"
            if good:
                ok = True
                break
        except Exception as e:
            detail = f"attempt {attempt}: {e}"
    record("structured-json", ok, detail)

    finish(results)


def finish(results):
    failed = [n for n, ok in results if not ok]
    print(f"\n{'FAILED: ' + ', '.join(failed) if failed else 'ALL CHECKS PASSED'}")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
