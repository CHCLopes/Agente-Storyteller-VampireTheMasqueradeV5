"""Offline contract and bounded-policy proofs for the isolated source profile."""
from datetime import datetime, timezone
import hashlib

from pydantic import ValidationError
import pytest

from api.narrative_grounding import (
    DerivationDecision, DerivationDestination, NarrativeVisibility, SemanticStatus,
    bind_narrative_derivation, create_narrative_source, materialize_source_projection,
)
from api.scene_director_service import SceneContinuationProposal, SceneProposalError
from api.scene_service import SceneState
from api.turn_models import CanonicalFact
from scripts import narrator_source_profile as profile


NARRATIVE = (
    "A chuva tamborila nas janelas da galeria enquanto a luminária oscila sobre o balcão. "
    "Um ruído seco atravessa o corredor vazio; sobre a mesa, um mapa dobrado repousa "
    "ao lado de uma caixa fechada."
)
QUESTION = "O que você faz agora?"
SCENE = SceneState(location="Galeria", npcs_present=("Mara",))


def _proposal(n=NARRATIVE, q=QUESTION):
    return profile.NarrativeSourceProposal.model_validate({"n": n, "q": q})


def _validate(proposal=None, **kwargs):
    args = {"current_scene": SCENE, "facts": (), "player_input": "Observo a galeria."}
    args.update(kwargs)
    return profile.validate_source_proposal(_proposal() if proposal is None else proposal, **args)


def _projection(index=1, **kwargs):
    args = {
        "source_id": f"source-{index}", "session_id": "synthetic-session",
        "turn_id": f"turn-{index}", "invocation_id": f"invocation-{index}",
        "current_scene": SCENE, "facts": (), "player_input": "Observo a galeria.",
    }
    args.update(kwargs)
    return profile.create_source_projection(_proposal(), **args)


def _resolution(success):
    return CanonicalFact(
        fact_id="resolution", fact_type="mechanics.resolution",
        predicate="resolved_player_action", value={"is_success": success},
        occurred_at=datetime(2026, 9, 7, tzinfo=timezone.utc),
    )


def _foreign_projection(**updates):
    args = {
        "source_id": "foreign", "session_id": "synthetic-session", "turn_id": "foreign-turn",
        "invocation_id": "foreign-invocation", "text": NARRATIVE,
        "source_policy": profile.VERSION, "visibility": "player",
    }
    args.update(updates)
    source = create_narrative_source(**args)
    binding = bind_narrative_derivation(
        source, source.text, destination=DerivationDestination.NARRATIVE_SOURCE_VIEW,
    )
    return materialize_source_projection(source, binding, source.text)


def test_wire_schema_has_only_required_n_and_q_with_exact_limits():
    schema = profile.NarrativeSourceProposal.model_json_schema(by_alias=True)
    assert set(schema["properties"]) == set(schema["required"]) == {"n", "q"}
    assert schema["additionalProperties"] is False
    assert (schema["properties"]["n"]["minLength"], schema["properties"]["n"]["maxLength"]) == (40, 1600)
    assert (schema["properties"]["q"]["minLength"], schema["properties"]["q"]["maxLength"]) == (3, 200)


def test_whitespace_normalization_precedes_length_and_source_identity():
    proposal = _proposal(" \n" + NARRATIVE.replace(" ", "\t\u00a0") + "\r\n", "  O que\n você faz agora?  ")
    assert proposal.narrative == NARRATIVE
    assert proposal.player_prompt == QUESTION
    assert _validate(proposal) == proposal
    with pytest.raises(ValidationError):
        _proposal(" " * 100 + "curto" + " " * 100)


@pytest.mark.parametrize("field,value", [
    ("n", 17), ("q", True), ("n", "x" * 39), ("n", "x" * 1601),
    ("q", "??"), ("q", "x" * 201),
])
def test_strict_text_types_and_length_bounds(field, value):
    with pytest.raises(ValidationError):
        profile.NarrativeSourceProposal.model_validate({"n": NARRATIVE, "q": QUESTION, field: value})


@pytest.mark.parametrize("field", ["o", "l", "p", "s", "f", "t", "r"])
def test_model_cannot_supply_outcome_scene_or_derived_records(field):
    with pytest.raises(ValidationError):
        profile.NarrativeSourceProposal.model_validate({"n": NARRATIVE, "q": QUESTION, field: []})


@pytest.mark.parametrize("scene", [None, {}, "Galeria"])
def test_existing_typed_scene_is_mandatory(scene):
    with pytest.raises(profile.SourceProfileError, match="source_profile_current_scene_required"):
        _validate(current_scene=scene)


def test_empty_derived_fields_are_valid_only_in_the_new_profile():
    assert _validate().narrative == NARRATIVE
    with pytest.raises(ValidationError, match="must add a fact"):
        SceneContinuationProposal.model_validate({
            "n": NARRATIVE, "q": QUESTION, "o": "unresolved", "l": "Galeria",
            "p": ["Mara"], "s": "A chuva ressoa na galeria.", "f": [], "t": [], "r": [],
        })


