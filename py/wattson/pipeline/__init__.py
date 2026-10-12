"""WATTSON intelligent vault pipeline (tagging + atom extraction proposals).

Stdlib-only so it runs under system python3 from scripts/vault_digest.py.
Validation of ETK note shapes uses the generated JSON Schema tag enum as the
single source of truth for established tags.
"""

__all__ = [
    "config",
    "state",
    "detect",
    "semantics",
    "apply",
    "proposals",
    "run",
]
