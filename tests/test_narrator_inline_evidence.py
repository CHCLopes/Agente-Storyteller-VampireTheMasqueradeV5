"""Offline structural proof; these tests never score semantic fidelity."""
from dataclasses import FrozenInstanceError
import copy
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest
from pydantic import ValidationError
from scripts import narrator_inline_evidence as inline


SOURCES = [{"id": "n0", "text": "Um sinal é percebido."}, {"id": "n1", "text": "Outra fonte completa."}]


def segment(text="Texto observado.", sources=None, modality="established"):
    return {"text": text, "sources": ["n0"] if sources is None else sources, "modality": modality}


def payload(summary=None, questions=None):
    return {"summary": [segment()] if summary is None else summary,
            "open_questions": [] if questions is None else questions}


def project(value=None, sources=None):
    return inline.project_inline_evidence(payload() if value is None else value, SOURCES if sources is None else sources)


def test_projection_has_only_summary_and_questions_and_declares_limits():
    result, audit = project(payload([segment("Texto "), segment("observado.")], [[segment("Qual "), segment("origem?")]]))
    assert result.summary == "Texto observado."
    assert result.open_questions == ("Qual origem?",)
    assert audit["protocol"] == "record-inline-evidence-v1"
    assert audit["structural_only"] is True and audit["semantic_not_evaluated"] is True
    assert audit["semantic_coverage_review"] == audit["semantic_entailment_review"] == "not_performed"
    assert audit["actor_validation"] == "not_performed"
    assert audit["runtime_promoted"] is False and audit["cap_001_status"] == "not_evaluated"
    assert [item["path"] for item in audit["segments"]] == ["/summary", "/summary", "/open_questions/0", "/open_questions/0"]
    with pytest.raises(FrozenInstanceError): result.summary = "changed"


def test_unicode_repeated_text_and_whitespace_use_ordered_code_point_offsets():
    texts = ["  e\u0301🚪", "  e\u0301🚪", "\n"]
    result, audit = project(payload([segment(t) for t in texts], [[segment("é"), segment("é?")]]))
    assert result.summary == "".join(texts)
    assert result.open_questions == ("éé?",)
    cursor = 0
    for text, item in zip(texts, audit["segments"][:3]):
        assert (item["start"], item["end"]) == (cursor, cursor + len(text))
        assert result.summary[item["start"]:item["end"]] == item["text"] == text
        cursor += len(text)
    assert [(item["start"], item["end"]) for item in audit["segments"][3:]] == [(0, 1), (1, 3)]


def test_no_separator_is_inserted_and_empty_question_list_is_valid():
    result, _ = project(payload([segment("abcd"), segment("efgh")]))
    assert result.summary == "abcdefgh" and result.open_questions == ()


@pytest.mark.parametrize("sources", [["n0", "n0"], ["n0", "missing"], ["N0"], ["n0 "], [""], [True], [1], [None], [], ["n0", "n1", "n2", "n3"]])
def test_reference_ids_are_exact_typed_distinct_and_bounded(sources):
    with pytest.raises(inline.InlineEvidenceError): project(payload([segment(sources=sources)]))


@pytest.mark.parametrize("text", ["", True, 1, 1.5, None, [], {}])
def test_segment_text_is_nonempty_and_never_coerced(text):
    with pytest.raises(inline.InlineEvidenceError): project(payload([segment(text)]))


@pytest.mark.parametrize("modality", [True, 1, None, "confirmed", "Established"])
def test_modality_is_a_closed_enum(modality):
    with pytest.raises(inline.InlineEvidenceError): project(payload([segment(modality=modality)]))


@pytest.mark.parametrize("field", ["p", "c", "b", "e", "path", "start", "end", "records", "source_units"])
def test_model_cannot_supply_a_path_quote_offset_or_own_sources(field):
    item = segment()
    item[field] = "synthetic-sensitive-canary"
    with pytest.raises(inline.InlineEvidenceError) as captured: project(payload([item]))
    assert "synthetic-sensitive-canary" not in str(captured.value)


