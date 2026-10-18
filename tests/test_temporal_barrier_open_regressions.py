"""Opening a barrier in a temporal clause still requires player intent."""

import pytest

from api.scene_director_service import (
    SceneContinuationProposal,
    SceneProposalError,
    _action_authorizations,
    _validate_implicit_player_contact,
    validate_scene_continuation,
)
from api.scene_service import SceneState


def _proposal(text, **updates):
    payload = {
        "n": text, "o": "unresolved", "l": "Galpão abandonado",
        "s": "O rádio emite um estalo e a corrente vibra.", "p": [],
        "f": [{"k": "observation", "s": "O rádio emite um estalo."}],
        "t": [], "r": [], "q": "O que você faz agora?",
    }
    payload.update(updates)
    return SceneContinuationProposal.model_validate(payload)


def _check(text, action="Investigo o galpão abandonado.", **updates):
    _validate_implicit_player_contact(
        _proposal(text, **updates), authorized_actions=_action_authorizations(action),
        player_input=action,
    )


@pytest.mark.parametrize("text", [
    "Ao abrir a porta metálica, encontra um mapa sobre a mesa.",
    "Ao tentar abrir o cadeado, a corrente vibra sem ceder.",
    "Ao abrir as portas laterais, a luz alcança o corredor.",
    "Ao abrir o portão, a corrente vibra e o rádio chia.",
    "Ao abrir as grades, o rádio chia sobre a bancada.",
    "Ao abrir a tranca, a corrente vibra e o rádio chia.",
    "Você observa Mara. Ao abrir a porta, encontra um mapa.",
    "Ao abrir a porta de Mara, encontra um mapa sobre a mesa.",
    "Mara aguarda. Ao abrir a porta, você encontra um mapa.",
    "Ao abrir a porta, o vento espalha os papéis da mesa.",
    "Você está diante da porta. Ao abrir a porta, o vento espalha os papéis.",
    "Você está diante da porta. Ao abrir a porta, a chuva molha o mapa.",
])
def test_temporal_opening_is_not_implied_by_investigation(text):
    with pytest.raises(SceneProposalError) as caught:
        _check(text, p=["Mara"])
    assert caught.value.code == "scene_player_agency_violation"
    assert caught.value.evidence["rule"] == "undeclared_player_barrier_open"


@pytest.mark.parametrize("text,action", [
    ("Ao abrir a porta metálica, o rádio chia na bancada.", "Abro a porta metálica."),
    ("Ao abrir a porta lateral, o rádio chia na bancada.", "Eu abro a porta lateral."),
    ("Ao tentar abrir o cadeado, o metal continua imóvel.", "Tento abrir o cadeado."),
    ("Ao abrir as portas laterais, o rádio chia na bancada.", "Vou abrir as portas laterais."),
    ("Ao abrir a porta, o rádio chia na bancada.", "Observo a sala e abro a porta."),
    ("Ao abrir a porta, o rádio chia na bancada.", "Não observo a sala e abro a porta."),
    ("Ao abrir a porta, o rádio chia na bancada.", "Mara pede que eu aguarde. Abro a porta."),
    ("Ao abrir a porta, o rádio chia na bancada.", "Se Mara concordar, observo a sala; abro a porta."),
    ("Ao abrir a porta, o rádio chia na bancada.", "Não é verdade que observo a sala; eu abro a porta."),
])
def test_matching_positive_player_declaration_allows_opening(text, action):
    _check(text, action)


@pytest.mark.parametrize("action", [
    "Abro o cadeado.", "Abro a porta frontal.", "Toco a porta lateral.",
    "Empurro a porta lateral.", "Não abro a porta lateral.",
    "Se eu abrir a porta lateral, observo o corredor.",
    "Caso eu decida, abro a porta lateral.",
    "Mara abre a porta lateral.", "Observo Mara abrir a porta lateral.",
    'Mara diz: "Abro a porta lateral."',
    "Peço a Mara para abrir a porta lateral.",
    "Abro a porta lateral se Mara concordar.",
    "Abro a porta lateral quando Mara der o sinal.",
    "Abro a porta lateral, caso Mara concorde.",
    "Não é verdade que observo a sala e abro a porta lateral.",
    "Abro a porta lateral ou espero?",
    "Abro a porta lateral? Não, apenas observo.",
    "Abro a porta lateral?",
])
def test_wrong_target_family_or_non_player_declaration_does_not_authorize(action):
    with pytest.raises(SceneProposalError) as caught:
        _check("Ao abrir a porta lateral, encontra um mapa sobre a mesa.", action, p=["Mara"])
    assert caught.value.evidence["rule"] == "undeclared_player_barrier_open"