@pytest.mark.parametrize("prefix", ["Você decide aceitar o convite. ", "Você abre a porta. "])
def test_inherited_player_agency_gate(prefix):
    with pytest.raises(SceneProposalError, match="scene_player_agency_violation"):
        _validate(_proposal(prefix + NARRATIVE))


def test_npc_action_remains_distinct_from_player_action():
    assert _validate(_proposal("Mara abre a porta. " + NARRATIVE)).narrative.startswith("Mara")


@pytest.mark.parametrize("question,code", [
    ("Quem Mara obedece?", "scene_player_prompt_not_actionable"),
    ("Escolha o passado de Mara.", "scene_player_prompt_not_open"),
    ("Como deseja prosseguir em relação à narrativa?", "scene_player_prompt_not_actionable"),
])
def test_question_cannot_delegate_npc_or_story_authority(question, code):
    with pytest.raises(SceneProposalError, match=code):
        _validate(_proposal(q=question))


def test_question_presupposition_still_requires_player_authorization():
    with pytest.raises(SceneProposalError, match="scene_player_agency_violation"):
        _validate(_proposal(q="O que você faz enquanto você abre a porta?"))


@pytest.mark.parametrize("field", ["n", "q"])
def test_secrets_are_checked_in_both_generated_fields(field):
    secret = "O Xerife armou uma emboscada no cais."
    proposal = _proposal(n=secret + " " + NARRATIVE) if field == "n" else _proposal(q="O Xerife armou uma emboscada no cais; o que faz?")
    with pytest.raises(SceneProposalError, match="scene_secret_disclosed"):
        _validate(proposal, protected_secrets=(secret,))


def test_portuguese_gate_handles_empty_summary_without_accepting_foreign_n():
    with pytest.raises(SceneProposalError, match="scene_output_not_portuguese"):
        _validate(_proposal(
            n="The cold rain hits the windows while the yellow lamp illuminates the empty room. A closed box rests on the wooden table, and the narrow corridor remains silent beside the door.",
            q="What do you do now?",
        ))


@pytest.mark.parametrize("narrative,code", [
    ("A chuva ressoa na galeria perto da porta.", "scene_narrative_too_short"),
    ("A chuva cai. " * 50, "scene_narrative_too_long"),
    ("O system log confirma a mudança. " + NARRATIVE, "scene_internal_content"),
])
def test_inherited_narrative_size_and_internal_content_gates(narrative, code):
    with pytest.raises(SceneProposalError, match=code):
        _validate(_proposal(n=narrative))


@pytest.mark.parametrize("success,prefix,accepted,code", [
    (True, "A porta cede e revela a sala. ", True, None),
    (False, "A porta não cede e a tentativa falha. ", True, None),
    (True, "A porta não cede e a tentativa falha. ", False, "scene_success_not_honored"),
    (False, "A porta cede e revela a sala. ", False, "scene_failure_not_honored"),
])
def test_server_outcome_is_enforced_without_model_owned_o(success, prefix, accepted, code):
    proposal = _proposal(n=prefix + NARRATIVE)
    if accepted:
        assert _validate(proposal, facts=(_resolution(success),), player_input="Abro a porta.") == proposal
    else:
        with pytest.raises(SceneProposalError, match=code):
            _validate(proposal, facts=(_resolution(success),), player_input="Abro a porta.")


@pytest.mark.parametrize("facts,code", [
    (({"fact_type": "mechanics.resolution", "value": {"is_success": True}},), "source_profile_facts_invalid"),
    ((_resolution(1),), "source_profile_resolution_invalid"),
    ((_resolution(True), _resolution(False)), "source_profile_resolution_ambiguous"),
])
def test_only_unambiguous_typed_server_facts_supply_outcome(facts, code):
    with pytest.raises(profile.SourceProfileError, match=code):
        _validate(facts=facts)


def test_forged_typed_proposal_is_revalidated():
    with pytest.raises(ValidationError):
        _validate(_proposal().model_copy(update={"narrative": 7}))


def test_policy_rejection_precedes_source_creation(monkeypatch):
    calls = []
    monkeypatch.setattr(profile, "create_narrative_source", lambda **kwargs: calls.append(kwargs))
    with pytest.raises(SceneProposalError, match="scene_player_agency_violation"):
        profile.create_source_projection(
            _proposal(n="Você abre a porta. " + NARRATIVE), source_id="s", session_id="session",
            turn_id="turn", invocation_id="invocation", current_scene=SCENE, facts=(),
            player_input="Observo a galeria.",
        )
    assert calls == []


@pytest.mark.parametrize("visibility", ["public", "player"])
def test_projection_preserves_complete_n_and_keeps_q_separate(visibility):
    projection = _projection(visibility=visibility)
    assert projection.text == projection.source.text == NARRATIVE
    assert QUESTION not in projection.text
    assert projection.source.sha256 == hashlib.sha256(NARRATIVE.encode("utf-8")).hexdigest()
    assert projection.assessment.decision is DerivationDecision.SOURCE_ONLY
    assert projection.assessment.semantic_status is SemanticStatus.NOT_ASSESSED
    assert projection.source.visibility is NarrativeVisibility(visibility)


