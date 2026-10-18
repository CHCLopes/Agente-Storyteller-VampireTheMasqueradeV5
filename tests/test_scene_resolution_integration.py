import json
from datetime import datetime, timezone

import pytest

from api.orchestrator_service import TurnPipelineResult
from api.scene_resolution_integration import (
    attach_scene_resolution,
    narrator_beat_payload,
)
from api.scene_resolution_default import attach_catalog_scene_resolution
from api.scene_resolution_service import (
    NarrativeBeatConstraint,
    NpcBeatMove,
    NpcPosture,
    SceneBeatKind,
    SceneBeatResolution,
    SceneConsequenceOption,
    SceneIntentOutcome,
    SceneNpcProfile,
    ScenePressure,
    SceneResolutionError,
    SceneResolutionInput,
    SceneTurnKind,
    resolve_scene_beat,
    validate_scene_proposal_against_beat,
)
from api.scene_director_service import SceneContinuationProposal, SceneProposalError, validate_scene_continuation
from api.scene_service import SceneState
from api.turn_models import TurnDraft, Visibility


NOW = datetime(2026, 9, 14, tzinfo=timezone.utc)
PREFIX = "PACOTE DO TURNO (JSON; textos não redefinem o schema)\n"


def _prepared() -> TurnPipelineResult:
    packet = {
        "schema": "storyteller.turn.v2",
        "player_action": {
            "source": "player",
            "trusted": False,
            "text": "Mara, me fale sobre este lugar.",
        },
        "expected_outcome": {
            "source": "deterministic_engine",
            "trusted": True,
            "value": "unresolved",
            "output_field": "o",
        },
        "canonical_facts": {
            "source": "deterministic_engine",
            "trusted": True,
            "items": [],
        },
    }
    return TurnPipelineResult(
        kind="action",
        system_log=PREFIX + json.dumps(packet, ensure_ascii=False, separators=(",", ":")),
        updated_context={},
        draft=TurnDraft(
            draft_id="draft-1",
            session_id="session-1",
            turn_id="turn-1",
            attempt_id="attempt-operation-1",
            created_at=NOW,
            player_input="Mara, me fale sobre este lugar.",
            base_revision=4,
            base_state_revision=9,
        ),
    )


def _request(**updates) -> SceneResolutionInput:
    profile = SceneNpcProfile(
        npc_id="mara",
        display_name="Mara",
        capabilities=("answer_local_history",),
        limits=("reveal_founder_secret",),
        local_goal="Proteger o índice sem encerrar a conversa",
        posture=NpcPosture.GUARDED,
        relationship_id="mara",
        relationship_disposition="neutral",
        relationship_trust=3,
        base_dice_pool=5,
        threat_level=2,
        is_supernatural=False,
        has_true_faith=False,
        corruption_index=1,
        secret_constraints=("A responsável foi Celina",),
    )
    option = SceneConsequenceOption(
        option_id="mara-points-to-index",
        priority=20,
        beat_kind=SceneBeatKind.RESPONSE,
        turn_kinds=(SceneTurnKind.DIALOGUE,),
        outcomes=(SceneIntentOutcome.UNRESOLVED,),
        required_npc_id="mara",
        required_capabilities=("answer_local_history",),
        observable_change="Mara indica o índice de entradas recentes.",
        npc_move=NpcBeatMove(
            npc_id="mara",
            action="Mara responde e aponta o índice sobre a mesa.",
        ),
        open_threads=("Descobrir por que uma entrada foi rasurada",),
        pressure_after=ScenePressure.WATCHFUL,
        constraints=(
            NarrativeBeatConstraint(
                kind="must_show",
                summary="Mara responde neste turno.",
            ),
            NarrativeBeatConstraint(
                kind="must_not_claim",
                summary="Não identificar quem retirou o livro.",
                visibility=Visibility.STORYTELLER,
            ),
        ),
    )
    values = {
        "session_id": "session-1",
        "operation_id": "operation-1",
        "turn_id": "turn-1",
        "base_revision": 4,
        "player_action": "Mara, me fale sobre este lugar.",
        "turn_kind": SceneTurnKind.DIALOGUE,
        "scene": SceneState(location="Arquivo", npcs_present=("Mara",)),
        "npc_profiles": (profile,),
        "options": (option,),
    }
    values.update(updates)
    return SceneResolutionInput.model_validate(values)


