"""The experimental actor metadata binds roster changes, not arbitrary prose."""

import pytest
from pydantic import ValidationError

from api.scene_director_service import SceneContinuationProposal, SceneProposalError
from api.scene_service import SceneState
from scripts.narrator_actor_contract import (
    FocusedSceneContinuationProposal,
    FocusedSceneFact,
    SceneActor,
    actor_identity_key,
    validate_actor_coherence,
)


def _fact(name="Mara", presence="present", *, kind="npc_action", visibility="player", summary=None):
    return {
        "k": kind, "s": summary or f"{name} ajusta a lanterna.", "v": visibility,
        "a": [{"n": name, "p": presence}],
    }


def _proposal(*, facts=None, roster=("Mara",), narrative=None, **updates):
    payload = {
        "n": narrative or "Mara ajusta a lanterna enquanto a chuva bate na janela. O rádio chia na bancada e uma corrente balança junto à porta.",
        "o": "unresolved", "l": "Oficina", "s": "A chuva bate na janela da oficina.",
        "p": list(roster), "f": facts if facts is not None else [_fact()],
        "t": [], "r": [], "q": "O que você faz agora?",
    }
    payload.update(updates)
    return FocusedSceneContinuationProposal.model_validate(payload)


def _check(proposal, *, previous=("Mara",), players=("Neófito",)):
    scene = SceneState(location="Oficina", npcs_present=previous) if previous is not None else None
    return validate_actor_coherence(proposal, scene, player_aliases=players)


def _reject(proposal, code, **context):
    with pytest.raises(SceneProposalError) as caught:
        _check(proposal, **context)
    assert caught.value.code == code
    assert set(caught.value.evidence) == {"field", "rule"}
    return caught.value


def test_actor_array_is_required_for_every_fact():
    with pytest.raises(ValidationError):
        FocusedSceneFact.model_validate({"k": "observation", "s": "Uma corrente oscila."})
    schema = FocusedSceneFact.model_json_schema(by_alias=True)
    assert "a" in schema["required"]


@pytest.mark.parametrize("presence", ["present", "departed", "offscene"])
def test_actor_wire_contract_is_explicit_and_round_trips(presence):
    actor = SceneActor.model_validate({"n": "  Mara  ", "p": presence})
    assert actor.model_dump(by_alias=True) == {"n": "Mara", "p": presence}


@pytest.mark.parametrize("actor", [
    {"n": "Mara"}, {"p": "present"}, {"n": "Mara", "p": "secret"},
    {"n": "Mara", "p": "present", "id": "invented"},
    {"n": " ", "p": "present"}, {"n": "---", "p": "present"},
])
def test_actor_schema_rejects_missing_fields_unknown_presence_and_ids(actor):
    with pytest.raises(ValidationError):
        SceneActor.model_validate(actor)


def test_legacy_runtime_contract_does_not_silently_accept_actor_extension():
    wire = _proposal().model_dump(by_alias=True)
    with pytest.raises(ValidationError):
        SceneContinuationProposal.model_validate(wire)


def test_existing_actor_with_own_fact_is_accepted_unchanged():
    proposal = _proposal()
    before = proposal.model_dump()
    assert _check(proposal) is proposal
    assert proposal.model_dump() == before


def test_unknown_footsteps_do_not_force_an_identified_npc():
    proposal = _proposal(
        facts=[{"k": "observation", "s": "Passos ressoam além da porta.", "a": []}],
        narrative="Passos ressoam além da porta enquanto a chuva cobre os ruídos da rua. Uma corrente bate na parede.",
    )
    assert _check(proposal) is proposal


def test_npc_action_cannot_omit_actor_even_if_roster_does_not_change():
    fact = _fact()
    fact["a"] = []
    _reject(_proposal(facts=[fact]), "scene_actor_missing")


@pytest.mark.parametrize("name", ["Neófito", "neofito", "O Neófito", "Você", "seu personagem", "jogador"])
def test_player_aliases_are_not_npc_actor_identities(name):
    proposal = _proposal(facts=[_fact(name)], roster=(name,), narrative=f"{name} ajusta a lanterna e a chuva bate contra a janela da oficina.")
    _reject(proposal, "scene_actor_identity_invalid", previous=())


def test_duplicate_actor_reference_is_not_silently_deduplicated():
    fact = _fact()
    fact["a"].append({"n": "MARA", "p": "present"})
    _reject(_proposal(facts=[fact]), "scene_actor_duplicate")


@pytest.mark.parametrize("narrative,summary", [
    ("Tamara ajusta a lanterna e a chuva bate na janela da oficina.", "Mara ajusta a lanterna."),
    ("Mara-Jade ajusta a lanterna e a chuva bate na janela da oficina.", "Mara ajusta a lanterna."),
    ("Mara ajusta a lanterna e a chuva bate na janela da oficina.", "Tamara ajusta a lanterna."),
    ("Mara ajusta a lanterna e a chuva bate na janela da oficina.", "Ela ajusta a lanterna."),
])
def test_visible_actor_requires_literal_label_in_fact_and_narrative(narrative, summary):
    _reject(_proposal(facts=[_fact(summary=summary)], narrative=narrative), "scene_actor_not_grounded")


