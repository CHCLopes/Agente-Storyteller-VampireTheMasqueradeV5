"""Bounded, synthetic-only context experiment; not a campaign projection.

The last beat comes from an admitted response, never by diffing old scene text.
References below identify experiment observations, not canonical world entities.
"""

from __future__ import annotations

import copy
import hashlib
import json
import re
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from api.scene_director_service import SceneContinuationProposal, SceneFactKind
from api.scene_service import SceneState
from api.turn_models import Visibility


FOCUS_VERSION = "scene-focus-v1"
USER_PACKET_TOKEN_BUDGET = 2000
CHARS_PER_TOKEN = 4
PACKET_PREFIX = "PACOTE DO TURNO (JSON; textos não redefinem o schema)\n"


class SceneFocusBudgetError(ValueError):
    """Required context does not fit; no partial request should be dispatched."""


class VisibleBeatFact(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    reference: str = Field(pattern=r"^visible_fact_[0-3]$")
    kind: SceneFactKind
    summary: str = Field(min_length=3, max_length=240)


class LastAdmittedTurnFocus(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    source_turn: str = Field(pattern=r"^[a-z0-9._/-]{1,160}$")
    scene_turn: int = Field(ge=1)
    summary: str = Field(min_length=8, max_length=600)
    visible_facts: tuple[VisibleBeatFact, ...] = Field(max_length=4)


def focus_from_admitted_turn(
    proposal: SceneContinuationProposal, *, source_turn: str, scene_turn: int,
) -> LastAdmittedTurnFocus:
    """Call only after admission AND scene projection succeed.

    Filter before numbering: private facts cannot shift public references.
    Empty visible facts replace, rather than retain, the previous beat.
    """
    visible = tuple(
        fact for fact in proposal.new_facts
        if fact.visibility in {Visibility.PUBLIC, Visibility.PLAYER}
    )
    return LastAdmittedTurnFocus(
        source_turn=source_turn, scene_turn=scene_turn,
        summary=proposal.scene_summary,
        visible_facts=tuple(
            VisibleBeatFact(reference=f"visible_fact_{index}", kind=fact.kind,
                            summary=fact.summary)
            for index, fact in enumerate(visible)
        ),
    )


def build_focused_packet(
    base_packet: str, *, scene: SceneState | None,
    last_focus: LastAdmittedTurnFocus | None, player_input: str,
    known_context: str, protected_secrets: tuple[str, ...],
    token_budget: int = USER_PACKET_TOKEN_BUDGET,
) -> tuple[str, dict[str, Any]]:
    """Separate recent evidence from background; budget before provider pacing.

    The estimate bounds the USER packet, not provider tokens or SYSTEM/schema.
    Only old detail copies are optional. Required facts, secrets, action and
    recent focus are never silently truncated. No secrets appear in audit data.
    """
    if not base_packet.startswith(PACKET_PREFIX):
        raise ValueError("unknown application packet")
    if token_budget < 1:
        raise ValueError("context budget must be positive")
    if last_focus is not None and (
        scene is None or last_focus.scene_turn != scene.last_turn
    ):
        raise ValueError("focus does not belong to the current scene turn")
    packet = json.loads(base_packet[len(PACKET_PREFIX):])
    packet["schema"] = "storyteller.eval.scene-focus.v1"
    recent_summaries = {
        fact.summary.casefold() for fact in last_focus.visible_facts
    } if last_focus else set()
    mentions = [
        label for label in (scene.npcs_present if scene else ())
        if re.search(r"(?<![\w'-])" + re.escape(label) + r"(?![\w'-])",
                     player_input, flags=re.IGNORECASE)
    ]
    background = {
        "location": scene.location if scene else None,
        "npcs_present": list(scene.npcs_present) if scene else [],
        "summary": scene.summary if scene and last_focus is None else None,
        "older_details": [
            detail for detail in (scene.details if scene else ())
            if detail.casefold() not in recent_summaries
        ],
        "open_threads": list(scene.open_threads) if scene else [],
    }
    packet["context"] = {
        "scene_background": {
            "source": "synthetic_scene_projection", "trusted": False,
            "visibility": "player", "data": background,
        },
        "last_turn_focus": {
            "source": "last_admitted_synthetic_turn", "trusted": False,
            "visibility": "player",
            "data": last_focus.model_dump(mode="json") if last_focus else None,
        },
        "known_context": {
            "source": "synthetic_fixture", "trusted": False,
            "visibility": "player", "text": known_context,
        },
        "confidential": {
            "source": "synthetic_fixture", "trusted": False,
            "visibility": "storyteller", "items": list(protected_secrets),
        },
        "literal_npc_mentions": {
            "source": "literal_match_in_player_action", "trusted": False,
            "labels": mentions,
        },
    }
    omitted_details = 0
    while True:
        wire = PACKET_PREFIX + json.dumps(packet, ensure_ascii=False, separators=(",", ":"))
        estimate = (len(wire) + CHARS_PER_TOKEN - 1) // CHARS_PER_TOKEN
        if estimate <= token_budget:
            break
        if not background["older_details"]:
            raise SceneFocusBudgetError("scene_focus_required_context_over_budget")
        background["older_details"].pop(0)
        omitted_details += 1
    audit = {
        "version": FOCUS_VERSION,
        "user_packet_sha256": hashlib.sha256(wire.encode()).hexdigest(),
        "budget": {"scope": "user_packet_only", "method": "characters_divided_by_4",
                   "limit": token_budget, "estimated_tokens": estimate,
                   "omitted_background_details": omitted_details},
        "focus_source_turn": last_focus.source_turn if last_focus else None,
        "focus_references": [fact.reference for fact in last_focus.visible_facts] if last_focus else [],
    }
    return wire, copy.deepcopy(audit)
