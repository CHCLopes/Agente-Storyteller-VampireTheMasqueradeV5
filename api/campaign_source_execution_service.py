"""Opt-in campaign H6 execution from one retained P/K preparation."""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime, timezone
import json
from typing import Awaitable, Callable

from pydantic import BaseModel

from .campaign_progression_service import build_campaign_narrator_packet
from .campaign_source_capsule import CampaignSourceCapsule
from .campaign_source_input_service import _gate_allows
from .campaign_source_profile import (
    CampaignSourceProposal, build_campaign_source_context,
    validate_campaign_source_proposal,
)
from .campaign_source_storage import (
    campaign_attempt_metadata, claim_campaign_narrative,
    read_campaign_source_snapshot,
)
from .campaign_source_turn import (
    CONTEXT_KEY, PROTOCOL, CampaignSourceTurnEnvelope,
    create_campaign_source_turn_envelope, validate_campaign_source_turn_commit,
)
from .llm.contract import (
    CancellationToken, ErrorCategory, InvocationEvidence, InvocationRecord,
    LLMGateway, LLMInvocationError, LLMMessage, MessageRole,
    StructuredGenerationRequest,
)
from .narrative_source_execution_service import _audit, _shielded
from .narrative_source_turn import INVOCATION_OPERATION
from .persistence import SQLitePersistence
from .turn_models import NarrativeRecord, Visibility


@dataclass(frozen=True)
class CampaignSourceExecutionResult:
    status: str
    operation_id: str
    original_operation_id: str
    turn_id: str
    narrative: NarrativeRecord | None = None
    envelope: CampaignSourceTurnEnvelope | None = None
    evidence: InvocationEvidence | None = None
    error_code: str | None = None


class _Stopped(Exception):
    def __init__(self, status: str, code: str):
        self.status, self.code = status, code


