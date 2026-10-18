"""Recognizing a verification question must not grant other actions or actors."""

import pytest

from api.scene_director_service import (
    SceneProposalError,
    _action_authorizations,
    _unauthorized_action_concepts,
    _validate_player_prompt,
)


@pytest.mark.parametrize(
    "question",
    [
        "Como você verifica suas condições imediatas?",
        "Como você verificará suas condições imediatas?",
        "Como você vai verificar suas condições imediatas?",
        "Como você pretende verificar a saída?",
    ],
)
def test_open_verification_question_invites_the_player_action(question: str) -> None:
    _validate_player_prompt(question)


@pytest.mark.parametrize("registered_npc", [False, True])
@pytest.mark.parametrize("choice", [
    "sua próxima atitude", "sua atitude", "sua próxima ação", "sua escolha",
    "sua decisão", "seu próximo passo", "seu próximo movimento",
])
def test_possessive_player_choice_before_npc_context_is_actionable(
    choice: str, registered_npc: bool,
) -> None:
    _validate_player_prompt(
        f"Qual será {choice} diante da hesitação de Mara?",
        npc_aliases=("Mara",) if registered_npc else (),
    )


@pytest.mark.parametrize("registered_npc", [False, True])
@pytest.mark.parametrize("question", [
    "Qual será a próxima atitude de Mara?",
    "Como Mara decide sua próxima atitude?",
    "Como a informante decide sua próxima atitude?",
    "Qual será a próxima atitude de Mara enquanto você espera?",
    "Como Mara reage à sua próxima atitude?",
    "O que você sabe sobre a próxima atitude de Mara?",
    "Sua próxima atitude será esperar por Mara?",
])
def test_possessive_choice_does_not_authorize_npc_decisions_or_closed_questions(
    question: str, registered_npc: bool,
) -> None:
    with pytest.raises(SceneProposalError):
        _validate_player_prompt(
            question, npc_aliases=("Mara", "informante") if registered_npc else (),
        )


@pytest.mark.parametrize("question", [
    "Qual será sua próxima atitude, Mara?",
    "Qual será sua decisão, Mara?",
    "Qual será sua próxima ação, Mara, enquanto você espera?",
    "Qual é sua escolha, João?",
    "Qual será sua decisão, Mara Luz?",
    "Qual será sua próxima atitude, Mara, diante do cadeado?",
    "Qual será sua escolha, João, diante da porta?",
])
def test_possessive_question_cannot_address_an_npc_by_vocative(question: str) -> None:
    with pytest.raises(SceneProposalError) as caught:
        _validate_player_prompt(question, npc_aliases=("Mara", "João", "Mara Luz"))
    assert caught.value.code == "scene_player_prompt_not_actionable"
    assert caught.value.evidence["reason"] == "addresses_non_player_actor"


@pytest.mark.parametrize("question", [
    "Qual será sua próxima atitude diante de Mara?",
    "Qual será sua próxima atitude para ajudar Mara?",
    "Qual é sua decisão diante de João?",
    "Qual será sua próxima atitude, diante de Mara?",
])
def test_npc_in_question_context_is_not_a_vocative(question: str) -> None:
    _validate_player_prompt(question, npc_aliases=("Mara", "João"))


def test_possessive_question_can_address_the_named_player_by_vocative() -> None:
    _validate_player_prompt(
        "Qual será sua próxima atitude, Mara?", player_aliases=("Mara",),
        npc_aliases=("João",),
    )
    _validate_player_prompt(
        "Qual será sua próxima atitude, Mara, diante do cadeado?",
        player_aliases=("Mara",), npc_aliases=("João",),
    )


@pytest.mark.parametrize(
    "question",
    [
        "Você verifica suas condições imediatas?",
        "Você verificará a saída?",
        "O que você sabe da verificação de Mara?",
        "O que você sabe sobre a verificação da saída?",
    ],
)
def test_closed_or_knowledge_question_is_not_mistaken_for_verification_action(
    question: str,
) -> None:
    with pytest.raises(SceneProposalError) as caught:
        _validate_player_prompt(question)

    assert caught.value.code in {
        "scene_player_prompt_not_open", "scene_player_prompt_not_actionable"
    }


@pytest.mark.parametrize("registered_npc", [False, True])
@pytest.mark.parametrize(
    ("question", "npc"),
    [
        ("Como Mara verifica o que você faz?", "Mara"),
        ("Como a guarda verifica o que você faz?", "guarda"),
        ("Como Mara verifica a saída enquanto você espera?", "Mara"),
        ("Como a guarda verifica a saída enquanto você espera?", "guarda"),
    ],
)
def test_embedded_player_cue_does_not_change_the_main_verifying_actor(
    question: str, npc: str, registered_npc: bool
) -> None:
    with pytest.raises(SceneProposalError) as caught:
        _validate_player_prompt(question, npc_aliases=(npc,) if registered_npc else ())

    assert caught.value.code == "scene_player_prompt_not_actionable"
    assert caught.value.evidence["reason"] == "addresses_non_player_actor"


def test_verification_has_its_own_action_family() -> None:
    assert set(_action_authorizations("Verifico a porta.")) == {("inspect", "verify")}
    assert set(_action_authorizations("Investigo a porta.")) == {("inspect", "inspect_general")}
    assert set(_action_authorizations("Observo a porta.")) == {("inspect", "observe")}
    assert _action_authorizations("A verificação da porta.") == {}


@pytest.mark.parametrize(
    ("declared", "proposed", "expected"),
    [
        ("Verifico a porta.", "verifica a porta", []),
        ("Verifico a porta.", "examina a porta", ["inspect"]),
        ("Verifico a porta.", "vasculha a porta", ["inspect"]),
        ("Verifico a porta.", "revista Mara", ["inspect"]),
        ("Verifico a porta.", "abre a porta", ["interact"]),
        ("Investigo a porta.", "verifica a porta", ["inspect"]),
        ("Observo a porta.", "verifica a porta", ["inspect"]),
    ],
)
def test_verification_does_not_expand_other_action_permissions(
    declared: str, proposed: str, expected: list[str]
) -> None:
    assert _unauthorized_action_concepts(
        proposed, authorized_actions=_action_authorizations(declared)
    ) == expected
