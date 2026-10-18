import json

import pytest
from pydantic import ValidationError

from api.scene_resolution_service import (
    MechanicalResolutionInput,
    NarrativeBeatConstraint,
    NpcBeatMove,
    NpcPosture,
    SceneBeatKind,
    SceneConsequenceOption,
    SceneIntentOutcome,
    SceneNpcProfile,
    ScenePressure,
    SceneResolutionError,
    SceneResolutionInput,
    SceneTurnKind,
    mechanical_resolution_from_result,
    resolve_scene_beat,
    scene_npc_profile_from_models,
    verify_scene_beat_resolution,
)
from api.npc_service import NpcEngineData, NpcModel, NpcNarrativeData
from api.relationship_service import NpcRelationship
from api.rules_service import ResolutionResult
from api.scene_service import SceneState
from api.turn_models import Visibility


def _npc(**updates) -> SceneNpcProfile:
    values = {
        "npc_id": "mara",
        "display_name": "Mara",
        "capabilities": ("answer_local_history", "move_inside_archive"),
        "limits": ("reveal_founder_secret",),
        "local_goal": "Descobrir se o visitante respeita o arquivo",
        "posture": NpcPosture.GUARDED,
        "relationship_id": "mara",
        "relationship_disposition": "neutral",
        "relationship_trust": 3,
        "base_dice_pool": 5,
        "threat_level": 2,
        "is_supernatural": False,
        "has_true_faith": False,
        "corruption_index": 1,
        "secret_constraints": ("A responsável foi Celina",),
    }
    values.update(updates)
    return SceneNpcProfile.model_validate(values)


def _option(option_id: str = "mara-points-to-index", **updates) -> SceneConsequenceOption:
    values = {
        "option_id": option_id,
        "priority": 20,
        "beat_kind": SceneBeatKind.RESPONSE,
        "turn_kinds": (SceneTurnKind.DIALOGUE,),
        "outcomes": (SceneIntentOutcome.UNRESOLVED,),
        "required_npc_id": "mara",
        "required_capabilities": ("answer_local_history",),
        "observable_change": "Mara indica o índice de entradas recentes.",
        "npc_move": NpcBeatMove(
            npc_id="mara",
            action="Mara responde e aponta o índice sobre a mesa.",
            posture_after=NpcPosture.GUARDED,
        ),
        "open_threads": ("Descobrir por que uma entrada foi rasurada",),
        "pressure_after": ScenePressure.WATCHFUL,
        "constraints": (
            NarrativeBeatConstraint(
                kind="must_show",
                summary="Mara responde neste turno e indica o índice.",
            ),
            NarrativeBeatConstraint(
                kind="must_not_claim",
                summary="Não afirmar quem removeu o livro azul.",
                visibility=Visibility.STORYTELLER,
            ),
        ),
    }
    values.update(updates)
    return SceneConsequenceOption.model_validate(values)


def _input(**updates) -> SceneResolutionInput:
    values = {
        "session_id": "session-1",
        "operation_id": "operation-1",
        "turn_id": "turn-1",
        "base_revision": 4,
        "player_action": "Mara, me fale sobre este lugar.",
        "turn_kind": SceneTurnKind.DIALOGUE,
        "scene": SceneState(
            location="Arquivo",
            npcs_present=("Mara",),
            open_threads=("Localizar o livro azul",),
            last_turn=4,
        ),
        "pressure": ScenePressure.CALM,
        "npc_profiles": (_npc(),),
        "options": (_option(),),
    }
    values.update(updates)
    return SceneResolutionInput.model_validate(values)


def _mechanical(*, success: bool) -> MechanicalResolutionInput:
    margin = 2 if success else -1
    return MechanicalResolutionInput(
        source_fact_id="mechanics-resolution-1",
        successes=4 if success else 1,
        is_success=success,
        bestial_failure=not success,
        messy_critical=False,
        summary="Resultado mecânico já calculado.",
        normal_rolls=(8, 7),
        hunger_rolls=((1,) if not success else (6,)),
        margin=margin,
    )


def test_dialogue_resolves_to_a_concrete_npc_response() -> None:
    result = resolve_scene_beat(_input())

    assert result.selected_option_id == "mara-points-to-index"
    assert result.outcome is SceneIntentOutcome.UNRESOLVED
    assert result.npc_move is not None
    assert result.npc_move.npc_id == "mara"
    assert result.observable_change == "Mara indica o índice de entradas recentes."
    assert result.pressure_after is ScenePressure.WATCHFUL
    assert len(result.input_sha256) == len(result.resolution_sha256) == 64