async def execute_campaign_source_turn(
    *, store: SQLitePersistence, capsule: CampaignSourceCapsule,
    operation_id: str, gateway: LLMGateway, deadline: datetime,
    cancellation: CancellationToken, on_chunk: Callable[[str], Awaitable[None]],
    resumes_operation_id: str | None = None,
) -> CampaignSourceExecutionResult:
    """No new classification/RNG on H reentry or explicit H resume."""
    if (type(capsule) is not CampaignSourceCapsule or type(deadline) is not datetime
            or deadline.utcoffset() is None or type(cancellation) is not CancellationToken
            or not callable(on_chunk)):
        raise ValueError("campaign_source_execution_arguments_invalid")
    retained = CampaignSourceCapsule.model_validate(capsule.model_dump(mode="json"))
    claimed = await _shielded(claim_campaign_narrative(
        store, capsule=retained, operation_id=operation_id,
        resumes_operation_id=resumes_operation_id,
    ))
    metadata = campaign_attempt_metadata(
        retained, operation_id=operation_id, invocation_id=claimed.invocation_id,
        resumes_operation_id=resumes_operation_id,
    )
    if not claimed.newly_claimed:
        if claimed.status == "completed":
            # The read validates the whole persisted causal history and P/K/H pair.
            await read_campaign_source_snapshot(store, retained.session_id)
            stored = await store.load_turn_by_operation(retained.session_id, operation_id)
            if stored is None:
                raise ValueError("campaign_source_replay_invalid")
            events = await store.list_events(retained.session_id, after_turn=retained.draft.base_revision)
            events = tuple(item["payload"] for item in events if item["turn_id"] == retained.draft.turn_id)
            envelope = validate_campaign_source_turn_commit(
                capsule=retained, envelope=stored["context"][CONTEXT_KEY],
                narrative=stored["narrative"], provenance=stored["provenance"],
                operation_id=operation_id, attempt_id=claimed.attempt_id,
                expected_invocation_id=claimed.invocation_id,
                facts=stored["facts"], events=events,
            )
            return CampaignSourceExecutionResult(
                "completed", operation_id, retained.operation_id, retained.draft.turn_id,
                narrative=NarrativeRecord.model_validate(stored["narrative"]), envelope=envelope,
            )
        return CampaignSourceExecutionResult(
            claimed.status, operation_id, retained.operation_id,
            retained.draft.turn_id, error_code="campaign_source_operation_terminal"
            if claimed.status != "pending" else "campaign_source_operation_pending",
        )

    records: list[InvocationRecord] = []
    evidence: InvocationEvidence | None = None
    stage = "preflight"
    committed = False

    async def fail(status: str, code: str) -> CampaignSourceExecutionResult:
        provenance, usage = _audit(records)
        await _shielded(store.record_failed_attempt(
            session_id=retained.session_id, operation_id=operation_id,
            attempt_id=claimed.attempt_id,
            requested_turn=retained.draft.base_revision + 1,
            user_input=retained.player_input, status=status,
            partial_narrative="", error={"code": code, "stage": stage},
            provenance=provenance, usage=usage, metadata=metadata,
            chronicle_name=retained.config.chronicle_name,
        ))
        return CampaignSourceExecutionResult(
            status, operation_id, retained.operation_id, retained.draft.turn_id,
            evidence=evidence, error_code=code,
        )

    try:
        if cancellation.is_cancelled:
            raise _Stopped("cancelled", "campaign_source_cancelled")
        current = await read_campaign_source_snapshot(store, retained.session_id)
        if current != retained.snapshot:
            raise _Stopped("failed", "campaign_source_base_mismatch")
        packet = build_campaign_narrator_packet(retained.campaign_request,
                                                retained.campaign_effect)
        context = build_campaign_source_context(current, packet)
        user_packet = json.dumps({
            "context": context, "player_input": retained.player_input,
            "turn": retained.draft.turn_id,
            "server_facts": [fact.model_dump(mode="json") for fact in retained.draft.facts
                             if fact.visibility in (Visibility.PUBLIC, Visibility.PLAYER)],
        }, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        if len(user_packet) > 12000:
            raise _Stopped("failed", "campaign_source_packet_too_large")
        if not await _gate_allows(store, retained.session_id, retained.config):
            raise _Stopped("failed", "campaign_source_gate_blocked")
        remaining = (deadline - datetime.now(timezone.utc)).total_seconds()
        if remaining <= 0:
            raise _Stopped("timeout", "campaign_source_deadline_exceeded")
        request = StructuredGenerationRequest(
            invocation_id=claimed.invocation_id, operation=INVOCATION_OPERATION,
            target=retained.config.target,
            messages=(
                LLMMessage(role=MessageRole.SYSTEM, content=retained.config.system_prompt),
                LLMMessage(role=MessageRole.USER, content=user_packet),
            ), deadline=deadline, cancellation=cancellation,
            parameters=retained.config.parameters,
            response_model=CampaignSourceProposal,
        )
        stage = "generation"
        async with asyncio.timeout(remaining):
            response = await gateway.generate_structured(request)
        evidence = InvocationEvidence.model_validate(response.evidence.model_dump(mode="json"))
        if (evidence.provenance.invocation_id != claimed.invocation_id
                or evidence.provenance.requested_target != retained.config.target
                or evidence.provenance.effective_model.value not in (None, retained.config.target.model)
                or evidence.provenance.effective_provider.value not in (None, retained.config.target.provider)):
            raise _Stopped("failed", "campaign_source_invocation_mismatch")
        records.append(InvocationRecord.completed(INVOCATION_OPERATION, evidence))
        if cancellation.is_cancelled:
            raise _Stopped("cancelled", "campaign_source_cancelled")
        stage = "policy"
        value = response.value
        if isinstance(value, BaseModel) and type(value) is not CampaignSourceProposal:
            value = value.model_dump(mode="json")
        proposal = validate_campaign_source_proposal(
            value, packet=packet, facts=retained.draft.facts,
            snapshot=retained.snapshot,
            player_aliases=retained.config.player_aliases,
            npc_aliases=retained.config.npc_aliases,
        )
        narrative = NarrativeRecord(
            narrative_id="narrative-" + claimed.invocation_id,
            session_id=retained.session_id, turn_id=retained.draft.turn_id,
            created_at=retained.draft.created_at, text=proposal.player_text,
            source_event_ids=tuple(event.event_id for event in retained.draft.events),
            invocation_id=claimed.invocation_id, visibility=Visibility.PLAYER,
        )
        provenance, usage = _audit(records)
        envelope = create_campaign_source_turn_envelope(
            capsule=retained, proposal=proposal, narrative=narrative,
            invocation_id=claimed.invocation_id, provenance=provenance,
            operation_id=operation_id, attempt_id=claimed.attempt_id,
        )
        validate_campaign_source_turn_commit(
            capsule=retained, envelope=envelope, narrative=narrative,
            provenance=provenance, operation_id=operation_id,
            attempt_id=claimed.attempt_id,
            expected_invocation_id=claimed.invocation_id,
            facts=retained.draft.facts, events=retained.draft.events,
        )
        commit_context = {
            CONTEXT_KEY: envelope.model_dump(mode="json"),
            "campaign_source_context": retained.snapshot.audit_payload(),
        }
        after_state = dict(retained.state)
        after_state["campaign_progression"] = retained.campaign_effect.after_state.model_dump(mode="json")
        if cancellation.is_cancelled:
            raise _Stopped("cancelled", "campaign_source_cancelled")
        stage = "delivery"
        await on_chunk(narrative.text)
        if cancellation.is_cancelled:
            raise _Stopped("cancelled", "campaign_source_cancelled")
        stage = "commit"
        commit_task = asyncio.create_task(store.commit_turn(
            session_id=retained.session_id, operation_id=operation_id,
            turn_id=retained.draft.turn_id, attempt_id=claimed.attempt_id,
            turn_number=retained.draft.base_revision + 1,
            base_revision=retained.draft.base_revision,
            base_state_revision=retained.draft.base_state_revision,
            state=after_state, narrative=narrative, facts=retained.draft.facts,
            events=retained.draft.events, memory_candidates=(), episodic_memories=(),
            relationships=retained.relationships, context=commit_context,
            provenance=provenance, usage=usage, user_input=retained.player_input,
            chronicle_name=retained.config.chronicle_name,
            narrative_contract=PROTOCOL,
        ))
        try:
            await asyncio.shield(commit_task)
        except asyncio.CancelledError as exc:
            try:
                await _shielded(commit_task)
            except Exception:
                raise exc from None
            committed = True
            raise
        committed = True
        return CampaignSourceExecutionResult(
            "completed", operation_id, retained.operation_id, retained.draft.turn_id,
            narrative=narrative, envelope=envelope, evidence=evidence,
        )
    except asyncio.CancelledError:
        cancellation.cancel("campaign source task cancelled")
        if not committed:
            await fail("cancelled", "campaign_source_cancelled")
        raise
    except _Stopped as exc:
        return await fail(exc.status, exc.code)
    except LLMInvocationError as exc:
        evidence = exc.error.evidence
        records.append(InvocationRecord.failed(INVOCATION_OPERATION, exc.error))
        status = {ErrorCategory.CANCELLED: "cancelled",
                  ErrorCategory.TIMEOUT: "timeout"}.get(exc.error.category, "failed")
        return await fail(status, "campaign_source_provider_failure")
    except TimeoutError:
        return await fail("timeout", "campaign_source_deadline_exceeded")
    except Exception:
        return await fail("failed", "campaign_source_" + stage + "_failed")