@pytest.mark.parametrize("visibility", ["storyteller", "system"])
def test_non_player_visible_source_cannot_be_created_or_emitted(visibility):
    with pytest.raises(profile.SourceProfileError, match="source_profile_visibility_forbidden"):
        _projection(visibility=visibility)
    with pytest.raises(profile.SourceProfileError, match="source_profile_visibility_forbidden"):
        profile.build_source_context(
            session_id="synthetic-session", current_scene=SCENE,
            attributed_sources=(_foreign_projection(visibility=visibility),),
        )


def test_two_sources_preserve_order_and_external_scene_without_derived_fields():
    scene = SCENE
    before = scene.model_dump(mode="json")
    first, second = _projection(1), _projection(2)
    context = profile.build_source_context(
        session_id="synthetic-session", current_scene=scene, attributed_sources=(first, second),
    )
    assert context["canonical_scene"] == {"location": "Galeria", "npcs_present": ["Mara"]}
    assert context["attributed_sources"] == [first.model_dump(mode="json"), second.model_dump(mode="json")]
    assert context["metadata"]["canonical_admission"] is False
    assert context["metadata"]["semantic_truth_assessed"] is False
    assert context["metadata"]["max_attributed_sources"] == 2
    assert scene.model_dump(mode="json") == before
    context["attributed_sources"][0]["text"] = "altered detached output"
    assert first.text == NARRATIVE


def test_empty_context_is_valid_but_three_sources_are_not():
    assert profile.build_source_context(session_id="synthetic-session", current_scene=SCENE)["attributed_sources"] == []
    with pytest.raises(profile.SourceProfileError, match="source_profile_sources_limit"):
        profile.build_source_context(session_id="synthetic-session", current_scene=SCENE,
                                     attributed_sources=(_projection(1), _projection(2), _projection(3)))


@pytest.mark.parametrize("updates", [
    {"session_id": "other-session"}, {"source_policy": "other-policy"},
])
def test_valid_projection_from_different_context_or_policy_is_not_emitted(updates):
    with pytest.raises(profile.SourceProfileError, match="source_profile_source_context_mismatch"):
        profile.build_source_context(session_id="synthetic-session", current_scene=SCENE,
                                     attributed_sources=(_foreign_projection(**updates),))


def test_duplicate_source_is_not_a_second_continuity_turn():
    source = _projection()
    with pytest.raises(profile.SourceProfileError, match="source_profile_source_duplicate"):
        profile.build_source_context(session_id="synthetic-session", current_scene=SCENE,
                                     attributed_sources=(source, source))


def test_forged_projection_and_self_declared_dict_are_not_emitted():
    source = _projection()
    for forged in (source.model_copy(update={"text": NARRATIVE.replace("galeria", "biblioteca")}), source.model_dump()):
        with pytest.raises(profile.SourceProfileError, match="source_profile_projection_invalid"):
            profile.build_source_context(session_id="synthetic-session", current_scene=SCENE,
                                         attributed_sources=(forged,))


@pytest.mark.parametrize("field,value", [
    ("summary", "Resumo prévio da cena."), ("details", ("Detalhe prévio.",)),
    ("open_threads", ("Pendência prévia.",)),
])
def test_richer_scene_context_is_rejected_instead_of_silently_omitted(field, value):
    scene = SceneState(location="Galeria", **{field: value})
    with pytest.raises(profile.SourceProfileError, match="source_profile_scene_requires_location_and_npcs_only"):
        _validate(current_scene=scene)
    with pytest.raises(profile.SourceProfileError, match="source_profile_scene_requires_location_and_npcs_only"):
        profile.build_source_context(session_id="synthetic-session", current_scene=scene)


@pytest.mark.parametrize("text", ["x" * 39, "x" * 1601])
def test_imported_source_obeys_profile_text_limits_even_when_core_accepts_it(text):
    projection = _foreign_projection(text=text)
    with pytest.raises(profile.SourceProfileError, match="source_profile_source_text_bounds"):
        profile.build_source_context(session_id="synthetic-session", current_scene=SCENE,
                                     attributed_sources=(projection,))


def test_serialized_context_limit_rejects_without_cutting_sources():
    session_id = "session-" + "s" * 232
    sources = tuple(_foreign_projection(
        source_id=str(index) + "s" * 239, session_id=session_id,
        turn_id=str(index) + "t" * 239, invocation_id=str(index) + "i" * 239,
        text="x" * 1600,
    ) for index in (1, 2))
    scene = SceneState(location="L" * 160, npcs_present=tuple(str(i) + "p" * 79 for i in range(8)))
    before = [source.model_dump(mode="json") for source in sources]
    with pytest.raises(profile.SourceProfileError, match="source_profile_context_size_exceeded"):
        profile.build_source_context(session_id=session_id, current_scene=scene, attributed_sources=sources)
    assert [source.model_dump(mode="json") for source in sources] == before
    assert profile.MAX_CONTEXT_CHARACTERS == 12000
