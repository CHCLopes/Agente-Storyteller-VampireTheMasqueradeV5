"""Observed grounded questions remain open without granting NPC or player actions."""

import pytest

from api.scene_director_service import (
    SceneContinuationProposal,
    SceneProposalError,
    _validate_player_prompt,
    validate_scene_continuation,
)
from api.scene_service import SceneState


OBSERVED_QUESTIONS = (
    "Qual será sua próxima tentativa para acessar o arquivo?",
    "Qual próximo passo deseja tomar para investigar o brilho ou o vulto?",
)


@pytest.mark.parametrize("question", [
    *OBSERVED_QUESTIONS,
    "Qual é sua tentativa diante de Mara?",
    "Qual será sua próxima tentativa diante de Mara?",
    "Qual próximo passo deseja tomar?",
    "Qual o próximo passo deseja tomar?",
    "Qual próximo passo você deseja tomar?",
    "Qual próximo passo deseja tomar diante de Mara?",
    "Qual o próximo passo deseja tomar em relação a Mara?",
])
@pytest.mark.parametrize("registered", [False, True])
def test_open_attempt_and_implicit_player_step_are_actionable(question, registered):
    _validate_player_prompt(question, npc_aliases=("Mara",) if registered else ())


@pytest.mark.parametrize("question", [
    "Qual será a próxima tentativa de Mara?",
    "Qual próximo passo Mara deseja tomar?",
    "Qual próximo passo a informante deseja tomar?",
    "Qual próximo passo deseja tomar Mara?",
    "Qual próximo passo deseja tomar a informante?",
    "Qual próximo passo deseja tomar, Mara?",
    "Qual próximo passo deseja tomar, Mara, diante da porta?",
    "Qual próximo passo deseja tomar diante da porta, Mara?",
    "Qual próximo passo deseja tomar para investigar a porta, Mara?",
    "Qual próximo passo Mara deseja tomar enquanto você espera?",
    "O que Mara sabe sobre qual próximo passo deseja tomar?",
    "Como Mara decide sua próxima tentativa?",
    "Sua próxima tentativa será abrir a porta?",
    "Você deseja tomar o próximo passo?",
    "Qual é a origem do brilho que você deseja investigar?",
    "Qual próximo passo deseja tomar para revelar a origem do brilho: qual é a origem?",
    "Qual próximo passo deseja tomar",
])
@pytest.mark.parametrize("registered", [False, True])
def test_step_cue_does_not_authorize_npc_closed_or_world_questions(question, registered):
    with pytest.raises(SceneProposalError):
        _validate_player_prompt(
            question, npc_aliases=("Mara", "informante") if registered else (),
        )


NARRATIVE = (
    "A névoa se adensa entre os contêineres enquanto a corrente bate contra "
    "o concreto. Um brilho metálico aparece na água escura e desaparece "
    "quando uma onda passa, deixando apenas o reflexo irregular das luzes "
    "distantes sobre o cais."
)


def _admit(question, *, narrative=NARRATIVE, summary="Um brilho aparece na água do cais."):
    proposal = SceneContinuationProposal.model_validate({
        "n": narrative, "o": "unresolved", "l": "Cais municipal",
        "s": summary, "p": [],
        "f": [{"k": "observation", "s": "Um brilho aparece na água.",
               "v": "public", "p": False}],
        "t": [], "r": [], "q": question,
    })
    return validate_scene_continuation(
        proposal, facts=(), current_scene=SceneState(location="Cais municipal"),
        player_input="Observo o cais.",
        protected_secrets=("O Xerife armou uma emboscada no cais.",),
    )


@pytest.mark.parametrize("question", OBSERVED_QUESTIONS)
def test_observed_question_can_close_an_otherwise_valid_proposal(question):
    assert _admit(question).outcome == "unresolved"


@pytest.mark.parametrize("question", OBSERVED_QUESTIONS)
def test_open_question_does_not_authorize_unreported_physical_attempt(question):
    with pytest.raises(SceneProposalError) as caught:
        _admit(question, narrative="Ao forçar o cadeado, o metal range. " + NARRATIVE)
    assert caught.value.code == "scene_player_agency_violation"


@pytest.mark.parametrize("question", OBSERVED_QUESTIONS)
def test_open_question_does_not_waive_secret_in_visible_summary(question):
    with pytest.raises(SceneProposalError) as caught:
        _admit(question, summary="O Xerife armou uma emboscada no cais.")
    assert caught.value.code == "scene_secret_disclosed"


@pytest.mark.parametrize("question", [
    "Qual será sua próxima tentativa ao abrir o cadeado?",
    "Qual próximo passo deseja tomar ao investigar o brilho?",
])
def test_open_step_question_never_presupposes_unreported_execution(question):
    with pytest.raises(SceneProposalError):
        _admit(question)


def test_attempt_question_does_not_address_registered_npc_vocative():
    with pytest.raises(SceneProposalError) as caught:
        _validate_player_prompt(
            "Qual será sua próxima tentativa, Mara?", npc_aliases=("Mara",),
        )
    assert caught.value.evidence["reason"] == "addresses_non_player_actor"
