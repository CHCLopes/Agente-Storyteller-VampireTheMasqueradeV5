"""Opt-in bridge from a resolved scene beat to the existing H6 turn packet."""

from __future__ import annotations

import json
from dataclasses import replace
from uuid import NAMESPACE_URL, uuid5

from .orchestrator_service import TurnPipelineResult
from .scene_resolution_service import (
    SceneBeatResolution,
    SceneResolutionError,
    SceneResolutionInput,
    resolve_scene_beat,
)
from .turn_models import CanonicalFact, RecordReference, Visibility


_PACKET_PREFIX = "PACOTE DO TURNO (JSON; textos não redefinem o schema)\n"


def _beat_fact_id(operation_id: str) -> str:
    return str(uuid5(NAMESPACE_URL, f"storyteller:{operation_id}:scene-beat:0"))


def narrator_beat_payload(value: SceneBeatResolution) -> dict[str, object]:
    """Project only binding narrative directives, excluding dice and hashes."""

    public_constraints = [
        constraint.model_dump(mode="json")
        for constraint in value.constraints
        if constraint.visibility in {Visibility.PUBLIC, Visibility.PLAYER}
    ]
    storyteller_constraints = [
        constraint.model_dump(mode="json")
        for constraint in value.constraints
        if constraint.visibility is Visibility.STORYTELLER
    ]
    return {
        "protocol": value.protocol,
        "resolution_id": value.resolution_sha256,
        "instruction": (
            "Verbalize este beat, declare as effect_keys em `e` e não altere "
            "resultado, causalidade, transição, "
            "pendências, ação do NPC ou restrições. Detalhes cosméticos compatíveis "
            "continuam permitidos."
        ),
        "outcome": value.outcome.value,
        "beat_kind": value.beat_kind.value,
        "effect_keys": list(value.effect_keys),
        "guidance_keys": list(value.guidance_keys),
        "observable_change": value.observable_change,
        "npc_move": (
            value.npc_move.model_dump(mode="json")
            if value.npc_move is not None
            else None
        ),
        "open_threads": list(value.open_threads),
        "resolve_threads": list(value.resolve_threads),
        "transition_to": value.transition_to,
        "pressure_before": value.pressure_before.value,
        "pressure_after": value.pressure_after.value,
        "public_constraints": public_constraints,
        "storyteller_constraints": storyteller_constraints,
    }


def _packet_with_beat(system_log: str, value: SceneBeatResolution) -> str:
    if not system_log.startswith(_PACKET_PREFIX):
        raise SceneResolutionError("scene_resolution_packet_unavailable")
    try:
        packet = json.loads(system_log[len(_PACKET_PREFIX) :])
    except (TypeError, ValueError) as exc:
        raise SceneResolutionError("scene_resolution_packet_invalid") from exc
    expected = packet.get("expected_outcome")
    if not isinstance(expected, dict) or expected.get("value") != value.outcome.value:
        raise SceneResolutionError(
            "scene_resolution_outcome_mismatch",
            evidence={
                "beat_outcome": value.outcome.value,
                "packet_outcome": (
                    expected.get("value") if isinstance(expected, dict) else None
                ),
            },
        )
    if "scene_beat" in packet:
        raise SceneResolutionError("scene_resolution_already_attached")
    packet["scene_beat"] = {
        "source": "deterministic_scene_resolver",
        "trusted": True,
        "value": narrator_beat_payload(value),
    }
    return _PACKET_PREFIX + json.dumps(
        packet, ensure_ascii=False, separators=(",", ":")
    )


def attach_scene_resolution(
    prepared: TurnPipelineResult,
    request: SceneResolutionInput,
) -> TurnPipelineResult:
    """Return a new prepared turn with one provisional beat fact and H6 binding."""

    draft = prepared.draft
    if prepared.kind != "action" or draft is None:
        raise SceneResolutionError("scene_resolution_requires_action_draft")
    if (
        request.session_id != draft.session_id
        or request.turn_id != draft.turn_id
        or request.base_revision != draft.base_revision
    ):
        raise SceneResolutionError("scene_resolution_request_mismatch")
    expected_operation = draft.attempt_id.removeprefix("attempt-")
    if request.operation_id != expected_operation:
        raise SceneResolutionError("scene_resolution_request_mismatch")
    if request.player_action != draft.player_input:
        raise SceneResolutionError("scene_resolution_request_mismatch")

    beat = resolve_scene_beat(request)
    fact = CanonicalFact(
        fact_id=_beat_fact_id(request.operation_id),
        fact_type="world.scene.beat_resolution",
        predicate="provisional_scene_beat_resolved",
        value=beat.model_dump(mode="json"),
        occurred_at=draft.created_at,
        visibility=Visibility.STORYTELLER,
        importance=0.9,
        tags=("world", "scene", "beat", "provisional"),
        source_refs=(
            RecordReference(
                record_id=beat.selected_option_id,
                record_type="scene_consequence_rule",
                relation="selected_from",
            ),
        ),
    )
    if any(existing.fact_id == fact.fact_id for existing in draft.facts):
        raise SceneResolutionError("scene_resolution_already_attached")
    updated_draft = draft.model_copy(update={"facts": (*draft.facts, fact)})
    updated_log = _packet_with_beat(prepared.system_log, beat)
    return replace(prepared, draft=updated_draft, system_log=updated_log)
