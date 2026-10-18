from __future__ import annotations

import ast
from copy import deepcopy
import json

import pytest

from scripts import evaluate_closed_world_render_plan as evaluation


def _narrative(case: dict) -> str:
    parts = [
        item["statement"]
        for field in ("required_units", "optional_units", "sensory_palette")
        for item in case[field]
    ]
    if case["authorized_transition"] is not None:
        parts.append(case["authorized_transition"]["statement"])
    parts.append(case["next_choice_boundary"])
    value = " ".join(parts)
    while evaluation._word_count(value) < 30:
        value += " " + case["next_choice_boundary"]
    return value


def _document() -> dict:
    corpus = evaluation.validate_corpus(evaluation._load_json(evaluation.CORPUS))
    prepared = evaluation.prepare_protocol()
    target = {
        "target_id": "synthetic-target-v1",
        "provider": "synthetic-provider",
        "model": "synthetic-model",
        "reasoning": "none",
    }
    responses = []
    for case in corpus["cases"]:
        progression = case["expected"]["progression_required"]
        responses.append(
            {
                "case_id": case["case_id"],
                "narrative": _narrative(case),
                "rendered_unit_ids": [
                    item["unit_id"]
                    for field in ("required_units", "optional_units", "sensory_palette")
                    for item in case[field]
                ],
                "transition_id": case["expected"]["required_transition_id"],
                "asserted_unknown_ids": [],
                "schema_valid": True,
                "capsule_link_valid": True,
                "review": {
                    "unlisted_render_claim": False,
                    "player_agency_attribution": False,
                    "unauthorized_secret_disclosure": False,
                    "mechanical_result_expansion": False,
                    "continuity_material_repetition": False,
                    "progression_observed": progression,
                    "coherent_hold_observed": not progression,
                    "next_choice_preserved": True,
                    "rationale": "Fixture sintética coerente com o contrato congelado.",
                },
            }
        )
    return {
        "version": evaluation.RESPONSE_VERSION,
        "protocol": evaluation.VERSION,
        "input_hashes": {
            "corpus_sha256": prepared["inputs"]["corpus"]["sha256"],
            "protocol_sha256": prepared["inputs"]["protocol"]["sha256"],
        },
        "target": {"requested": target, "reported": deepcopy(target)},
        "invocation": {"retry_count": 0, "fallback_used": False},
        "responses": responses,
    }


def test_preflight_freezes_eight_distinct_cases_and_remains_non_operational():
    prepared = evaluation.prepare_protocol()

    assert prepared["prepared_offline"] is True
    assert prepared["synthetic_only"] is True
    assert prepared["provider_calls"] == 0
    assert prepared["live_inference_authorized"] is False
    assert prepared["target_selected"] is False
    assert prepared["runtime_default_eligible"] is False
    assert prepared["case_count"] == 8
    assert prepared["verifier_fixture_count"] == 10
    assert len({item["sha256"] for item in prepared["cases"]}) == 8
    assert all(len(item["sha256"]) == 64 for item in prepared["cases"])
    assert all(len(item["sha256"]) == 64 for item in prepared["inputs"]["implementation"])


def test_valid_review_artifact_is_qualified_only_inside_protocol():
    result = evaluation.verify_responses(_document())

    assert result["qualified_in_protocol"] is True
    assert result["passed_count"] == 8
    assert result["failed_count"] == 0
    assert result["runtime_default_eligible"] is False
    assert result["human_admission_required"] is True


def test_request_templates_are_target_neutral_and_exclude_verifier_markers():
    prepared = evaluation.prepare_protocol()
    corpus = evaluation.validate_corpus(evaluation._load_json(evaluation.CORPUS))
    system = evaluation.render_system_prompt()

    assert system.startswith(evaluation._prompt_body(evaluation.BASE_PROMPT))
    assert system.endswith(evaluation._prompt_body(evaluation.CONTRACT_PROMPT))
    assert not system.startswith("---")
    assert len(prepared["request_templates"]) == 8
    assert all(item["target"] is None and item["is_live_request"] is False for item in prepared["request_templates"])
    assert len({item["body_sha256"] for item in prepared["request_templates"]}) == 8
    for case in corpus["cases"]:
        serialized = evaluation._canonical_json(evaluation.render_case_payload(case))
        assert '"markers"' not in serialized
        assert '"expected"' not in serialized


def test_only_wait_progression_case_depends_on_prior_candidate_source():
    corpus = evaluation.validate_corpus(evaluation._load_json(evaluation.CORPUS))
    payloads = {
        case["case_id"]: evaluation.render_case_payload(case)
        for case in corpus["cases"]
    }

    assert payloads["authorized-single-bell"]["attributed_source"] == {
        "case_id": "hold-silent-bell",
        "content": "<candidate-confirmed-source-bound-at-runtime>",
    }
    assert all(
        payload["attributed_source"] is None
        for case_id, payload in payloads.items()
        if case_id != "authorized-single-bell"
    )


