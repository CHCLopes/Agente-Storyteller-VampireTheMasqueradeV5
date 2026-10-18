"""A failed action is still a player action and requires matching intent."""

import pytest

from api.scene_director_service import (
    SceneContinuationProposal, SceneProposalError, _action_authorizations,
    _unauthorized_action_concepts, _validate_implicit_player_contact,
)


def _check(narrative, action="Investigo o cadeado.", npcs=()):
    proposal = SceneContinuationProposal.model_validate({
        "n": narrative, "o": "failure", "l": "Galpão", "s": "O cadeado resiste.",
        "p": list(npcs), "f": [{"k": "complication", "s": "Passos se aproximam."}],
        "t": [], "r": [], "q": "Como você reage?",
    })
    _validate_implicit_player_contact(proposal, authorized_actions=_action_authorizations(action))


@pytest.mark.parametrize("narrative", [
    "Seus dedos roçam o metal frio do cadeado, mas a estrutura resiste. Nada cede.",
    "Suas mãos roçam a porta fechada, mas nada cede.",
    "Ao tentar forçar o cadeado, o metal range e a ferramenta escorrega.",
    "Ao forçar a porta, a madeira range sem ceder.",
])
def test_investigation_does_not_authorize_contact_or_forcing(narrative):
    with pytest.raises(SceneProposalError) as caught:
        _check(narrative)
    assert caught.value.code == "scene_player_agency_violation"


@pytest.mark.parametrize("narrative,action", [
    ("Seus dedos roçam o cadeado, mas a estrutura resiste.", "Roço o cadeado."),
    ("Seus dedos roçam o metal frio do cadeado, mas nada cede.", "Roço o metal frio do cadeado."),
    ("Ao tentar forçar o cadeado, o metal range e a ferramenta escorrega.", "Tento forçar o cadeado."),
    ("Ao forçar a porta, a madeira range sem ceder.", "Forço a porta."),
    ("A porta vibra sob sua força, mas permanece fechada.", "Forço a porta."),
])
def test_explicit_same_family_and_target_remain_valid(narrative, action):
    _check(narrative, action)


@pytest.mark.parametrize("narrative,action", [
    ("Seus dedos roçam o cadeado, mas a estrutura resiste.", "Roço a parede."),
    ("Seus dedos roçam o cadeado, mas a estrutura resiste.", "Empurro o cadeado."),
    ("Ao tentar forçar o cadeado, o metal range.", "Tento forçar a porta."),
    ("Ao tentar forçar o cadeado, o metal range.", "Toco o cadeado."),
    ("A porta vibra sob sua força, mas permanece fechada.", "Forço o cadeado."),
])
def test_other_family_or_target_does_not_authorize_the_action(narrative, action):
    with pytest.raises(SceneProposalError):
        _check(narrative, action)


@pytest.mark.parametrize("narrative", [
    "Mara se aproxima. Seus dedos roçam o cadeado, mas a estrutura resiste.",
    "Seus dedos não roçam o cadeado; o frio atravessa o metal.",
    "O vento roça suas mãos enquanto a porta range.",
    "Ao tentar forçar o cadeado, Mara deixa a ferramenta cair.",
    "Mara se aproxima. Ao tentar forçar o cadeado, a ferramenta escorrega.",
    "Se decidir forçar o cadeado, o ruído poderá atrair atenção.",
    "Ao tentar entender o cadeado, o silêncio do galpão aumenta.",
    "Ao forçar as nuvens para longe, o vento traz uma chuva fria.",
])
def test_npc_environment_negation_and_hypothesis_do_not_become_player_actions(narrative):
    _check(narrative, npcs=("Mara",))


@pytest.mark.parametrize("narrative", [
    "Você observa Mara. Seus dedos roçam o cadeado, mas a estrutura resiste.",
    "Você observa Mara. Ao tentar forçar o cadeado, a ferramenta escorrega.",
    "Ao tentar forçar o cadeado de Mara, o metal range.",
])
def test_npc_as_object_or_owner_does_not_own_the_action(narrative):
    with pytest.raises(SceneProposalError):
        _check(narrative, npcs=("Mara",))


@pytest.mark.parametrize("clause", [
    "está na roça, perto do galpão", "sente sua força diminuir com o frio",
])
def test_nouns_do_not_become_brushing_or_forcing_verbs(clause):
    assert not _unauthorized_action_concepts(clause, authorized_actions={})
