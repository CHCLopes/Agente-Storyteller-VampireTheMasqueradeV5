"""Offline contract checks for two independent, immutable derivation fixtures."""

from dataclasses import FrozenInstanceError, replace
import hashlib
import json

import pytest
from pydantic import ValidationError

from api.scene_director_service import validate_scene_continuation
from scripts.narrator_actor_contract import validate_actor_coherence
from scripts import narrator_record_derivation as derivation


def _records(case):
    if case.episode_id == "opening":
        summary = "Um sussurro distante ecoa no corredor."
        location, actors, roster = "Corredor de pedra", [], []
    else:
        summary = "Mara desliza um papel amassado sobre o balcão."
        location = case.scene.location
        actors, roster = [{"n": "Mara", "p": "present"}], ["Mara"]
    return {"o": case.outcome, "l": location, "s": summary, "p": roster,
            "f": [{"k": "observation", "s": summary, "v": "public", "i": 0.5,
                   "p": True, "a": actors}], "t": [], "r": [], "q": "O que você faz agora?"}


def test_fixed_cases_are_only_the_two_registered_independent_inputs():
    cases = derivation.load_fixed_cases()
    assert isinstance(cases, tuple)
    assert [(c.episode_id, c.turn_id) for c in cases] == [
        ("opening", "establish-scene"), ("player-agency", "world-reacts-player-remains-free")]
    assert cases[0].scene is None
    assert cases[1].scene.last_turn == 14
    assert cases[1].scene.open_threads == ("Descobrir se Mara entregará o endereço",)
    assert [c.source["line_number"] for c in cases] == [3, 9]
    assert all(c.source["jsonl_sha256"] == derivation.SOURCE_JSONL_SHA256 for c in cases)
    assert all(c.source["narrative_sha256"] == hashlib.sha256(c.narrative.encode()).hexdigest() for c in cases)
    with pytest.raises(FrozenInstanceError):
        cases[0].narrative = "Alterada"


@pytest.mark.parametrize("index", [0, 1])
def test_user_packet_keeps_all_original_visible_input_and_no_previous_derivatives(index):
    case = derivation.load_fixed_cases()[index]
    wire, audit = derivation.build_derivation_packet(case)
    packet = json.loads(wire[len(derivation.PACKET_PREFIX):])
    assert packet["fixed_narrative"]["text"] == case.narrative
    assert packet["player_input"]["text"] == case.player_input
    assert packet["expected_outcome"]["value"] == case.outcome
    assert packet["context"]["known_context"]["text"] == case.known_context
    assert packet["context"]["scene_background"]["data"] == (
        case.scene.model_dump(mode="json") if case.scene else None)
    assert set(packet) == {"schema", "fixed_narrative", "player_input", "expected_outcome", "context"}
    assert set(packet["context"]) == {"known_context", "scene_background"}
    assert audit["user_packet_sha256"] == hashlib.sha256(wire.encode()).hexdigest()
    assert audit["budget"]["estimated_tokens"] == (len(wire) + 3) // 4
    assert audit["budget"]["estimated_tokens"] <= 2000
    assert audit["budget"]["omitted_background_details"] == 0
    audit["source"]["line_number"] = -1
    assert case.source["line_number"] in {3, 9}


@pytest.mark.parametrize("field", ["narrative", "player_input", "known_context", "outcome", "case_id", "episode_id", "turn_id"])
def test_modified_case_is_refused_before_build_or_composition(field):
    case = derivation.load_fixed_cases()[0]
    altered = replace(case, **{field: getattr(case, field) + " adulterado"})
    with pytest.raises(derivation.DerivationContractError):
        derivation.build_derivation_packet(altered)
    with pytest.raises(derivation.DerivationContractError):
        derivation.compose_derivation(altered, derivation.RecordDerivationProposal.model_validate(_records(case)))


def test_mutated_nested_source_is_refused_without_poisoning_future_loads():
    case = derivation.load_fixed_cases()[0]
    case.source["line_number"] = 9
    with pytest.raises(derivation.DerivationContractError):
        derivation.build_derivation_packet(case)
    assert derivation.load_fixed_cases()[0].source["line_number"] == 3


