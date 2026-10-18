"""Local nominal negation cannot become a grant or hide a separate grant."""

import pytest

from api.scene_director_service import (
    SceneContinuationProposal,
    SceneProposalError,
    _affirmative_goal_matches,
    _failure_goal_is_granted,
    _normalize_for_policy,
    validate_mechanical_narrative,
)
from api.turn_execution_service import NarrativeContractError, validate_narrative_contract


OBSERVED_NARRATIVE = (
    "Ao tocar o cadeado, a lâmina de metal vibra, mas o mecanismo não cede. "
    "O som de passos se aproxima, ecoando no galpão, e a tensão aumenta. "
    "Nenhuma prova surge; o segredo do arquivo permanece oculto, e a pressão para agir cresce."
)
OBSERVED_SUMMARY = (
    "O cadeado não abre, nenhum indício é encontrado e a aproximação de passos aumenta a pressão."
)


@pytest.mark.parametrize("text", [
    "Nenhum indício é encontrado.",
    "Nenhuma evidência é descoberta.",
    "Nenhuma pista é revelada.",
    "Nenhuns registros são encontrados.",
    "Nenhumas pistas são identificadas.",
    "Nenhuma informação é confirmada.",
    "Nenhum detalhe novo é descoberto.",
    "Na bancada, nenhuma prova nova é encontrada.",
    "Nenhum indício é encontrado no galpão.",
    "Nenhum indício é encontrado sobre a bancada.",
    "Nenhum indício é encontrado e a pressão aumenta.",
    OBSERVED_SUMMARY,
])
def test_present_passive_with_local_negative_subject_does_not_grant_goal(text):
    normalized = _normalize_for_policy(text)
    assert list(_affirmative_goal_matches(normalized)) == []
    assert not _failure_goal_is_granted(normalized)
    validate_mechanical_narrative(
        "O cadeado não cede. " + text, outcome="failure", player_input="Investigo o cadeado.",
    )
    with pytest.raises(SceneProposalError, match="scene_success_not_honored"):
        validate_mechanical_narrative(text, outcome="success", player_input="Investigo o cadeado.")


@pytest.mark.parametrize("text", [
    "Nenhum indício é encontrado, mas a prova foi encontrada.",
    "Nenhum indício é encontrado e a prova foi encontrada.",
    "Nenhum indício é encontrado; o cadeado abre.",
    "Nenhum indício é encontrado. Você obteve sucesso.",
    "Nenhum indício é encontrado: o registro foi localizado.",
    "Nenhum indício é encontrado e você encontra a prova.",
    "Nenhuma pista é revelada, porém o objetivo foi alcançado.",
    "Nenhumas pistas são identificadas, contudo o arquivo abre.",
    "Nenhum indício é encontrado, mas a prova está em sua posse.",
])
def test_nominal_negation_cannot_hide_another_achievement(text):
    with pytest.raises(SceneProposalError, match="scene_failure_granted_goal"):
        validate_mechanical_narrative(
            "O cadeado não cede. " + text, outcome="failure", player_input="Investigo o cadeado.",
        )


@pytest.mark.parametrize("text", [
    "Você vê nenhum indício e encontra a prova.",
    "Você não ouve nenhum som e encontra o registro.",
    "Nenhum som e o registro encontrado.",
    "Nenhum indício e a prova é encontrada.",
    "Com nenhum indício é encontrado o registro.",
    "No arquivo nenhum indício é encontrado o registro.",
    "Nenhum indício é encontrado o registro.",
    "Nenhum indício é encontrado um registro.",
    "Nenhum indício é encontrado e encontrado o registro.",
    "Nenhum indício e encontra a prova.",
    "Nenhum guarda encontra a prova, mas você encontra o registro.",
])
def test_conjunctions_other_subjects_and_active_verbs_do_not_inherit_passive_negation(text):
    assert _failure_goal_is_granted(_normalize_for_policy(text))
    with pytest.raises(SceneProposalError, match="scene_failure_granted_goal"):
        validate_mechanical_narrative(
            "O cadeado não cede. " + text, outcome="failure", player_input="Investigo o cadeado.",
        )


def _observed_proposal():
    return SceneContinuationProposal.model_validate({
        "n": OBSERVED_NARRATIVE, "o": "failure", "l": "Galpão abandonado",
        "s": OBSERVED_SUMMARY, "p": [],
        "f": [{
            "k": "complication",
            "s": "Passos rápidos se aproximam, indicando que alguém está vindo ao local.",
            "v": "public", "i": 0.0, "p": True,
        }],
        "t": ["Descobrir o conteúdo do arquivo"], "r": [],
        "q": "O que você fará diante dos passos que se aproximam e do cadeado ainda fechado?",
    })


def test_observed_response_is_not_a_mechanical_success_due_to_its_summary():
    proposal = _observed_proposal()
    assert not _failure_goal_is_granted(_normalize_for_policy(proposal.narrative))
    validate_mechanical_narrative(
        proposal.narrative, outcome="failure", proposal=proposal, player_input="Investigo o cadeado.",
    )


def test_legacy_and_structured_mechanics_apply_the_same_local_negation():
    proposal = _observed_proposal()
    facts = ({"fact_type": "mechanics.resolution", "value": {"is_success": False}},)
    assert validate_narrative_contract(
        proposal.player_text, facts=facts, scene_proposal=proposal, player_input="Investigo o cadeado.",
    ) == proposal.player_text
    assert validate_narrative_contract(proposal.narrative, facts=facts) == proposal.narrative
    cheated = proposal.model_copy(update={"scene_summary": OBSERVED_SUMMARY + " A prova foi encontrada."})
    with pytest.raises(NarrativeContractError, match="narrative_outcome_mismatch"):
        validate_narrative_contract(
            cheated.player_text, facts=facts, scene_proposal=cheated, player_input="Investigo o cadeado.",
        )