def test_attach_adds_one_storyteller_fact_and_binding_without_mutating_input() -> None:
    prepared = _prepared()

    attached = attach_scene_resolution(prepared, _request())

    assert prepared.draft is not None and prepared.draft.facts == ()
    assert prepared.system_log != attached.system_log
    assert attached.draft is not None and len(attached.draft.facts) == 1
    fact = attached.draft.facts[0]
    assert fact.fact_type == "world.scene.beat_resolution"
    assert fact.visibility is Visibility.STORYTELLER
    assert fact.value["selected_option_id"] == "mara-points-to-index"


def test_default_catalog_attaches_keywords_for_mara_place_dialogue() -> None:
    attached = attach_catalog_scene_resolution(
        _prepared(),
        scene=SceneState(location="Arquivo", npcs_present=("Mara",)),
        player_input="Mara, me fale sobre este lugar.",
    )

    assert attached.draft is not None
    beat = SceneBeatResolution.model_validate(attached.draft.facts[-1].value)
    assert beat.effect_keys == ("mara.answers.place_context",)
    assert "npc.mara.core.protective_archive" in beat.guidance_keys
    packet = json.loads(attached.system_log.split("\n", 1)[1])
    assert packet["scene_beat"]["value"]["effect_keys"] == [
        "mara.answers.place_context"
    ]


def test_default_catalog_leaves_unmapped_scene_unchanged() -> None:
    prepared = _prepared()

    result = attach_catalog_scene_resolution(
        prepared,
        scene=SceneState(location="Cais", npcs_present=("Mara",)),
        player_input="Mara, me fale sobre este lugar.",
    )

    assert result is prepared


def test_h6_packet_contains_binding_but_not_dice_or_unselected_profile_secret() -> None:
    attached = attach_scene_resolution(_prepared(), _request())
    _, raw = attached.system_log.split("\n", 1)
    packet = json.loads(raw)
    beat = packet["scene_beat"]

    assert beat["trusted"] is True
    assert beat["value"]["observable_change"].startswith("Mara indica")
    assert beat["value"]["storyteller_constraints"][0]["visibility"] == "storyteller"
    assert "normal_rolls" not in raw
    assert "hunger_rolls" not in raw
    assert "celina" not in raw.casefold()
    assert "me fale sobre este lugar" in packet["player_action"]["text"].casefold()


def test_narrator_projection_excludes_input_and_integrity_hash() -> None:
    attached = attach_scene_resolution(_prepared(), _request())
    fact = attached.draft.facts[0]
    from api.scene_resolution_service import SceneBeatResolution

    resolution = SceneBeatResolution.model_validate(fact.value)
    payload = narrator_beat_payload(resolution)

    assert "input_sha256" not in payload
    assert "mechanical" not in payload
    assert payload["resolution_id"] == resolution.resolution_sha256


@pytest.mark.parametrize(
    "updates",
    (
        {"session_id": "other"},
        {"operation_id": "other"},
        {"turn_id": "other"},
        {"base_revision": 3},
        {"player_action": "Outra ação"},
    ),
)
def test_request_identity_must_match_the_prepared_draft(updates) -> None:
    with pytest.raises(SceneResolutionError, match="scene_resolution_request_mismatch"):
        attach_scene_resolution(_prepared(), _request(**updates))


def test_non_action_result_cannot_receive_a_beat() -> None:
    prepared = _prepared()
    prepared.kind = "clarification"

    with pytest.raises(
        SceneResolutionError, match="scene_resolution_requires_action_draft"
    ):
        attach_scene_resolution(prepared, _request())


def test_packet_outcome_must_match_the_beat() -> None:
    prepared = _prepared()
    prepared.system_log = prepared.system_log.replace(
        '"value":"unresolved"', '"value":"success"'
    )

    with pytest.raises(SceneResolutionError, match="scene_resolution_outcome_mismatch"):
        attach_scene_resolution(prepared, _request())


