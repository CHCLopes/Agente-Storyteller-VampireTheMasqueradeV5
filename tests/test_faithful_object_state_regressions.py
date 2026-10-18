"""Physical barrier state does not assign waiting; manipulation still needs agency."""

import pytest

from api.scene_director_service import SceneContinuationProposal, SceneProposalError, validate_scene_continuation
from api.scene_service import SceneState


BACKGROUND = (
    " Passos ecoam no corredor, aproximando-se rapidamente. A pressão aumenta "
    "sobre o galpão enquanto a luz oscila sobre o corredor escuro e o acesso "
    "ao arquivo continua fechado."
)


def _admit(narrative, player_input="Investigo o cadeado.", *, player_aliases=("Neófito",)):
    proposal = SceneContinuationProposal.model_validate({
        "n": narrative + BACKGROUND, "o": "unresolved", "l": "Galpão abandonado",
        "s": "Passos ecoam no corredor.", "p": ["Mara"],
        "f": [{"k": "observation", "s": "Passos ecoam no corredor."}],
        "t": [], "r": [], "q": "O que você faz agora?",
    })
    return validate_scene_continuation(
        proposal, facts=(), current_scene=SceneState(location="Galpão abandonado", npcs_present=("Mara",)),
        player_input=player_input, player_aliases=player_aliases, npc_aliases=("Mara",),
    )


@pytest.mark.parametrize("narrative", [
    "Você examina o cadeado, mas ele permanece firme.",
    "Você examina o cadeado, mas o cadeado permanece firme.",
    "Você examina a porta, mas ela permanece fechada.",
    "Neófito examina o cadeado, mas ele permanece firme.",
])
def test_examined_barrier_state_is_not_a_player_waiting_action(narrative):
    assert _admit(narrative).outcome == "unresolved"


@pytest.mark.parametrize("narrative", [
    "Você examina o cadeado, mas você permanece firme.",
    "Você examina o cadeado, mas permanece firme.",
    "Você examina Mara, mas ele permanece firme.",
    "Você examina o cadeado e Mara, mas ele permanece firme.",
    "Você examina a porta, mas ele permanece firme.",
    "Você examina o cadeado, mas ele abre a porta.",
    "Você examina o cadeado, mas ele permanece firme e você abre a porta.",
    "Você examina o cadeado, mas ele permanece firme. Você abre a porta.",
])
def test_object_attribution_never_waives_player_ambiguous_or_later_actions(narrative):
    with pytest.raises(SceneProposalError) as caught:
        _admit(narrative)
    assert caught.value.code == "scene_player_agency_violation"


@pytest.mark.parametrize("narrative", [
    "Você tenta manipular o cadeado.",
    "Você manipula o cadeado.",
    "Neófito tenta manipular o cadeado.",
    "Você tenta manipular o cadeado, mas ele permanece firme, rangendo levemente ao toque.",
])
def test_investigation_does_not_authorize_physical_manipulation(narrative):
    with pytest.raises(SceneProposalError) as caught:
        _admit(narrative)
    assert caught.value.code == "scene_player_agency_violation"
    assert caught.value.evidence["unauthorized_concepts"] == ["interact"]


@pytest.mark.parametrize("player_input", [
    "Manipulo o cadeado.", "Eu manipulo o cadeado.", "Manipular o cadeado.",
    "Tento manipular o cadeado.", "Vou manipular o cadeado.",
    "Observo o corredor e eu manipulo o cadeado.",
])
def test_positive_manipulation_declaration_authorizes_only_that_action(player_input):
    assert _admit("Você tenta manipular o cadeado, mas ele permanece firme.", player_input).outcome == "unresolved"


@pytest.mark.parametrize("player_input", [
    "Não manipulo o cadeado.", "Nunca manipulo o cadeado.",
    "Se eu manipular o cadeado, observo o corredor.", "Manipulo o cadeado se Mara permitir.",
    "Mara manipula o cadeado.", "Mara diz que eu manipulo o cadeado.",
    '"Manipulo o cadeado."', "‘Observo o corredor. Manipulo o cadeado.’",
    "Digo: Manipulo o cadeado.", "Manipulo a porta.", "Manipulo o cadeado lateral.",
])
def test_nonpositive_or_different_target_input_cannot_authorize_manipulation(player_input):
    target = "cadeado traseiro" if player_input == "Manipulo o cadeado lateral." else "cadeado"
    with pytest.raises(SceneProposalError) as caught:
        _admit(f"Você manipula o {target}.", player_input)
    assert caught.value.evidence["unauthorized_concepts"] == ["interact"]


