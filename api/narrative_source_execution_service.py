"""Internal opt-in source-only turn bridge; no default route or provider selection.

The caller owns the trusted deterministic draft; the persisted B origin owns
the known scene and the eligible history. Full narrative
identity authorizes an attributed source, never a new canonical assertion.
Chunks remain provisional until the existing SQLite transaction succeeds.
"""
from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable, Mapping
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
from typing import Any
from uuid import NAMESPACE_URL, uuid5

from pydantic import BaseModel

from .llm.contract import (
    CancellationToken, ErrorCategory, GenerationParameters, InvocationEvidence,
    InvocationRecord, LLMGateway, LLMInvocationError, LLMMessage, LLMTarget,
    MessageRole, StructuredGenerationRequest,
)
from .narrative_grounding import NarrativeVisibility
from .narrative_source_context import (
    ORIGIN_KEY, ORIGIN_PROTOCOL, SELECTION_KEY, SourceContextError,
    validate_source_context_origin, validate_source_scene,
    validate_source_selection, validate_source_state_context,
)
from .narrative_source_profile import (
    MAX_CONTEXT_CHARACTERS, NarrativeSourceProposal, SourceProfileError,
    build_source_context,
    create_source_projection,
)
from .narrative_source_turn import (
    INVOCATION_OPERATION, PROTOCOL, NarrativeSourceTurnEnvelope,
    create_source_turn_envelope, validate_source_turn_commit,
    _FACT_TYPES as _SOURCE_FACT_TYPES, _EVENT_TYPES as _SOURCE_EVENT_TYPES,
)
from .persistence import IdempotencyConflictError, SQLitePersistence
from .scene_director_service import SceneProposalError
from .scene_service import SceneState
from .turn_models import NarrativeRecord, TurnDraft, Visibility


MAX_USER_CHARACTERS = MAX_CONTEXT_CHARACTERS


@dataclass(frozen=True)
class SourceTurnExecutionResult:
    status: str
    operation_id: str
    turn_id: str
    turn_number: int
    narrative: NarrativeRecord | None = None
    envelope: NarrativeSourceTurnEnvelope | None = None
    evidence: InvocationEvidence | None = None
    error: dict[str, str] | None = None


class SourceTurnExecutionError(ValueError):
    """Caller/preflight error with a machine code, never input content."""

    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


class _Stopped(Exception):
    def __init__(self, status: str, code: str):
        self.status = status
        self.code = code
        super().__init__(code)


def _json(value: Any) -> str:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
        allow_nan=False,
    )


def _digest(value: Any) -> str:
    return hashlib.sha256(_json(value).encode("utf-8")).hexdigest()


def _mapping_copy(value: object) -> dict[str, Any]:
    if not isinstance(value, Mapping) or any(type(key) is not str for key in value):
        raise SourceTurnExecutionError("source_turn_mapping_invalid")
    try:
        # A JSON round trip also prevents caller/callback mutation of nested values.
        return json.loads(_json(deepcopy(dict(value))))
    except (TypeError, ValueError, UnicodeError):
        raise SourceTurnExecutionError("source_turn_mapping_invalid") from None


def _strings_copy(value: object) -> tuple[str, ...]:
    if type(value) not in (tuple, list) or any(type(item) is not str for item in value):
        raise SourceTurnExecutionError("source_turn_policy_input_invalid")
    return tuple(value)


def _audit(records: list[InvocationRecord]) -> tuple[dict | None, dict | None]:
    if not records:
        return None, None
    identities = []
    measurements = []
    for record in records:
        evidence = record.evidence
        identity = {
            "invocation_id": evidence.provenance.invocation_id,
            "operation": record.operation,
            "status": record.status.value,
        }
        identities.append({
            **identity,
            "provenance": evidence.provenance.model_dump(mode="json"),
            # Do not persist adapter exception prose or arbitrary safe_message.
            "error": (
                {"category": record.error.category.value,
                 "code": "source_turn_provider_failure"}
                if record.error is not None else None
            ),
        })
        measurements.append({
            **identity, "tokens": evidence.usage.model_dump(mode="json"),
            "cost": evidence.cost.model_dump(mode="json"),
        })
    return {"invocations": identities}, {"invocations": measurements}


async def _shielded(awaitable: Awaitable[Any]) -> Any:
    task = asyncio.ensure_future(awaitable)
    try:
        return await asyncio.shield(task)
    except asyncio.CancelledError:
        # Finish the database boundary, then let the caller re-raise cancellation.
        return await asyncio.shield(task)


