"""Offline source attribution boundaries, without a semantic truth oracle."""

import hashlib
import json

import pytest
from pydantic import ValidationError

from api.narrative_grounding import (
    DerivationDecision, DerivationDestination, GroundingCode,
    NarrativeGroundingError, NarrativeVisibility, ReferenceStatus,
    SemanticStatus, SourceProjection, TextRelation,
    bind_narrative_derivation, create_narrative_source,
    evaluate_narrative_derivation, materialize_source_projection,
)


NARRATIVE = (
    "  Na galeria silenciosa, um espelho reflete a tapeçaria azul diante de uma "
    "janela fechada.\r\n"
    "Lia diz: “Talvez exista uma passagem, mas não ouvi ruído”. "
    "O catálogo de cafe\u0301 permanece sobre o banco, longe da porta.  "
)
QUESTION = "O que você deseja fazer agora?"
VIEW = DerivationDestination.NARRATIVE_SOURCE_VIEW
ASSERTION = DerivationDestination.CANONICAL_ASSERTION


def source(*, visibility=NarrativeVisibility.PLAYER):
    # The server supplies n alone. This module does not split n from q or
    # authenticate the server's earlier admission of the narrative.
    return create_narrative_source(
        source_id="narrative-source-1", session_id="session-1", turn_id="turn-1",
        invocation_id="invocation-1", text=NARRATIVE,
        source_policy="synthetic-server-admission.v1", visibility=visibility,
    )


def assert_rejected(narrative_source, binding, text, code):
    assessment = evaluate_narrative_derivation(narrative_source, binding, text)
    assert assessment.decision is DerivationDecision.REJECTED
    assert assessment.reference_status is ReferenceStatus.INVALID
    assert assessment.text_relation is TextRelation.NOT_CHECKED
    assert assessment.semantic_status is SemanticStatus.NOT_ASSESSED
    assert assessment.code is code
    with pytest.raises(NarrativeGroundingError) as error:
        materialize_source_projection(narrative_source, binding, text)
    assert error.value.code == code.value
    assert str(error.value) == code.value


def test_whole_source_view_preserves_literal_n_and_attribution_without_truth_approval():
    narrative_source = source()
    binding = bind_narrative_derivation(narrative_source, NARRATIVE, destination=VIEW)
    projection = materialize_source_projection(narrative_source, binding, NARRATIVE)

    assert len(NARRATIVE.split()) > 25  # The experiment's soft limit is not a gate.
    assert projection.text == narrative_source.text == NARRATIVE
    assert QUESTION not in projection.text
    assert "\r\n" in projection.text and "cafe\u0301" in projection.text
    assert projection.source == narrative_source
    assert projection.binding == binding
    assert projection.representation == "projected_source"
    assert narrative_source.sha256 == hashlib.sha256(NARRATIVE.encode("utf-8")).hexdigest()
    canonical_source = json.dumps(
        narrative_source.model_dump(mode="json"),
        ensure_ascii=False, sort_keys=True, separators=(",", ":"),
    )
    assert binding.source_fingerprint == hashlib.sha256(
        canonical_source.encode("utf-8")
    ).hexdigest()
    assessment = projection.assessment
    assert assessment.protocol == "narrative-derivation-assessment-v1"
    assert assessment.policy_version == "narrative-grounding.v1"
    assert assessment.reference_status is ReferenceStatus.VALID
    assert assessment.text_relation is TextRelation.IDENTICAL
    assert assessment.semantic_status is SemanticStatus.NOT_ASSESSED
    assert assessment.decision is DerivationDecision.SOURCE_ONLY


def test_identical_text_does_not_establish_a_canonical_assertion():
    narrative_source = source()
    binding = bind_narrative_derivation(narrative_source, NARRATIVE, destination=ASSERTION)
    assessment = evaluate_narrative_derivation(narrative_source, binding, NARRATIVE)

    assert assessment.reference_status is ReferenceStatus.VALID
    assert assessment.text_relation is TextRelation.IDENTICAL
    assert assessment.semantic_status is SemanticStatus.INDETERMINATE
    assert assessment.decision is DerivationDecision.INDETERMINATE
    assert assessment.code is GroundingCode.CANONICAL_NOT_ESTABLISHED
    with pytest.raises(NarrativeGroundingError, match=assessment.code.value):
        materialize_source_projection(narrative_source, binding, NARRATIVE)


@pytest.mark.parametrize(
    "derived",
    [
        pytest.param("exista uma passagem", id="literal-fragment-without-modal-context"),
        pytest.param(NARRATIVE.replace("não ouvi ruído", "ouvi ruído"), id="negation-removed"),
        pytest.param(
            NARRATIVE.replace("tapeçaria azul", "tapeçaria").replace(
                "janela fechada", "janela azul fechada"
            ), id="color-reattached",
        ),
        pytest.param(
            "\r\n".join(reversed(NARRATIVE.split("\r\n"))), id="sentences-reordered",
        ),
        pytest.param(
            NARRATIVE.replace("permanece sobre o banco", "continua em cima do banco"),
            id="faithful-paraphrase-not-certified",
        ),
        pytest.param(
            NARRATIVE.replace("Lia diz: “", "").replace("ruído”.", "ruído."),
            id="speaker-and-quotation-context-removed",
        ),
    ],
)
def test_changed_text_is_indeterminate_even_with_a_valid_reference(derived):
    narrative_source = source()
    binding = bind_narrative_derivation(narrative_source, derived, destination=VIEW)
    assessment = evaluate_narrative_derivation(narrative_source, binding, derived)

    assert assessment.reference_status is ReferenceStatus.VALID
    assert assessment.text_relation is TextRelation.DIFFERENT
    assert assessment.semantic_status is SemanticStatus.INDETERMINATE
    assert assessment.decision is DerivationDecision.INDETERMINATE
    with pytest.raises(NarrativeGroundingError, match=GroundingCode.TEXT_NOT_IDENTICAL.value):
        materialize_source_projection(narrative_source, binding, derived)


