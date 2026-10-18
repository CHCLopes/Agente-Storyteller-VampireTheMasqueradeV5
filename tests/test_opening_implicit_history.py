"""An actionable question must not admit invented history in a compact summary."""

import pytest

from api.scene_director_service import (
    SceneContinuationProposal, SceneProposalError, validate_scene_continuation,
)


def _opening(summary, question="Como você verifica suas condições imediatas?"):
    # Synthetic response from the 2026-09-05 opening probe; independent of logs.
    return SceneContinuationProposal.model_validate({
        "n": (
            "O cheiro acre de pólvora queimada e ozônio atinge suas narinas, "
            "misturado ao mofo antigo. Gota d’água cai num metal enferrujado, "
            "ecoando amplamente no silêncio absoluto. A escuridão ao redor parece "
            "densa, quase sólida, espremendo seus pulmões enquanto o coração "
            "dispara num ritmo frenético e solitário."
        ),
        "o": "unresolved", "l": "Subsolo industrial em ruínas", "s": summary,
        "p": [],
        "f": [{"k": "observation", "s": "Cheiro de pólvora e ozônio impregna o ar pesado."}],
        "t": ["Estabelecer localização exata", "Identificar origem do cheiro de pólvora"],
        "r": [], "q": question,
    })


@pytest.mark.parametrize("summary", [
    "Despertar na escuridão de um subsolo industrial, sem memória de chegada.",
    "Acordar no subsolo industrial sob luzes vermelhas.",
    "Amnésia no subsolo industrial, nenhuma lembrança da chegada.",
    "Sem memória da chegada ao subsolo industrial.",
    "Nenhuma lembrança de como chegou ao subsolo industrial.",
])
def test_implicit_opening_history_is_rejected_after_valid_question(summary):
    with pytest.raises(SceneProposalError) as caught:
        validate_scene_continuation(
            _opening(summary), facts=(), current_scene=None, player_input="Onde estou?",
        )
    assert caught.value.code == "scene_player_agency_violation"
    assert caught.value.evidence["field"] == "scene_summary"
    assert caught.value.evidence["rule"] == "unestablished_opening_history"
    assert summary not in str(caught.value.evidence)


@pytest.mark.parametrize("summary", [
    "O subsolo escuro tem cheiro de pólvora e ozônio e uma goteira sobre metal.",
    "O despertar de Mara no subsolo é acompanhado pelo ruído da goteira.",
    "Amnésia de Mara após a chegada ao subsolo industrial.",
    "O despertar do motor provoca um ruído no subsolo industrial.",
    "A lenda descreve o despertar no subsolo e a perda de memória.",
    'O livro "Despertar no subsolo" repousa no chão úmido.',
    "Não houve despertar no subsolo industrial; há somente o ruído da goteira.",
    "Se ocorrer um despertar no subsolo industrial, a cena poderá mudar.",
    "Despertar no subsolo é o título do livro.",
    "Despertar no subsolo não ocorreu.",
    "Despertar no subsolo seria uma possibilidade futura.",
    "Amnésia no subsolo afeta apenas Mara.",
])
def test_environment_npc_lore_and_non_assertive_history_are_not_assigned_to_player(summary):
    proposal = _opening(summary)
    assert validate_scene_continuation(
        proposal, facts=(), current_scene=None, player_input="Onde estou?",
        npc_aliases=("Mara",),
    ) is proposal


@pytest.mark.parametrize("player_input", [
    "Desperto no subsolo industrial, sem memória de como cheguei.",
    "Eu acordei no subsolo industrial. Não me lembro de como cheguei.",
])
def test_explicit_player_history_can_ground_waking_and_amnesia(player_input):
    proposal = _opening("Despertar no subsolo industrial, sem memória da chegada.")
    assert validate_scene_continuation(
        proposal, facts=(), current_scene=None, player_input=player_input,
    ) is proposal


def test_declared_waking_does_not_authorize_amnesia():
    with pytest.raises(SceneProposalError) as caught:
        validate_scene_continuation(
            _opening("Despertar no subsolo industrial, sem memória da chegada."),
            facts=(), current_scene=None, player_input="Acordei no subsolo industrial.",
        )
    assert caught.value.code == "scene_player_agency_violation"
    assert caught.value.evidence["history_concepts"] == ["memory_loss"]


@pytest.mark.parametrize("player_input", [
    "Eu acordei no subsolo, Mara está sem memória da chegada.",
    "Eu acordei no subsolo e Mara está sem memória da chegada.",
    "Eu acordei no subsolo enquanto Mara fala sobre amnésia.",
])
def test_another_actors_memory_loss_does_not_ground_the_players(player_input):
    with pytest.raises(SceneProposalError) as caught:
        validate_scene_continuation(
            _opening("Despertar no subsolo industrial, sem memória da chegada."),
            facts=(), current_scene=None, player_input=player_input,
        )
    assert caught.value.evidence["history_concepts"] == ["memory_loss"]


@pytest.mark.parametrize("declaration", [
    "Tenho um amigo com amnésia.",
    "Tenho um amigo, sem memória da chegada.",
    "Tenho medo de ficar sem memória.",
    "Acordei sem amnésia no subsolo.",
])
def test_memory_mention_or_absence_of_amnesia_is_not_player_memory_loss(declaration):
    with pytest.raises(SceneProposalError) as caught:
        validate_scene_continuation(
            _opening("Amnésia no subsolo industrial, nenhuma lembrança da chegada."),
            facts=(), current_scene=None, player_input=declaration,
        )
    assert caught.value.evidence["history_concepts"] == ["memory_loss"]


@pytest.mark.parametrize("player_input", [
    "Não despertei no subsolo.",
    "Se eu despertar no subsolo, vou observar.",
    "Eu acordei no subsolo?",
    "Mara acordou no subsolo, sem memória da chegada.",
    'O livro diz: "Eu acordei no subsolo, sem memória da chegada."',
])
def test_negation_hypothesis_question_npc_or_quote_does_not_grant_player_history(player_input):
    with pytest.raises(SceneProposalError) as caught:
        validate_scene_continuation(
            _opening("Despertar no subsolo industrial, sem memória da chegada."),
            facts=(), current_scene=None, player_input=player_input,
        )
    assert caught.value.code == "scene_player_agency_violation"
    assert caught.value.evidence["rule"] == "unestablished_opening_history"
