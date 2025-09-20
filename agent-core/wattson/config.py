import os, sys

VAULT_PATH = os.environ.get("WATTSON_VAULT")
if not VAULT_PATH:
    print("WATTSON_VAULT is not set. Configure it in your environment or .env", file=sys.stderr)
    sys.exit(2)

SCHEMA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "schema"))
ONTOLOGY_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "ontology"))
