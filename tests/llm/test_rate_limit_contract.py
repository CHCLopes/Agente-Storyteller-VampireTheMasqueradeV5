import math

import pytest
from pydantic import ValidationError

from api.llm.contract import RateLimitEvidence, RateLimitQuota
from scripts.evaluate_narrator_models import _safe_rate_limit_payload


def test_quota_evidence_round_trips_without_inferred_resource_or_legacy_bucket():
    quotas = (
        RateLimitQuota(resource="requests", window_seconds=86400, limit=1000,
                       remaining=994, reset_after_seconds=179.56),
        RateLimitQuota(resource="tokens", window_seconds=60, limit=8000,
                       remaining=0, reset_after_seconds=7.66),
    )
    evidence = RateLimitEvidence(quotas=quotas)
    assert evidence.resource is None
    assert evidence.limit is None
    assert evidence.remaining is None
    assert evidence.reset is None
    assert RateLimitEvidence.model_validate_json(evidence.model_dump_json()) == evidence
    payload = _safe_rate_limit_payload(evidence)
    assert payload["quotas"][0]["window_seconds"] == 86400
    assert payload["quotas"][1]["window_seconds"] == 60
    assert "resource" not in payload
    with pytest.raises(ValidationError):
        quotas[0].remaining = 0


@pytest.mark.parametrize("changes", [
    {"resource": "synthetic-secret"},
    {"window_seconds": 0},
    {"window_seconds": True},
    {"limit": "8000"},
    {"remaining": -1},
    {"remaining": True},
    {"reset_after_seconds": math.nan},
    {"reset_after_seconds": math.inf},
    {"reset_after_seconds": "synthetic-secret"},
    {"reset_after_seconds": True},
    {"raw_body": "synthetic-secret"},
])
def test_quota_contract_rejects_invalid_or_free_text_values(changes):
    values = {"resource": "tokens", "window_seconds": 60, "limit": 8000}
    with pytest.raises(ValidationError):
        RateLimitQuota(**(values | changes))


def test_replay_quota_metadata_drops_unapproved_keys_and_invalid_entries():
    safe = {"resource": "tokens", "window_seconds": 60, "limit": 8000,
            "remaining": 7000, "reset_after_seconds": 2.0}
    payload = _safe_rate_limit_payload({
        "origin": [],
        "resource": {"nested": "synthetic-secret"},
        "quotas": [
            safe | {"raw_body": "synthetic-secret"},
            safe | {"remaining": "synthetic-secret"},
            "synthetic-secret",
            safe | {"window_seconds": False},
        ],
    })
    assert payload["quotas"] == [safe]
    assert "resource" not in payload
    assert payload["origin"] == "unknown"
    assert "synthetic-secret" not in str(payload)


def test_unknown_quota_evidence_keeps_legacy_report_shape():
    assert _safe_rate_limit_payload(RateLimitEvidence()) == {
        "origin": "unknown", "limit": None, "remaining": None,
        "reset": None, "provider_code": None,
    }


def test_replay_preserves_explicit_resource_and_bounds_quota_count():
    quota = {"resource": "tokens", "window_seconds": 60, "limit": 8000}
    payload = _safe_rate_limit_payload({"resource": "tokens", "quotas": [quota] * 20})
    assert payload["resource"] == "tokens"
    assert len(payload["quotas"]) == 8