def _check_cancelled(cancellation: CancellationToken) -> None:
    if cancellation.is_cancelled:
        raise _Stopped("cancelled", "source_turn_cancelled")


def _validate_envelope(
    envelope: object, narrative: object, *, draft: TurnDraft, operation_id: str,
    invocation_id: str, facts: Any, events: Any, provenance: Any,
    memory_candidates: Any = (), episodic_memories: Any = (),
) -> NarrativeSourceTurnEnvelope:
    return validate_source_turn_commit(
        envelope=envelope, narrative=narrative, session_id=draft.session_id,
        turn_id=draft.turn_id, operation_id=operation_id, attempt_id=draft.attempt_id,
        expected_invocation_id=invocation_id,
        expected_invocation_operation=INVOCATION_OPERATION,
        facts=facts, events=events, memory_candidates=memory_candidates,
        episodic_memories=episodic_memories, provenance=provenance,
    )


async def execute_source_turn(
    *, draft: TurnDraft, operation_id: str, current_scene: SceneState,
    state: Mapping[str, Any], relationships: Mapping[str, Any],
    context: Mapping[str, Any], store: SQLitePersistence, gateway: LLMGateway,
    target: LLMTarget, system_prompt: str, parameters: GenerationParameters,
    deadline: datetime, cancellation: CancellationToken,
    on_chunk: Callable[[str], Awaitable[None]],
    protected_secrets: tuple[str, ...] = (), player_aliases: tuple[str, ...] = (),
    npc_aliases: tuple[str, ...] = (), chronicle_name: str = "",
) -> SourceTurnExecutionResult:
    """Execute one explicitly selected B turn; never choose a runtime/default.

    Invalid static arguments raise a closed SourceTurnExecutionError. Once this
    function owns a new pending attempt, failures are audited and returned
    without narrative/source output; task cancellation is audited and re-raised.
    Deadline is an explicit absolute UTC-aware deadline for a new invocation.
    A terminal replay ignores its expiration and never calls the gateway.
    """
    # Snapshot every caller-owned input before the first await.
    try:
        if type(draft) is not TurnDraft:
            raise ValueError
        checked_draft = TurnDraft.model_validate(draft.model_dump(mode="json"))
        scene = (
            SceneState.model_validate(current_scene.model_dump(mode="json"))
            if type(current_scene) is SceneState else None
        )
        if type(target) is not LLMTarget or type(parameters) is not GenerationParameters:
            raise ValueError
        checked_target = LLMTarget.model_validate(target.model_dump(mode="json"))
        checked_parameters = GenerationParameters.model_validate(parameters.model_dump(mode="json"))
        if (
            type(operation_id) is not str or not operation_id.strip()
            or type(system_prompt) is not str or not system_prompt.strip()
            or type(chronicle_name) is not str
            or not isinstance(deadline, datetime) or deadline.tzinfo is None
            or deadline.utcoffset() is None or type(cancellation) is not CancellationToken
            or not callable(on_chunk)
        ):
            raise ValueError
    except (TypeError, ValueError):
        raise SourceTurnExecutionError("source_turn_arguments_invalid") from None
    if scene is None:
        return SourceTurnExecutionResult(
            "failed", operation_id, checked_draft.turn_id, checked_draft.base_revision + 1,
            error={"code": "source_profile_current_scene_required"},
        )
    state_payload = _mapping_copy(state)
    relationships_payload = _mapping_copy(relationships)
    context_payload = _mapping_copy(context)
    # This first bridge accepts no passthrough legacy memory/context. Silently
    # ignoring arbitrary context while generating from l/p would hide a dependency.
    if context_payload:
        return SourceTurnExecutionResult(
            "failed", operation_id, checked_draft.turn_id, checked_draft.base_revision + 1,
            error={"code": "source_turn_context_incompatible"},
        )
    secrets = _strings_copy(protected_secrets)
    players = _strings_copy(player_aliases)
    npcs = _strings_copy(npc_aliases)
    draft = checked_draft
    turn_number = draft.base_revision + 1
    invocation_id = str(uuid5(
        NAMESPACE_URL, _json([PROTOCOL, draft.session_id, operation_id]),
    ))
    # Dynamic sources and the absolute deadline do not change the identity of
    # the already-reserved operation. Their values are checked on a new call.
    try:
        static_digest = _digest({
            "draft": draft.model_dump(mode="json"),
            "scene": scene.model_dump(mode="json"),
            "state": state_payload, "relationships": relationships_payload,
            "context": context_payload, "system_prompt": system_prompt,
            "target": checked_target.model_dump(mode="json"),
            "parameters": checked_parameters.model_dump(mode="json"),
            "protected_secrets": secrets, "player_aliases": players,
            "npc_aliases": npcs, "chronicle_name": chronicle_name,
        })
    except (TypeError, ValueError, UnicodeError):
        raise SourceTurnExecutionError("source_turn_arguments_invalid") from None
    metadata = {
        "narrative_contract": PROTOCOL,
        "source_context_protocol": ORIGIN_PROTOCOL,
        "source_context_base_state_revision": draft.base_state_revision,
        "expected_invocation_id": invocation_id,
        "expected_invocation_operation": INVOCATION_OPERATION,
        "source_turn_static_sha256": static_digest,
        "draft_id": draft.draft_id,
        "turn_id": draft.turn_id,
    }
    campaign = await store.load_campaign(draft.session_id)
    if campaign is None:
        raise SourceTurnExecutionError("source_turn_campaign_required")
    try:
        persisted_metadata = campaign.get("metadata")
        origin = validate_source_context_origin(
            persisted_metadata.get(ORIGIN_KEY) if isinstance(persisted_metadata, dict) else None,
            session_id=draft.session_id,
        )
        scene = validate_source_scene(scene, origin)
        validate_source_state_context(state_payload, origin)
    except SourceContextError as exc:
        return SourceTurnExecutionResult(
            "failed", operation_id, draft.turn_id, turn_number, error={"code": exc.code},
        )
    start_task = asyncio.create_task(store.start_attempt(
        session_id=draft.session_id, operation_id=operation_id,
        attempt_id=draft.attempt_id, requested_turn=turn_number,
        user_input=draft.player_input, metadata=metadata,
        chronicle_name=chronicle_name,
    ))
    try:
        attempt = await asyncio.shield(start_task)
    except IdempotencyConflictError:
        return SourceTurnExecutionResult(
            "failed", operation_id, draft.turn_id, turn_number,
            error={"code": "source_turn_operation_conflict"},
        )
    except asyncio.CancelledError:
        cancellation.cancel("source turn task cancelled")
        attempt = await _shielded(start_task)
        if not attempt.idempotent:
            await _shielded(store.record_failed_attempt(
                session_id=draft.session_id, operation_id=operation_id,
                attempt_id=draft.attempt_id, requested_turn=turn_number,
                user_input=draft.player_input, status="cancelled",
                partial_narrative="", error={"code": "source_turn_cancelled"},
                metadata=metadata, chronicle_name=chronicle_name,
            ))
        raise

    if attempt.idempotent:
        if attempt.status == "completed":
            stored = await store.load_turn_by_operation(draft.session_id, operation_id)
            anchored = await store.load_attempt_by_operation(draft.session_id, operation_id)
            try:
                # All historical rows and legacy dependencies must still be
                # eligible, including rows older than the two-source window.
                replay_context = await store.read_source_context_snapshot(draft.session_id)
                validate_source_scene(scene, replay_context.origin)
                if (
                    stored is None or anchored is None
                    or anchored.get("status") != "completed"
                    or anchored.get("attempt_id") != draft.attempt_id
                    or anchored.get("session_id") != draft.session_id
                    or anchored.get("operation_id") != operation_id
                    or anchored.get("committed_turn_id") != draft.turn_id
                    or type(anchored.get("requested_turn")) is not int
                    or anchored["requested_turn"] != turn_number
                    or anchored.get("user_input") != draft.player_input
                    or _json(anchored.get("metadata")) != _json(metadata)
                    or stored.get("session_id") != draft.session_id
                    or stored.get("operation_id") != operation_id
                    or stored.get("attempt_id") != draft.attempt_id
                    or stored.get("turn_id") != draft.turn_id
                    or type(stored.get("turn_number")) is not int
                    or stored["turn_number"] != turn_number
                    or stored.get("user_input") != draft.player_input
                    or stored.get("narrative_complete") is not True
                    or type(stored.get("narrative")) is not dict
                    or stored.get("narrative_text") != stored["narrative"].get("text")
                    or _json(anchored.get("provenance")) != _json(stored.get("provenance"))
                    or type(stored.get("payload_hash")) is not str
                    or len(stored["payload_hash"]) != 64
                    or any(c not in "0123456789abcdef" for c in stored["payload_hash"])
                    or stored["payload_hash"] != anchored.get("result_hash")
                ):
                    raise ValueError("invalid replay pair")
                # The snapshot checked persisted events and empty B memory
                # collections in one transaction. The reserved static digest
                # anchors this caller's original draft for replay validation.
                # Validate the raw persisted record before any string normalization.
                envelope = _validate_envelope(
                    (stored.get("context") or {}).get("narrative_source"), stored["narrative"],
                    draft=draft, operation_id=operation_id, invocation_id=invocation_id,
                    facts=stored.get("facts") or (), events=draft.events,
                    provenance=stored.get("provenance"),
                )
                narrative = NarrativeRecord.model_validate(stored["narrative"])
            except (TypeError, ValueError, KeyError, AttributeError):
                raise SourceTurnExecutionError("source_turn_replay_invalid") from None
            return SourceTurnExecutionResult(
                "completed", operation_id, draft.turn_id, int(stored["turn_number"]),
                narrative=narrative, envelope=envelope,
            )
        return SourceTurnExecutionResult(
            attempt.status, operation_id, draft.turn_id, turn_number,
            error={"code": (
                "source_turn_operation_pending" if attempt.status == "pending"
                else "source_turn_operation_terminal"
            )},
        )

    invocations: list[InvocationRecord] = []
    evidence: InvocationEvidence | None = None
    stage = "preflight"
    committed = False

    async def fail(status: str, code: str) -> SourceTurnExecutionResult:
        provenance, usage = _audit(invocations)
        await _shielded(store.record_failed_attempt(
            session_id=draft.session_id, operation_id=operation_id,
            attempt_id=draft.attempt_id, requested_turn=turn_number,
            user_input=draft.player_input, status=status, partial_narrative="",
            error={"code": code, "stage": stage},
            provenance=provenance, usage=usage, metadata=metadata,
            chronicle_name=chronicle_name,
        ))
        return SourceTurnExecutionResult(
            status, operation_id, draft.turn_id, turn_number,
            evidence=evidence, error={"code": code, "stage": stage},
        )

    try:
        _check_cancelled(cancellation)
        # One authoritative read decides eligibility before selection or budget.
        snapshot = await store.read_source_context_snapshot(
            draft.session_id, expected_turn=draft.base_revision,
            expected_revision=draft.base_state_revision,
        )
        scene = validate_source_scene(scene, snapshot.origin)
        validate_source_state_context(state_payload, snapshot.origin)
        # Reuse the source-turn contract's closed antecedent vocabulary.
        if (
            any(fact.fact_type not in _SOURCE_FACT_TYPES for fact in draft.facts)
            or any(event.event_type not in _SOURCE_EVENT_TYPES for event in draft.events)
        ):
            raise _Stopped("failed", "source_turn_antecedents_invalid")
        source_context = build_source_context(
            session_id=draft.session_id, current_scene=scene,
            attributed_sources=tuple(item.projection for item in snapshot.sources),
        )
        visible_facts = [
            fact.model_dump(mode="json") for fact in draft.facts
            if fact.visibility in (Visibility.PUBLIC, Visibility.PLAYER)
        ]
        user_packet = _json({
            "context": source_context, "player_input": draft.player_input,
            "turn": draft.turn_id, "server_facts": visible_facts,
        })
        if len(user_packet) > MAX_USER_CHARACTERS:
            raise _Stopped("failed", "source_turn_user_size_exceeded")
        _check_cancelled(cancellation)
        seconds_remaining = (deadline - datetime.now(timezone.utc)).total_seconds()
        if seconds_remaining <= 0:
            raise _Stopped("timeout", "source_turn_deadline_exceeded")
        request = StructuredGenerationRequest(
            invocation_id=invocation_id, operation=INVOCATION_OPERATION,
            target=checked_target,
            messages=(
                LLMMessage(role=MessageRole.SYSTEM, content=system_prompt),
                LLMMessage(role=MessageRole.USER, content=user_packet),
            ),
            deadline=deadline, cancellation=cancellation,
            parameters=checked_parameters, response_model=NarrativeSourceProposal,
        )
        stage = "generation"
        async with asyncio.timeout(seconds_remaining):
            response = await gateway.generate_structured(request)
        evidence = InvocationEvidence.model_validate(response.evidence.model_dump(mode="json"))
        if (
            evidence.provenance.invocation_id != invocation_id
            or evidence.provenance.requested_target != checked_target
            or (
                evidence.provenance.effective_model.value is not None
                and evidence.provenance.effective_model.value != checked_target.model
            )
            or (
                evidence.provenance.effective_provider.value is not None
                and evidence.provenance.effective_provider.value != checked_target.provider
            )
        ):
            raise _Stopped("failed", "source_turn_invocation_mismatch")
        invocations.append(InvocationRecord.completed(INVOCATION_OPERATION, evidence))
        _check_cancelled(cancellation)
        stage = "policy"
        value = response.value
        if isinstance(value, BaseModel) and type(value) is not NarrativeSourceProposal:
            value = value.model_dump(mode="json")
        proposal = NarrativeSourceProposal.model_validate(value)
        projection = create_source_projection(
            proposal, source_id="source-" + invocation_id,
            session_id=draft.session_id, turn_id=draft.turn_id,
            invocation_id=invocation_id, current_scene=scene, facts=draft.facts,
            player_input=draft.player_input, protected_secrets=secrets,
            player_aliases=players, npc_aliases=npcs,
            visibility=NarrativeVisibility.PLAYER,
        )
        visible_events = tuple(
            event for event in draft.events
            if event.visibility in (Visibility.PUBLIC, Visibility.PLAYER)
        )
        narrative = NarrativeRecord(
            narrative_id="narrative-" + invocation_id, session_id=draft.session_id,
            turn_id=draft.turn_id, created_at=draft.created_at,
            text=proposal.player_text,
            source_event_ids=tuple(event.event_id for event in visible_events),
            invocation_id=invocation_id, visibility=Visibility.PLAYER,
        )
        provenance, usage = _audit(invocations)
        stage = "admission"
        envelope = create_source_turn_envelope(
            projection=projection, narrative=narrative,
            question=proposal.player_prompt, operation_id=operation_id,
            attempt_id=draft.attempt_id, provenance=provenance,
        )
        envelope = _validate_envelope(
            envelope, narrative, draft=draft, operation_id=operation_id,
            invocation_id=invocation_id, facts=draft.facts, events=draft.events,
            provenance=provenance,
        )
        context_payload["narrative_source"] = envelope.model_dump(mode="json")
        context_payload[SELECTION_KEY] = validate_source_selection(
            snapshot.audit_payload(), origin=snapshot.origin,
            current_turn=draft.base_revision, state_revision=draft.base_state_revision,
            history_turn_ids=snapshot.omitted_turn_ids + snapshot.selected_turn_ids,
        )
        _check_cancelled(cancellation)
        stage = "delivery"
        try:
            await on_chunk(narrative.text)
        except asyncio.CancelledError:
            raise
        except Exception:
            cancellation.cancel("source turn delivery failed")
            raise _Stopped("cancelled", "source_turn_delivery_failed") from None
        _check_cancelled(cancellation)
        stage = "commit"
        commit_task = asyncio.create_task(store.commit_turn(
            session_id=draft.session_id, operation_id=operation_id,
            turn_id=draft.turn_id, attempt_id=draft.attempt_id,
            turn_number=turn_number, base_revision=draft.base_revision,
            base_state_revision=draft.base_state_revision, state=state_payload,
            narrative=narrative, facts=draft.facts, events=draft.events,
            memory_candidates=(), episodic_memories=(),
            relationships=relationships_payload, context=context_payload,
            provenance=provenance, usage=usage, user_input=draft.player_input,
            chronicle_name=chronicle_name, narrative_contract=PROTOCOL,
        ))
        try:
            await asyncio.shield(commit_task)
        except asyncio.CancelledError as cancellation_error:
            # SQLite runs in a worker thread. Cancellation cannot roll back a
            # transaction that already won; resolve it before auditing failure.
            try:
                await _shielded(commit_task)
            except Exception:
                raise cancellation_error from None
            committed = True
            raise
        committed = True
        return SourceTurnExecutionResult(
            "completed", operation_id, draft.turn_id, turn_number,
            narrative=narrative, envelope=envelope, evidence=evidence,
        )
    except asyncio.CancelledError:
        cancellation.cancel("source turn task cancelled")
        if not committed:
            await fail("cancelled", "source_turn_cancelled")
        raise
    except _Stopped as exc:
        return await fail(exc.status, exc.code)
    except LLMInvocationError as exc:
        evidence = exc.error.evidence
        invocations.append(InvocationRecord.failed(INVOCATION_OPERATION, exc.error))
        status = {
            ErrorCategory.CANCELLED: "cancelled", ErrorCategory.TIMEOUT: "timeout",
        }.get(exc.error.category, "failed")
        return await fail(status, "source_turn_provider_failure")
    except TimeoutError:
        return await fail("timeout", "source_turn_deadline_exceeded")
    except (SourceContextError, SourceProfileError, SceneProposalError) as exc:
        return await fail("failed", exc.code)
    except Exception:
        return await fail("failed", "source_turn_" + stage + "_failed")