def test_label_matching_normalizes_unicode_case_and_spaces_without_inventing_aliases():
    proposal = _proposal(
        facts=[_fact("José", summary="JOSE ajusta a lanterna.")], roster=("José",),
        narrative="Jose\u0301 ajusta a lanterna enquanto a chuva bate na janela da oficina.",
    )
    assert _check(proposal, previous=("José",)) is proposal


def test_label_alias_not_supplied_by_context_is_not_fuzzy_matched():
    _reject(_proposal(facts=[_fact("A informante")]), "scene_actor_not_grounded")


def test_distinct_accented_roster_identity_cannot_be_removed_by_normalization():
    _reject(_proposal(), "scene_actor_roster_mismatch", previous=("Mara", "Mará"))


def test_actor_reference_cannot_fuzzy_match_differently_named_roster_member():
    _reject(_proposal(roster=("Mará",)), "scene_actor_roster_mismatch", previous=("Mará",))


def test_canonically_equivalent_unicode_actor_reference_matches_roster_identity():
    proposal = _proposal(
        facts=[_fact("Jose\u0301")], roster=("José",),
        narrative="José ajusta a lanterna enquanto a chuva bate na janela da oficina.",
    )
    assert _check(proposal, previous=("José",)) is proposal


def test_public_actor_identity_helper_preserves_distinct_labels():
    assert actor_identity_key("  JOSE\u0301  ") == actor_identity_key("José")
    assert actor_identity_key("José") != actor_identity_key("Jose")


def test_new_present_actor_requires_own_visible_event():
    proposal = _proposal(facts=[_fact("Ivo")], roster=("Mara", "Ivo"), narrative="Ivo ajusta a lanterna enquanto a chuva bate na janela da oficina.")
    assert _check(proposal) is proposal


def test_new_present_actor_can_be_established_at_opening_without_invented_arrival():
    proposal = _proposal()
    assert _check(proposal, previous=None) is proposal


def test_unrelated_npc_event_does_not_cover_an_added_roster_identity():
    _reject(_proposal(roster=("Mara", "Ivo")), "scene_actor_roster_mismatch")


def test_actor_label_cannot_be_substituted_to_cover_the_wrong_event():
    fact = _fact()
    fact["a"][0]["n"] = "Ivo"
    _reject(_proposal(facts=[fact], roster=("Mara", "Ivo")), "scene_actor_not_grounded")


def test_present_event_actor_cannot_be_missing_from_roster():
    _reject(_proposal(roster=()), "scene_actor_roster_mismatch")


def test_observation_metadata_does_not_turn_unrelated_npc_event_into_arrival():
    proposal = _proposal(
        facts=[_fact(), _fact("Ivo", kind="observation")], roster=("Mara", "Ivo"),
        narrative="Mara ajusta a lanterna. Ivo examina a janela enquanto a chuva bate na oficina.",
    )
    _reject(proposal, "scene_actor_transition_missing")


@pytest.mark.parametrize("kind", ["observation", "clue"])
@pytest.mark.parametrize("event_first", [False, True])
def test_new_actor_companion_fact_is_justified_by_own_event_in_either_order(kind, event_first):
    event = _fact("Ivo", summary="Ivo acende uma lanterna.")
    companion = _fact("Ivo", kind=kind, summary="Ivo segura uma lanterna azul.")
    proposal = _proposal(
        facts=[event, companion] if event_first else [companion, event],
        roster=("Mara", "Ivo"),
        narrative="Ivo acende uma lanterna azul enquanto a chuva bate na janela da oficina.",
    )
    assert _check(proposal) is proposal


@pytest.mark.parametrize("kind", ["observation", "clue"])
def test_companion_fact_alone_cannot_introduce_new_actor(kind):
    proposal = _proposal(
        facts=[_fact("Ivo", kind=kind)], roster=("Mara", "Ivo"),
        narrative="Ivo ajusta a lanterna enquanto a chuva bate na janela da oficina.",
    )
    _reject(proposal, "scene_actor_transition_missing")


@pytest.mark.parametrize("event_first", [False, True])
def test_departure_companion_fact_is_justified_by_own_event_in_either_order(event_first):
    event = _fact(presence="departed", summary="Mara sai da oficina.")
    companion = _fact(presence="departed", kind="observation", summary="Mara deixa a porta entreaberta.")
    proposal = _proposal(
        facts=[event, companion] if event_first else [companion, event], roster=(),
        narrative="Mara sai da oficina e deixa a porta entreaberta. A corrente oscila enquanto a chuva bate na janela.",
    )
    assert _check(proposal) is proposal


