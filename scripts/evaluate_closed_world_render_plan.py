"""Prepare and verify HYP-002 artifacts without network, RNG, or credentials."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import sys
import unicodedata
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
CORPUS = ROOT / "evals/narrator/closed_world_render_contract_v1.json"
PROTOCOL = ROOT / "evals/narrator/closed_world_render_contract_protocol_v1.md"
FIXTURES = ROOT / "evals/narrator/closed_world_render_plan_verifier_fixtures_v1.json"
BASE_PROMPT = ROOT / "evals/narrator/prompts/narrative-source-progress-v1.md"
CONTRACT_PROMPT = ROOT / "evals/narrator/prompts/closed-world-render-contract-v1.md"
IMPLEMENTATION_FILES = (
    "scripts/evaluate_closed_world_render_plan.py",
    "api/scene_director_service.py",
    "api/scene_resolution_service.py",
    "api/turn_models.py",
)
VERSION = "closed-world-render-contract-v1"
RESPONSE_VERSION = "closed-world-render-responses-v1"
CASE_CLASSES = (
    "wait_without_authorized_transition",
    "wait_with_one_authorized_environmental_transition",
    "known_object_state_inspection",
    "unknown_object_state_inspection",
    "resolved_favorable_mechanical_attempt",
    "resolved_unfavorable_mechanical_attempt",
    "protected_secret_with_authorized_clue",
    "ambiguous_action_preserving_next_choice",
)
FATAL_REVIEW_FIELDS = (
    "unlisted_render_claim",
    "player_agency_attribution",
    "unauthorized_secret_disclosure",
    "mechanical_result_expansion",
)
REVIEW_FIELDS = frozenset(
    (*FATAL_REVIEW_FIELDS, "continuity_material_repetition",
     "progression_observed", "coherent_hold_observed",
     "next_choice_preserved", "rationale")
)
RESPONSE_FIELDS = frozenset(
    ("case_id", "narrative", "rendered_unit_ids", "transition_id",
     "asserted_unknown_ids", "schema_valid", "capsule_link_valid", "review")
)


def _reject_constant(value: str) -> None:
    raise ValueError(f"non_finite_json_number:{value}")


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate_json_key:{key}")
        result[key] = value
    return result


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(
        path.read_text(encoding="utf-8"),
        object_pairs_hook=_unique_object,
        parse_constant=_reject_constant,
    )
    if not isinstance(value, dict):
        raise ValueError("json_root_must_be_object")
    return value


def _canonical_json(value: object) -> str:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
        allow_nan=False,
    )


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _value_sha256(value: object) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _normalized(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value.casefold())
    plain = "".join(char for char in decomposed if not unicodedata.combining(char))
    return " ".join(plain.split())


def _word_count(value: str) -> int:
    return len(re.findall(r"[^\W_]+(?:[-’'][^\W_]+)*", value, flags=re.UNICODE))


def _required_string(value: object, code: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(code)
    return value


def _unique_ids(items: object, key: str, code: str) -> tuple[str, ...]:
    if not isinstance(items, list):
        raise ValueError(code)
    ids = tuple(_required_string(item.get(key) if isinstance(item, dict) else None, code) for item in items)
    if len(ids) != len(set(ids)):
        raise ValueError(code)
    return ids


def validate_corpus(corpus: dict[str, Any]) -> dict[str, Any]:
    if corpus.get("version") != VERSION:
        raise ValueError("closed_world_render_version_invalid")
    if corpus.get("hypothesis_id") != "closed_world_render_plan_v1":
        raise ValueError("closed_world_render_hypothesis_invalid")
    budget = corpus.get("word_budget")
    if budget != {"minimum": 30, "maximum": 150}:
        raise ValueError("closed_world_render_word_budget_invalid")
    if tuple(corpus.get("fatal_criteria", ())) != (
        "unlisted_render_claim",
        "player_agency_attribution",
        "unauthorized_secret_disclosure",
        "mechanical_result_expansion",
        "target_or_provenance_mismatch",
        "schema_or_capsule_invalid",
        "hidden_retry_or_fallback",
    ):
        raise ValueError("closed_world_render_fatal_criteria_invalid")
    cases = corpus.get("cases")
    if not isinstance(cases, list) or len(cases) != len(CASE_CLASSES):
        raise ValueError("closed_world_render_case_count_invalid")
    case_ids = tuple(_required_string(case.get("case_id"), "case_id_invalid") for case in cases)
    if len(case_ids) != len(set(case_ids)) or tuple(corpus.get("case_order", ())) != case_ids:
        raise ValueError("closed_world_render_case_order_invalid")
    if tuple(case.get("case_class") for case in cases) != CASE_CLASSES:
        raise ValueError("closed_world_render_case_classes_invalid")

    for case in cases:
        _required_string(case.get("player_input"), "player_input_invalid")
        prior_case_id = case.get("prior_case_id")
        if prior_case_id is not None:
            if not isinstance(prior_case_id, str) or prior_case_id not in case_ids:
                raise ValueError("closed_world_render_prior_case_invalid")
            if case_ids.index(prior_case_id) >= case_ids.index(case["case_id"]):
                raise ValueError("closed_world_render_prior_case_invalid")
        required_ids = _unique_ids(case.get("required_units"), "unit_id", "required_units_invalid")
        optional_ids = _unique_ids(case.get("optional_units"), "unit_id", "optional_units_invalid")
        sensory_ids = _unique_ids(case.get("sensory_palette"), "unit_id", "sensory_palette_invalid")
        _unique_ids(case.get("unknowns"), "unknown_id", "unknowns_invalid")
        _unique_ids(case.get("forbidden_claims"), "claim_id", "forbidden_claims_invalid")
        _unique_ids(case.get("protected_secrets"), "secret_id", "protected_secrets_invalid")
        if not required_ids or set(required_ids) & set(optional_ids) or (
            set(required_ids) | set(optional_ids)
        ) & set(sensory_ids):
            raise ValueError("render_unit_ids_overlap_or_empty")
        for collection in (case["required_units"], case["optional_units"],
                           case["sensory_palette"], case["unknowns"]):
            for item in collection:
                _required_string(item.get("statement"), "closed_world_render_statement_invalid")
        transition = case.get("authorized_transition")
        transition_id = None
        if transition is not None:
            if not isinstance(transition, dict) or set(transition) != {
                "transition_id", "statement"
            }:
                raise ValueError("authorized_transition_invalid")
            transition_id = _required_string(
                transition.get("transition_id"), "authorized_transition_invalid"
            )
            _required_string(transition.get("statement"), "authorized_transition_invalid")
        boundary = case.get("player_action_boundary")
        if not isinstance(boundary, dict) or set(boundary) != {
            "declared_action", "forbidden_extensions"
        }:
            raise ValueError("player_action_boundary_invalid")
        _required_string(boundary.get("declared_action"), "player_action_boundary_invalid")
        extensions = boundary.get("forbidden_extensions")
        if not isinstance(extensions, list) or not extensions or any(
            not isinstance(item, str) or not item.strip() for item in extensions
        ):
            raise ValueError("player_action_boundary_invalid")
        _required_string(case.get("next_choice_boundary"), "next_choice_boundary_invalid")
        for collection in (case["forbidden_claims"], case["protected_secrets"]):
            for item in collection:
                _required_string(item.get("statement"), "closed_world_render_statement_invalid")
                markers = item.get("markers")
                if not isinstance(markers, list) or not markers or any(
                    not isinstance(marker, str) or not marker.strip() for marker in markers
                ):
                    raise ValueError("closed_world_render_markers_invalid")
        expected = case.get("expected")
        if not isinstance(expected, dict) or set(expected) != {
            "progression_required", "required_transition_id", "required_unit_ids"
        }:
            raise ValueError("closed_world_render_expected_invalid")
        if not isinstance(expected["progression_required"], bool):
            raise ValueError("closed_world_render_expected_invalid")
        required_transition = expected["required_transition_id"]
        if expected["progression_required"]:
            if transition_id is None or required_transition != transition_id:
                raise ValueError("required_transition_invalid")
        elif required_transition is not None or transition is not None:
            raise ValueError("unauthorized_transition_in_hold_case")
        required_units = expected["required_unit_ids"]
        if not isinstance(required_units, list) or tuple(required_units) != required_ids:
            raise ValueError("required_units_invalid")
    return corpus


def validate_verifier_fixtures(fixtures: dict[str, Any]) -> dict[str, Any]:
    if fixtures.get("version") != "closed-world-render-verifier-fixtures-v1":
        raise ValueError("closed_world_render_fixture_version_invalid")
    records = fixtures.get("fixtures")
    if not isinstance(records, list) or len(records) < 8:
        raise ValueError("closed_world_render_fixtures_invalid")
    ids = tuple(
        _required_string(item.get("fixture_id") if isinstance(item, dict) else None,
                         "closed_world_render_fixture_id_invalid")
        for item in records
    )
    if len(ids) != len(set(ids)):
        raise ValueError("closed_world_render_fixture_id_invalid")
    for item in records:
        _required_string(item.get("mutation"), "closed_world_render_fixture_mutation_invalid")
        if item.get("expected") not in {"integrity_error", "case_rejected"}:
            raise ValueError("closed_world_render_fixture_expected_invalid")
    return fixtures


def _prompt_body(path: Path) -> str:
    document = path.read_text(encoding="utf-8")
    matched = re.match(r"\A---\r?\n.*?\r?\n---(?:\r?\n)+", document, re.DOTALL)
    if matched is None:
        raise ValueError("closed_world_render_prompt_frontmatter_invalid")
    body = document[matched.end():].strip()
    if not body:
        raise ValueError("closed_world_render_prompt_body_invalid")
    return body


def render_system_prompt() -> str:
    return _prompt_body(BASE_PROMPT) + "\n\n" + _prompt_body(CONTRACT_PROMPT)


def render_case_payload(case: dict[str, Any]) -> dict[str, Any]:
    """Return only request-visible context; verifier markers stay offline."""

    return {
        "protocol": VERSION,
        "case_id": case["case_id"],
        "player_action": case["player_input"],
        "attributed_source": (
            None if case["prior_case_id"] is None else {
                "case_id": case["prior_case_id"],
                "content": "<candidate-confirmed-source-bound-at-runtime>",
            }
        ),
        "closed_world_render_plan": {
            "required_units": case["required_units"],
            "optional_units": case["optional_units"],
            "authorized_transition": case["authorized_transition"],
            "player_action_boundary": case["player_action_boundary"],
            "unknowns": case["unknowns"],
            "forbidden_claims": [
                {"claim_id": item["claim_id"], "statement": item["statement"]}
                for item in case["forbidden_claims"]
            ],
            "sensory_palette": case["sensory_palette"],
            "next_choice_boundary": case["next_choice_boundary"],
            "protected_secrets": [
                {"secret_id": item["secret_id"], "statement": item["statement"]}
                for item in case["protected_secrets"]
            ],
        },
    }


def prepare_protocol() -> dict[str, Any]:
    corpus = validate_corpus(_load_json(CORPUS))
    fixtures = validate_verifier_fixtures(_load_json(FIXTURES))
    inputs = {
        "corpus": {"file": CORPUS.relative_to(ROOT).as_posix(), "sha256": _sha256(CORPUS)},
        "protocol": {"file": PROTOCOL.relative_to(ROOT).as_posix(), "sha256": _sha256(PROTOCOL)},
        "verifier_fixtures": {
            "file": FIXTURES.relative_to(ROOT).as_posix(), "sha256": _sha256(FIXTURES),
        },
        "base_prompt": {
            "file": BASE_PROMPT.relative_to(ROOT).as_posix(), "sha256": _sha256(BASE_PROMPT),
        },
        "contract_prompt": {
            "file": CONTRACT_PROMPT.relative_to(ROOT).as_posix(), "sha256": _sha256(CONTRACT_PROMPT),
        },
        "implementation": [
            {"file": name, "sha256": _sha256(ROOT / name)} for name in IMPLEMENTATION_FILES
        ],
    }
    system_prompt = render_system_prompt()
    templates = []
    for case in corpus["cases"]:
        payload = render_case_payload(case)
        body = {
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": _canonical_json(payload)},
            ],
            "response_schema": "narrative-source-v1",
        }
        templates.append(
            {
                "case_id": case["case_id"],
                "is_live_request": False,
                "target": None,
                "user_payload_sha256": _value_sha256(payload),
                "body_sha256": _value_sha256(body),
            }
        )
    return {
        "protocol": VERSION,
        "hypothesis_id": corpus["hypothesis_id"],
        "prepared_offline": True,
        "synthetic_only": True,
        "provider_calls": 0,
        "live_inference_authorized": False,
        "target_selected": False,
        "runtime_default_eligible": False,
        "cap_001_status": "proposed_for_this_protocol",
        "inputs": inputs,
        "word_budget": corpus["word_budget"],
        "fatal_criteria": corpus["fatal_criteria"],
        "case_count": len(corpus["cases"]),
        "verifier_fixture_count": len(fixtures["fixtures"]),
        "case_order": corpus["case_order"],
        "cases": [
            {
                "case_id": case["case_id"],
                "case_class": case["case_class"],
                "sha256": _value_sha256(case),
                "progression_required": case["expected"]["progression_required"],
                "prior_case_id": case["prior_case_id"],
            }
            for case in corpus["cases"]
        ],
        "request_templates": templates,
        "response_contract": {
            "version": RESPONSE_VERSION,
            "required_response_fields": sorted(RESPONSE_FIELDS),
            "required_review_fields": sorted(REVIEW_FIELDS),
            "semantic_review_required": True,
        },
    }


def _markers(case: dict[str, Any]) -> tuple[str, ...]:
    return tuple(
        _normalized(marker)
        for collection in (case["forbidden_claims"], case["protected_secrets"])
        for item in collection
        for marker in item["markers"]
    )


def _verify_case(case: dict[str, Any], response: dict[str, Any], budget: dict[str, int]) -> dict[str, Any]:
    reasons: list[str] = []
    if set(response) != RESPONSE_FIELDS:
        raise ValueError(f"response_fields_invalid:{case['case_id']}")
    if response.get("case_id") != case["case_id"]:
        raise ValueError("response_case_order_invalid")
    narrative = _required_string(response.get("narrative"), "response_narrative_invalid")
    count = _word_count(narrative)
    if count < budget["minimum"] or count > budget["maximum"]:
        reasons.append("word_budget_failed")

    allowed_units = {
        item["unit_id"]
        for field in ("required_units", "optional_units", "sensory_palette")
        for item in case[field]
    }
    rendered = response.get("rendered_unit_ids")
    if not isinstance(rendered, list) or len(rendered) != len(set(rendered)) or not set(rendered).issubset(allowed_units):
        raise ValueError(f"rendered_unit_ids_invalid:{case['case_id']}")
    if not set(case["expected"]["required_unit_ids"]).issubset(rendered):
        reasons.append("required_render_unit_failed")

    asserted = response.get("asserted_unknown_ids")
    if not isinstance(asserted, list) or any(not isinstance(value, str) for value in asserted):
        raise ValueError(f"asserted_unknown_ids_invalid:{case['case_id']}")
    unknown = {item["unknown_id"] for item in case["unknowns"]}
    if set(asserted) & unknown:
        reasons.append("unknown_content_asserted")

    transition = response.get("transition_id")
    required_transition = case["expected"]["required_transition_id"]
    authorized = case["authorized_transition"]
    authorized_id = authorized["transition_id"] if authorized is not None else None
    if transition is not None and transition != authorized_id:
        reasons.append("unauthorized_transition")
    if transition != required_transition:
        reasons.append("required_transition_failed")

    if response.get("schema_valid") is not True or response.get("capsule_link_valid") is not True:
        reasons.append("schema_or_capsule_invalid")
    normalized = _normalized(narrative)
    if any(marker in normalized for marker in _markers(case)):
        reasons.append("forbidden_marker_observed")

    review = response.get("review")
    if not isinstance(review, dict) or set(review) != REVIEW_FIELDS:
        raise ValueError(f"review_fields_invalid:{case['case_id']}")
    if any(review.get(field) is not False for field in FATAL_REVIEW_FIELDS):
        reasons.append("fatal_semantic_gate_failed")
    if review.get("continuity_material_repetition") is not False:
        reasons.append("continuity_repetition_failed")
    if not isinstance(review.get("rationale"), str) or not review["rationale"].strip():
        raise ValueError(f"review_rationale_invalid:{case['case_id']}")
    if case["expected"]["progression_required"]:
        if review.get("progression_observed") is not True:
            reasons.append("progression_review_failed")
    elif review.get("coherent_hold_observed") is not True:
        reasons.append("coherent_hold_review_failed")
    if not isinstance(review.get("progression_observed"), bool) or not isinstance(review.get("coherent_hold_observed"), bool):
        raise ValueError(f"review_boolean_invalid:{case['case_id']}")
    if review.get("next_choice_preserved") is not True:
        reasons.append("next_choice_not_preserved")

    return {
        "case_id": case["case_id"],
        "word_count": count,
        "passed": not reasons,
        "reasons": reasons,
    }


def verify_responses(document: dict[str, Any]) -> dict[str, Any]:
    prepared = prepare_protocol()
    corpus = validate_corpus(_load_json(CORPUS))
    if document.get("version") != RESPONSE_VERSION or document.get("protocol") != VERSION:
        raise ValueError("response_protocol_invalid")
    if document.get("input_hashes") != {
        "corpus_sha256": prepared["inputs"]["corpus"]["sha256"],
        "protocol_sha256": prepared["inputs"]["protocol"]["sha256"],
    }:
        raise ValueError("response_input_hashes_invalid")
    target = document.get("target")
    if not isinstance(target, dict) or set(target) != {"requested", "reported"}:
        raise ValueError("response_target_invalid")
    if not isinstance(target["requested"], dict) or target["requested"] != target["reported"]:
        raise ValueError("target_or_provenance_mismatch")
    for field in ("target_id", "provider", "model", "reasoning"):
        _required_string(target["requested"].get(field), "response_target_invalid")
    invocation = document.get("invocation")
    if invocation != {"retry_count": 0, "fallback_used": False}:
        raise ValueError("hidden_retry_or_fallback")
    responses = document.get("responses")
    if not isinstance(responses, list) or tuple(
        item.get("case_id") if isinstance(item, dict) else None for item in responses
    ) != tuple(corpus["case_order"]):
        raise ValueError("response_case_order_invalid")
    results = [
        _verify_case(case, response, corpus["word_budget"])
        for case, response in zip(corpus["cases"], responses, strict=True)
    ]
    return {
        "protocol": VERSION,
        "target": target["requested"],
        "case_count": len(results),
        "passed_count": sum(item["passed"] for item in results),
        "failed_count": sum(not item["passed"] for item in results),
        "qualified_in_protocol": all(item["passed"] for item in results),
        "runtime_default_eligible": False,
        "human_admission_required": True,
        "cases": results,
    }


def _render(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--preflight", action="store_true")
    mode.add_argument("--verify", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    result = prepare_protocol() if args.preflight else verify_responses(_load_json(args.verify))
    rendered = _render(result)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0 if args.preflight or result["qualified_in_protocol"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
