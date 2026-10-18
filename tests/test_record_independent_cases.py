"""Offline checks for independently authored inputs, without reference outputs."""
from dataclasses import FrozenInstanceError, replace
import hashlib
import json
import os
import re
from pathlib import Path
import subprocess
import sys

import pytest
from scripts import narrator_record_derivation as derivation
from scripts import narrator_record_independent_cases as independent
from scripts import narrator_record_quote_evidence as quote


def _rewrite(tmp_path, monkeypatch, mutate):
    document = json.loads(independent.CORPUS_PATH.read_bytes())
    mutate(document)
    path = tmp_path / "cases.json"
    path.write_text(json.dumps(document, ensure_ascii=False), encoding="utf-8")
    monkeypatch.setattr(independent, "CORPUS_PATH", path)
    monkeypatch.setattr(independent, "CORPUS_SHA256", hashlib.sha256(path.read_bytes()).hexdigest())


def test_cases_have_exact_order_and_independent_origin(monkeypatch):
    def no_old_cases():
        raise AssertionError("Historical API cases must not be loaded")
    monkeypatch.setattr(derivation, "load_fixed_cases", no_old_cases)
    cases = independent.load_independent_cases()
    assert type(cases) is tuple and len(cases) == 2
    assert tuple(c.case_id for c in cases) == ("uncertain-signal", "sensory-evidence")
    assert [(c.episode_id, c.turn_id) for c in cases] == [
        ("independent-uncertainty", "derive-uncertainty"),
        ("independent-sensory", "derive-sensory")]
    assert cases[0].narrative == "A luz de uma luminária acesa ilumina o interior da biblioteca, que está vazia naquele momento. Um ruído vindo de trás da estante sugere que algum mecanismo talvez esteja funcionando ali."
    assert cases[1].narrative == "No interior da oficina deserta, há um cheiro de tinta fresca que permanece no ar daquele lugar. Sobre a bancada da oficina, uma lâmpada de cor azul pisca de maneira intermitente."
    for index, case in enumerate(cases):
        assert type(case) is derivation.DerivationCase
        assert case.player_input == "Onde estou?" and case.outcome == "unresolved" and case.scene is None
        assert case.source["origin"] == "agent_authored_synthetic_cases"
        assert case.source["corpus_id"] == "storyteller-record-independent-cases-v1"
        assert case.source["corpus_file"] == "evals/narrator/record_independent_cases_v1.json"
        assert case.source["corpus_sha256"] == independent.CORPUS_SHA256
        assert case.source["case_path"] == f"/cases/{index}"
        assert case.source["case_id"] == case.case_id
        assert case.source["narrative_sha256"] == hashlib.sha256(case.narrative.encode()).hexdigest()
        assert case.source["protected_secrets_count"] == 0
        assert not set(case.source) & {"batch_id", "candidate_id", "model", "jsonl_file", "evaluation_invocation_id"}
        independent.verify_independent_case(case)
    with pytest.raises(FrozenInstanceError):
        cases[0].narrative = "changed"


@pytest.mark.parametrize("index", [0, 1])
def test_existing_quote_packet_reconstructs_every_input_without_historical_reads(index, monkeypatch):
    def no_old_cases():
        raise AssertionError("Historical API cases must not be loaded")
    monkeypatch.setattr(derivation, "load_fixed_cases", no_old_cases)
    case = independent.load_independent_cases()[index]
    wire, audit = quote.build_evidence_packet(case)
    packet = json.loads(wire[len(quote.PACKET_PREFIX):])
    assert packet["schema"] == "storyteller.eval.record-evidence.v1"
    assert packet["fixed_narrative"]["text"] == case.narrative
    assert packet["player_input"]["text"] == case.player_input
    assert packet["expected_outcome"]["value"] == case.outcome
    assert packet["context"]["known_context"]["text"] == case.known_context
    assert packet["context"]["known_context"]["source"] == "original_synthetic_corpus"
    assert packet["context"]["scene_background"]["data"] is None
    units = audit["source_units"]
    assert [u["id"] for u in units] == ["n0", "n1", "a0", "m0", "c0"]
    assert "".join(u["text"] for u in units if u["origin"] == "narrative") == case.narrative
    for unit in units[:2]:
        assert case.narrative[unit["start"]:unit["end"]] == unit["text"]
    assert audit["version"] == "record-evidence-v1"
    assert audit["source"] == case.source
    assert audit["user_packet_sha256"] == hashlib.sha256(wire.encode()).hexdigest()
    assert audit["narrative_reconstructed_exactly"] is True
    assert audit["budget"]["estimated_tokens"] == (len(wire) + 3) // 4 <= 2000
    assert audit["budget"]["omitted_background_details"] == 0
    assert not set(packet) & {"records", "supports", "reference_output", "expected_response"}
    audit["source"]["case_id"] = "mutated audit"
    assert case.source["case_id"] == independent.CASE_IDS[index]


@pytest.mark.parametrize("field", ["case_id", "episode_id", "turn_id", "narrative", "player_input", "outcome", "known_context"])
def test_forged_case_cannot_reach_packet(field):
    case = independent.load_independent_cases()[0]
    altered = replace(case, **{field: getattr(case, field) + " changed"})
    with pytest.raises(independent.IndependentCasesError):
        independent.verify_independent_case(altered)
    with pytest.raises(quote.QuoteEvidenceEnvelopeError):
        quote.build_evidence_packet(altered)


