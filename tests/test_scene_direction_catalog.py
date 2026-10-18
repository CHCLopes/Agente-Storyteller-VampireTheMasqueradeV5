from api.scene_direction_catalog import MARA_DIRECTION, mara_profile, mara_scene_options
from api.scene_resolution_service import SceneTurnKind
from api.scene_service import SceneState


def test_mara_catalog_is_keywords_without_finished_narrative() -> None:
    assert MARA_DIRECTION.core_traits == ("protective_archive", "observant", "reserved")
    assert MARA_DIRECTION.stable_objectives == ("preserve_archive",)
    assert all("." not in topic.effect_key or topic.effect_key.startswith("mara.") for topic in MARA_DIRECTION.topics)
    assert not hasattr(MARA_DIRECTION, "dialogue")
    assert not hasattr(MARA_DIRECTION, "narrative")


def test_place_topic_builds_semantic_options_with_a_reaction_spectrum() -> None:
    options = mara_scene_options(
        scene=SceneState(location="Arquivo", npcs_present=("Mara",)),
        player_input="Mara, fale sobre este lugar.",
        turn_kind=SceneTurnKind.DIALOGUE,
    )

    assert len(options) == 1
    assert options[0].effect_keys == ("mara.answers.place_context",)
    assert "npc.mara.core.protective_archive" in options[0].guidance_keys
    assert "npc.mara.reaction.partial_clue" in options[0].guidance_keys
    assert "story.advance.help" in options[0].guidance_keys


def test_catalog_does_not_claim_scenes_or_npcs_outside_its_scope() -> None:
    assert mara_scene_options(
        scene=SceneState(location="Cais", npcs_present=("Mara",)),
        player_input="Fale deste lugar.",
        turn_kind=SceneTurnKind.DIALOGUE,
    ) == ()
    assert mara_scene_options(
        scene=SceneState(location="Arquivo", npcs_present=("Xerife",)),
        player_input="Fale deste lugar.",
        turn_kind=SceneTurnKind.DIALOGUE,
    ) == ()


def test_profile_separates_stable_limits_from_current_objectives() -> None:
    profile = mara_profile(disposition="favorable", trust=4)

    assert "reveal_founder_identity_directly" in profile.limits
    assert profile.local_goal == "evaluate_visitor | protect_index"
    assert profile.relationship_disposition == "favorable"
    assert profile.relationship_trust == 4
