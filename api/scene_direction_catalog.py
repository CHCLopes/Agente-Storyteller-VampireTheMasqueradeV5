"""Minimal keyword direction catalog for deterministic scene beats.

Entries constrain identity, causal effects and limits. They intentionally contain
no finished dialogue, scene prose or ordered script for the narrator to copy.
"""
from __future__ import annotations

import re
import unicodedata
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from .scene_resolution_service import (
    NpcBeatMove,
    NpcPosture,
    SceneBeatKind,
    SceneConsequenceOption,
    SceneIntentOutcome,
    SceneNpcProfile,
    ScenePressure,
    SceneTurnKind,
)
from .scene_service import SceneState


class KeywordTopicReaction(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    topic_key: str
    trigger_words: tuple[str, ...]
    reaction_spectrum: tuple[str, ...] = Field(min_length=1)
    effect_key: str
    advance_mode: Literal["help", "hinder", "complicate"]


class KeywordNpcDirection(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    npc_id: str
    display_name: str
    scene_keys: tuple[str, ...]
    core_traits: tuple[str, ...] = Field(min_length=1)
    stable_objectives: tuple[str, ...] = Field(min_length=1)
    current_objectives: tuple[str, ...] = Field(min_length=1)
    capabilities: tuple[str, ...]
    limits: tuple[str, ...]
    topics: tuple[KeywordTopicReaction, ...]


MARA_DIRECTION = KeywordNpcDirection(
    npc_id="mara",
    display_name="Mara",
    scene_keys=("arquivo", "galeria"),
    core_traits=("protective_archive", "observant", "reserved"),
    stable_objectives=("preserve_archive",),
    current_objectives=("evaluate_visitor", "protect_index"),
    capabilities=("answer_local_history", "offer_partial_clue", "protect_archive"),
    limits=("reveal_founder_identity_directly",),
    topics=(
        KeywordTopicReaction(
            topic_key="place_history",
            trigger_words=("lugar", "arquivo", "galeria", "historia"),
            reaction_spectrum=("guarded_answer", "partial_clue", "conditional_help"),
            effect_key="mara.answers.place_context",
            advance_mode="help",
        ),
        KeywordTopicReaction(
            topic_key="founder",
            trigger_words=("fundadora", "fundador", "origem"),
            reaction_spectrum=("evasive", "defensive", "redirecting_clue"),
            effect_key="mara.responds.without_founder_identity",
            advance_mode="complicate",
        ),
        KeywordTopicReaction(
            topic_key="archive_damage",
            trigger_words=("agua", "fogo", "dano", "destruir"),
            reaction_spectrum=("immediate_intervention", "proportional_hostility"),
            effect_key="mara.reacts.to_archive_threat",
            advance_mode="hinder",
        ),
    ),
)


def _tokens(value: str) -> set[str]:
    decomposed = unicodedata.normalize("NFKD", value.casefold())
    plain = "".join(char for char in decomposed if not unicodedata.combining(char))
    return set(re.findall(r"[^\W_]+", plain, flags=re.UNICODE))


def _guidance(direction: KeywordNpcDirection, topic: KeywordTopicReaction) -> tuple[str, ...]:
    return (
        *(f"npc.{direction.npc_id}.core.{key}" for key in direction.core_traits),
        *(f"npc.{direction.npc_id}.objective.{key}" for key in direction.current_objectives),
        *(f"npc.{direction.npc_id}.reaction.{key}" for key in topic.reaction_spectrum),
        f"story.advance.{topic.advance_mode}",
    )


def mara_profile(*, disposition: str = "neutral", trust: int = 3) -> SceneNpcProfile:
    return SceneNpcProfile(
        npc_id=MARA_DIRECTION.npc_id,
        display_name=MARA_DIRECTION.display_name,
        capabilities=MARA_DIRECTION.capabilities,
        limits=MARA_DIRECTION.limits,
        local_goal=" | ".join(MARA_DIRECTION.current_objectives),
        posture=NpcPosture.GUARDED,
        relationship_id="mara",
        relationship_disposition=disposition,
        relationship_trust=trust,
        base_dice_pool=0,
        threat_level=1,
        is_supernatural=False,
        has_true_faith=False,
        corruption_index=1,
        secret_constraints=("founder_identity",),
    )


def mara_scene_options(
    *, scene: SceneState, player_input: str, turn_kind: SceneTurnKind
) -> tuple[SceneConsequenceOption, ...]:
    present = {value.casefold() for value in scene.npcs_present}
    if MARA_DIRECTION.display_name.casefold() not in present:
        return ()
    if scene.location.casefold() not in MARA_DIRECTION.scene_keys:
        return ()
    words = _tokens(player_input)
    if "mara" not in words:
        return ()
    options: list[SceneConsequenceOption] = []
    if turn_kind is SceneTurnKind.DIALOGUE:
        for topic in MARA_DIRECTION.topics:
            if words.intersection(topic.trigger_words):
                options.append(
                    SceneConsequenceOption(
                        option_id=f"mara.{topic.topic_key}",
                        priority=20,
                        beat_kind=SceneBeatKind.RESPONSE,
                        turn_kinds=(SceneTurnKind.DIALOGUE,),
                        outcomes=(SceneIntentOutcome.UNRESOLVED,),
                        required_npc_id="mara",
                        required_capabilities=("answer_local_history",),
                        effect_keys=(topic.effect_key,),
                        guidance_keys=_guidance(MARA_DIRECTION, topic),
                        npc_move=NpcBeatMove(npc_id="mara", action="mara.responds"),
                        pressure_after=ScenePressure.WATCHFUL,
                    )
                )
    return tuple(options)
