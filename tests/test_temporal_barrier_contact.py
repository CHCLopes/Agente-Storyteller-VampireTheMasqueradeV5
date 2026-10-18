"""A temporal barrier contact needs intent even if nothing opens or succeeds."""

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
        "n": text, "o": "failure", "l": "Galpão abandonado",
        "s": "O cadeado não abre, nenhum indício é encontrado e passos se aproximam.",
        "p": [], "f": [{"k": "complication", "s": "Passos se aproximam.", "p": True}],
        "t": ["Descobrir o conteúdo do arquivo"], "r": [],
        "q": "Como você reage aos passos?",
    }
    payload.update(updates)
    return SceneContinuationProposal.model_validate(payload)


def _check(text, action="Investigo o cadeado.", **updates):
    _validate_implicit_player_contact(
        _proposal(text, **updates), authorized_actions=_action_authorizations(action),
    )


@pytest.mark.parametrize("text", [
    "Ao tocar o cadeado, a lâmina de metal vibra, mas o mecanismo não cede.",
    "Ao tentar tocar o cadeado, a lâmina de metal vibra.",
    "Ao tocar a porta lateral, uma sirene ecoa na rua.",
    "Ao tocar as grades, o metal vibra sem ceder.",
    "Ao tocar o portão, o rádio chia sobre a mesa.",
    "Ao tocar a tranca, o ferrolho vibra sem ceder.",
    "Você observa Mara. Ao tocar o cadeado, o mecanismo continua travado.",
    "Ao tocar o cadeado de Mara, a lâmina de metal vibra.",
])
def test_undeclared_temporal_contact_is_not_implied_by_investigation(text):
    with pytest.raises(SceneProposalError) as caught:
        _check(text, p=["Mara"])
    assert caught.value.code == "scene_player_agency_violation"
    assert caught.value.evidence["rule"] == "undeclared_player_contact"


@pytest.mark.parametrize("text,action", [
    ("Ao tocar o cadeado, o mecanismo não cede.", "Toco o cadeado."),
    ("Ao tentar tocar a porta, a madeira range.", "Tento tocar a porta."),
    ("Ao tocar a porta lateral, a madeira range.", "Toco a porta lateral."),
])
def test_temporal_contact_allows_the_matching_declared_touch(text, action):
    _check(text, action)


@pytest.mark.parametrize("action", [
    "Toco a parede.", "Empurro a porta lateral.", "Toco a porta frontal.",
])
def test_touch_permission_keeps_family_and_target(action):
    with pytest.raises(SceneProposalError):
        _check("Ao tocar a porta lateral, o mecanismo não cede.", action)


@pytest.mark.parametrize("text", [
    "Ao tocar o cadeado, Mara recua diante do metal frio.",
    "Mara se aproxima. Ao tocar o cadeado, o mecanismo não cede.",
    "Ao tocar a porta, o vento faz a madeira vibrar.",
    "Se decidir tocar o cadeado, o ruído poderá aumentar.",
    "Ao observar o cadeado, você nota a ferrugem antiga.",
])
def test_explicit_npc_environment_and_prospective_contact_are_not_player_actions(text):
    _check(text, p=["Mara"])


@pytest.mark.parametrize("field", ["s", "f", "t", "r"])
def test_temporal_contact_cannot_enter_other_assertion_fields(field):
    claim = "Ao tocar o cadeado, a lâmina vibra sem ceder."
    value = [{"k": "complication", "s": claim, "p": True}] if field == "f" else (
        [claim] if field in {"t", "r"} else claim
    )
    with pytest.raises(SceneProposalError) as caught:
        _check("O mecanismo não cede e passos se aproximam.", **{field: value})
    assert caught.value.evidence["rule"] == "undeclared_player_contact"


def test_observed_failure_remains_rejected_for_contact_not_false_success():
    proposal = _proposal(
        "Ao tocar o cadeado, a lâmina de metal vibra, mas o mecanismo não cede. "
        "O som de passos se aproxima, ecoando no galpão, e a tensão aumenta. "
        "Nenhuma prova surge; o segredo do arquivo permanece oculto, e a pressão para agir cresce."
    )
    scene = SceneState(
        location="Galpão abandonado",
        summary="O arquivo permanece atrás de uma grade trancada enquanto passos se aproximam.",
        details=("A grade do arquivo está trancada.",),
        open_threads=("Descobrir o conteúdo do arquivo",), last_turn=8,
    )
    with pytest.raises(SceneProposalError) as caught:
        validate_scene_continuation(
            proposal, current_scene=scene,
            facts=({"fact_type": "mechanics.resolution", "value": {"is_success": False}},),
            player_input="Investigo o cadeado.",
        )
    assert caught.value.code == "scene_player_agency_violation"
    assert caught.value.evidence["rule"] == "undeclared_player_contact"
