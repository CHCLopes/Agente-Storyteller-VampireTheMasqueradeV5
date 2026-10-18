"""The narrator's advertised visibility choices match its accepted authority."""

import pytest
from pydantic import ValidationError

from api.scene_director_service import ProposedSceneFact, SceneContinuationProposal
from api.turn_models import Visibility


ALLOWED_VISIBILITIES = {"public", "player", "storyteller"}


@pytest.mark.parametrize("by_alias, field", [(True, "v"), (False, "visibility")])
def test_proposal_schema_advertises_only_narrator_visible_audiences(by_alias, field):
    schema = SceneContinuationProposal.model_json_schema(by_alias=by_alias)
    definition = schema["$defs"]["ProposedSceneFact"]["properties"][field]
    # A hidden field validator cannot constrain a provider's native JSON schema.
    assert definition["type"] == "string"
    assert set(definition["enum"]) == ALLOWED_VISIBILITIES
    assert definition["default"] == "player"


@pytest.mark.parametrize("visibility", [
    "public", "player", "storyteller",
    Visibility.PUBLIC, Visibility.PLAYER, Visibility.STORYTELLER,
])
@pytest.mark.parametrize("field", ["v", "visibility"])
def test_allowed_visibility_preserves_enum_identity_and_round_trip(visibility, field):
    fact = ProposedSceneFact.model_validate({
        "k": "observation", "s": "Uma porta entreaberta.", field: visibility,
    })
    expected = Visibility(visibility)
    assert fact.visibility is expected
    assert fact.model_dump(mode="json", by_alias=True)["v"] == expected.value
    assert ProposedSceneFact.model_validate_json(fact.model_dump_json(by_alias=True)) == fact


@pytest.mark.parametrize("visibility", ["system", Visibility.SYSTEM, "unknown", None, True])
@pytest.mark.parametrize("field", ["v", "visibility"])
def test_reserved_or_invalid_visibility_is_rejected_not_downgraded(visibility, field):
    with pytest.raises(ValidationError):
        ProposedSceneFact.model_validate({
            "k": "observation", "s": "Uma porta entreaberta.", field: visibility,
        })


def test_omitted_visibility_keeps_legacy_player_default():
    fact = ProposedSceneFact(k="observation", s="Uma porta entreaberta.")
    assert fact.visibility is Visibility.PLAYER


def test_internal_system_audience_is_not_removed_from_canonical_records():
    # Restrict only LLM proposals, not the shared visibility model or saved data.
    from api.turn_models import CanonicalFact

    schema = CanonicalFact.model_json_schema()
    assert "system" in schema["$defs"]["Visibility"]["enum"]
    assert Visibility("system") is Visibility.SYSTEM