def test_altered_previous_scene_is_refused():
    case = derivation.load_fixed_cases()[1]
    altered = replace(case, scene=case.scene.model_copy(update={"location": "Outro lugar"}))
    with pytest.raises(derivation.DerivationContractError):
        derivation.build_derivation_packet(altered)


@pytest.mark.parametrize("path_constant", ["SOURCE_JSONL_PATH", "SOURCE_CORPUS_PATH"])
def test_source_drift_is_refused(path_constant, tmp_path, monkeypatch):
    source = getattr(derivation, path_constant)
    changed = tmp_path / source.name
    changed.write_bytes(source.read_bytes() + b" ")
    monkeypatch.setattr(derivation, path_constant, changed)
    with pytest.raises(derivation.DerivationContractError):
        derivation.load_fixed_cases()


@pytest.mark.parametrize("field,value", [("batch_id", "other"), ("episode_id", "warehouse-continuity"),
    ("admitted", False), ("kind", "narrative_skip"), ("candidate_id", "other"), ("repetition", 2)])
def test_row_identity_is_checked_after_hash_verification(field, value, tmp_path, monkeypatch):
    rows = derivation.SOURCE_JSONL_PATH.read_text(encoding="utf-8").splitlines()
    row = json.loads(rows[2])
    row[field] = value
    rows[2] = json.dumps(row, ensure_ascii=False)
    changed = tmp_path / "changed.jsonl"
    changed.write_text("\n".join(rows), encoding="utf-8")
    monkeypatch.setattr(derivation, "SOURCE_JSONL_PATH", changed)
    monkeypatch.setattr(derivation, "SOURCE_JSONL_SHA256", hashlib.sha256(changed.read_bytes()).hexdigest())
    with pytest.raises(derivation.DerivationContractError):
        derivation.load_fixed_cases()


def test_protected_context_cannot_enter_the_two_public_fixtures(tmp_path, monkeypatch):
    corpus = json.loads(derivation.SOURCE_CORPUS_PATH.read_text(encoding="utf-8"))
    corpus["episodes"][0]["protected_secrets"] = ["Synthetic private canary"]
    changed = tmp_path / "changed.json"
    changed.write_text(json.dumps(corpus), encoding="utf-8")
    monkeypatch.setattr(derivation, "SOURCE_CORPUS_PATH", changed)
    corpus_sha = hashlib.sha256(changed.read_bytes()).hexdigest()
    monkeypatch.setattr(derivation, "SOURCE_CORPUS_SHA256", corpus_sha)
    rows = [json.loads(line) for line in derivation.SOURCE_JSONL_PATH.read_text(encoding="utf-8").splitlines()]
    for row in rows:
        row["corpus_sha256"] = corpus_sha
    changed_rows = tmp_path / "matching.jsonl"
    changed_rows.write_text("\n".join(json.dumps(row) for row in rows), encoding="utf-8")
    monkeypatch.setattr(derivation, "SOURCE_JSONL_PATH", changed_rows)
    monkeypatch.setattr(derivation, "SOURCE_JSONL_SHA256", hashlib.sha256(changed_rows.read_bytes()).hexdigest())
    with pytest.raises(derivation.DerivationContractError):
        derivation.load_fixed_cases()


def test_budget_overflow_rejects_instead_of_omitting_context(monkeypatch):
    case = derivation.load_fixed_cases()[1]
    monkeypatch.setattr(derivation, "USER_PACKET_TOKEN_BUDGET", 1)
    with pytest.raises(derivation.DerivationContractError, match="budget"):
        derivation.build_derivation_packet(case)


def test_schema_contains_only_required_derivatives_and_preserves_actor_contract():
    schema = derivation.RecordDerivationProposal.model_json_schema(by_alias=True)
    assert set(schema["properties"]) == set("olsp ftrq".replace(" ", ""))
    assert set(schema["required"]) == set(schema["properties"])
    assert schema["additionalProperties"] is False
    assert "a" in schema["$defs"]["FocusedSceneFact"]["required"]
    assert schema["$defs"]["SceneActor"]["additionalProperties"] is False


