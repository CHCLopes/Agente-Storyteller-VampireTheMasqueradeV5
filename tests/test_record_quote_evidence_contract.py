"""Authored offline controls for exact target quotes, never model inputs."""
from copy import deepcopy
from dataclasses import replace
import hashlib
import json

import pytest
from pydantic import ValidationError

from scripts import narrator_record_derivation as derivation
from scripts import narrator_record_evidence as legacy
from scripts import narrator_record_quote_evidence as quote


def _data(index=0):
    case = derivation.load_fixed_cases()[index]
    records = {
        "o": case.outcome,
        "l": case.scene.location if case.scene else "corredor de pedra fria",
        "s": "Mara desliza um papel no balcão." if case.scene else "Um sussurro sugere possível observação distante.",
        "p": ["Mara"] if case.scene else [],
        "f": [{"k": "observation", "s": "Um som ecoa ao longe.", "v": "public", "i": 0.5, "p": False, "a": []}],
        "t": ["Há algo ou alguém observando ao longe?"], "r": [], "q": "O que você faz agora?",
    }
    return case, {"records": records, "supports": [
        {"p": "/o", "c": records["o"], "s": ["m0"], "m": "established"},
        {"p": "/l", "c": records["l"], "s": ["n0"], "m": "established"},
        {"p": "/s", "c": records["s"], "s": ["n0"], "m": "suggested"},
    ]}


def _audit(data, case=None):
    case = case or derivation.load_fixed_cases()[0]
    model = quote.RecordQuoteEvidenceProposal.model_validate(data)
    return quote.validate_supports(case, model)


@pytest.mark.parametrize("index", [0, 1])
def test_source_packet_and_audit_remain_byte_exact_without_quote_protocol_in_user(index):
    case, _ = _data(index)
    wire, audit = quote.build_evidence_packet(case)
    assert (wire, audit) == legacy.build_evidence_packet(case)
    assert audit["version"] == "record-evidence-v1"
    assert audit["narrative_reconstructed_exactly"] is True
    assert "".join(u["text"] for u in audit["source_units"] if u["origin"] == "narrative") == case.narrative
    assert "target-quotes" not in wire
    assert "supports" not in json.loads(wire[len(quote.PACKET_PREFIX):])
    audit["source_units"][0]["text"] = "changed"
    assert quote.build_evidence_packet(case) == legacy.build_evidence_packet(case)


@pytest.mark.parametrize("index", [0, 1])
def test_exact_quotes_are_resolved_without_mutating_input_and_use_existing_numeric_gate(index, monkeypatch):
    case, data = _data(index)
    before = deepcopy(data)
    seen = []
    original = legacy.validate_supports
    def capture(actual_case, numeric):
        seen.append(numeric.model_dump(mode="json", by_alias=True))
        return original(actual_case, numeric)
    monkeypatch.setattr(legacy, "validate_supports", capture)
    model = quote.RecordQuoteEvidenceProposal.model_validate(data)
    audit = quote.validate_supports(case, model)
    assert data == before == model.model_dump(mode="json", by_alias=True)
    assert len(seen) == 1 and seen[0]["records"] == before["records"]
    assert audit["quote_protocol"] == quote.VERSION
    assert audit["version"] == "record-evidence-v1"
    assert audit["semantic_coverage_review"] == audit["semantic_entailment_review"] == "not_performed"
    for raw, checked in zip(data["supports"], audit["validated_supports"]):
        assert checked["quote"] == checked["text"] == raw["c"]
        assert checked["source_ids"] == raw["s"] and checked["modality"] == raw["m"]
        assert checked["start"] == 0 and checked["end"] == len(raw["c"])
    assert derivation.compose_derivation(case, model.records).narrative == case.narrative