@pytest.mark.parametrize("field", ["records", "narrative", "source_units", "supports", "location"])
def test_envelope_has_no_runtime_or_legacy_fields(field):
    value = payload()
    value[field] = "synthetic-sensitive-canary"
    with pytest.raises(inline.InlineEvidenceError): project(value)


@pytest.mark.parametrize("value", [None, "not a proposal", True, [], {"summary": []}, {"open_questions": []}])
def test_invalid_envelopes_are_safe(value):
    with pytest.raises(inline.InlineEvidenceError) as captured:
        inline.project_inline_evidence(value, SOURCES)
    assert str(captured.value) == captured.value.code


@pytest.mark.parametrize("units", [None, {}, "n0", [], [{"id": "n0"}], [{"id": "n0", "text": "text", "extra": True}], [{"id": True, "text": "text"}], [{"id": "n0", "text": 1}], [{"id": "", "text": "text"}], [{"id": "n0", "text": ""}], [{"id": "n0", "text": "one"}, {"id": "n0", "text": "two"}]])
def test_invalid_caller_sources_are_refused(units):
    with pytest.raises(inline.InlineEvidenceError) as captured:
        inline.project_inline_evidence(payload(), units)
    assert captured.value.code == "inline_evidence_source_units_invalid"


def test_forged_segment_and_proposal_instances_are_revalidated():
    forged_segment = inline.InlineEvidenceSegment.model_construct(text=True, sources=("n0",), modality="established")
    forged_proposal = inline.InlineEvidenceProposal.model_construct(summary=(forged_segment,), open_questions=())
    with pytest.raises(inline.InlineEvidenceError): project(forged_proposal)
    good = inline.InlineEvidenceProposal.model_validate(payload())
    altered = good.model_copy(update={"summary": (inline.InlineEvidenceSegment.model_construct(text="abcdefgh", sources=("n0", "n0"), modality="established"),)})
    with pytest.raises(inline.InlineEvidenceError): project(altered)


def test_forged_instance_extras_are_refused():
    good = inline.InlineEvidenceProposal.model_validate(payload())
    with pytest.raises(inline.InlineEvidenceError): project(good.model_copy(update={"unexpected": "synthetic-sensitive-canary"}))


@pytest.mark.parametrize("summary,questions", [([], []), ([segment()] * 9, []), ([segment()], [[]]), ([segment()], [[segment()] * 5]), ([segment()], [[segment()], [segment()], [segment()]])])
def test_local_list_limits_are_enforced(summary, questions):
    with pytest.raises(inline.InlineEvidenceError): project(payload(summary, questions))


def test_twelve_total_segments_are_valid_and_thirteen_are_not():
    value = payload([segment("x")] * 8, [[segment("?")] * 2, [segment("?")] * 2])
    result, audit = project(value)
    assert result.summary == "xxxxxxxx" and len(audit["segments"]) == 12
    value["open_questions"][1].append(segment("?"))
    with pytest.raises(inline.InlineEvidenceError): project(value)
    forged = inline.InlineEvidenceProposal.model_construct(summary=tuple(inline.InlineEvidenceSegment.model_validate(s) for s in value["summary"]), open_questions=tuple(tuple(inline.InlineEvidenceSegment.model_validate(s) for s in q) for q in value["open_questions"]))
    with pytest.raises(inline.InlineEvidenceError): project(forged)


@pytest.mark.parametrize("length,valid", [(7, False), (8, True), (600, True), (601, False)])
def test_summary_length_applies_after_literal_concatenation(length, valid):
    value = payload([segment("a"), segment("x" * (length - 1))])
    if valid:
        assert len(project(value)[0].summary) == length
    else:
        with pytest.raises(inline.InlineEvidenceError, match="summary_length"): project(value)


@pytest.mark.parametrize("length,valid", [(1, True), (200, True), (201, False)])
def test_question_length_applies_after_concatenation(length, valid):
    value = payload(questions=[[segment("x" * length)]])
    if valid:
        assert len(project(value)[0].open_questions[0]) == length
    else:
        with pytest.raises(inline.InlineEvidenceError, match="question_length"): project(value)


