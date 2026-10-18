"""Implicit actions must preserve actor, verb family and target permissions."""

import pytest

from api.scene_director_service import (
    SceneContinuationProposal, SceneProposalError, _action_authorizations,
    _validate_implicit_player_contact, validate_scene_continuation,
)
from api.scene_service import SceneState


def _proposal(**updates):
    payload = {
        "n": "Uma corrente bate contra a parede e uma sirene ecoa pela rua.",
        "o": "unresolved", "l": "Galpão abandonado",
        "s": "Uma corrente bate na parede do galpão.", "p": [],
        "f": [{"k": "observation", "s": "Uma corrente bate na parede."}],
        "t": [], "r": [], "q": "O que você faz agora?",
    }
    payload.update(updates)
    return SceneContinuationProposal.model_validate(payload)


def _check(proposal, player_input="Investigo o galpão abandonado."):
    _validate_implicit_player_contact(
        proposal, authorized_actions=_action_authorizations(player_input),
    )


@pytest.mark.parametrize("narrative", [
    "Seus dedos arrancam a ferrugem, mas o cadeado continua trancado.",
    "Suas mãos arrancam o papel que cobre a janela.",
    "O cadeado range sob a sua mão, mas a ferrugem impede o movimento.",
    "A porta vibra sob sua mão, enquanto a sirene ecoa pela rua.",
])
def test_voluntary_hand_action_is_not_implied_by_investigation(narrative):
    with pytest.raises(SceneProposalError) as caught:
        _check(_proposal(n=narrative))
    assert caught.value.code == "scene_player_agency_violation"
    assert caught.value.evidence["rule"] == "undeclared_player_contact"


@pytest.mark.parametrize("narrative,declared", [
    ("Seus dedos arrancam a ferrugem, mas o cadeado não cede.", "Arranco a ferrugem."),
    ("Suas mãos arrancam o papel, enquanto a sirene ecoa.", "Arranco o papel."),
    ("O cadeado range sob sua mão, mas permanece fechado.", "Toco o cadeado."),
])
def test_hand_action_accepts_matching_family_and_target(narrative, declared):
    _check(_proposal(n=narrative), declared)


@pytest.mark.parametrize("declared", [
    "Toco a ferrugem.", "Arranco o papel.", "Empurro o cadeado.",
])
def test_hand_action_rejects_other_family_or_target(declared):
    with pytest.raises(SceneProposalError):
        _check(_proposal(n="Seus dedos arrancam a ferrugem, mas o cadeado não cede."), declared)


@pytest.mark.parametrize("narrative", [
    "Mara arranca a ferrugem. Seus dedos arrancam mais uma lasca.",
    "Seus dedos não arrancam a ferrugem e o cadeado permanece fechado.",
    "O frio deixa seus dedos dormentes enquanto o cadeado range ao vento.",
    "Mara toca o cadeado, que range sob sua mão enquanto a sirene ecoa.",
])
def test_npc_or_involuntary_hand_description_is_not_player_action(narrative):
    _check(_proposal(n=narrative, p=["Mara"]))


@pytest.mark.parametrize("narrative", [
    "Ao mover a lanterna pela entrada, o rádio chia ainda mais alto.",
    "Ao mover o espelho, uma luz atravessa a parede do galpão.",
    "Ao acender a lanterna, a marca na parede fica visível.",
])
def test_temporal_tool_action_requires_declared_action(narrative):
    with pytest.raises(SceneProposalError) as caught:
        _check(_proposal(n=narrative))
    assert caught.value.code == "scene_player_agency_violation"
    assert caught.value.evidence["rule"] == "undeclared_player_instrument_action"


@pytest.mark.parametrize("narrative,declared", [
    ("Ao mover a lanterna pela entrada, o rádio chia mais alto.", "Movo a lanterna."),
    ("Ao mover o espelho, uma luz atravessa a parede.", "Movo o espelho."),
    ("Ao acender a lanterna, a marca na parede fica visível.", "Acendo a lanterna."),
])
def test_temporal_tool_action_accepts_matching_authorization(narrative, declared):
    _check(_proposal(n=narrative), declared)


@pytest.mark.parametrize("declared", [
    "Observo a lanterna.", "Movo a cadeira.", "Acendo a lanterna.",
])
def test_temporal_tool_action_does_not_share_family_or_target_permissions(declared):
    with pytest.raises(SceneProposalError):
        _check(_proposal(n="Ao mover a lanterna pela entrada, o rádio chia mais alto."), declared)