@pytest.mark.parametrize("field", ["o", "l", "s", "p", "f", "t", "r", "q"])
def test_no_derivative_can_be_silently_filled(field):
    payload = _records(derivation.load_fixed_cases()[0])
    del payload[field]
    with pytest.raises(ValidationError):
        derivation.RecordDerivationProposal.model_validate(payload)


@pytest.mark.parametrize("extra", ["n", "narrative", "explanation"])
def test_provider_cannot_return_or_replace_narrative(extra):
    payload = _records(derivation.load_fixed_cases()[0])
    payload[extra] = "Substituição não permitida."
    with pytest.raises(ValidationError):
        derivation.RecordDerivationProposal.model_validate(payload)


@pytest.mark.parametrize("index", [0, 1])
def test_composition_keeps_exact_original_n_and_existing_admission(index):
    case = derivation.load_fixed_cases()[index]
    records = derivation.RecordDerivationProposal.model_validate(_records(case))
    proposal = derivation.compose_derivation(case, records)
    assert proposal.narrative == case.narrative
    validate_actor_coherence(proposal, case.scene)
    validate_scene_continuation(proposal, facts=(), current_scene=case.scene, player_input=case.player_input)


def test_composition_preserves_a_different_outcome_for_admission_to_judge():
    case = derivation.load_fixed_cases()[0]
    payload = _records(case)
    payload["o"] = "success"
    records = derivation.RecordDerivationProposal.model_validate(payload)
    proposal = derivation.compose_derivation(case, records)
    assert proposal.outcome == "success"
    assert proposal.narrative == case.narrative


def test_prompt_body_is_loaded_without_metadata_and_has_no_fixture_answers():
    path, prompt = derivation.load_derivation_prompt()
    assert path.name == "record-derivation-v1.md"
    assert not prompt.startswith("---")
    assert "Mara" not in prompt and "corredor de pedra" not in prompt.casefold()
    assert "não" in prompt.casefold()


@pytest.mark.parametrize("field,value", [("a", None), ("a", [{"n": "Mara", "p": "unknown"}])])
def test_existing_actor_shape_remains_enforced(field, value):
    payload = _records(derivation.load_fixed_cases()[0])
    if value is None:
        del payload["f"][0][field]
    else:
        payload["f"][0][field] = value
    with pytest.raises(ValidationError):
        derivation.RecordDerivationProposal.model_validate(payload)


def test_composition_never_invents_a_fact_to_satisfy_forward_motion():
    case = derivation.load_fixed_cases()[0]
    payload = _records(case)
    payload["f"] = []
    records = derivation.RecordDerivationProposal.model_validate(payload)
    with pytest.raises(ValidationError):
        derivation.compose_derivation(case, records)
    assert records.new_facts == ()


def test_changing_narrative_and_its_reported_hash_cannot_replace_the_source():
    case = derivation.load_fixed_cases()[0]
    altered_n = case.narrative + " Um detalhe inventado surge."
    source = dict(case.source, narrative_sha256=hashlib.sha256(altered_n.encode()).hexdigest())
    altered = replace(case, narrative=altered_n, source=source)
    with pytest.raises(derivation.DerivationContractError):
        derivation.compose_derivation(altered, derivation.RecordDerivationProposal.model_validate(_records(case)))


def test_mutation_of_nested_source_is_rechecked_at_composition():
    case = derivation.load_fixed_cases()[0]
    derivation.build_derivation_packet(case)
    case.source["narrative_sha256"] = "0" * 64
    with pytest.raises(derivation.DerivationContractError):
        derivation.compose_derivation(case, derivation.RecordDerivationProposal.model_validate(_records(case)))


@pytest.mark.parametrize("content", ["Sem frontmatter.", "---\nname: changed\n---\nNovo SYSTEM."])
def test_prompt_drift_or_bad_metadata_is_rejected(content, tmp_path, monkeypatch):
    path = tmp_path / "prompt.md"
    path.write_text(content, encoding="utf-8")
    monkeypatch.setattr(derivation, "DERIVATION_PROMPT_PATH", path)
    with pytest.raises(derivation.DerivationContractError):
        derivation.load_derivation_prompt()
