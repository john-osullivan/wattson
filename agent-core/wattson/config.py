import os, sys

VAULT_PATH = os.environ.get("WATTSON_VAULT")
if not VAULT_PATH:
    print("WATTSON_VAULT is not set. Configure it in your environment or .env", file=sys.stderr)
    sys.exit(2)

SCHEMA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "schema"))
ONTOLOGY_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "ontology"))

LLM_ENABLED = os.environ.get("WATTSON_LLM_ENABLED", "1") == "1"
LLM_MODEL   = os.environ.get("WATTSON_LLM_MODEL", "gpt-4o-mini")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")  # or your local inference endpoint

APPLY_THRESHOLD   = float(os.environ.get("WATTSON_APPLY_THRESHOLD", "0.75"))
SUGGEST_THRESHOLD = float(os.environ.get("WATTSON_SUGGEST_THRESHOLD", "0.40"))
MAX_EXPANSIONS    = int(os.environ.get("WATTSON_MAX_EXPANSIONS", "3"))
