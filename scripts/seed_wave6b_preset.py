"""One-off seed script — inserts the 'Wave 6B: Code-Gen & Fixes' preset.

Run: python scripts/seed_wave6b_preset.py
"""

from __future__ import annotations

import sys

from db.connection import get_connection
from db.queries.presets import create_preset, list_presets


_PRESET_NAME = "Wave 6B: Code-Gen & Fixes"
_PRESET_FEATURES = ["self_healing_agent", "sonar_fix_agent",
                    "sql_generator", "auto_fix_agent"]
_PRESET_PROMPT = (
    "Generate patches for UI test selectors, Sonar issues, NL→SQL, and "
    "code auto-fix in a single run.\n"
    "F9 expects __page_html__ or sibling dom.html; F11 accepts "
    "__sonar_issues__ / JSON source / SONAR_URL env; F14 expects "
    "__prompt__ + DDL schema; F15 auto-scans Bug Analysis / Refactoring "
    "Advisor output from the same Reports/<ts>/ run or __findings__ prefix."
)


def main() -> int:
    conn = get_connection()
    existing = list_presets(conn)
    if any(p.get("name") == _PRESET_NAME for p in existing):
        print(f"Preset '{_PRESET_NAME}' already exists — skipping.")
        return 0
    for feat in _PRESET_FEATURES:
        create_preset(conn, name=_PRESET_NAME, feature=feat,
                      system_prompt=_PRESET_PROMPT,
                      extra_instructions="")
    print(f"Seeded '{_PRESET_NAME}' across {len(_PRESET_FEATURES)} features.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
