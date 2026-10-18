"""Perceived descriptions and known NPC relatives keep their own actor."""

import pytest

from api.scene_director_service import (
    SceneContinuationProposal,
    SceneProposalError,
    _action_authorizations,
    _validate_declared_player_actions,
    validate_scene_continuation,
)
from api.scene_service import SceneState


def _check(text, player_input="Examino o detalhe.", *, players=("Neófito",), npcs=("Mara",), field="n"):
    payload = {
        "n": text + " Uma corrente bate contra a parede.",
        "o": "unresolved", "l": "Galpão abandonado",
        "s": "Uma corrente bate contra a parede.", "p": [],
        "f": [{"k": "observation", "s": "Uma corrente bate contra a parede."}],
        "t": [], "r": [], "q": "O que você faz agora?",
    }
    if field != "n":
        payload["n"] = "Uma corrente bate contra a parede, rompendo o silêncio do galpão."
        if field == "f":
            payload["f"][0]["s"] = text
        else:
            payload[field] = text
    proposal = SceneContinuationProposal.model_validate(payload)
    _validate_declared_player_actions(
        proposal, authorized_actions=_action_authorizations(player_input),
        player_aliases=players, npc_aliases=npcs,
    )


@pytest.mark.parametrize("text", [
    "Ao focar no símbolo riscado no cadeado, você percebe que as linhas formam um padrão de runas antigas, parcialmente apagado por ferrugem.",
    "Você percebe a placa antiga, parcialmente apagada pela chuva.",
    "Você vê os textos, apagados pela água.",
    "Você nota as inscrições, quase apagadas pela umidade.",
    "Neófito percebe o símbolo, apagado pelo desgaste.",
])
def test_perceived_environmental_erasure_is_not_a_player_action(text):
    _check(text)


@pytest.mark.parametrize("text", [
    "Você fixa o olhar na figura de Mara, que permanece imóvel enquanto a sirene ecoa distante.",
    "Você observa Mara, que permanece imóvel.",
    "Você vê Mara, que abre a porta lateral.",
    "Você vê Mara, que abre a porta por você.",
    "Você vê Mara, que abre a porta por Neófito.",
    "Você percebe Mara, que ainda guarda o bilhete.",
    "Neófito observa Mara, que permanece imóvel.",
])
def test_known_npc_immediate_relative_does_not_control_player(text):
    _check(text, player_input="Observo Mara.")


@pytest.mark.parametrize("text", [
    "Você percebe que apaga o símbolo.",
    "Você percebe a placa e apaga o símbolo.",
    "Você percebe que a placa foi apagada por você.",
    "Você percebe a placa, parcialmente apagada por você.",
    "Você percebe a placa, parcialmente apagada pelo personagem.",
    "Você percebe que a placa foi apagada por Neófito.",
    "Você percebe a placa, parcialmente apagada pelo Neófito.",
    "Você percebe a placa, parcialmente apagada pela sua personagem.",
    "Você percebe que está apagado por ferrugem.",
    "Você percebe as marcas da sua pele, parcialmente apagadas por água.",
    "Você percebe a placa, parcialmente apagada por ferrugem provocada por você.",
    "Você percebe a placa, apagada por ferrugem, e abre a porta lateral.",
    "Você percebe a placa, apagada por ferrugem, mas você abre a porta lateral.",
    "Você percebe a placa, apagada por ferrugem, e depois decide abrir a porta.",
    "Você percebe que abriu a porta lateral.",
    "Você percebe que obrigam você a abrir a porta lateral.",
    "Você percebe que obrigam a abrir a porta lateral.",
    "Você fixa o olhar na figura de Mara, que você segue pelo corredor.",
    "Você fixa o olhar na figura de Mara, que seu personagem segue pelo corredor.",
    "Você observa Mara, que obriga você a abrir a porta lateral.",
    "Você observa Mara, que obriga a abrir a porta lateral.",
    "Você observa Mara, que manda abrir a porta lateral.",
    "Você observa Mara, que faz Neófito abrir a porta lateral.",
    "Você observa Mara, que permanece imóvel e abre a porta lateral.",
    "Você observa Mara, que permanece imóvel, e abre a porta lateral.",
    "Você observa Mara, mas permanece imóvel.",
    "Você observa Mara e permanece imóvel.",
    "Você fixa o olhar na figura de Mara enquanto permanece imóvel.",
    "Você observa alguém, que permanece imóvel.",
    "Você observa Mara, que decide sua próxima ação por você.",
    "Você observa Mara, que escolhe sua resposta por você.",
    "Você observa Mara, que convence você.",
    "Você observa Mara, que persuade Neófito.",
    "Você observa Mara, que mata você.",
    "Você observa Mara, que fere Neófito.",
    "Você observa Mara, que bebe seu sangue.",
    "Você observa Mara, que abre seus olhos.",
    "Você observa Mara, que guarda sua resposta.",
    "Você observa Mara, que fecha você no armário.",
])
def test_perception_keeps_player_and_ambiguous_actions_blocked(text):
    with pytest.raises(SceneProposalError) as caught:
        _check(text, player_input="Observo Mara e examino o detalhe.")
    assert caught.value.code == "scene_player_agency_violation"


