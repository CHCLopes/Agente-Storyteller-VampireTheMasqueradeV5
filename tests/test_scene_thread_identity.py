"""Thread labels compare conservatively without rewriting canonical sources."""

from copy import deepcopy

import pytest

from api.scene_director_service import (
    SceneContinuationProposal,
    SceneProposalError,
    project_scene,
    validate_scene_continuation,
)
from api.scene_service import SceneState
from api.turn_execution_service import _admit_scene_continuation
from api.turn_models import TurnDraft


THREAD = "Descobrir se Mara entregará o endereço"


def _proposal(**updates):
    payload = {
        "narrative": (
            "A luz do balcão oscila sobre a madeira molhada. O rádio solta um "
            "chiado baixo, enquanto a chuva bate nas janelas fechadas do bar. "
            "O vento frio sacode as placas soltas do lado de fora da porta."
        ),
        "outcome": "unresolved",
        "location": "Bar fechado",
        "scene_summary": "A luz oscila no balcão e o rádio chia baixo.",
        "new_facts": [{"kind": "observation", "summary": "O rádio chia baixo."}],
        "open_threads": [],
        "player_prompt": "O que você faz?",
    }
    payload.update(updates)
    return SceneContinuationProposal.model_validate(payload)


def _scene(*threads):
    return SceneState(location="Bar fechado", open_threads=threads)


def _resolution(*threads, **updates):
    return _proposal(
        narrative=(
            "O rádio esclarece a dúvida sobre o endereço. A voz gravada de Mara "
            "confirma que o endereço será entregue quando a chuva terminar. "
            "O vento frio sacode as placas soltas do lado de fora da porta."
        ),
        scene_summary="O rádio esclarece que Mara entregará o endereço.",
        resolved_threads=threads,
        **updates,
    )


@pytest.mark.parametrize("suffix", (".", "!", "?", "...", "…", "!?", " . "))
def test_projection_preserves_existing_label_for_terminal_punctuation(suffix):
    previous = _scene(THREAD)
    original = previous.model_dump(mode="json")
    proposal = _proposal(open_threads=[THREAD + suffix])
    proposal_original = proposal.model_dump(mode="json")

    next_scene = project_scene(proposal, previous=previous, turn_number=2)

    assert next_scene.open_threads == (THREAD,)
    assert previous.model_dump(mode="json") == original
    assert proposal.model_dump(mode="json") == proposal_original


def test_projection_keeps_first_incoming_label_without_rewriting_it():
    first = THREAD + "!"
    proposal = _proposal(open_threads=[first, THREAD + ".", THREAD])

    next_scene = project_scene(proposal, previous=None, turn_number=1)

    assert next_scene.open_threads == (first,)
    assert proposal.open_threads == (first, THREAD + ".", THREAD)


def test_legacy_projection_duplicates_do_not_consume_thread_capacity():
    previous = _scene(*(f"Pendência {index}" for index in range(12)))
    proposal = _proposal(open_threads=["Pendência 0."])

    next_scene = project_scene(proposal, previous=previous, turn_number=2)

    assert next_scene.open_threads == previous.open_threads


def test_distinct_thread_still_cannot_exceed_capacity():
    previous = _scene(*(f"Pendência {index}" for index in range(12)))

    with pytest.raises(SceneProposalError, match="scene_open_thread_capacity_exceeded"):
        project_scene(
            _proposal(open_threads=["Pendência nova"]),
            previous=previous, turn_number=2,
        )


def test_legacy_duplicates_coalesce_only_in_new_projection():
    previous = _scene(THREAD + ".", THREAD, "Descobrir quem enviou o rádio")
    original = previous.model_dump(mode="json")

    next_scene = project_scene(_proposal(), previous=previous, turn_number=2)

    assert next_scene.open_threads == (THREAD + ".", "Descobrir quem enviou o rádio")
    assert previous.model_dump(mode="json") == original


@pytest.mark.parametrize(
    ("existing", "incoming"),
    (
        (THREAD, "Descobrir se Mara não entregará o endereço"),
        (THREAD, "Descobrir se Sara entregará o endereço"),
        ("Encontrar o código 1.2", "Encontrar o código 12"),
        ("Encontrar a chave A-B", "Encontrar a chave AB"),
        ("Investigar o avô", "Investigar o avó"),
        ("Seguir pista A+", "Seguir pista A"),
        ("Seguir pista A-", "Seguir pista A"),
        ("Esclarecer: o endereço", "Esclarecer o endereço"),
        ("...", "!"),
    ),
)
def test_distinct_labels_are_not_semantically_merged(existing, incoming):
    previous = _scene(existing)
    proposal = _proposal(open_threads=[incoming])

    next_scene = project_scene(proposal, previous=previous, turn_number=2)

    assert next_scene.open_threads == (existing, incoming)


