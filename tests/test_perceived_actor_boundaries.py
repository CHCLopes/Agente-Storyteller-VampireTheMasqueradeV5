"""A perceived world subject never transfers its actions to the player."""

import pytest

from api.scene_director_service import (
    SceneContinuationProposal,
    SceneProposalError,
    _action_authorizations,
    _validate_declared_player_actions,
    _validate_implicit_player_contact,
)


def _proposal(narrative, **updates):
    payload = {
        "n": narrative + " Uma corrente bate contra a parede.",
        "o": "unresolved",
        "l": "Galpão abandonado",
        "s": "Uma corrente bate contra a parede do galpão.",
        "p": [],
        "f": [{"k": "observation", "s": "Uma corrente bate na parede."}],
        "t": [], "r": [], "q": "O que você faz agora?",
    }
    payload.update(updates)
    return SceneContinuationProposal.model_validate(payload)


def _check(narrative, player_input="Investigo o galpão abandonado.", **updates):
    proposal = _proposal(narrative, **updates)
    _validate_declared_player_actions(
        proposal,
        authorized_actions=_action_authorizations(player_input),
        player_aliases=("Neófito",), npc_aliases=("Mara",),
    )
    return proposal


@pytest.mark.parametrize("narrative", [
    "Você sente a vibração de passos no mezanino, mas a sombra permanece oculta.",
    "Você sente a vibração de passos no mezanino, porém a sombra permanece oculta.",
    "Você ouve passos no mezanino enquanto a sombra permanece oculta.",
    "Você não vê estivadores, apenas a maré subindo.",
    "Você sente o ar gelado, mas o vento abre a porta.",
    "Você sente a vibração de passos e a porta continua fechada.",
    "Neófito sente a vibração de passos, mas a sombra permanece oculta.",
    "Você sente o frio subir pelas botas enquanto o rádio chia sobre a mesa.",
])
def test_explicit_world_subject_after_perception_does_not_control_player(narrative):
    _check(narrative)


@pytest.mark.parametrize("narrative", [
    "Você sente frio, mas permanece oculta atrás da porta.",
    "Você sente passos, mas você permanece oculta atrás da porta.",
    "Você sente frio e abre a porta lateral.",
    "Você sente frio e depois abre a porta lateral.",
    "Você sente frio, mas ela abre a porta lateral.",
    "Você sente frio, mas sua personagem abre a porta lateral.",
    "Você sente frio, mas a sombra você segue pelo corredor.",
    "Você sente frio, mas a sombra exige que você abra a porta.",
    "Você sente frio, mas a sombra permite que o personagem abra a porta.",
    "Você sente frio, mas a sombra que Neófito segue abre a porta.",
    "Você sente frio, mas a sombra obriga a abrir a porta.",
    "Você sente frio, mas a sombra manda abrir a porta.",
    "Você sente frio, mas a sombra faz você abrir a porta.",
    "Você sente frio, mas a porta precisa abrir para escapar.",
    "Você sente frio, mas a sombra permanece oculta enquanto abre a porta.",
    "Você percebe que você abre a porta lateral.",
    "Você percebe que abre a porta lateral.",
    "Você percebe que seu personagem abre a porta lateral.",
    "Você percebe que precisa abrir a porta lateral.",
    "Você sente vontade de abrir a porta lateral.",
])
def test_perception_does_not_waive_player_or_ambiguous_actions(narrative):
    with pytest.raises(SceneProposalError) as caught:
        _check(narrative)
    assert caught.value.code == "scene_player_agency_violation"


def test_world_subject_exception_does_not_authorize_player_to_repeat_its_action():
    with pytest.raises(SceneProposalError):
        _check(
            "Você abre a porta lateral.",
            player_input="Sinto frio, mas o vento abre a porta lateral.",
        )


def test_declared_player_action_after_perception_still_authorizes_its_target():
    _check(
        "Você abre a porta lateral.",
        player_input="Sinto frio e abro a porta lateral.",
    )


def test_fixed_perception_does_not_waive_other_scene_agency_checks():
    proposal = _check(
        "Você sente a vibração de passos no mezanino, mas a sombra permanece oculta.",
        q="O que você faz ao seguir o rastro de óleo?",
    )
    with pytest.raises(SceneProposalError) as caught:
        _validate_implicit_player_contact(
            proposal,
            authorized_actions=_action_authorizations("Investigo o galpão abandonado."),
        )
    assert caught.value.evidence["rule"] == "presupposed_player_action"