@pytest.mark.parametrize("text,c,start,end", [
    ('💡Ação "distante".', 'Ação', 1, 5),
    ('X👩‍🚀Y', '👩‍🚀', 1, 4),
    ('X e\u0301 Z', 'e\u0301', 2, 4),
    ('A "luz"\n☔', '"luz"', 2, 7),
    ('Sem  pausa.', '  ', 3, 5),
])
def test_unicode_exact_quotes_resolve_codepoints_not_bytes_or_utf16(text, c, start, end):
    case, data = _data()
    data["records"]["s"] = text if len(text) >= 8 else "Prefixo " + text
    prefix = 0 if len(text) >= 8 else 8
    data["supports"] = [{"p": "/s", "c": c, "s": ["n0"], "m": "suggested"}]
    model = quote.RecordQuoteEvidenceProposal.model_validate_json(json.dumps(data, ensure_ascii=True))
    item = quote.validate_supports(case, model)["validated_supports"][0]
    assert (item["start"], item["end"]) == (prefix + start, prefix + end)
    assert item["text"] == item["quote"] == c


@pytest.mark.parametrize("text,c", [
    ("Árvore distante.", "A\u0301rvore"),
    ("A\u0301rvore distante.", "Árvore"),
    ("Árvore distante.", "árvore"),
    ("Árvore distante.", "Arvore"),
    ("Árvore distante.", " Árvore distante. "),
    ("Árvore distante.", r"\u00c1rvore"),
    ("Corredor vazio.", "Corredor  vazio."),
    ("Corredor vazio.", "corredor vazio."),
])
def test_absent_quotes_are_not_trimmed_normalized_casefolded_or_fuzzily_matched(text, c):
    _, data = _data()
    data["records"]["s"] = text
    data["supports"] = [{"p": "/s", "c": c, "s": ["n0"], "m": "established"}]
    with pytest.raises(quote.QuoteEvidenceEnvelopeError, match="^record_quote_evidence_quote_missing$"):
        _audit(data)


def test_quote_found_only_in_source_is_not_a_quote_of_target():
    case, data = _data()
    data["supports"] = [{"p": "/l", "c": case.narrative, "s": ["n0"], "m": "established"}]
    with pytest.raises(quote.QuoteEvidenceEnvelopeError, match="quote_missing"):
        _audit(data)


@pytest.mark.parametrize("text,c", [("banana distante", "ana"), ("aaaa distante", "aa"),
                                      ("eco distante; eco próximo", "eco"), ("💡💡💡 distante", "💡💡")])
def test_duplicate_and_overlapping_occurrences_are_ambiguous_not_first_match(text, c):
    _, data = _data()
    data["records"]["s"] = text
    data["supports"] = [{"p": "/s", "c": c, "s": ["n0"], "m": "suggested"}]
    before = deepcopy(data)
    with pytest.raises(quote.QuoteEvidenceEnvelopeError, match="^record_quote_evidence_quote_ambiguous$"):
        _audit(data)
    assert data == before


def test_uniqueness_is_per_pointed_field_not_across_all_records():
    _, data = _data()
    data["records"]["s"] = data["records"]["l"]
    data["supports"] = [{"p": "/l", "c": data["records"]["l"], "s": ["n0"], "m": "established"}]
    assert _audit(data)["support_count"] == 1


@pytest.mark.parametrize("field", ["records", "supports"])
def test_envelope_fields_required(field):
    _, data = _data()
    del data[field]
    with pytest.raises(ValidationError): quote.RecordQuoteEvidenceProposal.model_validate(data)


@pytest.mark.parametrize("field", ["p", "c", "s", "m"])
def test_support_fields_required(field):
    _, data = _data()
    del data["supports"][0][field]
    with pytest.raises(ValidationError): quote.RecordQuoteEvidenceProposal.model_validate(data)


@pytest.mark.parametrize("value", ["", None, True, 12, 1.5, [], {}, b"unresolved"])
def test_quote_is_nonempty_strict_string(value):
    _, data = _data()
    data["supports"][0]["c"] = value
    with pytest.raises(ValidationError): quote.RecordQuoteEvidenceProposal.model_validate(data)


