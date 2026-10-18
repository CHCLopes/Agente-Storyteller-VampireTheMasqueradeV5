"""Pure source-preserving foundation for narrative derivation admission.

The caller owns admission of the complete narrative ``n`` before creating a
source. This module neither verifies that external admission nor normalizes the
text. Whole-text identity authorizes an attributed source view only; it is not
proof of canonical truth, atomic claims, or semantic equivalence.
"""

from __future__ import annotations

import hashlib
import json
from enum import Enum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StrictStr, field_validator, model_validator


PROTOCOL = "narrative-source-v1"
_SHA256 = Annotated[StrictStr, Field(pattern=r"^[0-9a-f]{64}$")]
_Identifier = Annotated[StrictStr, Field(min_length=1, max_length=240)]
_Text = Annotated[StrictStr, Field(min_length=1)]


class NarrativeVisibility(str, Enum):
    PUBLIC = "public"
    PLAYER = "player"
    STORYTELLER = "storyteller"
    SYSTEM = "system"


class DerivationDestination(str, Enum):
    NARRATIVE_SOURCE_VIEW = "narrative_source_view"
    CANONICAL_ASSERTION = "canonical_assertion"


class ReferenceStatus(str, Enum):
    VALID = "valid"
    INVALID = "invalid"
    NOT_CHECKED = "not_checked"


class TextRelation(str, Enum):
    IDENTICAL = "identical"
    DIFFERENT = "different"
    NOT_CHECKED = "not_checked"


class SemanticStatus(str, Enum):
    NOT_ASSESSED = "not_assessed"
    INDETERMINATE = "indeterminate"


class DerivationDecision(str, Enum):
    SOURCE_ONLY = "source_only"
    INDETERMINATE = "indeterminate"
    REJECTED = "rejected"


class GroundingCode(str, Enum):
    SOURCE_INVALID = "narrative_grounding_source_invalid"
    BINDING_INVALID = "narrative_grounding_binding_invalid"
    TEXT_INVALID = "narrative_grounding_text_invalid"
    CONTEXT_MISMATCH = "narrative_grounding_context_mismatch"
    SOURCE_HASH_MISMATCH = "narrative_grounding_source_hash_mismatch"
    SOURCE_FINGERPRINT_MISMATCH = "narrative_grounding_source_fingerprint_mismatch"
    DERIVED_HASH_MISMATCH = "narrative_grounding_derived_hash_mismatch"
    WHOLE_SOURCE_IDENTITY = "narrative_grounding_whole_source_identity"
    CANONICAL_NOT_ESTABLISHED = "narrative_grounding_canonical_not_established"
    TEXT_NOT_IDENTICAL = "narrative_grounding_text_not_identical"
    PROJECTION_INVALID = "narrative_grounding_projection_invalid"


class NarrativeGroundingError(ValueError):
    """Closed diagnostic code, with no source text or external exception data."""

    def __init__(self, code: GroundingCode):
        self.code = code.value
        super().__init__(self.code)


class _ImmutableModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid", frozen=True, revalidate_instances="always",
        hide_input_in_errors=True,
    )


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class NarrativeSource(_ImmutableModel):
    protocol: Literal["narrative-source-v1"] = PROTOCOL
    source_id: _Identifier
    session_id: _Identifier
    turn_id: _Identifier
    invocation_id: _Identifier
    text: _Text
    source_policy: _Identifier
    visibility: NarrativeVisibility
    sha256: _SHA256

    @field_validator("source_id", "session_id", "turn_id", "invocation_id", "source_policy")
    @classmethod
    def require_nonblank_identity(cls, value: str) -> str:
        if not value.strip():
            raise ValueError(GroundingCode.SOURCE_INVALID.value)
        return value

    @model_validator(mode="after")
    def require_source_digest(self) -> "NarrativeSource":
        try:
            matches = self.sha256 == _sha256(self.text)
        except (TypeError, UnicodeError):
            matches = False
        if not matches:
            raise ValueError(GroundingCode.SOURCE_HASH_MISMATCH.value)
        return self