@pytest.mark.parametrize("field", ["source_id", "session_id", "turn_id", "invocation_id"])
def test_binding_from_another_context_cannot_materialize_same_text(field):
    narrative_source = source()
    binding = bind_narrative_derivation(narrative_source, NARRATIVE, destination=VIEW)
    changed = binding.model_copy(update={field: "other-context"})
    assert_rejected(narrative_source, changed, NARRATIVE, GroundingCode.CONTEXT_MISMATCH)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("visibility", NarrativeVisibility.PUBLIC),
        ("source_policy", "different-server-policy.v2"),
    ],
)
def test_old_binding_rejects_source_metadata_changes_even_when_text_hash_matches(field, value):
    narrative_source = source()
    binding = bind_narrative_derivation(narrative_source, NARRATIVE, destination=VIEW)
    changed = narrative_source.model_copy(update={field: value})
    assert changed.sha256 == narrative_source.sha256
    assert_rejected(changed, binding, NARRATIVE, GroundingCode.SOURCE_FINGERPRINT_MISMATCH)


@pytest.mark.parametrize("change", ["source-hash", "derived-hash", "source-text"])
def test_stale_or_forged_content_hashes_are_integrity_rejections(change):
    narrative_source = source()
    binding = bind_narrative_derivation(narrative_source, NARRATIVE, destination=VIEW)
    if change == "source-hash":
        binding = binding.model_copy(update={"source_sha256": "0" * 64})
        expected = GroundingCode.SOURCE_HASH_MISMATCH
    elif change == "derived-hash":
        binding = binding.model_copy(update={"derived_sha256": "0" * 64})
        expected = GroundingCode.DERIVED_HASH_MISMATCH
    else:
        narrative_source = narrative_source.model_copy(
            update={"text": NARRATIVE + " DADO_RESTRITO_NAO_ECOAR"}
        )
        expected = GroundingCode.SOURCE_INVALID
    assert_rejected(narrative_source, binding, NARRATIVE, expected)


def test_forged_binding_instance_is_revalidated_before_deciding():
    narrative_source = source()
    binding = bind_narrative_derivation(narrative_source, NARRATIVE, destination=VIEW)
    forged = binding.model_copy(update={"destination": "unapproved_destination"})
    assert_rejected(narrative_source, forged, NARRATIVE, GroundingCode.BINDING_INVALID)


@pytest.mark.parametrize("destination", [VIEW, ASSERTION], ids=["partial-view", "whole-assertion"])
def test_forged_source_only_assessment_cannot_materialize_an_unestablished_derivation(destination):
    narrative_source = source()
    whole_binding = bind_narrative_derivation(narrative_source, NARRATIVE, destination=VIEW)
    approved_view = evaluate_narrative_derivation(narrative_source, whole_binding, NARRATIVE)
    derived = "exista uma passagem" if destination is VIEW else NARRATIVE
    binding = bind_narrative_derivation(narrative_source, derived, destination=destination)
    actual = evaluate_narrative_derivation(narrative_source, binding, derived)
    forged = actual.model_copy(update=approved_view.model_dump())
    assert actual.decision is DerivationDecision.INDETERMINATE
    assert forged.decision is DerivationDecision.SOURCE_ONLY

    with pytest.raises(ValidationError, match=GroundingCode.PROJECTION_INVALID.value):
        SourceProjection.model_validate(
            {"text": derived, "source": narrative_source, "binding": binding, "assessment": forged}
        )
    with pytest.raises(NarrativeGroundingError):
        materialize_source_projection(narrative_source, binding, derived)


def test_existing_projection_instance_is_rechecked_after_text_and_binding_are_changed():
    narrative_source = source()
    binding = bind_narrative_derivation(narrative_source, NARRATIVE, destination=VIEW)
    projection = materialize_source_projection(narrative_source, binding, NARRATIVE)
    derived = "exista uma passagem"
    changed = projection.model_copy(
        update={
            "text": derived,
            "binding": bind_narrative_derivation(narrative_source, derived, destination=VIEW),
        }
    )
    with pytest.raises(ValidationError, match=GroundingCode.PROJECTION_INVALID.value):
        SourceProjection.model_validate(changed)


@pytest.mark.parametrize(
    "visibility", [NarrativeVisibility.STORYTELLER, NarrativeVisibility.SYSTEM]
)
def test_whole_source_projection_preserves_restricted_visibility(visibility):
    narrative_source = source(visibility=visibility)
    binding = bind_narrative_derivation(narrative_source, NARRATIVE, destination=VIEW)
    projection = materialize_source_projection(narrative_source, binding, NARRATIVE)
    assert projection.source.visibility is visibility
    assert projection.source.source_policy == narrative_source.source_policy
    assert projection.assessment.decision is DerivationDecision.SOURCE_ONLY
    assert projection.assessment.semantic_status is SemanticStatus.NOT_ASSESSED


def test_non_utf8_source_metadata_is_rejected_with_a_closed_diagnostic():
    narrative_source = source()
    binding = bind_narrative_derivation(narrative_source, NARRATIVE, destination=VIEW)
    changed = narrative_source.model_copy(update={"source_policy": "\ud800"})
    assert_rejected(changed, binding, NARRATIVE, GroundingCode.SOURCE_INVALID)
