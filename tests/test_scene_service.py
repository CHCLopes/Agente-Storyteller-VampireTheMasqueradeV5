from copy import deepcopy

from api.scene_service import (
    SceneState,
    ensure_scene_context,
    is_scene_query,
    load_scene_seed,
    scene_fact_text,
    scene_from_context,
    scene_query_response,
    scene_opening_response,
    seed_scene_context,
)
from api.state_service import sync_event_from_context


def test_explicit_scene_seed_reuses_the_tracked_campaign_seed() -> None:
    scene = load_scene_seed()

    assert scene.location == "Elysium"
    assert scene.npcs_present == ("Príncipe", "Xerife")
    assert scene_fact_text(scene) == (
        "Local atual: Elysium. Presenças registradas: Príncipe e Xerife."
    )


def test_scene_read_preserves_context_without_mutation() -> None:
    context = {
        "scene": {
            "location": "  Cais  ",
            "npcs_present": ["Xerife", "xerife", ""],
        }
    }
    original = deepcopy(context)

    scene = scene_from_context(context)

    assert scene == SceneState(location="Cais", npcs_present=("Xerife",))
    assert context == original


def test_missing_scene_remains_unknown_without_mutating_context() -> None:
    context = {"player_sheet": {"vigor": 4}}
    original = deepcopy(context)

    assert scene_from_context(context) is None
    assert ensure_scene_context(context) is None
    assert scene_fact_text(None) == "A localização atual ainda não foi estabelecida."
    assert scene_query_response(None) == "A localização atual ainda não foi estabelecida."
    assert context == original


def test_explicit_seed_creation_is_the_only_operation_that_adds_scene() -> None:
    context = {"player_sheet": {}}

    scene = seed_scene_context(context)

    assert context["scene"] == scene.model_dump(mode="json")
    assert scene.location == "Elysium"


def test_state_projection_keeps_missing_scene_unknown_without_mutation() -> None:
    context = {"player_sheet": {"vigor": 4}}
    original = deepcopy(context)

    event = sync_event_from_context(session_id="session-1", context=context)

    assert event.context.scene is None
    assert event.player_sheet == original
    assert context == original


def test_scene_queries_are_detected_without_treating_movement_as_a_query() -> None:
    assert is_scene_query("Onde estou?")
    assert is_scene_query("Me mostre o lugar")
    assert is_scene_query("Olhar ao redor")
    assert not is_scene_query("Vou até o galpão abandonado")
    assert not is_scene_query("Ataco o Xerife e pergunto onde estou")


def test_scene_query_response_exposes_only_established_facts() -> None:
    response = scene_query_response(
        SceneState(location="Elysium", npcs_present=("Príncipe", "Xerife"))
    )

    assert response == (
        "Você está em Elysium, com Príncipe e Xerife presentes; outros detalhes "
        "observáveis da cena ainda não foram estabelecidos."
    )
    assert "pedra" not in response
    assert "fumaça" not in response


def test_opening_uses_seed_without_inventing_player_history_or_scene_details():
    scene = SceneState(location="Biblioteca", npcs_present=("Lia",))
    original = scene.model_dump()
    opening = scene_opening_response(scene)
    assert opening == (
        "A crônica começa em Biblioteca. Presenças na cena: Lia.\n\n"
        "Você pode observar o lugar, iniciar uma conversa ou declarar outra ação. "
        "O que você faz?"
    )
    assert scene.model_dump() == original
    empty_cast = scene_opening_response(SceneState(location="Cais"))
    assert "Lia" not in empty_cast and "Príncipe" not in empty_cast
    assert "local definido" in scene_opening_response(None)
