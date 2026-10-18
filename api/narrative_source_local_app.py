"""Inactive ASGI factory for the trusted single-operator desktop trial.

No global app is exported or mounted by the legacy application or launcher.
The caller supplies the binding and async handler; client data never selects
the destination, target or store. Host/Origin comparisons do not authenticate
a person or prove the listening socket is bound to loopback.

The lifespan owns no background work and performs no bootstrap, migration,
recovery or diagnostics. The injected handler owns its operation cancellation,
deadline and cleanup; this boundary only selects, accepts and hands it the
internal selection. A returned handler closes normally if it has not closed
already. Handler failures/cancellation propagate without a second invocation.
"""
from __future__ import annotations

from collections.abc import Awaitable, Callable
from contextlib import asynccontextmanager
import inspect

from fastapi import FastAPI, WebSocket
from starlette.websockets import WebSocketState

from .narrative_source_local_selection import (
    SourceLocalSelection,
    select_source_local_entry,
)

SourceLocalHandler = Callable[[WebSocket, SourceLocalSelection], Awaitable[None]]


def create_source_local_app(*, binding: object, handler: SourceLocalHandler,
                            enabled: bool = False) -> FastAPI:
    """Build an unmounted app; creating or starting it never creates a session."""
    if type(enabled) is not bool or not inspect.iscoroutinefunction(handler):
        raise ValueError("source_local_app_configuration_invalid")

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        yield

    app = FastAPI(lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)

    @app.websocket("/ws/source-local/{session_id}")
    async def source_local_entry(websocket: WebSocket, session_id: str) -> None:
        selected = await select_source_local_entry(
            destination="source_local_trial", enabled=enabled, binding=binding,
            received_session_id=session_id, raw_headers=websocket.scope["headers"],
        )
        if selected.destination != "source_local_trial":
            await websocket.close(code=1008)
            return
        await websocket.accept()
        await handler(websocket, selected)
        # Receiving a disconnect leaves application_state connected, but the
        # ASGI transport has already closed and must not receive another close.
        if (websocket.application_state == WebSocketState.CONNECTED
                and websocket.client_state == WebSocketState.CONNECTED):
            await websocket.close(code=1000)

    return app
