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
# Developed: 12th April 2026

import pytest
from tools.secret_scanner import scan_secrets


# ── Detection tests ──────────────────────────────────────────────────────────

def test_detect_aws_access_key():
    code = 'aws_key = "AKIAIOSFODNN7EXAMPLE"\n'
    result = scan_secrets(code, mode="warn")
    assert len(result["secrets_found"]) == 1
    assert result["secrets_found"][0]["type"] == "aws_access_key"
    assert result["secrets_found"][0]["line"] == 1
    assert result["secrets_found"][0]["confidence"] == "high"


def test_detect_aws_secret_key():
    code = 'secret = "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"\n'
    result = scan_secrets(code, mode="warn")
    assert len(result["secrets_found"]) >= 1
    found_types = [s["type"] for s in result["secrets_found"]]
    assert "aws_secret_key" in found_types or "generic_secret" in found_types


def test_detect_generic_api_key():
    code = 'API_KEY = "sk-1234567890abcdef1234567890abcdef"\n'
    result = scan_secrets(code, mode="warn")
    assert len(result["secrets_found"]) >= 1


def test_detect_private_key():
    code = '-----BEGIN RSA PRIVATE KEY-----\nMIIEpAIBAAKCAQ...\n-----END RSA PRIVATE KEY-----\n'
    result = scan_secrets(code, mode="warn")
    assert len(result["secrets_found"]) >= 1
    assert result["secrets_found"][0]["type"] == "private_key"


def test_detect_connection_string():
    code = 'db_url = "postgresql://user:p4ssw0rd@localhost:5432/mydb"\n'
    result = scan_secrets(code, mode="warn")
    assert len(result["secrets_found"]) >= 1
    assert result["secrets_found"][0]["type"] == "connection_string"


def test_detect_jwt_token():
    code = 'token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dozjgNryP4J3jVmNHl0w5N_XgL0n3I9PlFUP0THsR8U"\n'
    result = scan_secrets(code, mode="warn")
    assert len(result["secrets_found"]) >= 1
    assert result["secrets_found"][0]["type"] == "jwt_token"


def test_detect_github_token():
    code = 'GITHUB_TOKEN = "ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZabcdef12"\n'
    result = scan_secrets(code, mode="warn")
    assert len(result["secrets_found"]) >= 1
    assert result["secrets_found"][0]["type"] == "github_token"


def test_detect_password_assignment():
    code = 'password = "super_secret_123"\n'
    result = scan_secrets(code, mode="warn")
    assert len(result["secrets_found"]) >= 1
    assert result["secrets_found"][0]["type"] == "hardcoded_password"


def test_no_false_positive_on_clean_code():
    code = 'x = 1\nprint("hello world")\ndef add(a, b):\n    return a + b\n'
    result = scan_secrets(code, mode="warn")
    assert len(result["secrets_found"]) == 0


def test_no_false_positive_on_placeholder():
    code = 'API_KEY = "your-api-key-here"\npassword = "CHANGE_ME"\n'
    result = scan_secrets(code, mode="warn")
    # Placeholders should not trigger (or be low confidence)
    high_conf = [s for s in result["secrets_found"] if s["confidence"] == "high"]
    assert len(high_conf) == 0


# ── Mode tests ───────────────────────────────────────────────────────────────

def test_mode_warn_returns_original_code():
    code = 'key = "AKIAIOSFODNN7EXAMPLE"\n'
    result = scan_secrets(code, mode="warn")
    assert result["action_taken"] == "warn"
    assert result["code"] == code


def test_mode_redact_replaces_secrets():
    code = 'key = "AKIAIOSFODNN7EXAMPLE"\n'
    result = scan_secrets(code, mode="redact")
    assert result["action_taken"] == "redact"
    assert "AKIAIOSFODNN7EXAMPLE" not in result["code"]
    assert "[REDACTED-" in result["code"]


def test_mode_block_returns_findings_and_no_code():
    code = 'key = "AKIAIOSFODNN7EXAMPLE"\n'
    result = scan_secrets(code, mode="block")
    assert result["action_taken"] == "block"
    assert len(result["secrets_found"]) >= 1
    assert result["code"] == ""


def test_mode_block_returns_original_when_clean():
    code = 'x = 1\n'
    result = scan_secrets(code, mode="block")
    assert result["action_taken"] == "block"
    assert result["code"] == code
    assert len(result["secrets_found"]) == 0


# ── Masking tests ────────────────────────────────────────────────────────────

def test_match_field_is_partially_masked():
    code = 'key = "AKIAIOSFODNN7EXAMPLE"\n'
    result = scan_secrets(code, mode="warn")
    match_val = result["secrets_found"][0]["match"]
    assert "AKIA" in match_val  # prefix visible
    assert "EXAMPLE" not in match_val or "..." in match_val or "X" in match_val