def test_valid_structure_does_not_establish_fidelity_or_a_new_word_gate():
    text = "Há uma nave extraterrestre invisível controlando a cidade. " + "palavra " * 26
    result, audit = project(payload([segment(text, modality="established")]))
    assert result.summary == text
    assert audit["semantic_not_evaluated"] is True
    assert audit["semantic_entailment_review"] == "not_performed"
    assert audit["semantic_coverage_review"] == "not_performed"


def test_input_and_audit_mutation_cannot_rewrite_projection_or_other_inputs():
    value, units = payload(), copy.deepcopy(SOURCES)
    initial_value, initial_units = copy.deepcopy(value), copy.deepcopy(units)
    result, audit = project(value, units)
    assert value == initial_value and units == initial_units
    audit["segments"][0]["sources"].append("forged")
    audit["source_units"][0]["text"] = "changed"
    value["summary"][0]["text"] = "changed"
    assert result.summary == "Texto observado." and units == initial_units


def test_safe_error_code_cannot_echo_arbitrary_content():
    error = inline.InlineEvidenceError("synthetic-sensitive-canary")
    assert error.code == str(error) == "inline_evidence_contract_invalid"


def test_wire_schema_is_required_and_forbids_runtime_or_offset_fields():
    schema = inline.InlineEvidenceProposal.model_json_schema()
    assert set(schema["required"]) == {"summary", "open_questions"}
    assert schema["additionalProperties"] is False
    segment_schema = schema["$defs"]["InlineEvidenceSegment"]
    assert set(segment_schema["required"]) == {"text", "sources", "modality"}
    assert segment_schema["additionalProperties"] is False


def test_module_import_never_enters_runtime_dotenv_or_transport():
    script = r"""
import importlib.abc,sys
class Guard(importlib.abc.MetaPathFinder):
    def find_spec(self,fullname,path=None,target=None):
        if fullname.split('.')[0] in {'api','dotenv','httpx','openai','groq'}:
            raise AssertionError('Runtime or transport import forbidden')
        return None
sys.meta_path.insert(0,Guard())
from scripts import narrator_inline_evidence
assert narrator_inline_evidence.VERSION == 'record-inline-evidence-v1'
"""
    environment = os.environ.copy()
    environment.pop("GROQ_API_KEY", None)
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    result = subprocess.run([sys.executable, "-c", script], cwd=Path(__file__).resolve().parents[1], env=environment, capture_output=True, text=True, timeout=20)
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize("mode", ["source_set", "source_iterator", "summary_set", "summary_iterator", "questions_iterator", "question_iterator"])
def test_only_explicit_ordered_wire_collections_are_accepted(mode):
    value = payload()
    if mode == "source_set": value["summary"][0]["sources"] = {"n0", "n1"}
    if mode == "source_iterator": value["summary"][0]["sources"] = iter(["n0"])
    if mode == "summary_set": value["summary"] = {inline.InlineEvidenceSegment.model_validate(segment())}
    if mode == "summary_iterator": value["summary"] = iter([segment()])
    if mode == "questions_iterator": value["open_questions"] = iter([[segment("Qual?")]])
    if mode == "question_iterator": value["open_questions"] = [iter([segment("Qual?")])]
    with pytest.raises(inline.InlineEvidenceError): project(value)


@pytest.mark.parametrize("modality", ["established", "suggested", "unresolved"])
def test_declared_modality_is_preserved_without_inference(modality):
    _, audit = project(payload([segment(modality=modality)]))
    assert audit["segments"][0]["modality"] == modality
    assert audit["semantic_not_evaluated"] is True


def test_all_array_limits_are_emitted_as_json_schema_item_constraints():
    schema = inline.InlineEvidenceProposal.model_json_schema()
    arrays = [
        (schema["properties"]["summary"], 1, 8),
        (schema["$defs"]["InlineEvidenceSegment"]["properties"]["sources"], 1, 3),
        (schema["properties"]["open_questions"], 0, 2),
        (schema["properties"]["open_questions"]["items"], 1, 4),
    ]
    for array_schema, minimum, maximum in arrays:
        assert array_schema["type"] == "array"
        assert array_schema.get("minItems", 0) == minimum
        assert array_schema["maxItems"] == maximum
        assert "minLength" not in array_schema and "maxLength" not in array_schema
