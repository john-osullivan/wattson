import json
import sys
from pathlib import Path

# Make the repo's `wattson` package importable even without an editable install.
PY_ROOT = Path(__file__).resolve().parents[1]
if str(PY_ROOT) not in sys.path:
    sys.path.insert(0, str(PY_ROOT))
