"""A known NPC's player object does not own that NPC's following actions."""

import pytest

from api.scene_director_service import (
    SceneContinuationProposal,
    SceneProposalError,
    _action_authorizations,
    _validate_declared_player_actions,
    validate_scene_continuation,
)
from api.scene_service import SceneState


def _proposal(text, *, field="n"):
    payload = {
        "n": text + " A chuva pesa contra a janela, o rádio chia no balcão e uma corrente bate na porta, rompendo o silêncio da sala.",
        "o": "unresolved", "l": "Bar fechado",
        "s": "Uma corrente bate na porta enquanto o rádio chia.", "p": ["Mara"],
        "f": [{"k": "observation", "s": "Uma corrente bate na porta."}],
        "t": [], "r": [], "q": "Qual será sua próxima atitude?",
    }
    if field != "n":
        payload["n"] = "A chuva pesa contra a janela enquanto o rádio chia no balcão. Uma corrente bate contra a porta, rompendo o silêncio da sala e ecoando pelo corredor estreito, onde a luz começa a falhar."
        if field == "f":
            payload["f"][0]["s"] = text
        else:
            payload[field] = text
    return SceneContinuationProposal.model_validate(payload)


def _check(text, *, field="n", players=("Neófito",), npcs=("Mara", "Ivo")):
    proposal = _proposal(text, field=field)
    _validate_declared_player_actions(
        proposal, authorized_actions=_action_authorizations("Observo Mara."),
        player_aliases=players, npc_aliases=npcs,
    )
    return proposal


@pytest.mark.parametrize("field", ["n", "s", "f"])
def test_recorded_npc_object_summary_keeps_npc_actor(field):
    _check("Mara observa você, cruza os braços e permanece em silêncio.", field=field)


@pytest.mark.parametrize("text", [
    "Mara observa Neófito, cruza os braços e permanece em silêncio.",
    "Ivo observa você, permanece imóvel.",
    "Mara vê você, cruza os braços e permanece em silêncio.",
    "Mara observa você, abre a porta lateral.",
    "Mara observa você, abre a porta por você.",
])
def test_object_attribution_supports_known_names_and_npc_owned_actions(text):
    _check(text)


@pytest.mark.parametrize("text", [
    "Mara observa você, que permanece em silêncio.",
    "Mara observa você, mas você permanece imóvel.",
    "Mara observa você, cruza os braços e você abre a porta.",
    "Mara observa você, cruza os braços e Neófito abre a porta.",
    "Mara observa Neófito, cruza os braços e você abre a porta.",
    "Mara observa você, exige que abra a porta.",
    "Mara observa você, obriga você a abrir a porta.",
    "Mara observa você, força sua mão a tocar o cadeado.",
    "Mara observa você, cruza os braços e decide sua próxima ação por você.",
    "Mara observa você, escolhe sua resposta por você.",
    "Mara observa você, convence você a cooperar.",
    "Mara observa você, cruza os braços e abre seus olhos.",
    "Mara observa Neófito, que abre a porta.",
    "Você observa Mara, cruza os braços e permanece em silêncio.",
])
def test_npc_object_exception_never_skips_subsequent_player_or_coerced_actions(text):
    with pytest.raises(SceneProposalError) as caught:
        _check(text)
    assert caught.value.code == "scene_player_agency_violation"


@pytest.mark.parametrize("text", [
    "Visitante observa você, permanece imóvel.",
    "Mara observa você, cruza os braços e permanece em silêncio.",
])
def test_exception_requires_a_known_npc_not_an_inferred_name(text):
    with pytest.raises(SceneProposalError):
        _check(text, npcs=())


def test_player_npc_alias_collision_is_not_used_to_waive_actions():
    with pytest.raises(SceneProposalError):
        _check("Mara observa você, permanece imóvel.", players=("Mara",), npcs=("Mara",))


@pytest.mark.parametrize("text", [
    "Mara observa você, abre-lhe os olhos.",
    "Mara observa você, abre os teus olhos.",
    "Mara observa você, abre a tua mão.",
])
def test_npc_object_exception_does_not_waive_player_bodily_control(text, monkeypatch):
    # These retain the same protected target as 'abre seus olhos'; replacing
    # the possessive must not turn forced bodily control into an NPC-only act.
    with monkeypatch.context() as prior_behavior:
        prior_behavior.setattr(
            "api.scene_director_service._is_npc_observer_coordinate_action",
            lambda *args, **kwargs: False,
        )
        with pytest.raises(SceneProposalError):
            _check(text)
    with pytest.raises(SceneProposalError) as caught:
        validate_scene_continuation(
            _proposal(text), facts=(),
            current_scene=SceneState(location="Bar fechado", npcs_present=("Mara",)),
            player_input="Observo Mara.", player_aliases=("Neófito",), npc_aliases=("Mara",),
        )
    assert caught.value.code == "scene_player_agency_violation"


def test_npc_owned_posture_is_accepted_by_complete_scene_policy():
    proposal = _check("Mara observa você, cruza os braços e permanece em silêncio.")
    assert validate_scene_continuation(
        proposal, facts=(), current_scene=SceneState(location="Bar fechado", npcs_present=("Mara",)),
        player_input="Observo Mara.", player_aliases=("Neófito",), npc_aliases=("Mara",),
    ) is proposal
