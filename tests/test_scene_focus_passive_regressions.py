"""An environmental adjective cannot authorize the player's next action."""

import pytest

from api import scene_director_service as director

from api.scene_director_service import (
    SceneContinuationProposal,
    SceneProposalError,
    _action_authorizations,
    _action_signatures,
    _validate_declared_player_actions,
    _validate_implicit_player_contact,
)


OBSERVED_DESCRIPTION = (
    "Ao vasculhar o galpão abandonado, você encontra uma porta de ferro "
    "enferrujada parcialmente oculta por entulhos."
)
OBSERVED_PUSH = (
    "Ao empurrá‑la, revela uma escada de madeira que desce silenciosamente ao mezanino."
)
HYPHENS = ["-", "\u2010", "\u2011"]


def _proposal(narrative, npcs=()):
    return SceneContinuationProposal.model_validate({
        "n": narrative + " Uma corrente vibra contra a parede.",
        "o": "unresolved", "l": "Galpão abandonado",
        "s": "Entulhos se acumulam diante da porta do galpão.",
        "p": list(npcs),
        "f": [{"k": "observation", "s": "Uma corrente vibra contra a parede.", "p": True}],
        "t": [], "r": [],
        "q": "O que você faz agora?",
    })


def _declared(proposal, action="Investigo o galpão abandonado."):
    _validate_declared_player_actions(
        proposal, authorized_actions=_action_authorizations(action),
        player_aliases=("Neófito",), npc_aliases=proposal.npcs_present,
    )


def _implicit(proposal, action="Investigo o galpão abandonado."):
    _validate_implicit_player_contact(proposal, authorized_actions=_action_authorizations(action))


@pytest.mark.parametrize("description", [
    OBSERVED_DESCRIPTION,
    "Você encontra uma porta parcialmente oculta por entulhos.",
    "Você encontra a porta lateral oculta por entulhos.",
    "Você vê uma porta parcialmente oculta por entulhos.",
    "Neófito encontra uma porta parcialmente oculta por entulhos.",
])
def test_physical_cover_of_a_found_door_is_not_a_player_concealment(description):
    _declared(_proposal(description))


@pytest.mark.parametrize("description", [
    "Você oculta a porta com entulhos.",
    "Você encontra a porta e a oculta com entulhos.",
    "Você encontra uma porta parcialmente oculta por você.",
    "Você vê uma porta parcialmente oculta por você.",
    "Você vê uma porta oculta pelo seu personagem.",
    "Você encontra uma porta oculta por Neófito.",
    "Você encontra uma porta oculta por suas mãos.",
])
def test_explicit_player_concealment_is_not_laundered_as_environment(description):
    with pytest.raises(SceneProposalError) as caught:
        _declared(_proposal(description))
    assert caught.value.code == "scene_player_agency_violation"
    assert "conceal" in caught.value.evidence["unauthorized_concepts"]


@pytest.mark.parametrize("description", [
    "Você encontra uma porta oculta por entulhos e a empurra.",
    "Você encontra uma porta oculta por entulhos. Você empurra a porta.",
])
def test_adjective_disambiguation_does_not_waive_a_later_explicit_push(description):
    with pytest.raises(SceneProposalError) as caught:
        _declared(_proposal(description))
    assert caught.value.code == "scene_player_agency_violation"
    assert caught.value.evidence["unauthorized_concepts"] == ["interact"]


@pytest.mark.parametrize("hyphen", HYPHENS)
def test_hyphenated_push_already_has_a_push_signature(hyphen):
    # The observed hyphen is U+2011, not ASCII. Recognition of the verb stem
    # must stay equivalent; the missing temporal/actor check is a separate bug.
    assert ("interact", "push") in _action_signatures(f"empurrá{hyphen}la")


@pytest.mark.parametrize("hyphen", HYPHENS)
def test_temporal_clitic_push_is_not_authorized_by_investigation(hyphen):
    proposal = _proposal(
        "Uma porta de ferro está diante da bancada. "
        f"Ao empurrá{hyphen}la, a dobradiça range e o rádio chia."
    )
    with pytest.raises(SceneProposalError) as caught:
        _implicit(proposal)
    assert caught.value.code == "scene_player_agency_violation"
    assert caught.value.evidence["unauthorized_concepts"] == ["interact"]