@pytest.mark.parametrize("resolved", (THREAD + ".", THREAD.upper() + "?", THREAD + "…"))
def test_resolution_recognizes_punctuation_variant_with_evidence(resolved):
    previous = _scene(THREAD)
    proposal = _resolution(resolved)

    accepted = validate_scene_continuation(proposal, facts=(), current_scene=previous)

    assert project_scene(accepted, previous=previous, turn_number=2).open_threads == ()


def test_resolution_variant_still_requires_grounding():
    with pytest.raises(SceneProposalError, match="scene_thread_resolution_without_evidence"):
        validate_scene_continuation(
            _proposal(resolved_threads=[THREAD + "."]),
            facts=(), current_scene=_scene(THREAD),
        )


def test_distinct_unknown_thread_resolution_remains_rejected():
    with pytest.raises(SceneProposalError, match="scene_unknown_thread_resolution"):
        validate_scene_continuation(
            _resolution("Descobrir se Sara entregará o endereço."),
            facts=(), current_scene=_scene(THREAD),
        )


def test_thread_cannot_be_resolved_and_reopened_using_punctuation():
    with pytest.raises(SceneProposalError, match="scene_thread_reopened_while_resolved"):
        validate_scene_continuation(
            _resolution(THREAD + ".", open_threads=[THREAD + "?"]),
            facts=(), current_scene=_scene(THREAD),
        )


def _admit(proposal, previous):
    context = {"scene": previous.model_dump(mode="json")}
    draft = TurnDraft(
        draft_id="draft", session_id="session", turn_id="turn", attempt_id="attempt",
        player_input="Observo o bar.",
    )
    original = deepcopy(draft.model_dump(mode="json"))
    result, _, _ = _admit_scene_continuation(
        draft, proposal, operation_id="operation", turn_number=2,
        invocation_id="invocation", context=context,
    )
    assert draft.model_dump(mode="json") == original
    return result, context


def test_unchanged_thread_punctuation_does_not_create_opened_event_fact():
    proposal = _proposal(open_threads=[THREAD + "."])

    draft, context = _admit(proposal, _scene(THREAD))

    assert not any(f.fact_type == "world.scene.thread_opened" for f in draft.facts)
    assert context["scene"]["open_threads"] == [THREAD]


def test_new_thread_variants_create_one_fact_preserving_first_label():
    proposal = _proposal(open_threads=[THREAD + "!", THREAD + ".", THREAD])

    draft, _ = _admit(proposal, _scene())

    opened = [f for f in draft.facts if f.fact_type == "world.scene.thread_opened"]
    assert [f.value["summary"] for f in opened] == [THREAD + "!"]


def test_resolution_variants_create_one_fact_using_existing_canonical_label():
    proposal = _resolution(THREAD + ".", THREAD + "?")

    draft, context = _admit(proposal, _scene(THREAD))

    resolved = [f for f in draft.facts if f.fact_type == "world.scene.thread_resolved"]
    assert [f.value["summary"] for f in resolved] == [THREAD]
    assert context["scene"]["open_threads"] == []
    assert proposal.resolved_threads == (THREAD + ".", THREAD + "?")


def test_resolution_of_legacy_duplicates_creates_only_one_canonical_fact():
    previous = _scene(THREAD + "!", THREAD + ".", "Descobrir quem enviou o rádio")
    original = previous.model_dump(mode="json")

    draft, context = _admit(_resolution(THREAD), previous)

    resolved = [f for f in draft.facts if f.fact_type == "world.scene.thread_resolved"]
    assert [f.value["summary"] for f in resolved] == [THREAD + "!"]
    assert context["scene"]["open_threads"] == ["Descobrir quem enviou o rádio"]
    assert previous.model_dump(mode="json") == original


def test_semantically_different_label_creates_a_separate_opened_fact():
    new_thread = "Descobrir se Sara entregará o endereço."

    draft, context = _admit(_proposal(open_threads=[new_thread]), _scene(THREAD))

    opened = [f for f in draft.facts if f.fact_type == "world.scene.thread_opened"]
    assert [f.value["summary"] for f in opened] == [new_thread]
    assert context["scene"]["open_threads"] == [THREAD, new_thread]
