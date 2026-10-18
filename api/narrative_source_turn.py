"""Pure binding of an admitted attributed source to an opt-in turn commit.

The server owns the origin and admission of the draft and n/q. This module
checks identity, references and literal presentation; it does not derive facts,
authenticate a provider, or establish the semantic truth of narrative text.
"""
from __future__ import annotations

from collections.abc import Mapping
from enum import Enum
import hashlib
import json
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StrictStr, field_validator, model_validator

from api.llm.contract import Provenance
from api.narrative_grounding import SourceProjection
from api.narrative_source_profile import VERSION as SOURCE_POLICY
from api.turn_models import CanonicalEvent, CanonicalFact, NarrativeRecord

PROTOCOL = "narrative-source-turn-v1"
INVOCATION_OPERATION = "H6.narrative_source"
_FACT_TYPES = frozenset({"mechanics.resolution", "action.declaration", "state.character", "world.relationships"})
_EVENT_TYPES = frozenset({"player_action_resolved", "player_action_declared", "relationship_state_updated"})
_VISIBILITY = {"public": 0, "player": 1, "storyteller": 2, "system": 3}
_Identifier = Annotated[StrictStr, Field(min_length=1, max_length=240)]
_SHA256 = Annotated[StrictStr, Field(pattern=r"^[0-9a-f]{64}$")]


class SourceTurnCode(str, Enum):
    INVALID = "source_turn_invalid"
    ENVELOPE_INVALID = "source_turn_envelope_invalid"
    NARRATIVE_INVALID = "source_turn_narrative_invalid"
    PROJECTION_INVALID = "source_turn_projection_invalid"
    PRESENTATION_MISMATCH = "source_turn_presentation_mismatch"
    IDENTITY_MISMATCH = "source_turn_identity_mismatch"
    ANTECEDENTS_INVALID = "source_turn_antecedents_invalid"
    REFERENCES_INVALID = "source_turn_references_invalid"
    MEMORIES_FORBIDDEN = "source_turn_memories_forbidden"
    PROVENANCE_INVALID = "source_turn_provenance_invalid"
    PROVENANCE_MISMATCH = "source_turn_provenance_mismatch"
    CONTRACT_REQUIRED = "source_turn_contract_required"
    ATTEMPT_MISMATCH = "source_turn_attempt_mismatch"
    STORED_PAIR_MISMATCH = "source_turn_stored_pair_mismatch"
    VISIBILITY_FORBIDDEN = "source_turn_visibility_forbidden"
    HISTORY_INCOMPATIBLE = "source_turn_history_incompatible"
    QUERY_INVALID = "source_turn_query_invalid"


class SourceTurnContractError(ValueError):
    """Closed diagnostics shared with the opt-in persistence boundary."""

    def __init__(self, code: SourceTurnCode | str):
        try:
            self.code = SourceTurnCode(code).value
        except (TypeError, ValueError):
            self.code = SourceTurnCode.INVALID.value
        super().__init__(self.code)


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _canonical_sha(value: object) -> str:
    return _sha(json.dumps(value, ensure_ascii=False, sort_keys=True,
                           separators=(",", ":"), allow_nan=False))


