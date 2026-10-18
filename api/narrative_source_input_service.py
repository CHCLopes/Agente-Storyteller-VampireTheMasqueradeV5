"""Internal B action entry: acquire P, produce once, finish P/K atomically.

This service accepts public intent and explicit server configuration. It never
accepts a claim, receipt, producer callback or mechanical pool from a client.
It does not dispatch H6 or select a runtime. Call the retained coordinator only
after a completed preparation; that coordinator owns narrative arbitration.
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from .llm.contract import CancellationToken
from .narrative_source_action_producer import produce_source_player_action
from .narrative_source_capsule import create_source_turn_capsule
from .narrative_source_entry import validate_source_player_action_request
from .narrative_source_input import (
    SourceInputClaim, SourceInputFailure, SourceInputRequest, SourceProducerConfig,
    create_source_input_completion, source_input_operation_id, source_input_request_hash,
)
from .narrative_source_preparation import DeclaredActionPreparation, ResolvedActionPreparation
from .persistence import SQLitePersistence


class SourceInputServiceError(ValueError):
    """Closed preflight diagnostic without input or exception details."""

    def __init__(self):
        super().__init__("source_input_service_arguments_invalid")


async def _settle_local_transaction(awaitable):
    """Settle the same local operation despite repeated task cancellation.

    A SQLite worker may have committed after its awaiter was cancelled. Observe
    that one worker's outcome before cleanup; never start another claim/finalize.
    """
    task = asyncio.ensure_future(awaitable)
    interrupted = False
    while not task.done():
        try:
            await asyncio.shield(task)
        except asyncio.CancelledError:
            interrupted = True
    return task.result(), interrupted


def _stopped(cancellation: CancellationToken, deadline: datetime) -> SourceInputFailure | None:
    if cancellation.is_cancelled:
        return SourceInputFailure(code="source_input_cancelled", stage="production")
    if datetime.now(timezone.utc) >= deadline:
        return SourceInputFailure(code="source_input_deadline_exceeded", stage="production")
    return None


async def prepare_source_player_action(
    *, session_id: str, request: object, store: SQLitePersistence,
    producer_config: SourceProducerConfig, deadline: datetime,
    cancellation: CancellationToken,
) -> SourceInputClaim:
    """Produce only on the immediate new-claim return from the server store.

    Reentry returns the original pending/terminal observation. An uncertain crash
    may leave P pending, which cannot authorize another production. Absolute
    deadline and cancellation are transient handles, never part of the request.
    Local synchronous production is bounded by its authored grammar/dice limits;
    the deadline is checked before and after it, not a preemptive CPU interrupt.
    """
    try:
        public = validate_source_player_action_request(request)
        source_input_operation_id(session_id, public.operation_id)
        if (type(producer_config) is not SourceProducerConfig
                or type(deadline) is not datetime or deadline.utcoffset() is None
                or type(cancellation) is not CancellationToken
                or not isinstance(store, SQLitePersistence)):
            raise ValueError
        config = SourceProducerConfig.model_validate(producer_config)
    except (ValueError, TypeError, AttributeError, RecursionError, OverflowError):
        raise SourceInputServiceError() from None

    observed, interrupted = await _settle_local_transaction(store.claim_source_input(
        session_id, public, producer_config=config,
    ))
    # Only this direct storage return is eligible. No user-supplied claim or
    # callable reaches the boundary; validation alone is not authentication.
    claim = SourceInputClaim.model_validate(observed)
    if not claim.newly_claimed:
        if interrupted:
            raise asyncio.CancelledError
        return claim

    original = claim.request
    failure = (SourceInputFailure(code="source_input_cancelled", stage="production")
               if interrupted else _stopped(cancellation, deadline))
    capsule = None
    if failure is None:
        try:
            # A producer receives its own copy, preserving the retained request
            # even if a faulty implementation mutates nested members locally.
            produced = produce_source_player_action(SourceInputRequest.model_validate(original))
            if type(produced) is SourceInputFailure:
                failure = SourceInputFailure.model_validate(produced)
            elif type(produced) in (DeclaredActionPreparation, ResolvedActionPreparation):
                failure = _stopped(cancellation, deadline)
                if failure is None:
                    capsule = create_source_turn_capsule(
                        original.snapshot, operation_id=original.operation_id,
                        created_at=original.created_at, player_input=original.player_input,
                        preparation=produced, state=original.state,
                        relationships=original.relationships,
                        **original.config.model_dump(exclude={"profile"}),
                    )
            else:
                raise ValueError
        except asyncio.CancelledError:
            interrupted = True
            failure = SourceInputFailure(code="source_input_cancelled", stage="production")
        except Exception:
            # Do not persist raw parser/rules exception prose or a partial receipt.
            failure = SourceInputFailure(code="source_input_production_failed", stage="production")

    if failure is None:
        completion = create_source_input_completion(original, status="completed", capsule=capsule)
    else:
        status = {"source_input_cancelled": "cancelled", "process_interrupted": "cancelled",
                  "source_input_deadline_exceeded": "timeout"}.get(failure.code, "failed")
        completion = create_source_input_completion(original, status=status, failure=failure)
        capsule = None
    finished, final_interrupted = await _settle_local_transaction(store.finalize_source_input(
        session_id, public.operation_id, request_sha256=source_input_request_hash(original),
        completion=completion, capsule=capsule,
    ))
    if interrupted or final_interrupted:
        raise asyncio.CancelledError
    return SourceInputClaim.model_validate(finished)