class DerivationBinding(_ImmutableModel):
    protocol: Literal["narrative-derivation-binding-v1"] = "narrative-derivation-binding-v1"
    source_id: _Identifier
    session_id: _Identifier
    turn_id: _Identifier
    invocation_id: _Identifier
    source_sha256: _SHA256
    source_fingerprint: _SHA256
    derived_sha256: _SHA256
    destination: DerivationDestination

    @field_validator("source_id", "session_id", "turn_id", "invocation_id")
    @classmethod
    def require_nonblank_identity(cls, value: str) -> str:
        if not value.strip():
            raise ValueError(GroundingCode.BINDING_INVALID.value)
        return value


class DerivationAssessment(_ImmutableModel):
    protocol: Literal["narrative-derivation-assessment-v1"] = "narrative-derivation-assessment-v1"
    policy_version: Literal["narrative-grounding.v1"] = "narrative-grounding.v1"
    reference_status: ReferenceStatus
    text_relation: TextRelation
    semantic_status: SemanticStatus
    decision: DerivationDecision
    code: GroundingCode


class SourceProjection(_ImmutableModel):
    protocol: Literal["narrative-source-projection-v1"] = "narrative-source-projection-v1"
    representation: Literal["projected_source"] = "projected_source"
    text: _Text
    source: NarrativeSource
    binding: DerivationBinding
    assessment: DerivationAssessment

    @model_validator(mode="after")
    def require_recomputed_source_only(self) -> "SourceProjection":
        actual = evaluate_narrative_derivation(self.source, self.binding, self.text)
        if actual.decision is not DerivationDecision.SOURCE_ONLY or self.assessment != actual:
            raise ValueError(GroundingCode.PROJECTION_INVALID.value)
        return self


def _validated_source(source: object) -> NarrativeSource:
    if type(source) is not NarrativeSource:
        raise NarrativeGroundingError(GroundingCode.SOURCE_INVALID)
    try:
        return NarrativeSource.model_validate(source)
    except ValueError:
        raise NarrativeGroundingError(GroundingCode.SOURCE_INVALID) from None


def _source_fingerprint(source: NarrativeSource) -> str:
    """Bind all source metadata as supplied; this does not authenticate it."""
    canonical = json.dumps(
        source.model_dump(mode="json"), ensure_ascii=False, sort_keys=True,
        separators=(",", ":"),
    )
    return _sha256(canonical)


def _validated_binding(binding: object) -> DerivationBinding:
    if type(binding) is not DerivationBinding:
        raise NarrativeGroundingError(GroundingCode.BINDING_INVALID)
    try:
        return DerivationBinding.model_validate(binding)
    except ValueError:
        raise NarrativeGroundingError(GroundingCode.BINDING_INVALID) from None


def _derived_digest(derived_text: object) -> str:
    if not isinstance(derived_text, str) or not derived_text:
        raise NarrativeGroundingError(GroundingCode.TEXT_INVALID)
    try:
        return _sha256(derived_text)
    except UnicodeError:
        raise NarrativeGroundingError(GroundingCode.TEXT_INVALID) from None


def create_narrative_source(
    *, source_id: str, session_id: str, turn_id: str, invocation_id: str,
    text: str, source_policy: str,
    visibility: NarrativeVisibility | str = NarrativeVisibility.PLAYER,
) -> NarrativeSource:
    """Bind the caller's already-admitted complete ``n`` without rewriting it."""
    digest = _derived_digest(text)
    try:
        return NarrativeSource(
            source_id=source_id, session_id=session_id, turn_id=turn_id,
            invocation_id=invocation_id, text=text, source_policy=source_policy,
            visibility=visibility, sha256=digest,
        )
    except ValueError:
        raise NarrativeGroundingError(GroundingCode.SOURCE_INVALID) from None


