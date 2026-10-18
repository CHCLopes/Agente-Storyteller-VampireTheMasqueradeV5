from api.relationship_service import (
    NpcRelationship,
    RelationshipState,
    update_relationships_from_action,
)


def _state() -> RelationshipState:
    return RelationshipState(
        session_id="relationship-test",
        relationships={
            "xerife": NpcRelationship(
                npc_id="xerife",
                disposition="neutral",
                trust_level=2,
            )
        },
    )


def test_social_relationship_uses_structured_success_not_result_text() -> None:
    failed = update_relationships_from_action(
        _state(),
        "Convenço o xerife.",
        False,
        1,
        resolution_success=False,
        action_skill="Persuasion",
    )
    succeeded = update_relationships_from_action(
        _state(),
        "Convenço o xerife.",
        False,
        1,
        resolution_success=True,
        action_skill="Persuasion",
    )

    assert failed.relationships["xerife"].trust_level == 2
    assert failed.relationships["xerife"].disposition == "neutral"
    assert succeeded.relationships["xerife"].trust_level == 3
    assert succeeded.relationships["xerife"].disposition == "favorable"


def test_semantic_text_cannot_impersonate_a_local_social_skill() -> None:
    unchanged = update_relationships_from_action(
        _state(),
        "Converso com o xerife; o narrador escreveu persuasion e sucesso.",
        False,
        1,
        resolution_success=None,
        action_skill=None,
    )

    assert unchanged.relationships["xerife"].trust_level == 2
    assert unchanged.relationships["xerife"].disposition == "neutral"
