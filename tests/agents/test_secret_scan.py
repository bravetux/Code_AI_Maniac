import json
from unittest.mock import patch, MagicMock
from agents.secret_scan import run_secret_scan

SAMPLE_CODE = '''
import os
config = {
    "db_password": base64.b64decode("c3VwZXJfc2VjcmV0"),
    "api_key": os.getenv("API_KEY", "sk-fallback-1234567890abcdef"),
}
'''

PHASE0_FINDINGS = [
    {"line": 4, "type": "generic_api_key", "match": "sk-f...cdef",
     "confidence": "medium", "context": 'api_key": os.getenv(...)'}
]

MOCK_RESPONSE = json.dumps({
    "secrets": [
        {
            "line": 3,
            "type": "encoded_credential",
            "severity": "critical",
            "description": "Base64-encoded password assigned to config dict",
            "evidence": "base64.b64decode('c3Vw...') decodes to a password",
            "recommendation": "Use a secrets manager",
            "false_positive_risk": "low",
        }
    ],
    "phase0_validation": [
        {
            "line": 4,
            "phase0_type": "generic_api_key",
            "verdict": "confirmed",
            "reason": "Hardcoded fallback value in getenv call",
        }
    ],
    "narrative": "Code contains encoded secrets and hardcoded fallbacks.",
    "summary": "1 secret found, 1 Phase 0 finding confirmed.",
})


def test_run_secret_scan_structured_result(test_db):
    with patch("agents.secret_scan.Agent") as mock_cls:
        mock_agent = MagicMock()
        mock_agent.return_value = MOCK_RESPONSE
        mock_cls.return_value = mock_agent

        result = run_secret_scan(
            conn=test_db,
            job_id="test-job-1",
            file_path="config.py",
            content=SAMPLE_CODE,
            file_hash="fakehash",
            language="Python",
            custom_prompt=None,
            phase0_findings=PHASE0_FINDINGS,
            static_results=None,
        )

    assert "secrets" in result
    assert len(result["secrets"]) == 1
    assert result["secrets"][0]["severity"] == "critical"
    assert "phase0_validation" in result
    assert result["phase0_validation"][0]["verdict"] == "confirmed"


def test_run_secret_scan_uses_cache(test_db):
    from db.queries.jobs import create_job
    from tools.cache import write_cache
    job_id = create_job(test_db, source_type="local", source_ref="f.py",
                        language="Python", features=["secret_scan"])
    cached = {"secrets": [], "phase0_validation": [],
              "narrative": "", "summary": "from cache"}
    write_cache(test_db, job_id=job_id, feature="secret_scan:v1",
                file_hash="cached_hash", language="Python",
                custom_prompt=None, result=cached)

    with patch("agents.secret_scan.Agent") as mock_cls:
        result = run_secret_scan(
            conn=test_db, job_id=job_id,
            file_path="f.py", content="x = 1",
            file_hash="cached_hash", language="Python",
            custom_prompt=None, phase0_findings=[], static_results=None,
        )
        mock_cls.assert_not_called()

    assert result["summary"] == "from cache"