@pytest.mark.parametrize("narrative", [
    "Ao amanhecer, uma luz atravessa a parede do galpão.",
    "Ao mover as nuvens, o vento afasta a chuva da rua.",
    "Ao mover a lanterna, Mara encontra uma marca na parede.",
    "Ao mover a lanterna de Mara, ela encontra uma marca na parede.",
    "Mara ergue a cabeça. Ao mover a lanterna, o rádio chia mais alto.",
    "Ao mover a lanterna, a corrente de ar a derruba da mesa.",
    "Se decidir mover a lanterna, a marca poderá ficar visível.",
    "A mão de Mara treme ao mover a lanterna pela entrada.",
])
def test_npc_environment_and_hypothesis_do_not_become_player_tool_actions(narrative):
    _check(_proposal(n=narrative, p=["Mara"]))


@pytest.mark.parametrize("narrative", [
    "Você observa Mara. Ao mover a lanterna, o rádio chia mais alto.",
    "Ao mover a lanterna de Mara, o rádio chia ainda mais alto.",
    "Ao mover a lanterna, ela percebe uma marca na parede.",
])
def test_tool_owner_or_npc_object_is_not_the_acting_npc(narrative):
    with pytest.raises(SceneProposalError):
        _check(_proposal(n=narrative, p=["Mara"]))


@pytest.mark.parametrize("question", [
    "O que faz ao seguir o rastro de sangue até a escada?",
    "Como você reage ao abrir a porta?",
    "O que você faz depois de entrar no porão?",
    "O que faz ao decidir entrar no porão?",
    "Como reage ao escolher abrir a porta?",
])
def test_open_question_cannot_presuppose_undeclared_player_action(question):
    with pytest.raises(SceneProposalError) as caught:
        _check(_proposal(q=question))
    assert caught.value.code == "scene_player_agency_violation"
    assert caught.value.evidence["field"] == "player_prompt"
    assert caught.value.evidence["rule"] == "presupposed_player_action"


@pytest.mark.parametrize("question,declared", [
    ("O que faz ao seguir o rastro de sangue?", "Sigo o rastro de sangue."),
    ("Como você reage ao abrir a porta?", "Abro a porta."),
    ("O que você faz depois de entrar no porão?", "Entro no porão."),
])
def test_question_may_reference_the_players_declared_action(question, declared):
    _check(_proposal(q=question), declared)


@pytest.mark.parametrize("declared", ["Observo o rastro.", "Sigo o vulto."])
def test_question_presupposition_checks_family_and_target(declared):
    with pytest.raises(SceneProposalError):
        _check(_proposal(q="O que faz ao seguir o rastro de sangue?"), declared)


@pytest.mark.parametrize("question", [
    "O que faz se decidir seguir o rastro?",
    "Como pretende seguir o rastro?",
    "O que você faz diante do rastro de sangue?",
    "O que faz ao ouvir o ruído?",
    "Como reage ao ver Mara entrar?",
    "O que faz ao anoitecer?",
    "Como reage ao abrir da porta pelo vento?",
    "Como reage depois de Mara abrir a porta?",
    "O que faz antes de seguir o rastro?",
])
def test_invitation_perception_npc_or_environment_is_not_presupposed_choice(question):
    _check(_proposal(q=question, p=["Mara"]))


@pytest.mark.parametrize("field", ["n", "s", "f"])
def test_temporal_tool_action_cannot_enter_visible_memory(field):
    statement = "Ao mover a lanterna, o rádio chia ainda mais alto."
    value = [{"k": "observation", "s": statement}] if field == "f" else statement
    with pytest.raises(SceneProposalError):
        _check(_proposal(**{field: value}))


def test_agency_helpers_are_integrated_before_mechanical_admission():
    proposal = _proposal(n=(
        "Ao mover a lanterna pela entrada, o rádio chia ainda mais alto. "
        "O vento atravessa a janela e uma corrente bate na parede enquanto uma sirene ecoa."
    ))
    with pytest.raises(SceneProposalError) as caught:
        validate_scene_continuation(
            proposal, current_scene=SceneState(location="Galpão abandonado"),
            facts=(), player_input="Investigo o galpão abandonado.",
        )
    assert caught.value.evidence["rule"] == "undeclared_player_instrument_action"