@pytest.mark.parametrize("field,value", [("p", 1), ("p", True), ("s", []),
    ("s", ["n0", "n1", "n2", "m0"]), ("s", [1]), ("s", [True]), ("s", [b"n0"]),
    ("m", "certain"), ("m", True), ("m", None)])
def test_strict_types_and_source_count_limits(field, value):
    _, data = _data()
    data["supports"][0][field] = value
    with pytest.raises(ValidationError): quote.RecordQuoteEvidenceProposal.model_validate(data)


@pytest.mark.parametrize("level,field", [("envelope", "b"), ("records", "n"), ("support", "b"),
                                        ("support", "e"), ("support", "text")])
def test_extra_fields_and_old_numeric_protocol_are_rejected(level, field):
    _, data = _data()
    target = {"envelope": data, "records": data["records"], "support": data["supports"][0]}[level]
    target[field] = 1
    with pytest.raises(ValidationError): quote.RecordQuoteEvidenceProposal.model_validate(data)


def test_schema_has_only_quote_protocol_and_reuses_records_definition():
    schema = quote.RecordQuoteEvidenceProposal.model_json_schema(by_alias=True)
    old = legacy.RecordEvidenceProposal.model_json_schema(by_alias=True)
    assert set(schema["required"]) == {"records", "supports"}
    item = schema["$defs"]["RecordQuoteSupport"]
    assert set(item["required"]) == set(item["properties"]) == {"p", "c", "s", "m"}
    assert item["additionalProperties"] is schema["additionalProperties"] is False
    assert schema["$defs"]["RecordDerivationProposal"] == old["$defs"]["RecordDerivationProposal"]
    assert "RecordSupport" not in schema["$defs"]


@pytest.mark.parametrize("path", ["", "/", "/n", "/records/s", "/scene_summary", "/f/0",
    "/f/0/a/0/n", "/f/0/k", "/f/0/i", "/f/0/p", "/f/0/v", "/t", "/s/0", "/f/-1/s",
    "/f/00/s", "/f/9/s", "/t/9", "/p/0", "/r/0", "/t/01", "/q/"])
def test_closed_legacy_paths_are_preserved(path):
    _, data = _data()
    data["supports"] = [{"p": path, "c": "x", "s": ["n0"], "m": "established"}]
    with pytest.raises(quote.QuoteEvidenceEnvelopeError, match="^record_quote_evidence_path_invalid$"):
        _audit(data)


@pytest.mark.parametrize("ids", [["n9"], ["unknown"], ["n0", "n0"], ["n0", " c0"]])
def test_unknown_duplicate_or_modified_source_ids_are_rejected_by_existing_gate(ids):
    _, data = _data()
    data["supports"][0]["s"] = ids
    with pytest.raises(quote.QuoteEvidenceEnvelopeError, match="^record_quote_evidence_source_ids_invalid$"):
        _audit(data)


def test_all_closed_text_path_forms_and_maximum_supports_are_preserved():
    case, data = _data(1)
    data["records"]["r"] = ["Questão sintética pendente"]
    values = {"/p/0": "Mara", "/f/0/s": data["records"]["f"][0]["s"],
              "/t/0": data["records"]["t"][0], "/r/0": data["records"]["r"][0], "/q": data["records"]["q"]}
    data["supports"] = [{"p": p, "c": c, "s": ["n0", "n1", "m0"], "m": "unresolved"}
                        for p, c in values.items()]
    data["supports"] = (data["supports"] * 3)[:12]
    assert _audit(data, case)["support_count"] == 12
    data["supports"].append(data["supports"][0])
    with pytest.raises(ValidationError): quote.RecordQuoteEvidenceProposal.model_validate(data)


