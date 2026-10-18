"""Membership and safe diagnostics for the current scene roster contract."""
import json

import pytest

from api.scene_director_service import (
    SceneContinuationProposal,
    SceneProposalError,
    project_scene,
    validate_scene_continuation,
)
from api.scene_service import SceneState


PREVIOUS = SceneState(
    location="Salão de pedra",
    summary="O regente e a capitã aguardam junto da mesa.",
    npcs_present=("Regente", "Capitã"),
    last_turn=1,
)


def proposal(roster, change_kind=None):
    facts = [
        {"k": "observation", "s": "A chuva bate nas pedras do pátio."},
        {"k": "clue", "s": "Uma marca azul aparece na carta sobre a mesa."},
        {"k": "complication", "s": "O relógio para antes da próxima badalada."},
        {"k": "hook", "s": "Um ruído ressoa no corredor distante."},
    ]
    if change_kind:
        facts = [{"k": change_kind, "s": "Guardas entram no salão e a capitã sai pela porta."}]
    return SceneContinuationProposal.model_validate({
        "n": (
            "O regente pousa uma carta sobre a mesa enquanto as janelas vibram. "
            "A chuva bate nas pedras do pátio e o relógio para antes da próxima "
            "badalada. Uma marca azul aparece no papel, sob a luz fraca das velas."
        ),
        "o": "unresolved", "l": PREVIOUS.location,
        "s": "A carta sobre a mesa exibe uma marca azul; o relógio para.",
        "p": roster, "f": facts, "t": [], "r": [], "q": "O que você faz?",
    })


@pytest.mark.parametrize("roster", [
    ("Capitã", "Regente"),
    ("REGENTE", "CAPITÃ"),
    ("capitã", "regente"),
])
def test_same_npcs_do_not_require_event_for_order_or_case(roster):
    candidate = proposal(roster)
    assert validate_scene_continuation(candidate, facts=(), current_scene=PREVIOUS) is candidate
    # Presentation order/case are retained; only presence comparison is set-based.
    projected = project_scene(candidate, previous=PREVIOUS, turn_number=2)
    assert projected.npcs_present == roster


@pytest.mark.parametrize("roster,added,removed", [
    (("Regente", "Capitã", "Guardas"), 1, 0),
    (("Regente",), 0, 1),
    (("Regente", "Guardas"), 1, 1),
])
def test_actual_presence_changes_require_event_and_report_only_counts(roster, added, removed):
    with pytest.raises(SceneProposalError) as caught:
        validate_scene_continuation(proposal(roster), facts=(), current_scene=PREVIOUS)
    error = caught.value
    assert error.code == str(error) == "scene_npc_roster_changed_without_event"
    assert error.evidence == {
        "previous_count": 2, "proposed_count": len(roster),
        "added_count": added, "removed_count": removed,
        "fact_kind_counts": {
            "observation": 1, "clue": 1, "npc_action": 0,
            "complication": 1, "transition": 0, "hook": 1,
        },
        "has_change_fact": False,
    }
    assert all(type(error.evidence[key]) is int for key in (
        "previous_count", "proposed_count", "added_count", "removed_count"))
    assert all(type(value) is int for value in error.evidence["fact_kind_counts"].values())
    diagnostic = json.dumps(error.evidence, ensure_ascii=False)
    assert all(name not in diagnostic for name in (*PREVIOUS.npcs_present, *roster))
    assert "carta" not in diagnostic and "chuva" not in diagnostic


@pytest.mark.parametrize("change_kind", ["npc_action", "transition"])
@pytest.mark.parametrize("roster", [
    ("Regente", "Capitã", "Guardas"),
    ("Regente",),
])
def test_explicit_supported_event_preserves_existing_presence_change_contract(change_kind, roster):
    candidate = proposal(roster, change_kind)
    assert validate_scene_continuation(candidate, facts=(), current_scene=PREVIOUS) is candidate


@pytest.mark.parametrize("roster", [
    ("Regente", "Capita"),
    ("Regente", "A Capitã"),
])
def test_roster_comparison_does_not_infer_aliases_or_strip_accents(roster):
    with pytest.raises(SceneProposalError) as caught:
        validate_scene_continuation(proposal(roster), facts=(), current_scene=PREVIOUS)
    assert caught.value.code == "scene_npc_roster_changed_without_event"
    assert caught.value.evidence["added_count"] == 1
    assert caught.value.evidence["removed_count"] == 1