def test_matching_departure_removes_only_that_previously_present_actor():
    proposal = _proposal(facts=[_fact(presence="departed", summary="Mara sai da oficina.")], roster=(), narrative="Mara sai da oficina enquanto a chuva bate na janela. A corrente continua oscilando junto à porta.")
    assert _check(proposal) is proposal


def test_unestablished_actor_cannot_be_declared_departed():
    proposal = _proposal(facts=[_fact(presence="departed")], roster=())
    _reject(proposal, "scene_actor_departure_unestablished", previous=())


def test_departed_actor_cannot_remain_in_final_roster():
    _reject(_proposal(facts=[_fact(presence="departed")]), "scene_actor_roster_mismatch")


def test_unrelated_event_does_not_remove_another_npc():
    _reject(_proposal(), "scene_actor_roster_mismatch", previous=("Mara", "Ivo"))


def test_remote_actor_does_not_have_to_enter_local_roster():
    proposal = _proposal(facts=[_fact("Ivo", presence="offscene", summary="Ivo fala pelo rádio.")], narrative="Ivo fala pelo rádio enquanto a chuva bate na janela. A corrente oscila junto à porta.")
    assert _check(proposal) is proposal


def test_remote_actor_cannot_also_be_locally_present():
    proposal = _proposal(facts=[_fact(presence="offscene")])
    _reject(proposal, "scene_actor_roster_mismatch")


def test_remote_tag_does_not_replace_a_missing_departure_event():
    proposal = _proposal(facts=[_fact(presence="offscene")], roster=())
    _reject(proposal, "scene_actor_roster_mismatch")


def test_order_only_roster_change_is_accepted_without_modifying_order():
    proposal = _proposal(roster=("Ivo", "Mara"))
    assert _check(proposal, previous=("Mara", "Ivo")) is proposal
    assert proposal.npcs_present == ("Ivo", "Mara")


def test_actor_presence_is_final_state_not_two_conflicting_sequence_labels():
    proposal = _proposal(facts=[_fact(), _fact(presence="departed")])
    _reject(proposal, "scene_actor_presence_conflict")


def test_same_actor_can_participate_in_two_facts_with_same_final_presence():
    proposal = _proposal(facts=[_fact(), _fact(summary="Mara verifica a janela.")])
    assert _check(proposal) is proposal


def test_private_actor_stays_out_of_roster_and_visible_fields():
    proposal = _proposal(facts=[_fact("Vulto secreto", presence="offscene", visibility="storyteller")])
    assert _check(proposal) is proposal


@pytest.mark.parametrize("field", ["n", "s", "l", "q", "t", "r", "p"])
def test_new_private_actor_cannot_leak_through_any_visible_field(field):
    value = "Vulto secreto"
    update = {field: [value] if field in {"t", "r", "p"} else f"{value} aparece enquanto a chuva bate na janela da oficina."}
    proposal = _proposal(facts=[_fact(value, presence="offscene", visibility="storyteller")], **update)
    _reject(proposal, "scene_private_actor_disclosed")


def test_known_public_npc_may_have_confidential_activity_without_banning_its_name():
    proposal = _proposal(facts=[_fact(visibility="storyteller", summary="Mara oculta uma intenção confidencial.")])
    assert _check(proposal) is proposal


def test_private_event_cannot_remove_a_publicly_present_npc():
    proposal = _proposal(facts=[_fact(presence="departed", visibility="storyteller")], roster=())
    _reject(proposal, "scene_actor_presence_conflict")


@pytest.mark.parametrize("private_first", [False, True])
def test_private_final_presence_cannot_contradict_public_departure(private_first):
    private = _fact(visibility="storyteller", summary="Mara oculta uma intenção confidencial.")
    departure = _fact(presence="departed", summary="Mara sai da oficina.")
    proposal = _proposal(
        facts=[private, departure] if private_first else [departure, private], roster=(),
        narrative="Mara sai da oficina enquanto a chuva bate na janela. Uma corrente oscila junto à porta.",
    )
    _reject(proposal, "scene_actor_presence_conflict")


def test_actor_errors_never_echo_private_labels_or_prose():
    proposal = _proposal(facts=[_fact("RotuloPrivadoSentinela", presence="offscene", visibility="storyteller")], q="Como RotuloPrivadoSentinela reage à chuva?")
    error = _reject(proposal, "scene_private_actor_disclosed")
    assert "RotuloPrivadoSentinela" not in str(error) + repr(error.evidence)


def test_literal_label_coherence_is_not_a_general_prose_subject_proof():
    # Deliberate limit: mentions can be objects. The unchanged agency/mechanical
    # guards and human semantic review are still required after this check.
    proposal = _proposal(facts=[_fact(summary="Ivo observa Mara.")], narrative="Ivo observa Mara enquanto a chuva bate na janela da oficina.")
    assert _check(proposal) is proposal
