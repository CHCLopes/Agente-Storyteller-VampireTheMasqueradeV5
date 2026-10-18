"""An affirmative opening state cannot bypass a failed barrier objective."""

import pytest

from api.scene_director_service import _failure_goal_is_granted, _normalize_for_policy
from api.scene_service import SceneState


@pytest.mark.parametrize("text, action", [
    ("O cadeado está aberto.", "Investigo o cadeado."),
    ("A grade ficou aberta.", "Investigo a grade."),
    ("A porta lateral está agora aberta.", "Investigo a porta lateral."),
    ("O portão permanece aberto.", "Investigo o portão."),
    ("A tranca está completamente aberta.", "Investigo a tranca."),
    ("As grades estão abertas.", "Investigo as grades."),
    ("O cadeado não cede, mas a grade está aberta.", "Investigo a grade."),
    ("A grade não estava aberta; agora a grade está aberta.", "Investigo a grade."),
])
def test_affirmative_open_state_of_active_barrier_grants_failed_goal(text, action):
    assert _failure_goal_is_granted(_normalize_for_policy(text), player_input=action)


@pytest.mark.parametrize("text", [
    "A grade não está aberta.",
    "A grade nunca ficou aberta.",
    "Se a grade está aberta, há outro caminho.",
    "Se a grade está agora aberta, há outro caminho.",
    "Caso a grade esteja aberta, há outro caminho.",
    "Talvez a grade esteja aberta.",
    "Não há certeza de que a grade está aberta.",
    "Não há certeza de que a grade está agora aberta.",
    "Ninguém sabe se a grade está aberta.",
    "Ontem a grade ficou aberta.",
    "Antes da investigação, a grade ficou aberta.",
    "A grade estava aberta antes da investigação.",
    "A grade está aberta?",
    'Mara diz: "A grade está aberta."',
    "A boca está aberta.",
    "A janela está aberta.",
])
def test_non_assertions_history_and_unrelated_objects_do_not_grant_barrier_goal(text):
    assert not _failure_goal_is_granted(
        _normalize_for_policy(text), player_input="Investigo a grade.",
    )


def test_distinct_door_is_not_the_declared_target():
    assert not _failure_goal_is_granted(
        "a porta frontal esta aberta.", player_input="Investigo a porta lateral.",
    )


def test_previous_closed_barrier_protects_access_without_repeating_its_name_in_action():
    assert _failure_goal_is_granted(
        "a grade esta aberta.", player_input="Investigo o arquivo.",
        current_scene=SceneState(location="Galpão", details=("Uma grade fechada bloqueia o arquivo.",)),
    )


def test_previously_open_barrier_is_not_a_new_granted_access():
    assert not _failure_goal_is_granted(
        "a grade esta aberta.", player_input="Investigo o arquivo.",
        current_scene=SceneState(location="Galpão", details=("Uma grade aberta delimita o arquivo.",)),
    )


def test_uncertain_previous_closure_does_not_activate_unrelated_barrier():
    assert not _failure_goal_is_granted(
        "a grade esta aberta.", player_input="Investigo o arquivo.",
        current_scene=SceneState(location="Galpão", details=("Talvez a grade esteja fechada.",)),
    )


def test_historical_closure_is_not_current_mechanical_barrier():
    assert not _failure_goal_is_granted(
        "a grade esta aberta.", player_input="Investigo o arquivo.",
        current_scene=SceneState(location="Galpão", details=("Uma grade estava fechada diante do arquivo.",)),
    )


def test_no_target_and_no_prior_closure_does_not_treat_all_doors_as_the_goal():
    assert not _failure_goal_is_granted("a porta esta aberta.")
