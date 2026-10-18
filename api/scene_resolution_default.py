"""Narrow default composition for catalog-backed scene resolution."""
from __future__ import annotations

from .orchestrator_service import TurnPipelineResult
from .relationship_service import NpcRelationship
from .scene_direction_catalog import mara_profile, mara_scene_options
from .scene_resolution_integration import attach_scene_resolution
from .scene_resolution_service import (
    ScenePressure,
    SceneResolutionInput,
    SceneTurnKind,
)
from .scene_service import SceneState


def attach_catalog_scene_resolution(
    prepared: TurnPipelineResult,
    *,
    scene: SceneState | None,
    player_input: str,
    relationship: NpcRelationship | None = None,
) -> TurnPipelineResult:
    """Attach only when a trusted catalog entry covers the current turn."""

    draft = prepared.draft
    if prepared.kind != "action" or draft is None or scene is None:
        return prepared
    if any(fact.fact_type == "mechanics.resolution" for fact in draft.facts):
        return prepared
    options = mara_scene_options(
        scene=scene,
        player_input=player_input,
        turn_kind=SceneTurnKind.DIALOGUE,
    )
    if not options:
        return prepared
    profile = mara_profile(
        disposition=(relationship.disposition if relationship else "neutral"),
        trust=(relationship.trust_level if relationship else 3),
    )
    request = SceneResolutionInput(
        session_id=draft.session_id,
        operation_id=draft.attempt_id.removeprefix("attempt-"),
        turn_id=draft.turn_id,
        base_revision=draft.base_revision,
        player_action=player_input,
        turn_kind=SceneTurnKind.DIALOGUE,
        scene=scene,
        pressure=ScenePressure.CALM,
        npc_profiles=(profile,),
        options=options,
    )
    return attach_scene_resolution(prepared, request)
