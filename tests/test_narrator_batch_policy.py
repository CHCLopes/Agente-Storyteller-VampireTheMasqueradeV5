"""Bounded regressions from screening, not exemptions for a model or episode."""

import pytest

from api.scene_director_service import (
    SceneContinuationProposal,
    SceneProposalError,
    _action_authorizations,
    _failure_goal_is_granted,
    _unauthorized_action_concepts,
    _validate_player_prompt,
    validate_scene_continuation,
)


@pytest.mark.parametrize("question", [
    "Como você aborda a figura no mezanino?",
    "Como você abordará Mara?",
    "Como você pretende abordar o assunto?",
])
def test_open_approach_question_is_actionable(question):
    _validate_player_prompt(question)


@pytest.mark.parametrize("registered", [False, True])
@pytest.mark.parametrize("question", [
    "Como Mara aborda o que você faz?",
    "Como Mara abordará o que você faz?",
    "Como a informante aborda o que você faz?",
    "Como Mara aborda a figura enquanto você espera?",
])
def test_approach_question_does_not_delegate_npc_action(question, registered):
    with pytest.raises(SceneProposalError) as caught:
        _validate_player_prompt(
            question, npc_aliases=("Mara", "informante") if registered else (),
        )
    assert caught.value.code == "scene_player_prompt_not_actionable"
    assert caught.value.evidence["reason"] == "addresses_non_player_actor"


def test_named_player_can_be_the_actor_of_approach_question():
    _validate_player_prompt("Como Neófito aborda Mara?", player_aliases=("Neófito",))


@pytest.mark.parametrize("question", [
    "Você aborda a figura no mezanino?",
    "O que você sabe da abordagem de Mara?",
])
def test_closed_or_knowledge_question_is_not_an_approach_invitation(question):
    with pytest.raises(SceneProposalError):
        _validate_player_prompt(question)


def test_approach_has_distinct_family_and_target():
    assert set(_action_authorizations("Abordo Mara.")) == {("social", "address")}
    assert _action_authorizations("A abordagem de Mara.") == {}
    assert _unauthorized_action_concepts(
        "aborda Mara", authorized_actions=_action_authorizations("Abordo Mara."),
    ) == []
    assert _unauthorized_action_concepts(
        "aborda João", authorized_actions=_action_authorizations("Abordo Mara."),
    ) == ["social"]


@pytest.mark.parametrize("declared, proposed, concepts", [
    ("Observo Mara.", "aborda Mara", ["social"]),
    ("Abordo Mara.", "aproxima-se de Mara", ["move"]),
    ("Abordo Mara.", "convence Mara", ["social"]),
    ("Abordo Mara.", "ataca Mara", ["combat"]),
])
def test_approach_does_not_authorize_other_actions(declared, proposed, concepts):
    assert _unauthorized_action_concepts(
        proposed, authorized_actions=_action_authorizations(declared),
    ) == concepts


def _failure_proposal(result):
    return SceneContinuationProposal.model_validate({
        "n": (
            f"{result} Ao mesmo tempo, o som de passos pesados ecoa pelo corredor "
            "escuro, cada vez mais perto da grade do arquivo. A lâmpada sobre a "
            "bancada pisca e sombras longas cobrem o chão de concreto."
        ),
        "o": "failure", "l": "Galpão abandonado",
        "s": "O cadeado segue fechado e passos ecoam no corredor.",
        "f": [{"k": "complication", "s": "Passos ecoam no corredor."}],
        "q": "Como você reage ao som dos passos?",
    })


def _admit_failure(proposal):
    return validate_scene_continuation(
        proposal, facts=({"fact_type": "mechanics.resolution", "value": {"is_success": False}},),
        current_scene=None, player_input="Investigo o cadeado.",
    )


@pytest.mark.parametrize("result", [
    "O cadeado não cede.", "O cadeado não cedeu.",
    "A grade não se abre.", "A grade não abriu.",
])
def test_explicit_negated_opening_honors_failure(result):
    assert _admit_failure(_failure_proposal(result)).outcome == "failure"


@pytest.mark.parametrize("result", [
    "O cadeado não cede, mas a grade abre e revela o arquivo.",
    "O cadeado não cede. A prova foi encontrada sobre a bancada.",
])
def test_failure_marker_does_not_allow_a_granted_goal_elsewhere(result):
    with pytest.raises(SceneProposalError, match="scene_failure_granted_goal"):
        _admit_failure(_failure_proposal(result))


def test_a_failure_mentioned_only_in_summary_is_insufficient():
    with pytest.raises(SceneProposalError, match="scene_failure_not_honored"):
        _admit_failure(_failure_proposal("A lâmpada ilumina o cadeado."))


def test_failed_attempt_summary_does_not_assert_achieved_goal():
    proposal = _failure_proposal("O cadeado não cede.").model_copy(update={
        "scene_summary": "Tentativa de abrir o cadeado falha enquanto ameaças se aproximam.",
    })
    assert _admit_failure(proposal) is proposal


@pytest.mark.parametrize("text", [
    "tentativa de abrir o cadeado nao falha",
    "tentativa de abrir o cadeado revela a prova, mas falha",
    "tentativa de abrir o cadeado falha, mas a prova foi encontrada",
    "tentativa de abrir o cadeado falha. o arquivo abre",
])
def test_failed_attempt_does_not_hide_a_grant_or_negated_failure(text):
    assert _failure_goal_is_granted(text)


def test_h6_explains_existing_visibility_identity_and_pending_contract():
    from api.orchestrator_service import STORYTELLER_SYSTEM_PROMPT
    from scripts.evaluate_narrator_models import load_storyteller_prompt

    prompt = load_storyteller_prompt()
    assert prompt == STORYTELLER_SYSTEM_PROMPT
    assert len(prompt.split()) <= 400
    assert "`player`/`public` para fatos narrados" in prompt
    assert "`storyteller` nunca aparece em campos visíveis" in prompt
    assert "`observation`/`clue` exigem `f[].p=true`" in prompt
    assert "copie o local atual" in prompt
    assert "mudanças exigem `npc_action` ou `transition`" in prompt
    assert "nem implicitamente por dedos, força ou peso" in prompt