@pytest.mark.parametrize("field", ["narrative", "player_input", "known_context", "case_id"])
def test_case_drift_is_rejected_by_packet_and_unchanged_structural_gate(field):
    case, data = _data()
    forged = replace(case, **{field: getattr(case, field) + " changed"})
    with pytest.raises(quote.QuoteEvidenceEnvelopeError, match="^record_quote_evidence_case_invalid$"):
        quote.build_evidence_packet(forged)
    with pytest.raises(quote.QuoteEvidenceEnvelopeError, match="^record_quote_evidence_case_invalid$"):
        _audit(data, forged)


@pytest.mark.parametrize("field,value", [("quote", True), ("quote", b"unresolved"), ("quote", ""),
                                         ("source_ids", (1,)), ("path", 3)])
def test_forged_support_instances_are_revalidated_before_serialization(field, value):
    case, data = _data()
    model = quote.RecordQuoteEvidenceProposal.model_validate(data)
    forged = model.model_copy(update={"supports": (model.supports[0].model_copy(update={field: value}),)})
    with pytest.raises(quote.QuoteEvidenceEnvelopeError, match="^record_quote_evidence_schema_invalid$"):
        quote.validate_supports(case, forged)


def test_literal_matching_does_not_approve_semantic_presupposition_or_fill_coverage():
    case, data = _data()
    question = "Quem ou o que está observando?"
    data["records"]["t"] = [question]
    data["supports"] = [{"p": "/t/0", "c": question, "s": ["n0"], "m": "suggested"}]
    before = deepcopy(data)
    audit = _audit(data, case)
    assert audit["structurally_valid"] is True
    assert audit["semantic_entailment_review"] == audit["semantic_coverage_review"] == "not_performed"
    assert audit["support_count"] == 1 and data == before
    audit["validated_supports"][0]["quote"] = "changed"
    assert _audit(data, case)["validated_supports"][0]["quote"] == question
    data["supports"] = []
    empty = _audit(data, case)
    assert empty["support_count"] == 0 and empty["semantic_coverage_review"] == "not_performed"


def test_prompt_preserves_all_authority_records_semantics_and_historical_budget():
    path, body = quote.load_quote_evidence_prompt()
    old = (path.parent / "record-evidence-target-spans-v1.md").read_text(encoding="utf-8").split("---", 2)[2].strip()
    assert body.split("SUPPORTS", 1)[0] == old.split("SUPPORTS", 1)[0]
    assert body.splitlines()[-1] == old.splitlines()[-1]
    assert "p/c/s/m" in body and "Não envie b/e" in body and "ocorrências sobrepostas" in body
    assert "rua vazia" in body and "Mara" not in body and "sussurro" not in body
    assert "citações distintas" in body and "lista vazia não demonstra cobertura" in body
    assert hashlib.sha256(body.encode()).hexdigest() == quote.PROMPT_SHA256


@pytest.mark.parametrize("mutation,code", [("missing", "prompt_unavailable"),
    ("metadata", "prompt_metadata_invalid"), ("body", "prompt_hash_mismatch")])
def test_prompt_missing_metadata_and_body_drift_fail_closed(mutation, code, monkeypatch, tmp_path):
    original = quote.PROMPT_PATH.read_text(encoding="utf-8")
    path = tmp_path / "quote.md"
    if mutation != "missing":
        path.write_text(original.replace(quote.VERSION, "wrong", 1) if mutation == "metadata"
                        else original + "\nChanged.", encoding="utf-8")
    monkeypatch.setattr(quote, "PROMPT_PATH", path)
    with pytest.raises(quote.QuoteEvidenceEnvelopeError, match="^record_quote_evidence_" + code + "$"):
        quote.load_quote_evidence_prompt()


def test_safe_error_does_not_accept_raw_response_as_code():
    exc = quote.QuoteEvidenceEnvelopeError("Raw sensitive source or response text")
    assert str(exc) == exc.code == "record_quote_evidence_contract_invalid"
