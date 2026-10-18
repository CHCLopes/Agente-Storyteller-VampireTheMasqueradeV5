"""Internal B entry over retained, already resolved server preparation.

This coordinator never classifies input, rolls dice or selects a runtime. A
separate completed control record retains the capsule; only the existing H6
attempt can acquire dispatch. Pending and terminal attempts never authorize
automatic resend. No public game route uses this entry.
"""
from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable, Mapping
from copy import deepcopy
from datetime import datetime
from typing import Any

from .llm.contract import CancellationToken, GenerationParameters, LLMGateway, LLMTarget
from .narrative_source_capsule import (
    SourceTurnCapsule, create_source_turn_capsule,
    source_preparation_operation_id,
)
from .narrative_source_execution_service import SourceTurnExecutionResult, execute_source_turn
from .narrative_source_preparation import DeclaredActionPreparation, ResolvedActionPreparation
from .persistence import SQLitePersistence


class SourceCoordinatorError(ValueError):
    """Closed coordinator failure, never caller content."""

    def __init__(self, code: str):
        self.code = code if code in {
            "source_coordinator_arguments_invalid", "source_coordinator_capsule_missing",
        } else "source_coordinator_arguments_invalid"
        super().__init__(self.code)


async def prepare_retained_source_turn(
    *, session_id: str, operation_id: str, created_at: datetime,
    player_input: str, preparation: DeclaredActionPreparation | ResolvedActionPreparation,
    state: Mapping[str, Any], relationships: Mapping[str, Any],
    store: SQLitePersistence, target: LLMTarget, system_prompt: str,
    parameters: GenerationParameters, protected_secrets: tuple[str, ...] = (),
    player_aliases: tuple[str, ...] = (), npc_aliases: tuple[str, ...] = (),
    chronicle_name: str = "",
) -> SourceTurnCapsule:
    """Retain a trusted, already resolved receipt before any H6 invocation.

    Repeated input must identify the same capsule, including its original time.
    Call execute_retained_source_turn by identity to resume without supplying the
    receipt again. The caller remains responsible for any RNG performed before
    this boundary; this function does not claim an earlier mechanical gate.
    """
    source_preparation_operation_id(session_id, operation_id)
    # Capture caller-owned values before the first await. The pure factory then
    # performs strict validation, including forged model instances and extras.
    try:
        captured = deepcopy(dict(
            operation_id=operation_id, created_at=created_at, player_input=player_input,
            preparation=preparation, state=state, relationships=relationships,
            target=target, system_prompt=system_prompt, parameters=parameters,
            protected_secrets=protected_secrets, player_aliases=player_aliases,
            npc_aliases=npc_aliases, chronicle_name=chronicle_name,
        ))
    except (TypeError, ValueError):
        raise SourceCoordinatorError("source_coordinator_arguments_invalid") from None
    retained = await store.load_source_preparation(session_id, operation_id)
    snapshot = retained.snapshot if retained is not None else await store.read_source_context_snapshot(session_id)
    capsule = create_source_turn_capsule(snapshot, **captured)
    task = asyncio.create_task(store.save_source_preparation(capsule))
    try:
        await asyncio.shield(task)
    except asyncio.CancelledError:
        # Finish the local retention transaction before propagating cancellation.
        # No narrative dispatch has happened in this entry.
        while not task.done():
            try:
                await asyncio.shield(task)
            except asyncio.CancelledError:
                continue
        task.result()
        raise
    return capsule


async def execute_retained_source_turn(
    *, session_id: str, operation_id: str, store: SQLitePersistence,
    gateway: LLMGateway, deadline: datetime, cancellation: CancellationToken,
    on_chunk: Callable[[str], Awaitable[None]],
) -> SourceTurnExecutionResult:
    """Execute or replay using only the persisted static capsule and new handles.

    Gateway, cancellation, callback and deadline are never stored. The existing
    executor arbitrates simultaneous callers and validates completed replay.
    Supplying a fresh deadline does not authorize retry of a terminal operation.
    """
    source_preparation_operation_id(session_id, operation_id)
    capsule = await store.load_source_preparation(session_id, operation_id)
    if capsule is None:
        raise SourceCoordinatorError("source_coordinator_capsule_missing")
    return await execute_source_turn(
        draft=capsule.draft, operation_id=capsule.operation_id,
        current_scene=capsule.snapshot.canonical_scene,
        state=capsule.state, relationships=capsule.relationships, context={},
        store=store, gateway=gateway, target=capsule.target,
        system_prompt=capsule.system_prompt, parameters=capsule.parameters,
        deadline=deadline, cancellation=cancellation, on_chunk=on_chunk,
        protected_secrets=(), player_aliases=capsule.player_aliases,
        npc_aliases=capsule.npc_aliases, chronicle_name=capsule.chronicle_name,
    )
