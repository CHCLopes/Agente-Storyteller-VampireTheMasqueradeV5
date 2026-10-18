"""Exact target quotes for an experimental envelope; no runtime or semantic approval.

Only this declared protocol resolves offsets. Historical numeric supports and
returned records are never repaired, normalized, or rewritten.
"""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
import re
from typing import Any, Literal

os.environ["STORYTELLER_DISABLE_DOTENV"] = "1"

from pydantic import BaseModel, ConfigDict, Field, StrictStr, ValidationError

from scripts import narrator_record_evidence as evidence
from scripts.narrator_record_derivation import DerivationCase, RecordDerivationProposal

VERSION = "record-evidence-target-quotes-v1"
PROMPT_PATH = Path(__file__).resolve().parent.parent / "evals/narrator/prompts/record-evidence-target-quotes-v1.md"
PROMPT_SHA256 = "4583e3c1ade0896696636e7e8174e7183f73b85c46c524809862b632de948ae3"
PACKET_PREFIX = evidence.PACKET_PREFIX
MAX_SUPPORTS = evidence.MAX_SUPPORTS
MAX_SOURCES_PER_SUPPORT = evidence.MAX_SOURCES_PER_SUPPORT
_ERROR_CODES = frozenset({
    "record_quote_evidence_contract_invalid", "record_quote_evidence_case_invalid",
    "record_quote_evidence_schema_invalid", "record_quote_evidence_source_units_invalid",
    "record_quote_evidence_source_ids_invalid", "record_quote_evidence_path_invalid",
    "record_quote_evidence_span_invalid", "record_quote_evidence_quote_missing",
    "record_quote_evidence_quote_ambiguous", "record_quote_evidence_user_budget_exceeded",
    "record_quote_evidence_prompt_unavailable", "record_quote_evidence_prompt_metadata_invalid",
    "record_quote_evidence_prompt_hash_mismatch",
})


class QuoteEvidenceEnvelopeError(ValueError):
    """A closed reason set; raw source/response text must not escape as an error."""

    def __init__(self, code: str) -> None:
        self.code = code if code in _ERROR_CODES else "record_quote_evidence_contract_invalid"
        super().__init__(self.code)


def _legacy_error(exc: evidence.EvidenceEnvelopeError) -> QuoteEvidenceEnvelopeError:
    return QuoteEvidenceEnvelopeError(exc.code.replace("record_evidence_", "record_quote_evidence_", 1))


class RecordQuoteSupport(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, populate_by_name=True, revalidate_instances="always")

    path: str = Field(alias="p", strict=True)
    quote: str = Field(alias="c", min_length=1, strict=True)
    source_ids: tuple[StrictStr, ...] = Field(alias="s", min_length=1, max_length=MAX_SOURCES_PER_SUPPORT)
    modality: Literal["established", "suggested", "unresolved"] = Field(alias="m")


class RecordQuoteEvidenceProposal(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, populate_by_name=True, revalidate_instances="always")

    records: RecordDerivationProposal
    supports: tuple[RecordQuoteSupport, ...] = Field(max_length=MAX_SUPPORTS)


def build_evidence_packet(case: DerivationCase) -> tuple[str, dict[str, Any]]:
    """Reuse the entire old packet and audit byte-for-byte, including its version."""
    try:
        return evidence.build_evidence_packet(case)
    except evidence.EvidenceEnvelopeError as exc:
        raise _legacy_error(exc) from None


def load_quote_evidence_prompt() -> tuple[Path, str]:
    try:
        document = PROMPT_PATH.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        raise QuoteEvidenceEnvelopeError("record_quote_evidence_prompt_unavailable") from None
    match = re.match(r"\A---\r?\n(?P<meta>.*?)\r?\n---(?:\r?\n)+", document, flags=re.DOTALL)
    if match is None or not re.search(
        rf"^name: *{re.escape(VERSION)} *$", match["meta"], flags=re.MULTILINE
    ):
        raise QuoteEvidenceEnvelopeError("record_quote_evidence_prompt_metadata_invalid")
    body = document[match.end():].strip()
    if hashlib.sha256(body.encode("utf-8")).hexdigest() != PROMPT_SHA256:
        raise QuoteEvidenceEnvelopeError("record_quote_evidence_prompt_hash_mismatch")
    return PROMPT_PATH, body


def validate_supports(case: DerivationCase, envelope: RecordQuoteEvidenceProposal) -> dict[str, Any]:
    """Resolve unique exact target quotes, then reuse the unchanged numeric gate."""
    try:
        if not isinstance(envelope, RecordQuoteEvidenceProposal):
            raise ValueError
        envelope = RecordQuoteEvidenceProposal.model_validate(envelope)
        checked = RecordQuoteEvidenceProposal.model_validate(
            envelope.model_dump(mode="json", by_alias=True, warnings="error"))
    except (ValidationError, ValueError, TypeError, AttributeError):
        raise QuoteEvidenceEnvelopeError("record_quote_evidence_schema_invalid") from None
    records = checked.records.model_dump(mode="json", by_alias=True)
    resolved = []
    try:
        for support in checked.supports:
            field_text = evidence._record_text(records, support.path)
            start = field_text.find(support.quote)
            if start < 0:
                raise QuoteEvidenceEnvelopeError("record_quote_evidence_quote_missing")
            # Advancing by one counts overlapping occurrences, not just disjoint ones.
            if field_text.find(support.quote, start + 1) >= 0:
                raise QuoteEvidenceEnvelopeError("record_quote_evidence_quote_ambiguous")
            resolved.append({"p": support.path, "b": start, "e": start + len(support.quote),
                             "s": list(support.source_ids), "m": support.modality})
        numeric = evidence.RecordEvidenceProposal.model_validate({"records": records, "supports": resolved})
        audit = evidence.validate_supports(case, numeric)
    except evidence.EvidenceEnvelopeError as exc:
        raise _legacy_error(exc) from None
    audit["quote_protocol"] = VERSION
    audit["quote_resolution"] = "unique_exact_substring"
    audit["validated_supports"] = [
        {**item, "quote": support.quote}
        for item, support in zip(audit["validated_supports"], checked.supports)
    ]
    return audit
