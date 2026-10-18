"""Experimental participant metadata; never imported by the game runtime.

The checks bind declared actors and final scene presence, not the grammatical
subject or meaning of arbitrary prose. Existing mechanical, agency, secrecy and
scene validators remain required. Labels are visible references, not generated
canonical IDs; anonymous sensory observations may have no actor at all.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Iterable, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from api.scene_director_service import (
    ProposedSceneFact,
    SceneContinuationProposal,
    SceneFactKind,
    SceneProposalError,
    _normalize_for_policy,
    _player_visible_scene_fields,
)
from api.scene_service import SceneState
from api.turn_models import Visibility


class SceneActor(BaseModel):
    """A public label and its presence at the end of this proposed beat."""

    model_config = ConfigDict(extra="forbid", frozen=True, populate_by_name=True)

    label: str = Field(alias="n", min_length=1, max_length=80)
    presence: Literal["present", "departed", "offscene"] = Field(alias="p")

    @field_validator("label")
    @classmethod
    def normalize_label(cls, value: str) -> str:
        label = " ".join(value.split())
        if not label or not any(character.isalnum() for character in label):
            raise ValueError("actor label must contain a non-blank name")
        return label


class FocusedSceneFact(ProposedSceneFact):
    # Required even for observations: [] means no asserted identified actor.
    actors: tuple[SceneActor, ...] = Field(alias="a", max_length=8)


class FocusedSceneContinuationProposal(SceneContinuationProposal):
    new_facts: tuple[FocusedSceneFact, ...] = Field(default=(), alias="f", max_length=4)


def actor_identity_key(label: str) -> str:
    """Normalize actor references without inventing aliases or dropping accents."""

    # Canonically equivalent Unicode is the same reference; differently named
    # actors are not aliases merely because removing accents would merge them.
    return unicodedata.normalize("NFC", " ".join(label.casefold().split()))


def _contains_label(text: str, label: str) -> bool:
    # Do not match Mara inside Tamara, or a short name inside a hyphenated name.
    return re.search(
        rf"(?<![\w'-]){re.escape(_normalize_for_policy(label))}(?![\w'-])",
        _normalize_for_policy(text),
    ) is not None


def _reject(code: str, *, field: str, rule: str) -> None:
    # Actor labels, provider text and private context must never enter errors.
    raise SceneProposalError(code, evidence={"field": field, "rule": rule})


def validate_actor_coherence(
    proposal: FocusedSceneContinuationProposal,
    previous: SceneState | None,
    *,
    player_aliases: Iterable[str] = (),
) -> FocusedSceneContinuationProposal:
    """Validate explicit participant references against the final visible roster.

    Presence is a final-state assertion, not an inferred sequence of movements.
    A newly established visible NPC needs its own npc_action/transition fact;
    departures must name a previously present NPC. Remote actors do not enter
    the roster. Private facts cannot mutate it or reveal a previously secret
    label; confidential activity of an already public NPC stays possible.
    """

    old_roster = {actor_identity_key(name) for name in previous.npcs_present} if previous else set()
    roster = {actor_identity_key(name) for name in proposal.npcs_present}
    players = {
        "voce", "eu", "jogador", "personagem", "seu personagem", "sua personagem",
        *(_normalize_for_policy(name) for name in player_aliases),
    }
    players |= {f"{article} {name}" for article in ("o", "a") for name in tuple(players)}
    visible_fields = _player_visible_scene_fields(proposal)
    visible_actor_labels = tuple(
        actor.label for fact in proposal.new_facts
        if fact.visibility in {Visibility.PUBLIC, Visibility.PLAYER}
        for actor in fact.actors
    )
    actor_states: dict[str, str] = {}
    additions: set[str] = set()
    departures: set[str] = set()
    required_events: dict[str, tuple[str, str]] = {}

    for fact_index, fact in enumerate(proposal.new_facts):
        fact_field = f"new_facts[{fact_index}]"
        if fact.kind is SceneFactKind.NPC_ACTION and not fact.actors:
            _reject("scene_actor_missing", field=f"{fact_field}.actors", rule="npc_action_requires_actor")
        seen: set[str] = set()
        for actor_index, actor in enumerate(fact.actors):
            field = f"{fact_field}.actors[{actor_index}]"
            key = actor_identity_key(actor.label)
            if _normalize_for_policy(actor.label) in players:
                _reject("scene_actor_identity_invalid", field=field, rule="player_is_not_npc")
            if key in seen:
                _reject("scene_actor_duplicate", field=field, rule="duplicate_actor_reference")
            seen.add(key)

            if not _contains_label(fact.summary, actor.label):
                _reject("scene_actor_not_grounded", field=field, rule="label_missing_from_fact")
            if key in actor_states and actor_states[key] != actor.presence:
                _reject("scene_actor_presence_conflict", field=field, rule="conflicting_final_presence")
            actor_states[key] = actor.presence

            if fact.visibility is Visibility.STORYTELLER:
                if key not in old_roster:
                    if key in roster or any(
                        _contains_label(text, actor.label)
                        for text in (*visible_fields, *visible_actor_labels)
                    ):
                        _reject("scene_private_actor_disclosed", field=field, rule="private_label_became_visible")
                elif actor.presence != "present":
                    _reject("scene_actor_presence_conflict", field=field, rule="private_fact_cannot_change_public_presence")
                # Private participation never justifies a visible roster delta.
                continue

            if not _contains_label(proposal.narrative, actor.label):
                _reject("scene_actor_not_grounded", field=field, rule="label_missing_from_narrative")
            if actor.presence == "present":
                if key not in roster:
                    _reject("scene_actor_roster_mismatch", field=field, rule="present_actor_missing_from_roster")
                if key not in old_roster:
                    required_events[key] = (actor.presence, field)
                    if fact.kind in {SceneFactKind.NPC_ACTION, SceneFactKind.TRANSITION}:
                        additions.add(key)
            elif actor.presence == "departed":
                if key not in old_roster:
                    _reject("scene_actor_departure_unestablished", field=field, rule="departure_requires_previous_presence")
                if key in roster:
                    _reject("scene_actor_roster_mismatch", field=field, rule="departed_actor_remains_in_roster")
                required_events[key] = (actor.presence, field)
                if fact.kind in {SceneFactKind.NPC_ACTION, SceneFactKind.TRANSITION}:
                    departures.add(key)
            elif key in roster:
                _reject("scene_actor_roster_mismatch", field=field, rule="offscene_actor_in_local_roster")

    # These fields assert the same final beat, not a sequence. A companion
    # observation may precede or follow the actor's own presence-change event.
    # Only the matching identity and event kind can supply that justification.
    for key, (presence, field) in required_events.items():
        if presence == "present" and key not in additions:
            _reject("scene_actor_transition_missing", field=field, rule="new_actor_requires_own_event")
        if presence == "departed" and key not in departures:
            _reject("scene_actor_transition_missing", field=field, rule="departure_requires_own_event")
    if roster != (old_roster | additions) - departures:
        _reject("scene_actor_roster_mismatch", field="npcs_present", rule="roster_delta_without_matching_actor_event")
    return proposal