def test_effect_keys_are_preserved_as_semantic_commitments() -> None:
    result = resolve_scene_beat(
        _input(options=(_option(
            effect_keys=("mara.offers_archive_lead",),
            guidance_keys=("mara.core.protective", "mara.reaction.guarded"),
        ),))
    )

    assert result.effect_keys == ("mara.offers_archive_lead",)
    assert result.guidance_keys == (
        "mara.core.protective",
        "mara.reaction.guarded",
    )


def test_same_input_produces_identical_wire_bytes_and_hashes() -> None:
    value = _input()

    first = resolve_scene_beat(value)
    second = resolve_scene_beat(value)

    assert first == second
    assert first.model_dump_json() == second.model_dump_json()
    assert first.resolution_sha256 == second.resolution_sha256


def test_priority_then_option_id_is_the_stable_tie_breaker() -> None:
    lower_id = _option("a-option", priority=30)
    higher_id = _option("z-option", priority=30)
    low_priority = _option("00-option", priority=29)

    result = resolve_scene_beat(
        _input(options=(higher_id, low_priority, lower_id))
    )

    assert result.selected_option_id == "a-option"


@pytest.mark.parametrize(
    "turn_kind",
    (
        SceneTurnKind.QUERY,
        SceneTurnKind.COMMAND,
        SceneTurnKind.CLARIFICATION,
        SceneTurnKind.TECHNICAL_FAILURE,
    ),
)
def test_non_fictional_turns_do_not_resolve_a_beat(turn_kind: SceneTurnKind) -> None:
    with pytest.raises(
        SceneResolutionError, match="scene_turn_does_not_require_beat"
    ) as caught:
        resolve_scene_beat(_input(turn_kind=turn_kind))

    assert caught.value.evidence == {"turn_kind": turn_kind.value}


def test_wait_requires_an_observable_change_but_no_dice() -> None:
    wait = _option(
        "rain-reaches-ledger",
        beat_kind=SceneBeatKind.CHANGE,
        turn_kinds=(SceneTurnKind.WAIT,),
        required_npc_id=None,
        required_capabilities=(),
        npc_move=None,
        observable_change="A água alcança a borda do livro-caixa.",
        open_threads=("Impedir que o livro-caixa seja molhado",),
    )
    value = _input(
        player_action="Aguardo para ver o que acontece.",
        turn_kind=SceneTurnKind.WAIT,
        options=(wait,),
    )

    result = resolve_scene_beat(value)

    assert result.mechanical is None
    assert result.outcome is SceneIntentOutcome.UNRESOLVED
    assert result.observable_change.startswith("A água")


@pytest.mark.parametrize("success", (True, False))
def test_mechanical_result_is_preserved_exactly(success: bool) -> None:
    mechanical = _mechanical(success=success)
    expected = (
        SceneIntentOutcome.SUCCESS if success else SceneIntentOutcome.FAILURE
    )
    option = _option(
        "mechanical-consequence",
        beat_kind=SceneBeatKind.CONSEQUENCE,
        turn_kinds=(SceneTurnKind.FICTION_ACTION,),
        outcomes=(expected,),
    )
    value = _input(
        player_action="Examino o índice.",
        turn_kind=SceneTurnKind.FICTION_ACTION,
        mechanical=mechanical,
        options=(option,),
    )

    result = resolve_scene_beat(value)

    assert result.outcome is expected
    assert result.mechanical == mechanical
    assert result.mechanical.model_dump_json() == mechanical.model_dump_json()


def test_mechanical_success_and_margin_must_agree() -> None:
    with pytest.raises(ValidationError, match="mechanical success must agree"):
        _mechanical(success=True).model_copy(update={"margin": -1}).__class__.model_validate(
            {
                **_mechanical(success=True).model_dump(),
                "margin": -1,
            }
        )


def test_existing_mechanical_result_is_copied_without_reroll() -> None:
    existing = ResolutionResult(
        successes=3,
        is_success=True,
        bestial_failure=False,
        messy_critical=False,
        summary="Rolagem já encerrada.",
        normal_rolls=[6, 7],
        hunger_rolls=[8],
        margin=1,
    )

    adapted = mechanical_resolution_from_result(
        existing, source_fact_id="mechanics-1"
    )

    assert adapted.normal_rolls == (6, 7)
    assert adapted.hunger_rolls == (8,)
    assert existing.normal_rolls == [6, 7]
    assert adapted.margin == existing.margin