@pytest.mark.parametrize("narrative", [
    "Você não manipula o cadeado.",
    "Você nunca manipula o cadeado.",
    "Se você manipular o cadeado, a luz pode oscilar.",
    "Caso Neófito manipule o cadeado, a luz pode oscilar.",
    "Mara manipula o cadeado.",
])
def test_negated_hypothetical_and_npc_manipulation_are_not_player_claims(narrative):
    assert _admit(narrative).outcome == "unresolved"


def test_negation_does_not_waive_a_later_independent_manipulation():
    with pytest.raises(SceneProposalError) as caught:
        _admit("Você não manipula o cadeado, mas manipula a porta.")
    assert caught.value.evidence["unauthorized_concepts"] == ["interact"]


@pytest.mark.parametrize("noun", ["manipulação", "manipulador"])
def test_manipulation_nouns_do_not_become_performed_actions(noun):
    assert _admit(f"Você examina o registro do {noun}.").outcome == "unresolved"


@pytest.mark.parametrize("narrative", [
    "Você examina o cadeado, mas Mara manipula a porta.",
    "Você examina o cadeado e Mara tenta manipular a porta.",
    "Você examina o cadeado, mas ele permanece firme e Mara manipula a porta.",
])
def test_explicit_npc_manipulation_after_player_inspection_keeps_its_actor(narrative):
    assert _admit(narrative).outcome == "unresolved"


@pytest.mark.parametrize("narrative", [
    "Você examina a porta, mas o Cadeado permanece firme.",
    "Você examina o Cadeado, mas ele permanece firme.",
])
def test_registered_player_alias_cannot_be_treated_as_a_barrier(narrative):
    with pytest.raises(SceneProposalError) as caught:
        _admit(narrative, player_aliases=("Cadeado",))
    assert caught.value.evidence["unauthorized_concepts"] == ["wait"]


@pytest.mark.parametrize("narrative", [
    "Você examina o cadeado e Mara manipula a porta, mas você manipula a grade.",
    "Você examina o cadeado e Mara manipula a porta. Você manipula a grade.",
])
def test_npc_manipulation_never_waives_a_later_player_manipulation(narrative):
    with pytest.raises(SceneProposalError) as caught:
        _admit(narrative)
    assert caught.value.evidence["unauthorized_concepts"] == ["interact"]


@pytest.mark.parametrize("narrative", [
    "Você manipula o cadeado se Mara permitir.",
    "Você tenta manipular o cadeado caso Mara permita.",
    "Você manipula o cadeado, se Mara permitir.",
])
def test_a_condition_attached_to_manipulation_is_not_a_performed_claim(narrative):
    assert _admit(narrative).outcome == "unresolved"


@pytest.mark.parametrize("narrative", [
    "Você manipula o cadeado e Mara espera se quiser.",
    "Você manipula o cadeado, Mara espera se quiser.",
    "Você manipula o cadeado se Mara permitir, mas manipula a porta.",
])
def test_a_condition_never_waives_an_independent_manipulation(narrative):
    with pytest.raises(SceneProposalError) as caught:
        _admit(narrative)
    assert "interact" in caught.value.evidence["unauthorized_concepts"]


@pytest.mark.parametrize("target", [
    "suas mãos", "seus dedos", "tua mão", "tuas mãos", "teus dedos",
    "sua mão", "as mãos do jogador", "as mãos de Neófito",
])
def test_npc_manipulation_does_not_gain_control_of_the_players_body(target):
    with pytest.raises(SceneProposalError) as caught:
        _admit(f"Você observa Mara, e Mara manipula {target}.", "Observo Mara.")
    assert caught.value.evidence["unauthorized_concepts"] == ["interact"]


@pytest.mark.parametrize("target", ["a mão dela", "a porta"])
def test_npc_own_body_or_world_target_remains_external_to_player_control(target):
    assert _admit(f"Você observa Mara, e Mara manipula {target}.", "Observo Mara.").outcome == "unresolved"
