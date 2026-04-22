# AI Code Maniac - Multi-Agent Code Analysis Platform
# Copyright (C) 2026 B.Vignesh Kumar (Bravetux) <ic19939@gmail.com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.
#
# Author: B.Vignesh Kumar aka Bravetux
# Email:  ic19939@gmail.com
# Developed: 22nd April 2026

"""Deterministic load-profile builder.

Subagent for F6 (perf_test_generator). Produces fixed numeric constants
(virtual users, ramp-up, steady state, think time, target rps) so the
LLM only composes framework syntax around them instead of hallucinating
timings. Three targets: small / medium / large.
"""

from __future__ import annotations

_TARGETS = {
    "small":  {"vus": 10,  "ramp": 30,  "steady": 120, "think_ms": 500},
    "medium": {"vus": 50,  "ramp": 60,  "steady": 300, "think_ms": 500},
    "large":  {"vus": 200, "ramp": 120, "steady": 600, "think_ms": 300},
}


def build_profile(num_endpoints: int, target: str = "medium") -> dict:
    """Return the fixed load-profile block for the named target."""
    t = _TARGETS.get(target) or _TARGETS["medium"]
    think_s = max(t["think_ms"] / 1000.0, 0.001)
    base_rps = t["vus"] / think_s
    scale = max(num_endpoints, 1) / 5.0
    target_rps = max(int(round(base_rps * scale)), 1)
    return {
        "virtual_users":        t["vus"],
        "ramp_up_seconds":      t["ramp"],
        "steady_state_seconds": t["steady"],
        "think_time_ms":        t["think_ms"],
        "target_rps":           target_rps,
    }