def test_existing_npc_and_relationship_are_adapted_without_inventing_goal() -> None:
    npc = NpcModel(
        engine_data=NpcEngineData(
            base_dice_pool=7,
            threat_level=4,
            is_supernatural=True,
            has_true_faith=False,
            corruption_index=2,
        ),
        narrative_data=NpcNarrativeData(
            description="Guardião do arquivo.",
            combat_tactics="Evita confronto direto.",
            social_standing="Arquivista respeitada.",
        ),
    )
    relationship = NpcRelationship(
        npc_id="mara", disposition="favorable", trust_level=4
    )

    adapted = scene_npc_profile_from_models(
        npc_id="mara",
        display_name="Mara",
        npc=npc,
        relationship=relationship,
        local_goal="Proteger o índice sem encerrar a conversa",
        posture=NpcPosture.GUARDED,
        capabilities=("answer_local_history",),
        limits=("reveal_founder_secret",),
    )

    assert adapted.local_goal == "Proteger o índice sem encerrar a conversa"
    assert adapted.base_dice_pool == 7
    assert adapted.threat_level == 4
    assert adapted.relationship_disposition == "favorable"
    assert adapted.relationship_trust == 4


def test_npc_without_required_capability_cannot_take_the_option() -> None:
    with pytest.raises(SceneResolutionError, match="scene_no_eligible_consequence"):
        resolve_scene_beat(
            _input(npc_profiles=(_npc(capabilities=("move_inside_archive",)),))
        )


def test_npc_limit_blocks_a_forbidden_option() -> None:
    option = _option(forbidden_limits=("reveal_founder_secret",))

    with pytest.raises(SceneResolutionError, match="scene_no_eligible_consequence"):
        resolve_scene_beat(_input(options=(option,)))


def test_npc_profile_must_refer_to_an_actor_present_in_scene() -> None:
    with pytest.raises(ValidationError, match="actors present"):
        _input(scene=SceneState(location="Arquivo", npcs_present=("Rui",)))


def test_resolved_thread_must_already_be_open() -> None:
    option = _option(resolve_threads=("Pendência inexistente",))

    with pytest.raises(SceneResolutionError, match="scene_no_eligible_consequence"):
        resolve_scene_beat(_input(options=(option,)))


def test_duplicate_open_thread_is_not_a_new_consequence() -> None:
    option = _option(open_threads=("Localizar o livro azul",))

    with pytest.raises(SceneResolutionError, match="scene_no_eligible_consequence"):
        resolve_scene_beat(_input(options=(option,)))


def test_transition_requires_an_explicit_transition_beat() -> None:
    with pytest.raises(ValidationError, match="transition_to requires"):
        _option(transition_to="Corredor Norte")


def test_transition_to_current_location_is_ineligible() -> None:
    option = _option(
        beat_kind=SceneBeatKind.TRANSITION,
        transition_to="Arquivo",
    )

    with pytest.raises(SceneResolutionError, match="scene_no_eligible_consequence"):
        resolve_scene_beat(_input(options=(option,)))


def test_storyteller_constraint_retains_its_visibility() -> None:
    result = resolve_scene_beat(_input())

    secret = result.constraints[1]
    assert secret.visibility is Visibility.STORYTELLER
    assert "livro azul" in secret.summary


def test_result_does_not_copy_the_player_action_or_unselected_npc_secret() -> None:
    result = resolve_scene_beat(_input())
    wire = result.model_dump_json()

    assert "me fale sobre este lugar" not in wire.casefold()
    assert "celina" not in wire.casefold()
    assert result.constraints[1].summary.startswith("Não afirmar")


def test_mutated_resolution_does_not_verify() -> None:
    value = _input()
    result = resolve_scene_beat(value)
    altered = result.model_copy(update={"selected_option_id": "forged"})

    with pytest.raises(SceneResolutionError, match="scene_resolution_mismatch"):
        verify_scene_beat_resolution(value, altered)


def test_wire_round_trip_is_strict_and_frozen() -> None:
    result = resolve_scene_beat(_input())
    restored = result.__class__.model_validate_json(result.model_dump_json())

    assert restored == result
    with pytest.raises(ValidationError):
        result.__class__.model_validate(
            {**json.loads(result.model_dump_json()), "unexpected": True}
        )


def test_option_must_describe_a_meaningful_beat() -> None:
    with pytest.raises(ValidationError, match="must change or answer"):
        SceneConsequenceOption(
            option_id="empty",
            beat_kind=SceneBeatKind.CHANGE,
            turn_kinds=(SceneTurnKind.WAIT,),
            outcomes=(SceneIntentOutcome.UNRESOLVED,),
        )
