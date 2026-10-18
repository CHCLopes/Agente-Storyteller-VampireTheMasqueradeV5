"""Authored offline controls; no expected response is sent to the candidate."""
from dataclasses import replace
import hashlib
import json

import pytest
from pydantic import ValidationError

from scripts import narrator_record_derivation as derivation
from scripts import narrator_record_evidence as evidence


def _authored_envelope(case):
    """Compact representations, not observations or mandatory paraphrases."""
    if case.case_id == "opening":
        summary = "O corredor tem pedra fria; um sussurro sugere possível observação distante."
        records = {
            "o": case.outcome, "l": "corredor de pedra fria", "s": summary, "p": [],
            "f": [{"k": "observation", "s": "Um sussurro sugere possível observação distante.",
                   "v": "public", "i": 0.5, "p": False, "a": []}],
            "t": ["Há algo ou alguém observando ao longe?"], "r": [],
            "q": "O que você faz agora?",
        }
        sources = [
            ("/o", 0, len(records["o"]), ["m0"], "established"),
            ("/l", 0, len(records["l"]), ["n0"], "established"),
            ("/s", 0, summary.index(";"), ["n0"], "established"),
            ("/s", summary.index(";") + 2, len(summary), ["n0"], "suggested"),
            ("/f/0/s", 0, len(records["f"][0]["s"]), ["n0"], "suggested"),
            ("/t/0", 0, len(records["t"][0]), ["n0"], "suggested"),
        ]
    else:
        summary = "Mara desliza um papel no balcão; a sirene ecoa na rua."
        records = {
            "o": case.outcome, "l": case.scene.location, "s": summary, "p": ["Mara"],
            "f": [
                {"k": "npc_action", "s": "Mara desliza um papel amassado sobre o balcão.",
                 "v": "public", "i": 0.5, "p": True, "a": [{"n": "Mara", "p": "present"}]},
                {"k": "observation", "s": "A sirene ecoa na rua.",
                 "v": "public", "i": 0.3, "p": False, "a": []},
            ],
            "t": ["Descobrir se Mara entregará o endereço"], "r": [],
            "q": "O que você faz agora?",
        }
        sources = [
            ("/o", 0, len(records["o"]), ["m0"], "established"),
            ("/l", 0, len(records["l"]), ["c1"], "established"),
            ("/p/0", 0, 4, ["c3", "n0"], "established"),
            ("/s", 0, summary.index(";"), ["n1"], "established"),
            ("/s", summary.index(";") + 2, len(summary), ["n2"], "established"),
            ("/f/0/s", 0, len(records["f"][0]["s"]), ["n1"], "established"),
            ("/f/1/s", 0, len(records["f"][1]["s"]), ["n2"], "established"),
            ("/t/0", 0, len(records["t"][0]), ["c5"], "unresolved"),
        ]
    return {"records": records, "supports": [
        {"p": path, "b": start, "e": end, "s": ids, "m": modality}
        for path, start, end, ids, modality in sources
    ]}


def _packet(case):
    wire, audit = evidence.build_evidence_packet(case)
    return wire, json.loads(wire[len(evidence.PACKET_PREFIX):]), audit


@pytest.mark.parametrize("index", [0, 1])
def test_authored_complete_envelopes_fit_the_same_estimated_output_budget(index):
    case = derivation.load_fixed_cases()[index]
    envelope = evidence.RecordEvidenceProposal.model_validate(_authored_envelope(case))
    before = envelope.model_dump(mode="json", by_alias=True)
    audit = evidence.validate_supports(case, envelope)
    wire = json.dumps(before, ensure_ascii=False, separators=(",", ":"))
    assert (len(wire) + 3) // 4 <= 768
    assert len(envelope.supports) <= 12
    assert audit["support_count"] == len(envelope.supports)
    assert audit["structurally_valid"] is True
    assert audit["semantic_coverage_review"] == "not_performed"
    assert audit["semantic_entailment_review"] == "not_performed"
    proposal = derivation.compose_derivation(case, envelope.records)
    assert proposal.narrative == case.narrative
    assert envelope.model_dump(mode="json", by_alias=True) == before