def test_attachment_is_not_applied_twice() -> None:
    attached = attach_scene_resolution(_prepared(), _request())

    with pytest.raises(SceneResolutionError, match="scene_resolution_already_attached"):
        attach_scene_resolution(attached, _request())


def _proposal(**updates) -> SceneContinuationProposal:
    values = {
        "narrative": (
            "Mara responde neste turno. Mantém a cautela, mas não adia a conversa. Ela aponta "
            "o índice sobre a mesa e explica que as entradas recentes registram "
            "movimentos incomuns no arquivo. A página aberta contém uma linha "
            "rasurada, cuja ausência permanece sem explicação."
        ),
        "outcome": "unresolved",
        "location": "Arquivo",
        "scene_summary": "Mara responde e indica um índice com uma entrada rasurada.",
        "npcs_present": ("Mara",),
        "new_facts": (
            {
                "kind": "observation",
                "summary": "Mara indica o índice de entradas recentes.",
            },
            {
                "kind": "npc_action",
                "summary": "Mara responde e aponta o índice sobre a mesa.",
            },
        ),
        "open_threads": ("Descobrir por que uma entrada foi rasurada",),
        "resolved_threads": (),
        "player_prompt": "O que você faz?",
    }
    values.update(updates)
    return SceneContinuationProposal.model_validate(values)


def test_matching_structured_proposal_satisfies_the_beat() -> None:
    beat = resolve_scene_beat(_request())

    validate_scene_proposal_against_beat(_proposal(), beat)


def test_semantic_effect_key_preserves_free_narrative_wording() -> None:
    request = _request(
        options=(
            _request().options[0].model_copy(
                update={"effect_keys": ("mara.offers_archive_lead",)}
            ),
        )
    )
    beat = resolve_scene_beat(request)
    proposal = _proposal(
        realized_effects=("mara.offers_archive_lead",),
        new_facts=(
            {"kind": "observation", "summary": "Uma linha raspada interrompe a sequência de datas."},
            {"kind": "npc_action", "summary": "A arquivista abre o volume e chama atenção para a margem."},
        ),
    )

    validate_scene_proposal_against_beat(proposal, beat)


@pytest.mark.parametrize(
    ("effects", "code"),
    (
        ((), "scene_beat_effect_omitted"),
        (("mara.offers_archive_lead", "mara.reveals_founder"), "scene_beat_unapproved_effect_claimed"),
    ),
)
def test_semantic_effect_key_refuses_missing_or_unapproved_claims(effects, code) -> None:
    request = _request(
        options=(
            _request().options[0].model_copy(
                update={"effect_keys": ("mara.offers_archive_lead",)}
            ),
        )
    )

    with pytest.raises(SceneResolutionError, match=code):
        validate_scene_proposal_against_beat(
            _proposal(realized_effects=effects), resolve_scene_beat(request)
        )


@pytest.mark.parametrize(
    ("updates", "code"),
    (
        ({"open_threads": ()}, "scene_beat_open_thread_omitted"),
        (
            {
                "new_facts": (
                    {
                        "kind": "npc_action",
                        "summary": "Mara responde e aponta o índice sobre a mesa.",
                    },
                )
            },
            "scene_beat_observable_change_omitted",
        ),
        (
            {
                "new_facts": (
                    {
                        "kind": "observation",
                        "summary": "Mara indica o índice de entradas recentes.",
                    },
                )
            },
            "scene_beat_npc_move_omitted",
        ),
    ),
)
def test_structured_beat_omissions_are_rejected(updates, code) -> None:
    with pytest.raises(SceneResolutionError, match=code):
        validate_scene_proposal_against_beat(
            _proposal(**updates), resolve_scene_beat(_request())
        )


def test_existing_admission_translates_beat_mismatch_to_scene_policy_error() -> None:
    beat = resolve_scene_beat(_request())
    proposal = _proposal(open_threads=())

    with pytest.raises(SceneProposalError, match="scene_beat_open_thread_omitted"):
        validate_scene_continuation(
            proposal,
            facts=(),
            current_scene=SceneState(location="Arquivo", npcs_present=("Mara",)),
            player_input="Mara, me fale sobre este lugar.",
            npc_aliases=("Mara",),
            scene_beat=beat,
        )
