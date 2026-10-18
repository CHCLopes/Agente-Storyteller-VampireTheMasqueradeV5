"""Offline structural proof for inline source references; no runtime integration.

The caller supplies trusted complete source units independently of the proposal.
This boundary checks shape and references, never whether text follows from a
source. It does not infer words, separators, modalities, coverage or meaning.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated, Any, Literal

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, StrictStr, ValidationError, field_validator, model_validator

VERSION = "record-inline-evidence-v1"
MAX_SEGMENTS = 12
_ERROR_CODES = frozenset({
    "inline_evidence_contract_invalid", "inline_evidence_schema_invalid",
    "inline_evidence_source_units_invalid", "inline_evidence_source_ids_invalid",
    "inline_evidence_summary_length_invalid", "inline_evidence_question_length_invalid",
})


class InlineEvidenceError(ValueError):
    """Only a fixed reason escapes projection, never input or validator details."""

    def __init__(self, code: str) -> None:
        self.code = code if code in _ERROR_CODES else "inline_evidence_contract_invalid"
        super().__init__(self.code)


def _ordered_collection(value: Any) -> Any:
    # JSON arrays and explicit Python tuples preserve the declared segment order.
    # Pydantic's generic iterable coercion must not accept sets or consume iterators.
    if type(value) not in (tuple, list):
        raise ValueError("ordered_collection_required")
    return value


class InlineEvidenceSegment(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, revalidate_instances="always")

    text: StrictStr = Field(min_length=1)
    sources: Annotated[tuple[StrictStr, ...], BeforeValidator(_ordered_collection)] = Field(min_length=1, max_length=3)
    modality: Literal["established", "suggested", "unresolved"]

    @field_validator("sources")
    @classmethod
    def distinct_source_ids(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if len(set(value)) != len(value):
            raise ValueError("duplicate_source_ids")
        return value


_QuestionSegments = Annotated[tuple[InlineEvidenceSegment, ...], Field(min_length=1, max_length=4), BeforeValidator(_ordered_collection)]


class InlineEvidenceProposal(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, revalidate_instances="always")

    summary: Annotated[tuple[InlineEvidenceSegment, ...], BeforeValidator(_ordered_collection)] = Field(min_length=1, max_length=8)
    open_questions: Annotated[tuple[_QuestionSegments, ...], BeforeValidator(_ordered_collection)] = Field(max_length=2)

    @model_validator(mode="after")
    def bounded_total_segments(self) -> InlineEvidenceProposal:
        if len(self.summary) + sum(len(question) for question in self.open_questions) > MAX_SEGMENTS:
            raise ValueError("total_segment_limit_exceeded")
        return self


@dataclass(frozen=True, slots=True)
class InlineEvidenceProjection:
    summary: str
    open_questions: tuple[str, ...]


def _trusted_source_units(source_units: Any) -> tuple[dict[str, str], ...]:
    """Validate caller data; never retrieve units from model-generated fields."""
    if type(source_units) not in (tuple, list) or not source_units:
        raise InlineEvidenceError("inline_evidence_source_units_invalid")
    seen: set[str] = set()
    copied = []
    for unit in source_units:
        if (type(unit) is not dict or set(unit) != {"id", "text"}
                or type(unit["id"]) is not str or not unit["id"]
                or type(unit["text"]) is not str or not unit["text"]
                or unit["id"] in seen):
            raise InlineEvidenceError("inline_evidence_source_units_invalid")
        seen.add(unit["id"])
        copied.append({"id": unit["id"], "text": unit["text"]})
    return tuple(copied)


def project_inline_evidence(
    proposal: InlineEvidenceProposal | dict[str, Any],
    source_units: tuple[dict[str, str], ...] | list[dict[str, str]],
) -> tuple[InlineEvidenceProjection, dict[str, Any]]:
    """Concatenate literally and compute Unicode offsets in each fixed field.

    JSON lists may become immutable tuples; scalar values are not coerced.
    Empty question lists are allowed. Whitespace is text and is never trimmed.
    The 25-word summary instruction is deliberately not a new structural gate.
    """
    try:
        if type(proposal) not in (InlineEvidenceProposal, dict):
            raise ValueError
        checked = InlineEvidenceProposal.model_validate(proposal)
        checked = InlineEvidenceProposal.model_validate(checked.model_dump(mode="python", warnings="error"))
    except (ValidationError, ValueError, TypeError, AttributeError):
        raise InlineEvidenceError("inline_evidence_schema_invalid") from None
    units = _trusted_source_units(source_units)
    source_ids = {unit["id"] for unit in units}
    audit_segments: list[dict[str, Any]] = []

    def concatenate(segments: tuple[InlineEvidenceSegment, ...], path: str) -> str:
        cursor = 0
        parts = []
        for segment in segments:
            if any(source_id not in source_ids for source_id in segment.sources):
                raise InlineEvidenceError("inline_evidence_source_ids_invalid")
            end = cursor + len(segment.text)
            audit_segments.append({
                "path": path, "start": cursor, "end": end, "text": segment.text,
                "sources": list(segment.sources), "modality": segment.modality,
            })
            parts.append(segment.text)
            cursor = end
        return "".join(parts)

    summary = concatenate(checked.summary, "/summary")
    if not 8 <= len(summary) <= 600:
        raise InlineEvidenceError("inline_evidence_summary_length_invalid")
    questions = tuple(concatenate(segments, f"/open_questions/{index}")
                      for index, segments in enumerate(checked.open_questions))
    if any(not 1 <= len(question) <= 200 for question in questions):
        raise InlineEvidenceError("inline_evidence_question_length_invalid")
    projection = InlineEvidenceProjection(summary=summary, open_questions=questions)
    return projection, {
        "protocol": VERSION, "structurally_valid": True,
        "structural_only": True, "semantic_not_evaluated": True,
        "semantic_coverage_review": "not_performed",
        "semantic_entailment_review": "not_performed",
        "actor_validation": "not_performed", "runtime_promoted": False,
        "cap_001_status": "not_evaluated",
        "offset_unit": "unicode_code_points", "interval": "[start,end)",
        "concatenation": "literal_no_separator", "segment_count": len(audit_segments),
        "source_units": list(units), "segments": audit_segments,
    }