def test_observed_description_can_pass_but_the_observed_undeclared_push_cannot():
    proposal = _proposal(OBSERVED_DESCRIPTION + " " + OBSERVED_PUSH)
    _declared(proposal)
    with pytest.raises(SceneProposalError) as caught:
        _implicit(proposal)
    assert caught.value.code == "scene_player_agency_violation"
    assert caught.value.evidence["unauthorized_concepts"] == ["interact"]


@pytest.mark.parametrize("hyphen", HYPHENS)
def test_declared_push_with_its_explicit_target_remains_allowed(hyphen):
    proposal = _proposal(
        "Uma porta está diante da bancada. "
        f"Ao empurrá{hyphen}la, a dobradiça range e o rádio chia."
    )
    _implicit(proposal, "Empurro a porta.")


@pytest.mark.parametrize("declared", ["Empurro a parede.", "Toco a porta."])
def test_clitic_must_not_transfer_another_target_or_action_family(declared):
    proposal = _proposal(
        "Uma porta está diante da bancada. Ao empurrá‑la, a dobradiça range."
    )
    with pytest.raises(SceneProposalError) as caught:
        _implicit(proposal, declared)
    assert caught.value.evidence["unauthorized_concepts"] == ["interact"]


def test_named_npc_owns_its_own_temporal_push():
    proposal = _proposal(
        "Mara se aproxima da porta. Ao empurrá‑la, a dobradiça range.", npcs=("Mara",),
    )
    _implicit(proposal)


@pytest.mark.parametrize("coordination", [
    "e por você", "e pelo seu personagem", "e por suas mãos", "e você", ", por você",
])
def test_physical_cover_exception_cannot_hide_a_coordinated_player_agent(monkeypatch, coordination):
    text = f"Você encontra uma porta oculta por entulhos {coordination}.".replace(" ,", ",")
    proposal = _proposal(text)
    # Isolate the new exception: without it, this player-owned concealment was
    # already rejected. The physical-cause branch must not introduce a bypass.
    with monkeypatch.context() as previous_behavior:
        previous_behavior.setattr(director, "_is_found_physical_cover", lambda *_: False)
        with pytest.raises(SceneProposalError):
            _declared(proposal)
    with pytest.raises(SceneProposalError) as caught:
        _declared(proposal)
    assert "conceal" in caught.value.evidence["unauthorized_concepts"]


@pytest.mark.parametrize("player_subject", ["você", "seu personagem", "sua personagem", "o personagem", "a personagem"])
def test_previous_npc_cannot_own_a_temporal_push_with_a_new_player_subject(player_subject):
    proposal = _proposal(
        "Mara se aproxima da porta. "
        f"Ao empurrá-la, {player_subject} sente uma vibração.", npcs=("Mara",),
    )
    _declared(proposal)
    with pytest.raises(SceneProposalError) as caught:
        _implicit(proposal)
    assert caught.value.evidence["unauthorized_concepts"] == ["interact"]


@pytest.mark.parametrize("introduced,declared", [
    ("frontal", "lateral"), ("lateral", "frontal"),
])
def test_clitic_antecedent_preserves_the_barriers_qualifier(introduced, declared):
    proposal = _proposal(
        f"Uma porta {introduced} está diante da bancada. "
        "Ao empurrá-la, a dobradiça range."
    )
    with pytest.raises(SceneProposalError) as caught:
        _implicit(proposal, f"Empurro a porta {declared}.")
    assert caught.value.evidence["unauthorized_concepts"] == ["interact"]


@pytest.mark.parametrize("qualifier", ["frontal", "lateral"])
def test_clitic_antecedent_allows_the_same_declared_qualified_barrier(qualifier):
    proposal = _proposal(
        f"Uma porta {qualifier} está diante da bancada. "
        "Ao empurrá-la, a dobradiça range."
    )
    _implicit(proposal, f"Empurro a porta {qualifier}.")


@pytest.mark.parametrize("previous", [
    "", "Um rádio está diante da bancada. ",
    "A porta frontal fica ao lado da porta lateral. ",
])
def test_missing_or_ambiguous_clitic_antecedent_is_not_push_authority(previous):
    proposal = _proposal(previous + "Ao empurrá-la, a dobradiça range.")
    with pytest.raises(SceneProposalError) as caught:
        _implicit(proposal, "Empurro a porta frontal.")
    assert caught.value.evidence["unauthorized_concepts"] == ["interact"]
