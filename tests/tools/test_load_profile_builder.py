import pytest
from tools.load_profile_builder import build_profile


def test_profile_returns_required_fields():
    p = build_profile(num_endpoints=5)
    for key in ("virtual_users", "ramp_up_seconds", "steady_state_seconds",
                "think_time_ms", "target_rps"):
        assert key in p, key
        assert isinstance(p[key], (int, float))


def test_medium_profile_defaults():
    p = build_profile(num_endpoints=5, target="medium")
    assert p["virtual_users"] == 50
    assert p["ramp_up_seconds"] == 60
    assert p["steady_state_seconds"] == 300
    assert p["think_time_ms"] == 500


def test_small_profile_has_fewer_vus_than_medium():
    assert build_profile(3, "small")["virtual_users"] < build_profile(3, "medium")["virtual_users"]


def test_large_profile_has_more_vus_than_medium():
    assert build_profile(3, "large")["virtual_users"] > build_profile(3, "medium")["virtual_users"]


def test_unknown_target_falls_back_to_medium():
    assert build_profile(3, target="ludicrous") == build_profile(3, target="medium")


def test_rps_scales_with_endpoint_count():
    assert build_profile(10)["target_rps"] > build_profile(2)["target_rps"]


def test_zero_endpoints_still_returns_safe_defaults():
    p = build_profile(0)
    assert p["target_rps"] >= 1
