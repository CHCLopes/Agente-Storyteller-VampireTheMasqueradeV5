"""Experimental n/q-only continuation profile, isolated from canonical runtime.

A trusted caller supplies the existing scene, server facts and prior sources.
The complete scene-policy function checks n/q before a source can be created.
The private policy view supplies no derived summary, fact or thread; it is not
an instance of the legacy wire proposal and never enters its projection path.
Passing these bounded gates is not a proof of semantic fidelity or world truth.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StrictStr, field_validator

from api.narrative_grounding import (
    DerivationDestination,
    NarrativeVisibility,
    SourceProjection,
    bind_narrative_derivation,
    create_narrative_source,
    materialize_source_projection,
)
from api.scene_director_service import (
    expected_narrative_outcome,
    validate_scene_continuation,
)
from api.scene_service import SceneState
from api.turn_models import CanonicalFact

VERSION = "narrative-source-profile-v1"
CONTEXT_PROTOCOL = "narrative-source-context-v1"
MAX_ATTRIBUTED_SOURCES = 2
MAX_CONTEXT_CHARACTERS = 12000
TEXT_NORMALIZATION = "collapse_unicode_whitespace"


class SourceProfileError(ValueError):
    """Profile diagnostics contain closed codes, never narrative or secrets."""

    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


class NarrativeSourceProposal(BaseModel):
    """Only n and q are model-owned; whitespace normalization is explicit."""

    model_config = ConfigDict(
        extra="forbid", frozen=True, populate_by_name=True,
        revalidate_instances="always", hide_input_in_errors=True,
    )
    narrative: Annotated[StrictStr, Field(min_length=40, max_length=1600)] = Field(alias="n")
    player_prompt: Annotated[StrictStr, Field(min_length=3, max_length=200)] = Field(alias="q")

    @field_validator("narrative", "player_prompt", mode="before")
    @classmethod
    def normalize_whitespace(cls, value: object) -> object:
        if isinstance(value, str):
            return " ".join(value.split())
        return value

    @property
    def player_text(self) -> str:
        return f"{self.narrative}\n\n{self.player_prompt}"


@dataclass(frozen=True)
class _SourcePolicyView:
    """Attribute-only input to all existing scene gates; never persisted."""

    narrative: str
    player_prompt: str
    outcome: str
    location: str
    npcs_present: tuple[str, ...]
    scene_summary: Literal[""] = ""
    new_facts: tuple[()] = ()
    open_threads: tuple[()] = ()
    resolved_threads: tuple[()] = ()

    @property
    def player_text(self) -> str:
        return f"{self.narrative}\n\n{self.player_prompt}"


def _checked_scene(current_scene: object) -> SceneState:
    if type(current_scene) is not SceneState:
        raise SourceProfileError("source_profile_current_scene_required")
    try:
        # SceneState has no revalidate_instances policy; validate its fields.
        checked = SceneState.model_validate(current_scene.model_dump(round_trip=True))
    except ValueError:
        raise SourceProfileError("source_profile_scene_invalid") from None
    if checked.summary or checked.details or checked.open_threads:
        raise SourceProfileError("source_profile_scene_requires_location_and_npcs_only")
    return checked


def _checked_facts(facts: object) -> tuple[CanonicalFact, ...]:
    if type(facts) not in (list, tuple):
        raise SourceProfileError("source_profile_facts_invalid")
    checked = []
    resolutions = []
    for fact in facts:
        if type(fact) is not CanonicalFact:
            raise SourceProfileError("source_profile_facts_invalid")
        try:
            item = CanonicalFact.model_validate(fact.model_dump(round_trip=True))
        except ValueError:
            raise SourceProfileError("source_profile_facts_invalid") from None
        if item.fact_type == "mechanics.resolution":
            if not isinstance(item.value, dict) or type(item.value.get("is_success")) is not bool:
                raise SourceProfileError("source_profile_resolution_invalid")
            resolutions.append(item)
        checked.append(item)
    if len(resolutions) > 1:
        raise SourceProfileError("source_profile_resolution_ambiguous")
    return tuple(checked)


def validate_source_proposal(
    proposal: NarrativeSourceProposal | dict,
    *, current_scene: SceneState, facts: tuple[CanonicalFact, ...],
    player_input: str, protected_secrets: tuple[str, ...] = (),
    player_aliases: tuple[str, ...] = (), npc_aliases: tuple[str, ...] = (),
) -> NarrativeSourceProposal:
    """Apply n/q, Portuguese, outcome, agency and secrecy gates without commit.

    This new profile intentionally has no legacy require_forward_motion model
    validator: continuity lives in attributed full n, not invented f/t/r. Its
    empty f also cannot activate the legacy structured-clue success branch.
    """
    scene = _checked_scene(current_scene)
    checked_facts = _checked_facts(facts)
    if type(proposal) not in (NarrativeSourceProposal, dict):
        raise SourceProfileError("source_profile_proposal_invalid")
    checked = NarrativeSourceProposal.model_validate(proposal)
    if type(player_input) is not str:
        raise SourceProfileError("source_profile_player_input_invalid")
    for values in (protected_secrets, player_aliases, npc_aliases):
        if type(values) not in (tuple, list) or any(type(value) is not str for value in values):
            raise SourceProfileError("source_profile_policy_context_invalid")
    view = _SourcePolicyView(
        narrative=checked.narrative, player_prompt=checked.player_prompt,
        outcome=expected_narrative_outcome(checked_facts),
        location=scene.location, npcs_present=scene.npcs_present,
    )
    # All helper calls consume attributes; no schema bypass or false fact is
    # required. Do not pass this view to project_scene or runtime admission.
    validate_scene_continuation(
        view, facts=checked_facts, current_scene=scene, player_input=player_input,
        protected_secrets=protected_secrets, player_aliases=player_aliases,
        npc_aliases=npc_aliases,
    )
    return checked


def create_source_projection(
    proposal: NarrativeSourceProposal | dict,
    *, source_id: str, session_id: str, turn_id: str, invocation_id: str,
    current_scene: SceneState, facts: tuple[CanonicalFact, ...],
    player_input: str, protected_secrets: tuple[str, ...] = (),
    player_aliases: tuple[str, ...] = (), npc_aliases: tuple[str, ...] = (),
    visibility: NarrativeVisibility | str = NarrativeVisibility.PLAYER,
) -> SourceProjection:
    """Create an attributed complete n only after this profile admits n/q.

    q is not part of source.text or its hash. The source is the explicitly
    normalized proposal field, not a claim of identity with raw provider bytes.
    """
    if visibility not in (NarrativeVisibility.PUBLIC, NarrativeVisibility.PLAYER):
        raise SourceProfileError("source_profile_visibility_forbidden")
    checked = validate_source_proposal(
        proposal, current_scene=current_scene, facts=facts, player_input=player_input,
        protected_secrets=protected_secrets, player_aliases=player_aliases,
        npc_aliases=npc_aliases,
    )
    source = create_narrative_source(
        source_id=source_id, session_id=session_id, turn_id=turn_id,
        invocation_id=invocation_id, text=checked.narrative,
        source_policy=VERSION, visibility=visibility,
    )
    binding = bind_narrative_derivation(
        source, checked.narrative, destination=DerivationDestination.NARRATIVE_SOURCE_VIEW,
    )
    return materialize_source_projection(source, binding, checked.narrative)


def build_source_context(
    *, session_id: str, current_scene: SceneState,
    attributed_sources: tuple[SourceProjection, ...] = (),
) -> dict[str, object]:
    """Return an attributed experimental envelope, never CONHECIDO memory.

    This pilot only accepts a known scene with empty summary/details/threads;
    it cannot silently discard richer or legacy context. The caller
    authenticates the canonical fixture and supplied source objects.
    Recomputed bindings prove their integrity, not the identity of that caller
    or general truth. No previous summary, fact, detail or thread is projected.
    """
    scene = _checked_scene(current_scene)
    if type(session_id) is not str or not session_id.strip() or len(session_id) > 240:
        raise SourceProfileError("source_profile_session_invalid")
    if type(attributed_sources) not in (tuple, list) or len(attributed_sources) > MAX_ATTRIBUTED_SOURCES:
        raise SourceProfileError("source_profile_sources_limit")
    projections = []
    seen = {field: set() for field in ("source_id", "turn_id", "invocation_id")}
    for projection in attributed_sources:
        if type(projection) is not SourceProjection:
            raise SourceProfileError("source_profile_projection_invalid")
        if type(projection.text) is not str or not 40 <= len(projection.text) <= 1600:
            raise SourceProfileError("source_profile_source_text_bounds")
        try:
            checked = SourceProjection.model_validate(projection)
        except ValueError:
            raise SourceProfileError("source_profile_projection_invalid") from None
        source = checked.source
        if source.session_id != session_id or source.source_policy != VERSION:
            raise SourceProfileError("source_profile_source_context_mismatch")
        if source.visibility not in (NarrativeVisibility.PUBLIC, NarrativeVisibility.PLAYER):
            raise SourceProfileError("source_profile_visibility_forbidden")
        for field, values in seen.items():
            value = getattr(source, field)
            if value in values:
                raise SourceProfileError("source_profile_source_duplicate")
            values.add(value)
        projections.append(checked.model_dump(mode="json"))
    context = {
        "protocol": CONTEXT_PROTOCOL,
        "profile": VERSION,
        "metadata": {
            "experimental": True,
            "representation": "source_only",
            "canonical_admission": False,
            "semantic_truth_assessed": False,
            "text_normalization": TEXT_NORMALIZATION,
            "max_attributed_sources": MAX_ATTRIBUTED_SOURCES,
            "max_context_characters": MAX_CONTEXT_CHARACTERS,
            "serialization": "json_unicode_sorted_compact",
        },
        "canonical_scene": {"location": scene.location, "npcs_present": list(scene.npcs_present)},
        "attributed_sources": projections,
    }
    serialized = json.dumps(context, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    if len(serialized) > MAX_CONTEXT_CHARACTERS:
        raise SourceProfileError("source_profile_context_size_exceeded")
    return context