def _unpack(value: object) -> object:
    # Legacy records do not revalidate instances. Preserve even forged extra
    # fields while rebuilding their complete nested data for model validation.
    if isinstance(value, BaseModel):
        result = dict(value.__dict__)
        result.update(value.__pydantic_extra__ or {})
        return {key: _unpack(item) for key, item in result.items()}
    if isinstance(value, Mapping):
        return {key: _unpack(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_unpack(item) for item in value]
    return value


def _checked(model, value: object, code: SourceTurnCode):
    if type(value) is not model and not isinstance(value, Mapping):
        raise SourceTurnContractError(code)
    try:
        return model.model_validate(_unpack(value))
    except (ValueError, TypeError, AttributeError, RecursionError):
        raise SourceTurnContractError(code) from None


def _ordered(value: object, code: SourceTurnCode) -> tuple:
    if type(value) not in (list, tuple):
        raise SourceTurnContractError(code)
    return tuple(value)


def _identity(value: object) -> bool:
    return type(value) is str and 0 < len(value) <= 240 and value == value.strip() and bool(value)


class NarrativeSourceTurnEnvelope(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, revalidate_instances="always",
                              hide_input_in_errors=True)
    protocol: Literal["narrative-source-turn-v1"] = PROTOCOL
    operation_id: _Identifier
    attempt_id: _Identifier
    narrative_id: _Identifier
    question: Annotated[StrictStr, Field(min_length=3, max_length=200)]
    projection: SourceProjection
    source_event_ids: tuple[_Identifier, ...] = Field(min_length=1)
    presentation_sha256: _SHA256
    invocation_operation: Literal["H6.narrative_source"] = INVOCATION_OPERATION
    provenance_sha256: _SHA256

    @field_validator("operation_id", "attempt_id", "narrative_id")
    @classmethod
    def identifiers_are_literal(cls, value: str) -> str:
        if not _identity(value):
            raise ValueError(SourceTurnCode.IDENTITY_MISMATCH.value)
        return value

    @field_validator("source_event_ids", mode="before")
    @classmethod
    def ordered_references(cls, value: object) -> object:
        if type(value) not in (list, tuple):
            raise ValueError(SourceTurnCode.REFERENCES_INVALID.value)
        return value

    @model_validator(mode="after")
    def bind_integral_presentation(self) -> "NarrativeSourceTurnEnvelope":
        source = self.projection.source
        if source.source_policy != SOURCE_POLICY or source.visibility.value not in ("public", "player"):
            raise ValueError(SourceTurnCode.PROJECTION_INVALID.value)
        if not 40 <= len(self.projection.text) <= 1600:
            raise ValueError(SourceTurnCode.PROJECTION_INVALID.value)
        if any(not _identity(getattr(source, name)) for name in
               ("source_id", "session_id", "turn_id", "invocation_id")):
            raise ValueError(SourceTurnCode.IDENTITY_MISMATCH.value)
        if any(text != " ".join(text.split()) for text in (self.projection.text, self.question)):
            raise ValueError(SourceTurnCode.PRESENTATION_MISMATCH.value)
        ids = self.source_event_ids
        if any(not _identity(item) for item in ids) or tuple(sorted(set(ids))) != ids:
            raise ValueError(SourceTurnCode.REFERENCES_INVALID.value)
        if self.presentation_sha256 != _sha(self.projection.text + "\n\n" + self.question):
            raise ValueError(SourceTurnCode.PRESENTATION_MISMATCH.value)
        return self


def _narrative(value: object) -> NarrativeRecord:
    record = _checked(NarrativeRecord, value, SourceTurnCode.NARRATIVE_INVALID)
    raw = _unpack(value)
    literal_fields = ("text", "narrative_id", "session_id", "turn_id", "invocation_id")
    if (any(raw.get(name) != getattr(record, name) for name in literal_fields)
            or raw.get("complete", True) is not True):
        raise SourceTurnContractError(SourceTurnCode.NARRATIVE_INVALID)
    raw_ids = _ordered(raw.get("source_event_ids"), SourceTurnCode.NARRATIVE_INVALID)
    if raw_ids != record.source_event_ids:
        raise SourceTurnContractError(SourceTurnCode.NARRATIVE_INVALID)
    return record


def _check_pair(envelope: NarrativeSourceTurnEnvelope, narrative: NarrativeRecord) -> None:
    source = envelope.projection.source
    if (envelope.narrative_id != narrative.narrative_id or source.session_id != narrative.session_id
            or source.turn_id != narrative.turn_id or source.invocation_id != narrative.invocation_id):
        raise SourceTurnContractError(SourceTurnCode.IDENTITY_MISMATCH)
    if source.visibility.value != narrative.visibility.value:
        raise SourceTurnContractError(SourceTurnCode.VISIBILITY_FORBIDDEN)
    if narrative.text != envelope.projection.text + "\n\n" + envelope.question:
        raise SourceTurnContractError(SourceTurnCode.PRESENTATION_MISMATCH)
    ids = narrative.source_event_ids
    if len(set(ids)) != len(ids) or tuple(sorted(ids)) != envelope.source_event_ids:
        raise SourceTurnContractError(SourceTurnCode.REFERENCES_INVALID)


def _audit_digest(provenance: object, invocation_id: str, operation: str) -> str:
    try:
        if not isinstance(provenance, Mapping) or set(provenance) != {"invocations"}:
            raise ValueError()
        rows = _ordered(provenance["invocations"], SourceTurnCode.PROVENANCE_INVALID)
        ids = set()
        matches = []
        for row in rows:
            if not isinstance(row, Mapping) or set(row) != {"invocation_id", "operation", "status", "provenance", "error"}:
                raise ValueError()
            if not _identity(row["invocation_id"]) or row["invocation_id"] in ids or not _identity(row["operation"]):
                raise ValueError()
            ids.add(row["invocation_id"])
            if row["operation"] == operation or row["invocation_id"] == invocation_id:
                matches.append(row)
        if len(matches) != 1:
            raise ValueError()
        row = matches[0]
        if (row["operation"] != INVOCATION_OPERATION or operation != INVOCATION_OPERATION
                or row["invocation_id"] != invocation_id or row["status"] != "completed"
                or row["error"] is not None):
            raise ValueError()
        typed = _checked(Provenance, row["provenance"], SourceTurnCode.PROVENANCE_INVALID)
        if typed.invocation_id != invocation_id:
            raise ValueError()
        # Whole received JSON is bound. Provider authority and absent usage are
        # deliberately not inferred from this internally consistent audit.
        return _canonical_sha(provenance)
    except (ValueError, TypeError, AttributeError, RecursionError):
        raise SourceTurnContractError(SourceTurnCode.PROVENANCE_INVALID) from None


def create_source_turn_envelope(
    *, projection: SourceProjection, narrative: NarrativeRecord, question: str,
    operation_id: str, attempt_id: str, provenance: Mapping,
) -> NarrativeSourceTurnEnvelope:
    """Bind a source/presentation pair; aggregate commit validation is separate."""
    record = _narrative(narrative)
    checked = _checked(SourceProjection, projection, SourceTurnCode.PROJECTION_INVALID)
    try:
        envelope = NarrativeSourceTurnEnvelope(
            operation_id=operation_id, attempt_id=attempt_id, narrative_id=record.narrative_id,
            question=question, projection=checked, source_event_ids=tuple(sorted(record.source_event_ids)),
            presentation_sha256=_sha(checked.text + "\n\n" + question),
            provenance_sha256=_audit_digest(provenance, checked.source.invocation_id, INVOCATION_OPERATION),
        )
    except (ValueError, TypeError, AttributeError, RecursionError):
        raise SourceTurnContractError(SourceTurnCode.ENVELOPE_INVALID) from None
    _check_pair(envelope, record)
    return envelope


def validate_source_turn_commit(
    envelope: NarrativeSourceTurnEnvelope | Mapping, *, narrative: NarrativeRecord | Mapping,
    session_id: str, turn_id: str, operation_id: str, attempt_id: str,
    expected_invocation_id: str, expected_invocation_operation: str,
    facts, events, memory_candidates, episodic_memories, provenance: Mapping,
) -> NarrativeSourceTurnEnvelope:
    """Revalidate the complete opt-in aggregate against server-owned identities.

    The restricted fact/event kinds are existing server antecedents, not output
    of narrative derivation. Empty memory collections are mandatory even when a
    caller removes an optional marker elsewhere; persistence anchors that duty
    independently in the pre-existing attempt.
    """
    checked = _checked(NarrativeSourceTurnEnvelope, envelope, SourceTurnCode.ENVELOPE_INVALID)
    record = _narrative(narrative)
    _check_pair(checked, record)
    source = checked.projection.source
    for actual, expected in ((source.session_id, session_id), (source.turn_id, turn_id),
                             (checked.operation_id, operation_id), (checked.attempt_id, attempt_id),
                             (source.invocation_id, expected_invocation_id),
                             (checked.invocation_operation, expected_invocation_operation)):
        if not _identity(expected) or actual != expected:
            raise SourceTurnContractError(SourceTurnCode.IDENTITY_MISMATCH)
    for memories in (memory_candidates, episodic_memories):
        if _ordered(memories, SourceTurnCode.MEMORIES_FORBIDDEN):
            raise SourceTurnContractError(SourceTurnCode.MEMORIES_FORBIDDEN)
    checked_facts = tuple(_checked(CanonicalFact, item, SourceTurnCode.ANTECEDENTS_INVALID)
                          for item in _ordered(facts, SourceTurnCode.ANTECEDENTS_INVALID))
    checked_events = tuple(_checked(CanonicalEvent, item, SourceTurnCode.ANTECEDENTS_INVALID)
                           for item in _ordered(events, SourceTurnCode.ANTECEDENTS_INVALID))
    fact_map = {item.fact_id: item for item in checked_facts}
    event_map = {item.event_id: item for item in checked_events}
    if (len(fact_map) != len(checked_facts) or len(event_map) != len(checked_events)
            or len({item.sequence for item in checked_events}) != len(checked_events)
            or any(item.fact_type not in _FACT_TYPES for item in checked_facts)):
        raise SourceTurnContractError(SourceTurnCode.ANTECEDENTS_INVALID)
    for event in checked_events:
        if (event.event_type not in _EVENT_TYPES or event.session_id != session_id
                or event.turn_id != turn_id or event.pending
                or len(set(event.fact_ids)) != len(event.fact_ids)):
            raise SourceTurnContractError(SourceTurnCode.ANTECEDENTS_INVALID)
        if not event.fact_ids or set(event.fact_ids) - fact_map.keys():
            raise SourceTurnContractError(SourceTurnCode.REFERENCES_INVALID)
        if any(_VISIBILITY[fact_map[item].visibility.value] > _VISIBILITY[event.visibility.value]
               for item in event.fact_ids):
            raise SourceTurnContractError(SourceTurnCode.VISIBILITY_FORBIDDEN)
    if set(checked.source_event_ids) - event_map.keys():
        raise SourceTurnContractError(SourceTurnCode.REFERENCES_INVALID)
    if any(_VISIBILITY[event_map[item].visibility.value] > _VISIBILITY[source.visibility.value]
           for item in checked.source_event_ids):
        raise SourceTurnContractError(SourceTurnCode.VISIBILITY_FORBIDDEN)
    digest = _audit_digest(provenance, expected_invocation_id, expected_invocation_operation)
    if digest != checked.provenance_sha256:
        raise SourceTurnContractError(SourceTurnCode.PROVENANCE_MISMATCH)
    return checked