def bind_narrative_derivation(
    source: NarrativeSource, derived_text: str, *,
    destination: DerivationDestination | str,
) -> DerivationBinding:
    """Create a content-bound request for assessment; this grants no admission."""
    checked_source = _validated_source(source)
    digest = _derived_digest(derived_text)
    try:
        return DerivationBinding(
            source_id=checked_source.source_id, session_id=checked_source.session_id,
            turn_id=checked_source.turn_id, invocation_id=checked_source.invocation_id,
            source_sha256=checked_source.sha256,
            source_fingerprint=_source_fingerprint(checked_source), derived_sha256=digest,
            destination=destination,
        )
    except ValueError:
        raise NarrativeGroundingError(GroundingCode.BINDING_INVALID) from None


def _rejected(code: GroundingCode) -> DerivationAssessment:
    return DerivationAssessment(
        reference_status=ReferenceStatus.INVALID,
        text_relation=TextRelation.NOT_CHECKED,
        semantic_status=SemanticStatus.NOT_ASSESSED,
        decision=DerivationDecision.REJECTED, code=code,
    )


def evaluate_narrative_derivation(
    source: NarrativeSource, binding: DerivationBinding, derived_text: str,
) -> DerivationAssessment:
    """Revalidate all inputs and distinguish attribution from canonical truth."""
    try:
        checked_source = _validated_source(source)
        checked_binding = _validated_binding(binding)
        digest = _derived_digest(derived_text)
    except NarrativeGroundingError as exc:
        return _rejected(GroundingCode(exc.code))
    for field in ("source_id", "session_id", "turn_id", "invocation_id"):
        if getattr(checked_source, field) != getattr(checked_binding, field):
            return _rejected(GroundingCode.CONTEXT_MISMATCH)
    if checked_binding.source_sha256 != checked_source.sha256:
        return _rejected(GroundingCode.SOURCE_HASH_MISMATCH)
    if checked_binding.source_fingerprint != _source_fingerprint(checked_source):
        return _rejected(GroundingCode.SOURCE_FINGERPRINT_MISMATCH)
    if checked_binding.derived_sha256 != digest:
        return _rejected(GroundingCode.DERIVED_HASH_MISMATCH)
    if derived_text != checked_source.text:
        return DerivationAssessment(
            reference_status=ReferenceStatus.VALID,
            text_relation=TextRelation.DIFFERENT,
            semantic_status=SemanticStatus.INDETERMINATE,
            decision=DerivationDecision.INDETERMINATE,
            code=GroundingCode.TEXT_NOT_IDENTICAL,
        )
    source_view = checked_binding.destination is DerivationDestination.NARRATIVE_SOURCE_VIEW
    return DerivationAssessment(
        reference_status=ReferenceStatus.VALID,
        text_relation=TextRelation.IDENTICAL,
        semantic_status=(SemanticStatus.NOT_ASSESSED if source_view else SemanticStatus.INDETERMINATE),
        decision=(DerivationDecision.SOURCE_ONLY if source_view else DerivationDecision.INDETERMINATE),
        code=(GroundingCode.WHOLE_SOURCE_IDENTITY if source_view else GroundingCode.CANONICAL_NOT_ESTABLISHED),
    )


def materialize_source_projection(
    source: NarrativeSource, binding: DerivationBinding, derived_text: str,
) -> SourceProjection:
    """Materialize only the attributed whole source, never an atomic fact.

    No caller-provided assessment is accepted. The decision is recomputed from
    the source, binding, identities and exact text on every invocation.
    """
    assessment = evaluate_narrative_derivation(source, binding, derived_text)
    if assessment.decision is not DerivationDecision.SOURCE_ONLY:
        raise NarrativeGroundingError(assessment.code)
    try:
        return SourceProjection(
            text=derived_text, source=_validated_source(source),
            binding=_validated_binding(binding), assessment=assessment,
        )
    except ValueError:
        raise NarrativeGroundingError(GroundingCode.PROJECTION_INVALID) from None
