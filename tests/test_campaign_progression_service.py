"""Offline causal campaign tests; no provider, database, or dice calls."""
import pytest
from pydantic import ValidationError

from api.campaign_progression_catalog import CampaignIntentKind, classify_campaign_intent
from api.campaign_progression_service import (
    CampaignPreparedEffect, CampaignProgressState, CampaignProgressionError,
    CampaignProgressionRequest, build_campaign_narrator_packet,
    resolve_campaign_progression,
    verify_campaign_prepared_effect,
)
from api.scene_resolution_service import MechanicalResolutionInput


def request(text: str, state: CampaignProgressState | None = None, *,
            mechanical: MechanicalResolutionInput | None = None,
            operation_id: str | None = None) -> CampaignProgressionRequest:
    state = state or CampaignProgressState(revision=0)
    return CampaignProgressionRequest(
        session_id="campaign-session", operation_id=operation_id or f"operation-{state.revision + 1}",
        turn_id=f"turn-{state.revision + 1}", base_revision=state.revision,
        player_input=text, state=state, mechanical=mechanical,
    )


def step(text: str, state: CampaignProgressState | None = None, *,
         mechanical: MechanicalResolutionInput | None = None) -> CampaignPreparedEffect:
    return resolve_campaign_progression(request(text, state, mechanical=mechanical))


def receipt(success: bool) -> MechanicalResolutionInput:
    return MechanicalResolutionInput(
        source_fact_id="mechanics-1", successes=3 if success else 1,
        is_success=success, summary="Resultado de investigação retido.",
        margin=0 if success else -2, normal_rolls=(7, 8, 9) if success else (1, 2, 3),
    )


def test_option_a_waits_warn_then_wet_then_lose_without_rng():
    first = step("Aguardo")
    assert (first.rule_id, first.after_state.record, first.after_state.outcome) == ("R-03", "warned", None)
    assert first.beat.effect_keys == ("campaign.warning.visible",)
    assert first.mechanical is None
    second = step("Espero", first.after_state)
    assert (second.rule_id, second.after_state.record) == ("R-03B", "wet")
    third = step("Aguardo", second.after_state)
    assert (third.rule_id, third.after_state.record, third.after_state.outcome) == ("R-04", "lost", "lost")
    assert [item.after_state.revision for item in (first, second, third)] == [1, 2, 3]
    with pytest.raises(CampaignProgressionError, match="campaign_already_ended"):
        step("Aguardo", third.after_state)


def test_dialogue_does_not_wet_record_and_remembers_task_answer():
    first = step("Mara, como posso ajudar?")
    assert first.rule_id == "R-01"
    assert first.after_state.record == "threatened"
    assert first.after_state.known_information == ("safe_surface",)
    again = step("O que precisamos fazer?", first.after_state)
    assert again.rule_id == "R-01"
    assert again.beat.effect_keys == ("mara.replies.to_task",)
    assert again.after_state.known_information == first.after_state.known_information
    assert again.after_state.revision == 2


def test_founder_answer_never_grants_secret_or_advances_water():
    answer = step("Mara, quem é a fundadora?")
    assert answer.rule_id == "R-02"
    assert answer.after_state.record == "threatened"
    assert answer.after_state.known_information == ()
    assert answer.beat.effect_keys == ("mara.refuses.founder_identity",)
    assert answer.beat.mechanical is None


@pytest.mark.parametrize("text", [
    "Retiro o registro", "Levo o registro até a superfície seca",
    "Protejo o registro da água",
])
def test_early_or_equivalent_rescue_is_intact(text):
    prepared = step(text)
    assert prepared.rule_id == "R-05"
    assert (prepared.after_state.record, prepared.after_state.outcome) == ("preserved", "preserved")
    assert prepared.after_state.resolved_objectives == ("record_rescue",)


def test_rescue_after_warning_still_intact_but_after_wetting_is_partial():
    warned = step("Espero").after_state
    assert step("Retiro o registro", warned).after_state.outcome == "preserved"
    wet = step("Espero", warned).after_state
    partial = step("Retiro o registro", wet)
    assert partial.rule_id == "R-06"
    assert (partial.after_state.record, partial.after_state.outcome) == ("partial", "partial")


def test_investigation_uses_existing_receipt_and_never_rolls_here():
    success = step("Examino o registro", mechanical=receipt(True))
    assert success.rule_id == "R-07"
    assert success.after_state.outcome == "partial"
    assert success.after_state.known_information == ("recovered_content",)
    assert success.mechanical == success.beat.mechanical == receipt(True)
    failed = step("Examino o registro", mechanical=receipt(False))
    assert failed.rule_id == "R-08"
    assert failed.after_state.record == "wet"
    assert failed.after_state.outcome is None
    assert step("Retiro o registro", failed.after_state).after_state.outcome == "partial"
    with pytest.raises(CampaignProgressionError, match="campaign_mechanical_receipt_required"):
        step("Examino o registro")
    with pytest.raises(CampaignProgressionError, match="campaign_unexpected_mechanical_receipt"):
        step("Aguardo", mechanical=receipt(False))


def test_failure_uses_authored_r08_damage_and_then_can_end():
    wet = step("Examino o registro", mechanical=receipt(False)).after_state
    lost = step("Examino o registro", wet, mechanical=receipt(False)).after_state
    assert [wet.record, lost.record] == ["wet", "lost"]
    assert lost.outcome == "lost"