def test_rehashing_forged_narrative_does_not_authorize_it():
    case = independent.load_independent_cases()[0]
    narrative = case.narrative + " Uma decisão é tomada."
    altered = replace(case, narrative=narrative, source=dict(case.source, narrative_sha256=hashlib.sha256(narrative.encode()).hexdigest()))
    with pytest.raises(independent.IndependentCasesError):
        independent.verify_independent_case(altered)


@pytest.mark.parametrize("field,value", [("case_id", "sensory-evidence"), ("protected_secrets_count", 1), ("protected_secrets_count", False), ("synthetic_only", 1), ("corpus_sha256", "0" * 64), ("origin", "model_generated")])
def test_mutating_source_is_rejected_without_poisoning_future_loads(field, value):
    case = independent.load_independent_cases()[0]
    case.source[field] = value
    with pytest.raises(independent.IndependentCasesError):
        independent.verify_independent_case(case)
    with pytest.raises(quote.QuoteEvidenceEnvelopeError):
        quote.build_evidence_packet(case)
    independent.verify_independent_case(independent.load_independent_cases()[0])


@pytest.mark.parametrize("missing", [False, True])
def test_frozen_file_drift_and_unavailability_are_safe(tmp_path, monkeypatch, missing):
    path = tmp_path / "changed.json"
    if not missing:
        path.write_bytes(independent.CORPUS_PATH.read_bytes() + b" ")
    monkeypatch.setattr(independent, "CORPUS_PATH", path)
    with pytest.raises(independent.IndependentCasesError) as captured:
        independent.load_independent_cases()
    assert captured.value.code in {"record_independent_cases_source_unavailable", "record_independent_cases_hash_mismatch"}
    assert "changed.json" not in str(captured.value)


@pytest.mark.parametrize("field,value", [("corpus_id", "other"), ("synthetic_only", False), ("synthetic_only", 1), ("origin", "model_generated"), ("cases", {}), ("reference_output", {})])
def test_forged_corpus_identity_is_refused_even_with_matching_new_hash(tmp_path, monkeypatch, field, value):
    _rewrite(tmp_path, monkeypatch, lambda document: document.update({field: value}))
    with pytest.raises(independent.IndependentCasesError, match="identity"):
        independent.load_independent_cases()


@pytest.mark.parametrize("mutation", ["reverse", "duplicate", "remove", "append"])
def test_exact_case_count_and_order_cannot_be_forged(tmp_path, monkeypatch, mutation):
    def mutate(document):
        cases = document["cases"]
        if mutation == "reverse": cases.reverse()
        if mutation == "duplicate": cases[1] = dict(cases[0])
        if mutation == "remove": cases.pop()
        if mutation == "append": cases.append(dict(cases[0]))
    _rewrite(tmp_path, monkeypatch, mutate)
    with pytest.raises(independent.IndependentCasesError, match="identity"):
        independent.load_independent_cases()


@pytest.mark.parametrize("field,value", [("case_id", "other"), ("narrative", "Other narrative."), ("narrative", None), ("narrative", 1), ("scene", {}), ("outcome", "success"), ("player_input", "Other input"), ("known_context", []), ("protected_secrets", ["Synthetic canary"]), ("records", {})])
def test_case_fields_and_types_are_checked_after_hash(tmp_path, monkeypatch, field, value):
    _rewrite(tmp_path, monkeypatch, lambda document: document["cases"][0].update({field: value}))
    with pytest.raises(independent.IndependentCasesError, match="identity"):
        independent.load_independent_cases()


def test_import_disables_dotenv_before_any_api_module_loads(tmp_path):
    script = r"""
import importlib.abc, os, sys
class Guard(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname == 'api' or fullname.startswith('api.'):
            assert os.environ.get('STORYTELLER_DISABLE_DOTENV') == '1'
        return None
sys.meta_path.insert(0, Guard())
from scripts import narrator_record_independent_cases
assert os.environ.get('STORYTELLER_DISABLE_DOTENV') == '1'
assert len(narrator_record_independent_cases.load_independent_cases()) == 2
"""
    environment = os.environ.copy()
    environment.pop("GROQ_API_KEY", None)
    environment.pop("STORYTELLER_DISABLE_DOTENV", None)
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    result = subprocess.run([sys.executable, "-c", script], cwd=Path(__file__).resolve().parents[1], env=environment, capture_output=True, text=True, timeout=20)
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize("index", [0, 1])
def test_fixed_narratives_satisfy_minimum_without_padding_the_player_question(index):
    case = independent.load_independent_cases()[index]
    words = re.findall(r"[^\W_]+(?:[-’'][^\W_]+)*", case.narrative, flags=re.UNICODE)
    assert len(words) >= 30


@pytest.mark.parametrize("index,location", [(0, "biblioteca"), (1, "oficina")])
def test_fixed_case_is_admissible_with_a_short_neutral_player_question(index, location):
    from api.scene_director_service import validate_scene_continuation
    from scripts.narrator_actor_contract import validate_actor_coherence
    case = independent.load_independent_cases()[index]
    _, audit = quote.build_evidence_packet(case)
    # Authored verification data only, never a corpus output or provider input.
    observed = audit["source_units"][0]["text"].strip()
    records = derivation.RecordDerivationProposal.model_validate({
        "o": "unresolved", "l": location, "s": observed, "p": [],
        "f": [{"k": "observation", "s": observed, "v": "public",
               "i": 0.5, "p": True, "a": []}],
        "t": [], "r": [], "q": "O que você faz agora?",
    })
    proposal = derivation.compose_derivation(case, records)
    assert proposal.narrative == case.narrative
    assert proposal.player_prompt == "O que você faz agora?"
    validate_actor_coherence(proposal, case.scene)
    validate_scene_continuation(proposal, facts=(), current_scene=case.scene, player_input=case.player_input)
