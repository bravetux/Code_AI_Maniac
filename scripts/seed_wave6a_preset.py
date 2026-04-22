"""One-off seed script — inserts the 'Wave 6A: API + Perf + Traceability' preset.

Run: python scripts/seed_wave6a_preset.py
"""

from __future__ import annotations

import sys

from db.connection import get_connection
from db.queries.presets import create_preset, list_presets


_PRESET_NAME = "Wave 6A: API + Perf + Traceability"
_PRESET_FEATURES = ["api_test_generator", "perf_test_generator", "traceability_matrix"]
_PRESET_PROMPT = (
    "Generate API tests, performance plan, and traceability matrix in a single run.\n"
    "Spec resolution honours __openapi_spec__; story resolution honours __mode__requirements.\n"
    "F10 auto-scans F5/F6 outputs from the same Reports/<ts>/ folder."
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
