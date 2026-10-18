"""Negated achievements and blocked barriers keep their local mechanical scope."""

import pytest

from api.scene_director_service import (
    SceneProposalError,
    _failure_goal_is_granted,
    _normalize_for_policy,
    validate_mechanical_narrative,
)
from api.scene_service import SceneState
from api.turn_execution_service import NarrativeContractError, validate_narrative_contract


@pytest.mark.parametrize("text", [
    "Nada cede.",
    "Nada se abre.",
    "A estrutura resiste. Nada cede.",
    "Nada revela a combinação do cadeado.",
    "A grade range, nada cede.",
    "A grade range, mas nada cede.",
])
def test_nada_negates_only_its_immediate_achievement(text):
    assert not _failure_goal_is_granted(_normalize_for_policy(text))


@pytest.mark.parametrize("text", [
    "Nada cede, mas a prova foi encontrada.",
    "Nada cede e a porta abre.",
    "Nada cede. A prova foi encontrada.",
    "Nada revela a combinação, porém o cadeado cede.",
    "Nada cede: o registro definitivo foi encontrado.",
    "Nada cede; a investigação teve sucesso.",
])
def test_nada_cannot_hide_another_affirmative_achievement(text):
    assert _failure_goal_is_granted(_normalize_for_policy(text))
    with pytest.raises(SceneProposalError, match="scene_failure_granted_goal"):
        validate_mechanical_narrative("A estrutura resiste. " + text, outcome="failure", player_input="Investigo o cadeado.")


@pytest.mark.parametrize("text", [
    "Você do nada encontra a prova.",
    "Do nada encontra a prova.",
    "Você, do nada encontra a prova.",
    "No nada encontra a prova.",
    "Uma teoria de nada resolve o mistério.",
    "O cadeado range, mas você do nada encontra a prova.",
])
def test_nada_inside_an_adjunct_or_noun_phrase_is_not_a_negated_subject(text):
    assert _failure_goal_is_granted(_normalize_for_policy(text))
    with pytest.raises(SceneProposalError, match="scene_failure_granted_goal"):
        validate_mechanical_narrative(
            "A estrutura resiste. " + text, outcome="failure", player_input="Investigo o cadeado.",
        )


def test_nada_cede_honors_failure_without_additional_failure_keywords():
    validate_mechanical_narrative("Nada cede.", outcome="failure", player_input="Investigo o cadeado.")
    with pytest.raises(SceneProposalError, match="scene_success_not_honored"):
        validate_mechanical_narrative("Nada cede.", outcome="success", player_input="Investigo o cadeado.")


@pytest.mark.parametrize("text,action", [
    ("A grade permanece intransponível.", "Investigo a grade."),
    ("A grade está ainda intransponível.", "Investigo a grade."),
    ("As grades estão intransponíveis.", "Investigo as grades."),
    ("A porta lateral segue intransponível.", "Investigo a porta lateral."),
])
def test_current_impassable_target_honors_failure(text, action):
    validate_mechanical_narrative(text, outcome="failure", player_input=action)


def test_prior_closed_barrier_is_a_mechanically_relevant_target():
    validate_mechanical_narrative(
        "A grade permanece intransponível.", outcome="failure", player_input="Investigo o arquivo.",
        current_scene=SceneState(location="Galpão", details=("A grade do arquivo está trancada.",)),
    )


@pytest.mark.parametrize("text", [
    "A grade não está intransponível.",
    "A grade nunca ficou intransponível.",
    "A grade não é intransponível.",
    "Se a grade está intransponível, há outro caminho.",
    "Talvez a grade esteja intransponível.",
    "A grade talvez está intransponível.",
    "A grade provavelmente está intransponível.",
    "A grade possivelmente está intransponível.",
    "Caso a grade permaneça intransponível, há outro caminho.",
    "Não há certeza de que a grade está intransponível.",
    "Não é verdade que a grade está intransponível.",
    "Não está confirmado que a grade está intransponível.",
    "Ninguém sabe se a grade está intransponível.",
    "Ontem a grade ficou intransponível.",
    "A grade estava intransponível antes da investigação.",
    "A grade está intransponível?",
    'Mara diz: "A grade está intransponível."',
    "A porta está intransponível.",
    "A trilha permanece intransponível.",
])
def test_negated_uncertain_historical_or_unrelated_states_do_not_honor_failure(text):
    with pytest.raises(SceneProposalError, match="scene_failure_not_honored"):
        validate_mechanical_narrative(text, outcome="failure", player_input="Investigo a grade.")


def test_different_door_is_not_silently_equated_to_canonical_grade_and_lock():
    with pytest.raises(SceneProposalError, match="scene_failure_not_honored"):
        validate_mechanical_narrative(
            "A porta permanece intransponível.", outcome="failure", player_input="Investigo o cadeado.",
            current_scene=SceneState(location="Galpão", details=("A grade do arquivo está trancada.",)),
        )


def test_a_named_door_does_not_activate_every_other_door():
    with pytest.raises(SceneProposalError, match="scene_failure_not_honored"):
        validate_mechanical_narrative(
            "A porta frontal permanece intransponível.", outcome="failure",
            player_input="Investigo a porta lateral.",
        )


def test_impassable_target_cannot_launder_a_later_granted_goal():
    with pytest.raises(SceneProposalError, match="scene_failure_granted_goal"):
        validate_mechanical_narrative(
            "A grade permanece intransponível, mas o registro definitivo foi encontrado.",
            outcome="failure", player_input="Investigo a grade.",
        )


def test_structured_and_legacy_prose_mechanical_checks_share_local_negation():
    narrative = (
        "Nada cede. O rádio chia sobre a bancada, enquanto a luz azulada oscila "
        "sobre as vigas e o vento frio atravessa as janelas quebradas do galpão."
    )
    failure = ({"fact_type": "mechanics.resolution", "value": {"is_success": False}},)
    assert validate_narrative_contract(narrative, facts=failure) == narrative
    with pytest.raises(NarrativeContractError, match="narrative_outcome_mismatch"):
        validate_narrative_contract(narrative + " A prova foi encontrada.", facts=failure)
