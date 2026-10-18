"""Player aliases in question subjects are not arbitrary NPC authorization."""

import pytest

from api.scene_director_service import SceneProposalError, _validate_player_prompt


@pytest.mark.parametrize("alias", [
    "você", "seu personagem", "sua personagem", "o personagem", "a personagem",
    "Neófito", "Ana Luz",
])
@pytest.mark.parametrize("template", [
    "Como {alias} reage à presença do vulto encapuzado?",
    "Como {alias} responderá diante de Mara?",
    "O que {alias} fará diante de Mara?",
])
def test_alias_in_player_subject_invites_action(alias: str, template: str) -> None:
    _validate_player_prompt(
        template.format(alias=alias),
        player_aliases=("Neófito", "Ana Luz"),
        npc_aliases=("Mara", "vulto encapuzado"),
    )


@pytest.mark.parametrize("registered", [False, True])
@pytest.mark.parametrize("question", [
    "Como Mara reage à presença do seu personagem?",
    "Como a guarda reage à presença do seu personagem?",
    "Como Mara reage enquanto seu personagem espera?",
    "Como Mara decide o que seu personagem faz?",
    "Como a guarda decide o que sua personagem faz?",
    "O que Mara fará diante do seu personagem?",
    "Como a sombra do seu personagem reage?",
    "Como o personagem de Mara reage?",
    "Como Neófito reage à presença de Mara?",
])
def test_player_alias_as_object_or_subordinate_is_not_the_actor(
    question: str, registered: bool,
) -> None:
    with pytest.raises(SceneProposalError):
        _validate_player_prompt(
            question,
            npc_aliases=("Mara", "guarda", "Neófito") if registered else (),
        )


@pytest.mark.parametrize("question", [
    "Seu personagem reage ao vulto encapuzado?",
    "Sua personagem responderá diante de Mara?",
    "O personagem decide esperar por Mara?",
    "O que seu personagem sabe sobre Mara?",
    "O que sua personagem sabe da decisão de Mara?",
    "Como seu personagem reage, Mara?",
])
def test_alias_does_not_allow_closed_knowledge_or_npc_vocative_questions(
    question: str,
) -> None:
    with pytest.raises(SceneProposalError):
        _validate_player_prompt(question, npc_aliases=("Mara",))