@pytest.mark.parametrize(
    ("mutation", "expected_error"),
    [
        (lambda doc: doc["target"]["reported"].update(model="other"), "target_or_provenance_mismatch"),
        (lambda doc: doc["invocation"].update(retry_count=1), "hidden_retry_or_fallback"),
        (lambda doc: doc["input_hashes"].update(corpus_sha256="0" * 64), "response_input_hashes_invalid"),
    ],
)
def test_integrity_mutations_fail_closed(mutation, expected_error):
    document = _document()
    mutation(document)

    with pytest.raises(ValueError, match=expected_error):
        evaluation.verify_responses(document)


@pytest.mark.parametrize(
    ("mutate", "reason"),
    [
        (
            lambda doc: doc["responses"][0]["review"].update(
                unlisted_render_claim=True
            ),
            "fatal_semantic_gate_failed",
        ),
        (
            lambda doc: doc["responses"][0].update(
                asserted_unknown_ids=["bell-purpose"]
            ),
            "unknown_content_asserted",
        ),
        (
            lambda doc: doc["responses"][0].update(
                narrative=doc["responses"][0]["narrative"] + " O sino toca."
            ),
            "forbidden_marker_observed",
        ),
        (
            lambda doc: doc["responses"][1].update(transition_id=None),
            "required_transition_failed",
        ),
        (
            lambda doc: doc["responses"][0].update(narrative="palavra " * 151),
            "word_budget_failed",
        ),
        (
            lambda doc: doc["responses"][0].update(rendered_unit_ids=[]),
            "required_render_unit_failed",
        ),
        (
            lambda doc: doc["responses"][0]["review"].update(
                next_choice_preserved=False
            ),
            "next_choice_not_preserved",
        ),
    ],
)
def test_case_mutations_are_rejected_without_changing_artifact_integrity(mutate, reason):
    document = _document()
    mutate(document)

    result = evaluation.verify_responses(document)

    assert result["qualified_in_protocol"] is False
    assert result["failed_count"] >= 1
    assert reason in {item_reason for case in result["cases"] for item_reason in case["reasons"]}


def test_progression_and_hold_reviews_are_both_required():
    progressing = _document()
    progressing["responses"][1]["review"]["progression_observed"] = False
    holding = _document()
    holding["responses"][0]["review"]["coherent_hold_observed"] = False

    progression_result = evaluation.verify_responses(progressing)
    hold_result = evaluation.verify_responses(holding)

    assert "progression_review_failed" in progression_result["cases"][1]["reasons"]
    assert "coherent_hold_review_failed" in hold_result["cases"][0]["reasons"]


def test_response_order_and_closed_fields_are_enforced():
    reordered = _document()
    reordered["responses"][0], reordered["responses"][1] = (
        reordered["responses"][1], reordered["responses"][0]
    )
    extra = _document()
    extra["responses"][0]["unreviewed"] = True

    with pytest.raises(ValueError, match="response_case_order_invalid"):
        evaluation.verify_responses(reordered)
    with pytest.raises(ValueError, match="response_fields_invalid"):
        evaluation.verify_responses(extra)


def test_json_loader_rejects_duplicate_keys_and_non_finite_numbers(tmp_path):
    duplicate = tmp_path / "duplicate.json"
    duplicate.write_text('{"version":"a","version":"b"}', encoding="utf-8")
    non_finite = tmp_path / "non-finite.json"
    non_finite.write_text('{"value":NaN}', encoding="utf-8")

    with pytest.raises(ValueError, match="duplicate_json_key"):
        evaluation._load_json(duplicate)
    with pytest.raises(ValueError, match="non_finite_json_number"):
        evaluation._load_json(non_finite)


def test_fixture_matrix_matches_the_proved_mutation_surface():
    fixtures = evaluation.validate_verifier_fixtures(
        evaluation._load_json(evaluation.FIXTURES)
    )

    assert {item["expected"] for item in fixtures["fixtures"]} == {
        "integrity_error", "case_rejected"
    }
    assert {item["fixture_id"] for item in fixtures["fixtures"]} == {
        "target-mismatch",
        "hidden-retry",
        "input-hash-mismatch",
        "unlisted-render-claim",
        "unknown-content-asserted",
        "forbidden-marker",
        "required-transition-missing",
        "required-unit-missing",
        "next-choice-lost",
        "word-budget-exceeded",
    }


def test_offline_preparer_has_no_network_or_credential_access():
    tree = ast.parse(evaluation.__file__ and open(evaluation.__file__, encoding="utf-8").read())
    imports = {
        alias.name.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, (ast.Import, ast.ImportFrom))
        for alias in node.names
    }
    source = open(evaluation.__file__, encoding="utf-8").read()

    assert imports.isdisjoint({"httpx", "requests", "urllib", "socket"})
    assert "getenv" not in source
    assert "os.environ" not in source
    assert "api_key" not in source
    assert ".env" not in source


def test_cli_preflight_is_json_and_keyless(capsys):
    assert evaluation.main(["--preflight"]) == 0
    result = json.loads(capsys.readouterr().out)

    assert result["provider_calls"] == 0
    assert result["live_inference_authorized"] is False
    assert "target" not in result