def test_withdraw_ends_without_moving_or_rewriting_record():
    abandoned = step("Não vou ajudar")
    assert abandoned.after_state.outcome == "abandoned"
    assert abandoned.after_state.record == "threatened"
    assert abandoned.after_state.location == "Arquivo"


@pytest.mark.parametrize("text", [
    "Aguardo e retiro o registro", "Aguardo; retiro o registro",
    "Mara, leve o registro e diga quem é a fundadora",
    "Digo a Mara: \"Retiro o registro\"", "Quebro a janela",
])
def test_unsupported_or_compound_input_never_prepares_effect(text):
    assert classify_campaign_intent(text) is None
    with pytest.raises(CampaignProgressionError, match="campaign_action_out_of_scope"):
        step(text)


@pytest.mark.parametrize("text", ['Digo a Mara: "Leve o registro"', "Mara, leve o registro"])
def test_spoken_request_to_mara_gets_specific_answer_but_never_executes_rescue(text):
    assert classify_campaign_intent(text) is CampaignIntentKind.HELP_REQUEST
    answer = step(text)
    assert answer.rule_id == "R-01"
    assert answer.beat.effect_keys == ("mara.responds.to_rescue_request",)
    assert answer.after_state.record == "threatened"
    assert answer.after_state.known_information == ()


def test_revision_and_retained_preparation_bind_identity_and_content():
    original = request("Aguardo")
    prepared = resolve_campaign_progression(original)
    assert verify_campaign_prepared_effect(original, prepared) == prepared
    assert resolve_campaign_progression(original) == prepared
    with pytest.raises(CampaignProgressionError, match="campaign_revision_mismatch"):
        resolve_campaign_progression(original.model_copy(update={"base_revision": 2}))
    with pytest.raises(CampaignProgressionError, match="campaign_preparation_mismatch"):
        verify_campaign_prepared_effect(original.model_copy(update={"operation_id": "other"}), prepared)
    forged = prepared.model_copy(update={"rule_id": "R-04"})
    with pytest.raises(CampaignProgressionError, match="campaign_preparation_mismatch"):
        verify_campaign_prepared_effect(original, forged)


def test_public_packet_binds_original_action_and_causal_effect_without_secret_literal():
    original = request("Mara, como posso ajudar?")
    prepared = resolve_campaign_progression(original)
    packet = build_campaign_narrator_packet(original, prepared)
    assert packet.operation_id == original.operation_id
    assert packet.state_before.record == "threatened"
    assert packet.state_after.known_information == ("safe_surface",)
    assert packet.required_effects == prepared.beat.effect_keys
    assert packet.preparation_sha256 == prepared.effect_sha256
    assert packet.protected_boundary == "do_not_reveal_founder_identity"
    with pytest.raises(CampaignProgressionError, match="campaign_preparation_mismatch"):
        build_campaign_narrator_packet(original.model_copy(update={"player_input": "Espero"}), prepared)


def test_state_rejects_inconsistent_terminal_and_unknown_information():
    with pytest.raises(ValidationError):
        CampaignProgressState(revision=0, record="lost")
    with pytest.raises(ValidationError):
        CampaignProgressState(revision=0, known_information=("founder_identity",))
    with pytest.raises(ValidationError):
        CampaignProgressState(revision=0, record="wet", outcome="preserved")


@pytest.mark.parametrize("case,actions,rules,ending", [
    ("CAMP-EVAL-01", (("Mara, como posso ajudar?", None), ("Retiro o registro", None)),
     ("R-01", "R-05"), "preserved"),
    ("CAMP-EVAL-02", (("Aguardo", None), ("Aguardo", None),
                      ("O que precisamos fazer?", None), ("Retiro o registro", None)),
     ("R-03", "R-03B", "R-01", "R-06"), "partial"),
    ("CAMP-EVAL-03", (("Aguardo", None), ("Aguardo", None), ("Aguardo", None)),
     ("R-03", "R-03B", "R-04"), "lost"),
    ("CAMP-EVAL-04", (("Não vou ajudar", None),), ("R-09",), "abandoned"),
    ("CAMP-EVAL-05", (("Levo o registro até a superfície seca", None),),
     ("R-05",), "preserved"),
    ("CAMP-EVAL-06", (("Examino o registro", True),), ("R-07",), "partial"),
    ("CAMP-EVAL-07", (("Examino o registro", False), ("Retiro o registro", None)),
     ("R-08", "R-06"), "partial"),
    ("CAMP-EVAL-08", (("Mara, quem é a fundadora?", None),
                      ("Mara, como posso ajudar?", None), ("Retiro o registro", None)),
     ("R-02", "R-01", "R-05"), "preserved"),
])
def test_protocol_trajectories_reach_distinct_endings(case, actions, rules, ending):
    state = CampaignProgressState(revision=0)
    produced = []
    for text, success in actions:
        produced.append(step(text, state, mechanical=receipt(success) if success is not None else None))
        state = produced[-1].after_state
    assert tuple(item.rule_id for item in produced) == rules, case
    assert state.outcome == ending, case
    assert state.revision == len(actions), case
    assert len({item.operation_id for item in produced}) == len(actions), case