@pytest.mark.parametrize("text", [
    "Ao abrir a porta, Mara encontra um mapa sobre a mesa.",
    "Mara se aproxima. Ao abrir a porta, encontra um mapa.",
    "Mara, ao abrir a porta, encontra um mapa sobre a mesa.",
    "Ao abrir a porta de Mara, ela encontra um mapa.",
    "O vento abre a porta e espalha os papéis da mesa.",
    "Ao não abrir a porta, a corrente permanece imóvel.",
    "Se abrir a porta, o ruído poderá atrair atenção.",
    "Caso decida abrir a porta, o ruído poderá aumentar.",
    "Ao abrir da porta, a corrente vibra contra a parede.",
    "A porta se abre com o vento e a corrente vibra.",
    "Você observa a porta abrir com o vento que sopra.",
])
def test_npc_environment_negation_and_prospective_opening_are_not_player_actions(text):
    _check(text, p=["Mara"])


@pytest.mark.parametrize("field", ["s", "f", "t", "r"])
def test_temporal_opening_cannot_enter_other_visible_assertion_fields(field):
    claim = "Ao abrir a porta lateral, encontra um mapa sobre a mesa."
    value = [{"k": "observation", "s": claim}] if field == "f" else (
        [claim] if field in {"t", "r"} else claim
    )
    with pytest.raises(SceneProposalError) as caught:
        _check("O rádio emite um estalo e a corrente vibra na parede.", **{field: value})
    assert caught.value.evidence["rule"] == "undeclared_player_barrier_open"


def test_full_admission_rejects_temporal_opening_after_permitted_examination():
    proposal = _proposal(
        "Você examina o galpão abandonado, examinando o cadeado riscado, o rádio "
        "chiando e os ecos do mezanino. Ao abrir a porta metálica, encontra um "
        "mapa sobre a mesa. O rádio emite um estalo e uma corrente vibra na parede."
    )
    with pytest.raises(SceneProposalError) as caught:
        validate_scene_continuation(
            proposal, facts=(), current_scene=SceneState(location="Galpão abandonado"),
            player_input="Investigo o galpão abandonado.",
        )
    assert caught.value.evidence["rule"] == "undeclared_player_barrier_open"


def test_npc_opening_does_not_waive_subsequent_player_coercion():
    proposal = _proposal(
        "Mara, ao abrir a porta, obriga você a entrar no corredor. O rádio "
        "emite um estalo e uma corrente vibra na parede, enquanto a chuva "
        "bate no telhado e a luz da rua atravessa a janela.", p=["Mara"],
    )
    with pytest.raises(SceneProposalError) as caught:
        validate_scene_continuation(
            proposal, facts=(),
            current_scene=SceneState(location="Galpão abandonado", npcs_present=("Mara",)),
            player_input="Investigo o galpão abandonado.",
        )
    assert caught.value.code == "scene_player_agency_violation"


def test_observed_environmental_opening_still_passes_full_admission():
    proposal = _proposal(
        "Você observa a porta abrir com o vento que sopra do corredor. O rádio "
        "emite um estalo e uma corrente vibra na parede, enquanto a chuva bate "
        "no telhado e a luz da rua atravessa a janela."
    )
    assert validate_scene_continuation(
        proposal, facts=(), current_scene=SceneState(location="Galpão abandonado"),
        player_input="Observo a porta.",
    ) is proposal


def test_observed_warehouse_output_remains_rejected_at_original_inspection_family():
    proposal = _proposal(
        "Você vasculha o galpão abandonado, examinando o cadeado riscado, o rádio "
        "chiando e os ecos do mezanino. Ao abrir a porta metálica, encontra um "
        "mapa rasgado sobre uma mesa suja, marcando rotas de contrabando e um "
        "pequeno compartimento oculto contendo um frasco de sangue coagulado. "
        "Um leve estalo vem do mezanino, indicando que alguém ainda está lá.",
        o="success", l="Galpão abandonado, interior próximo à porta principal",
    )
    with pytest.raises(SceneProposalError) as caught:
        validate_scene_continuation(
            proposal, facts=({"fact_type": "mechanics.resolution", "value": {"is_success": True}},),
            current_scene=SceneState(location="Galpão abandonado"),
            player_input="Investigo o galpão abandonado.",
        )
    assert caught.value.evidence["rule"] == "undeclared_player_action"
    assert caught.value.evidence["unauthorized_concepts"] == ["inspect"]