@pytest.mark.parametrize("index", [0, 1])
def test_packet_preserves_every_original_input_and_whole_narrative_units(index):
    case = derivation.load_fixed_cases()[index]
    wire, packet, audit = _packet(case)
    old_wire, old_audit = derivation.build_derivation_packet(case)
    previous = json.loads(old_wire[len(derivation.PACKET_PREFIX):])
    assert {k: v for k, v in packet.items() if k not in {"schema", "source_units"}} == {
        k: v for k, v in previous.items() if k != "schema"}
    assert packet["schema"] == "storyteller.eval.record-evidence.v1"
    units = packet["source_units"]
    narrative_units = [unit for unit in units if unit["origin"] == "narrative"]
    assert len(narrative_units) == [1, 3][index]
    assert "".join(unit["text"] for unit in narrative_units) == case.narrative
    cursor = 0
    for unit in narrative_units:
        assert unit["start"] == cursor
        assert unit["text"] == case.narrative[unit["start"]:unit["end"]]
        cursor = unit["end"]
    assert cursor == len(case.narrative)
    assert len({u["id"] for u in units}) == len(units)
    for unit in units:
        if unit["origin"] == "narrative":
            continue
        value = packet
        for key in unit["path"].strip("/").split("/"):
            value = value[int(key)] if isinstance(value, list) else value[key]
        assert unit["value"] == value
    assert audit["source"] == old_audit["source"]
    assert audit["user_packet_sha256"] == hashlib.sha256(wire.encode()).hexdigest()
    source_json = json.dumps(units, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    assert audit["source_units_sha256"] == hashlib.sha256(source_json.encode()).hexdigest()
    assert audit["budget"]["estimated_tokens"] == (len(wire) + 3) // 4
    assert audit["budget"]["estimated_tokens"] <= 2000
    assert audit["budget"]["omitted_background_details"] == 0
    assert audit["narrative_reconstructed_exactly"] is True
    assert "supports" not in packet
    assert "records" not in packet
    assert set(packet) == set(previous) | {"source_units"}
    assert "Corredor subterrâneo da velha fábrica" not in wire
    assert "indica presença observadora" not in wire
    assert "O conteúdo do papel pode conter o endereço" not in wire


def test_full_source_preserves_the_opening_modal_scope_and_audit_is_detached():
    case = derivation.load_fixed_cases()[0]
    _, packet, audit = _packet(case)
    unit = packet["source_units"][0]
    assert unit["text"] == case.narrative
    assert "sugerindo que algo ou alguém observa ao longe" in unit["text"]
    audit["source"]["line_number"] = -1
    packet["source_units"][0]["text"] = "recorte"
    _, fresh, fresh_audit = _packet(case)
    assert fresh["source_units"][0]["text"] == case.narrative
    assert fresh_audit["source"]["line_number"] == 3


def test_empty_supports_are_required_as_a_field_but_not_a_coverage_gate():
    case = derivation.load_fixed_cases()[0]
    data = _authored_envelope(case)
    data["supports"] = []
    envelope = evidence.RecordEvidenceProposal.model_validate(data)
    audit = evidence.validate_supports(case, envelope)
    assert audit["support_count"] == 0
    assert audit["semantic_coverage_review"] == "not_performed"
    del data["supports"]
    with pytest.raises(ValidationError):
        evidence.RecordEvidenceProposal.model_validate(data)


@pytest.mark.parametrize("field", ["records", "supports"])
def test_all_envelope_fields_are_required(field):
    case = derivation.load_fixed_cases()[0]
    data = _authored_envelope(case)
    del data[field]
    with pytest.raises(ValidationError):
        evidence.RecordEvidenceProposal.model_validate(data)


@pytest.mark.parametrize("field", ["p", "b", "e", "s", "m"])
def test_all_support_fields_are_required(field):
    item = _authored_envelope(derivation.load_fixed_cases()[0])["supports"][0]
    del item[field]
    with pytest.raises(ValidationError):
        evidence.RecordSupport.model_validate(item)


@pytest.mark.parametrize("field,value", [
    ("b", True), ("e", False), ("b", 1.0), ("e", "3"), ("b", -1), ("e", 0),
    ("s", []), ("s", ["n0", "a0", "m0", "c0"]),
    ("m", "certain"), ("m", ""), ("p", 3),
])
def test_support_types_and_bounded_counts_are_enforced(field, value):
    item = _authored_envelope(derivation.load_fixed_cases()[0])["supports"][0]
    item[field] = value
    with pytest.raises(ValidationError):
        evidence.RecordSupport.model_validate(item)


@pytest.mark.parametrize("level", ["envelope", "records", "support"])
def test_extra_fields_are_forbidden_at_each_new_or_reused_level(level):
    data = _authored_envelope(derivation.load_fixed_cases()[0])
    target = {"envelope": data, "records": data["records"], "support": data["supports"][0]}[level]
    target["unexpected"] = "ignored?"
    with pytest.raises(ValidationError):
        evidence.RecordEvidenceProposal.model_validate(data)


def test_thirteen_supports_are_rejected_by_schema():
    data = _authored_envelope(derivation.load_fixed_cases()[0])
    data["supports"] = [data["supports"][0]] * 13
    with pytest.raises(ValidationError):
        evidence.RecordEvidenceProposal.model_validate(data)


@pytest.mark.parametrize("path", [
    "", "/", "/n", "/records/s", "/scene_summary", "/f/0", "/f/0/a/0/n",
    "/f/0/k", "/f/0/i", "/f/0/p", "/f/0/v", "/t", "/s/0", "/f/-1/s",
    "/f/00/s", "/f/9/s", "/t/9", "/p/0", "/r/0", "/t/01", "/q/",
])
def test_invalid_or_missing_text_paths_fail_closed(path):
    case = derivation.load_fixed_cases()[0]
    data = _authored_envelope(case)
    data["supports"] = [{"p": path, "b": 0, "e": 1, "s": ["n0"], "m": "established"}]
    envelope = evidence.RecordEvidenceProposal.model_validate(data)
    with pytest.raises(evidence.EvidenceEnvelopeError, match="^record_evidence_path_invalid$"):
        evidence.validate_supports(case, envelope)


@pytest.mark.parametrize("start,end", [(1, 1), (2, 1), (0, 9999)])
def test_nonempty_unicode_range_must_exist_in_the_referenced_field(start, end):
    case = derivation.load_fixed_cases()[0]
    data = _authored_envelope(case)
    data["supports"] = [{"p": "/s", "b": start, "e": end, "s": ["n0"], "m": "established"}]
    with pytest.raises(evidence.EvidenceEnvelopeError, match="^record_evidence_span_invalid$"):
        evidence.validate_supports(case, evidence.RecordEvidenceProposal.model_validate(data))


@pytest.mark.parametrize("ids", [["n9"], ["unknown"], ["n0", "n0"], ["n0", " c0"]])
def test_unknown_or_duplicate_source_ids_are_rejected(ids):
    case = derivation.load_fixed_cases()[0]
    data = _authored_envelope(case)
    data["supports"][0]["s"] = ids
    with pytest.raises(evidence.EvidenceEnvelopeError, match="^record_evidence_source_ids_invalid$"):
        evidence.validate_supports(case, evidence.RecordEvidenceProposal.model_validate(data))


def test_unicode_offsets_are_codepoints_not_utf8_utf16_or_serialized_json():
    case = derivation.load_fixed_cases()[0]
    data = _authored_envelope(case)
    data["records"]["s"] = '💡Ação "distante".'
    data["supports"] = [{"p": "/s", "b": 1, "e": 5, "s": ["n0"], "m": "suggested"}]
    audit = evidence.validate_supports(case, evidence.RecordEvidenceProposal.model_validate(data))
    assert audit["validated_supports"][0]["text"] == "Ação"


@pytest.mark.parametrize("field", ["narrative", "player_input", "known_context", "case_id"])
def test_case_snapshot_drift_is_refused_for_packet_and_validation(field):
    case = derivation.load_fixed_cases()[0]
    bad = replace(case, **{field: getattr(case, field) + " adulterado"})
    envelope = evidence.RecordEvidenceProposal.model_validate(_authored_envelope(case))
    for call in (lambda: evidence.build_evidence_packet(bad),
                 lambda: evidence.validate_supports(bad, envelope)):
        with pytest.raises(evidence.EvidenceEnvelopeError, match="^record_evidence_case_invalid$"):
            call()


@pytest.mark.parametrize("mutation", ["source", "scene"])
def test_nested_snapshot_drift_cannot_bypass_validation(mutation):
    case = derivation.load_fixed_cases()[1]
    envelope = evidence.RecordEvidenceProposal.model_validate(_authored_envelope(case))
    if mutation == "source":
        case.source["line_number"] = 3
    else:
        case = replace(case, scene=case.scene.model_copy(update={"location": "Novo lugar"}))
    with pytest.raises(evidence.EvidenceEnvelopeError, match="^record_evidence_case_invalid$"):
        evidence.validate_supports(case, envelope)


@pytest.mark.parametrize("constant", ["SOURCE_JSONL_PATH", "SOURCE_CORPUS_PATH"])
def test_original_frozen_sources_are_rechecked(constant, tmp_path, monkeypatch):
    case = derivation.load_fixed_cases()[0]
    envelope = evidence.RecordEvidenceProposal.model_validate(_authored_envelope(case))
    path = getattr(derivation, constant)
    altered = tmp_path / path.name
    altered.write_bytes(path.read_bytes() + b" ")
    monkeypatch.setattr(derivation, constant, altered)
    with pytest.raises(evidence.EvidenceEnvelopeError, match="^record_evidence_case_invalid$"):
        evidence.validate_supports(case, envelope)


def test_constructed_models_are_revalidated_at_the_boundary():
    case = derivation.load_fixed_cases()[0]
    envelope = evidence.RecordEvidenceProposal.model_validate(_authored_envelope(case))
    bad_item = envelope.supports[0].model_copy(update={"start": True})
    forged = envelope.model_copy(update={"supports": (bad_item,)})
    with pytest.raises(evidence.EvidenceEnvelopeError, match="^record_evidence_schema_invalid$"):
        evidence.validate_supports(case, forged)


def test_structure_does_not_evaluate_entailment_or_fill_missing_supports():
    case = derivation.load_fixed_cases()[0]
    data = _authored_envelope(case)
    data["records"]["s"] = "Uma presença definitivamente observa o corredor."
    data["supports"] = [{"p": "/s", "b": 0, "e": len(data["records"]["s"]),
                         "s": ["n0"], "m": "suggested"}]
    envelope = evidence.RecordEvidenceProposal.model_validate(data)
    before = envelope.model_dump(mode="json", by_alias=True)
    audit = evidence.validate_supports(case, envelope)
    assert audit["structurally_valid"] is True
    assert audit["semantic_entailment_review"] == "not_performed"
    assert envelope.model_dump(mode="json", by_alias=True) == before


def test_outcome_remains_intact_for_separate_existing_admission():
    case = derivation.load_fixed_cases()[0]
    data = _authored_envelope(case)
    data["records"]["o"] = "success"
    data["supports"] = []
    envelope = evidence.RecordEvidenceProposal.model_validate(data)
    assert evidence.validate_supports(case, envelope)["structurally_valid"] is True
    assert derivation.compose_derivation(case, envelope.records).outcome == "success"


def test_user_over_budget_is_refused_without_omission(monkeypatch):
    case = derivation.load_fixed_cases()[0]
    monkeypatch.setattr(evidence, "USER_PACKET_TOKEN_BUDGET", 1)
    with pytest.raises(evidence.EvidenceEnvelopeError, match="^record_evidence_user_budget_exceeded$"):
        evidence.build_evidence_packet(case)


def test_system_body_is_frozen_and_does_not_include_authored_answers():
    path, body = evidence.load_evidence_prompt()
    assert path == evidence.PROMPT_PATH
    assert not body.startswith("---")
    assert hashlib.sha256(body.encode()).hexdigest() == evidence.PROMPT_SHA256
    assert "records" in body and "supports" in body
    assert "Mara" not in body and "sussurro" not in body
    assert "validação estrutural" in body
    schema = evidence.RecordEvidenceProposal.model_json_schema(by_alias=True)
    assert set(schema["required"]) == {"records", "supports"}
    assert schema["additionalProperties"] is False
    assert set(schema["$defs"]["RecordSupport"]["required"]) == {"p", "b", "e", "s", "m"}
    assert schema["$defs"]["RecordSupport"]["additionalProperties"] is False


@pytest.mark.parametrize("mutation,reason", [
    ("body", "record_evidence_prompt_hash_mismatch"),
    ("metadata", "record_evidence_prompt_metadata_invalid"),
    ("missing", "record_evidence_prompt_unavailable"),
])
def test_prompt_drift_is_refused(mutation, reason, tmp_path, monkeypatch):
    document = evidence.PROMPT_PATH.read_text(encoding="utf-8")
    path = tmp_path / "prompt.md"
    if mutation != "missing":
        path.write_text(document + "\nAlterado." if mutation == "body" else "Sem metadados.", encoding="utf-8")
    monkeypatch.setattr(evidence, "PROMPT_PATH", path)
    with pytest.raises(evidence.EvidenceEnvelopeError, match="^" + reason + "$"):
        evidence.load_evidence_prompt()


def test_remaining_text_paths_and_full_limits_are_structural_not_semantic():
    case = derivation.load_fixed_cases()[1]
    data = _authored_envelope(case)
    data["records"]["r"] = list(case.scene.open_threads)
    data["supports"] = [
        {"p": "/r/0", "b": 0, "e": len(data["records"]["r"][0]),
         "s": ["n0", "n1", "c5"], "m": "unresolved"},
        {"p": "/q", "b": 0, "e": len(data["records"]["q"]),
         "s": ["a0"], "m": "unresolved"},
    ] * 6
    envelope = evidence.RecordEvidenceProposal.model_validate(data)
    audit = evidence.validate_supports(case, envelope)
    assert audit["support_count"] == 12
    assert audit["semantic_entailment_review"] == "not_performed"
    # A declared resolution is not automatically justified by valid IDs.
    assert envelope.records.resolved_threads == tuple(case.scene.open_threads)


def test_error_code_is_bounded_even_if_accidentally_given_source_text():
    error = evidence.EvidenceEnvelopeError("raw provider/source text must not escape")
    assert error.code == "record_evidence_contract_invalid"
    assert str(error) == error.code
