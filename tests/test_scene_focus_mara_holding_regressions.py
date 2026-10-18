"""An NPC's deliberation keeps its subject without realizing the action."""

import pytest

from api.scene_director_service import (
    SceneContinuationProposal,
    SceneProposalError,
    _action_authorizations,
    _validate_declared_player_actions,
    validate_scene_continuation,
)
from api.scene_service import SceneState


OBSERVED_SUMMARY = (
    "Mara observa você, segura o envelope e parece indecisa sobre entregá-lo."
)


def _proposal(text, *, field="n"):
    payload = {
        "n": text + " A chuva pesa contra a janela enquanto o rádio chia no balcão. Uma corrente bate contra a porta do bar, rompendo o silêncio da sala.",
        "o": "unresolved", "l": "Bar fechado", "p": ["Mara"],
        "s": "Uma corrente bate contra a porta do bar.",
        "f": [{"k": "observation", "s": "Uma corrente bate contra a porta do bar."}],
        "t": [], "r": [], "q": "Qual será sua próxima atitude?",
    }
    if field != "n":
        payload["n"] = (
            "A chuva pesa contra a janela enquanto o rádio chia no balcão. "
            "Uma corrente bate contra a porta do bar, rompendo o silêncio da sala."
        )
        if field == "f":
            payload["f"][0]["s"] = text
        elif field in {"t", "r"}:
            payload[field] = [text]
        else:
            payload[field] = text
    return SceneContinuationProposal.model_validate(payload)


def _check(text, *, field="n", players=("Neófito",), npcs=("Mara", "Ivo")):
    proposal = _proposal(text, field=field)
    _validate_declared_player_actions(
        proposal,
        authorized_actions=_action_authorizations("Observo Mara e espero sua reação."),
        player_aliases=players, npc_aliases=npcs,
    )
    return proposal


@pytest.mark.parametrize("field", ["n", "s", "f", "t", "r"])
def test_observed_holding_and_deliberation_keeps_the_known_npc_subject(field):
    _check(OBSERVED_SUMMARY, field=field)


@pytest.mark.parametrize("text", [
    "Ivo observa você, segura uma carta e parece indeciso sobre entregá-la.",
    "Mara vê Neófito, segura um pequeno envelope selado e parece indecisa sobre entregá-lo.",
    "Mara observa você, segura o livro e parece indecisa sobre entregar o livro.",
    "Mara observa você, segura a carta e parece indecisa sobre guardá-la.",
    "Mara observa você, segura o envelope e parece indecisa sobre entregá‐lo.",
    "Mara observa você, segura o envelope e parece indecisa sobre entregá‑lo.",
])
def test_deliberation_is_not_specific_to_one_npc_object_or_clitic(text):
    _check(text)


@pytest.mark.parametrize("text", [
    "Mara observa você, que segura o envelope e parece indeciso sobre entregá-lo.",
    "Mara observa você, segura o envelope e você parece indeciso sobre entregá-lo.",
    "Mara observa você, segura o envelope e Neófito parece indeciso sobre entregá-lo.",
    "Mara observa você, segura o envelope e parece indecisa sobre você entregar o envelope.",
    "Mara observa você, segura o envelope e parece indecisa sobre entregá-lo e você pega o livro.",
    "Mara observa você, segura o envelope e parece indecisa sobre entregá-lo e Neófito pega o livro.",
    "Mara observa você, segura o envelope e parece indecisa sobre entregá-lo para você pegar.",
    "Mara observa você, segura o envelope e parece indecisa sobre entregá-lo para Neófito entregar.",
    "Mara observa você, segura o envelope e parece indecisa sobre decidir sua próxima ação por você.",
    "Mara observa você, segura o envelope e parece indecisa sobre abrir seus olhos.",
    "Mara observa você, segura o envelope e parece indecisa sobre abrir-lhe os olhos.",
    "Mara observa você, segura o envelope e parece indecisa sobre abrir os teus olhos.",
    "Mara observa você, segura o envelope e parece indecisa sobre forçar sua mão a entregá-lo.",
    "Mara observa você, segura o envelope e parece indecisa sobre entrega o livro.",
    "Mara observa você, segura o envelope de Neófito e parece indecisa sobre entregá-lo.",
    "Mara observa você, segura o envelope que você pegou e parece indecisa sobre entregá-lo.",
    "Você observa Mara, segura o envelope e parece indeciso sobre entregá-lo.",
])
def test_deliberation_cannot_hide_player_subjects_control_or_finite_actions(text):
    with pytest.raises(SceneProposalError) as caught:
        _check(text)
    assert caught.value.code == "scene_player_agency_violation"


@pytest.mark.parametrize("players,npcs", [
    (("Neófito",), ()),
    (("Mara",), ("Mara",)),
])
def test_deliberation_requires_an_unambiguous_registered_npc(players, npcs):
    with pytest.raises(SceneProposalError) as caught:
        _check(OBSERVED_SUMMARY, players=players, npcs=npcs)
    assert caught.value.code == "scene_player_agency_violation"


def test_subject_correction_preserves_deliberation_text_and_unresolved_outcome():
    proposal = _check(OBSERVED_SUMMARY)
    admitted = validate_scene_continuation(
        proposal, facts=(),
        current_scene=SceneState(location="Bar fechado", npcs_present=("Mara",)),
        player_input="Observo Mara e espero sua reação.",
        player_aliases=("Neófito",), npc_aliases=("Mara",),
    )
    assert admitted is proposal
    assert admitted.narrative.startswith(OBSERVED_SUMMARY)
    assert admitted.outcome == "unresolved"


def test_subject_correction_does_not_authorize_a_location_change():
    proposal = _check(OBSERVED_SUMMARY).model_copy(update={"location": "Bar fechado, mesas gastas"})
    with pytest.raises(SceneProposalError) as caught:
        validate_scene_continuation(
            proposal, facts=(),
            current_scene=SceneState(location="Bar fechado", npcs_present=("Mara",)),
            player_input="Observo Mara e espero sua reação.",
            player_aliases=("Neófito",), npc_aliases=("Mara",),
        )
    assert caught.value.code == "scene_location_changed_without_transition"


@pytest.mark.parametrize("question", [
    "O que Mara decide por você?", "O que Mara decide sobre sua próxima ação?",
])
def test_npc_deliberation_does_not_make_npc_decision_a_player_prompt(question):
    proposal = _check(OBSERVED_SUMMARY).model_copy(update={"player_prompt": question})
    with pytest.raises(SceneProposalError) as caught:
        validate_scene_continuation(
            proposal, facts=(),
            current_scene=SceneState(location="Bar fechado", npcs_present=("Mara",)),
            player_input="Observo Mara e espero sua reação.",
            player_aliases=("Neófito",), npc_aliases=("Mara",),
        )
    assert caught.value.code == "scene_player_prompt_not_actionable"
    assert caught.value.evidence["field"] == "player_prompt"
