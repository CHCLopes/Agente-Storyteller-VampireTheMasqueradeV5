"""Internal authored setup: public briefing, explicit server state, no action."""
from __future__ import annotations

import asyncio
from copy import deepcopy
from typing import Any

from .narrative_source_setup import SourceSetupManifest, create_source_setup_manifest
from .persistence import SQLitePersistence


class SourceSetupServiceError(ValueError):
    """Closed invalid-argument diagnostic without reflecting caller content."""

    def __init__(self):
        super().__init__("source_setup_service_arguments_invalid")


async def create_source_trial_setup(
    *, session_id: str, request: object, store: SQLitePersistence,
    initial_state: dict[str, Any], relationships: dict[str, Any] | None = None,
    chronicle_name: str = "",
) -> SourceSetupManifest:
    """Create one new setup with no fabricated player action or narrative.

    The caller supplies server-owned state and a separately bootstrapped store.
    Mechanical eligibility is checked by the real action producer later; this
    presentation never constructs an action merely to test that eligibility.
    Target, prompt and generation parameters belong to the later action service.
    """
    try:
        if (not isinstance(store, SQLitePersistence) or type(initial_state) is not dict
                or relationships is not None and type(relationships) is not dict
                or type(chronicle_name) is not str):
            raise ValueError
        manifest = create_source_setup_manifest(request, session_id=session_id)
        state = deepcopy(initial_state)
        relations = deepcopy({} if relationships is None else relationships)
    except (ValueError, TypeError, AttributeError, KeyError, RecursionError, OverflowError):
        raise SourceSetupServiceError() from None
    task = asyncio.create_task(store.create_source_setup_campaign(
        session_id, manifest=manifest, initial_state=state, relationships=relations,
        chronicle_name=chronicle_name,
    ))
    interrupted = False
    while not task.done():
        try:
            await asyncio.shield(task)
        except asyncio.CancelledError:
            interrupted = True
    # Observe the same worker before propagating cancellation. Never compensate
    # with a second creation: after commit, reconnection uses the public reader.
    result = task.result()
    if interrupted:
        raise asyncio.CancelledError
    return result