def test_npc_alias_that_is_also_player_does_not_receive_relative_exception():
    with pytest.raises(SceneProposalError):
        _check("Você observa Mara, que abre a porta.", players=("Mara",))


def test_explicit_player_erasure_still_requires_matching_action_and_target():
    _check("Você apaga a placa.", player_input="Apago a placa.")
    with pytest.raises(SceneProposalError):
        _check("Você apaga o símbolo.", player_input="Apago a placa.")


@pytest.mark.parametrize("npc", ["Lia", "Guarda do cais", "José"])
def test_relative_actor_uses_provided_npc_identity_not_one_corpus_name(npc):
    _check(f"Você observa {npc}, que abre a porta.", player_input=f"Observo {npc}.", npcs=(npc,))


def test_erasure_description_does_not_authorize_later_player_erasing():
    with pytest.raises(SceneProposalError):
        _check("Você apaga a placa.", player_input="Percebo a placa, apagada pela chuva.")


def test_entire_recorded_control_proposal_no_longer_assigns_npc_relative_to_player():
    # This test checks actor attribution only: the source's paper fact is not
    # corroborated by its narrative and still needs separate semantic review.
    proposal = SceneContinuationProposal.model_validate({
        "n": "Você fixa o olhar na figura de Mara, que permanece imóvel enquanto a sirene ecoa distante. Seus olhos estreitam, a mão ainda dentro do casaco tremula levemente, como se ponderasse entre revelar algo ou se esconder na sombra do balcão.",
        "o": "unresolved", "l": "Bar fechado",
        "s": "Mara observa o jogador, hesitando antes de decidir revelar ou guardar o que tem.",
        "p": ["Mara"],
        "f": [{"k": "npc_action", "s": "Mara levanta lentamente a mão, mostrando um pequeno pedaço de papel amassado.", "v": "public", "i": 0.0, "p": False}],
        "t": ["Descobrir se Mara entregará o endereço"], "r": [],
        "q": "Qual será sua próxima atitude diante da hesitação de Mara?",
    })
    _validate_declared_player_actions(
        proposal, authorized_actions=_action_authorizations("Observo Mara e espero sua reação."),
        player_aliases=("Neófito",), npc_aliases=("Mara",),
    )


def test_entire_variant_narrative_does_not_attribute_passive_or_other_actor_to_player():
    _check(
        "Ao focar no símbolo riscado no cadeado, você percebe que as linhas formam um padrão de runas antigas, parcialmente apagado por ferrugem. Um leve brilho verde surge onde a última runa foi raspada, indicando que alguém recentemente tentou ocultar ou reforçar o sinal.",
        player_input="Examino com cuidado o detalhe que a investigação revelou.",
    )


@pytest.mark.parametrize("field", ["n", "s", "f"])
@pytest.mark.parametrize("text", [
    "Você percebe a placa, parcialmente apagada pela chuva.",
    "Você observa Mara, que permanece imóvel.",
])
def test_attribution_fix_applies_to_each_visible_assertion_field(field, text):
    _check(text, player_input="Observo Mara e examino o detalhe.", field=field)


@pytest.mark.parametrize("field", ["n", "s", "f"])
@pytest.mark.parametrize("text", [
    "Você percebe que a placa foi apagada por Neófito.",
    "Você observa Mara, que obriga você a abrir a porta lateral.",
])
def test_visible_summary_or_fact_cannot_hide_player_agency(field, text):
    with pytest.raises(SceneProposalError):
        _check(text, player_input="Observo Mara e examino o detalhe.", field=field)


@pytest.mark.parametrize("forces_player", [False, True])
def test_scene_admission_keeps_world_action_and_forced_player_action_distinct(forces_player):
    lead = (
        "Você observa Mara, que obriga você a abrir a porta lateral."
        if forces_player else "Você observa Mara, que abre a porta lateral."
    )
    proposal = SceneContinuationProposal.model_validate({
        "n": lead + " O vento espalha poeira pelo balcão enquanto uma sirene ecoa na rua. Do lado de fora, passos rápidos cortam o silêncio, e a luz da avenida desenha uma faixa estreita no chão.",
        "o": "unresolved", "l": "Bar fechado", "s": "Mara abre a porta lateral e passos ecoam na rua.",
        "p": ["Mara"], "f": [{"k": "npc_action", "s": "Mara abre a porta lateral.", "v": "player"}],
        "t": [], "r": [], "q": "Como você reage agora?",
    })
    arguments = {
        "facts": (), "current_scene": SceneState(location="Bar fechado", npcs_present=("Mara",)),
        "player_input": "Observo Mara.", "player_aliases": ("Neófito",), "npc_aliases": ("Mara",),
    }
    if forces_player:
        with pytest.raises(SceneProposalError) as caught:
            validate_scene_continuation(proposal, **arguments)
        assert caught.value.code == "scene_player_agency_violation"
    else:
        assert validate_scene_continuation(proposal, **arguments) is proposal
