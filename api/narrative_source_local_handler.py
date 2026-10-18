"""Inactive local B socket handler, composed only with trusted server handles.

Connect/query observe persisted state; only an explicit submit can prepare and
execute an action. One absolute server deadline covers preparation and narrative.
Provisional executor chunks never cross the socket. Confirmed n/q are restored
from the readonly aggregate after commit. Delivery may be repeated by query and
must be deduplicated by operation_id; it is not exactly-once network delivery.

No listener, runtime/default, bootstrap, recovery or UI is activated here. The
ASGI factory owns selection/accept; this handler owns its receive/operation tasks
and settles cancellation before returning. It never retries a disconnected action.
"""
from __future__ import annotations

import asyncio
from collections.abc import Callable
import inspect
from datetime import datetime, timedelta, timezone
import json
import math

from fastapi import WebSocket
from starlette.websockets import WebSocketDisconnect

from .llm.contract import CancellationToken, LLMGateway
from .narrative_source_coordinator import execute_retained_source_turn
from .narrative_source_entry import MAX_OPERATION_ID_CHARS, SourcePlayerActionRequest, validate_source_player_action_request
from .narrative_source_input_service import prepare_source_player_action
from .narrative_source_local_selection import SourceLocalSelection
from .narrative_source_observation import validate_source_player_observation
from .narrative_source_transport import (
    project_source_briefing, project_source_operation, project_source_preparation,
    project_source_unavailable,
)

COMMAND_PROTOCOL = "narrative-source-command-v1"
MAX_COMMAND_BYTES = 16384


class SourceLocalHandlerError(ValueError):
    def __init__(self):
        super().__init__("source_local_handler_invalid")


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise SourceLocalHandlerError()
        result[key] = value
    return result


def _invalid_constant(_):
    raise SourceLocalHandlerError()


def decode_source_local_command(text: object) -> tuple[str, SourcePlayerActionRequest | str]:
    """Decode bounded JSON without duplicate-key or privileged-field coercion."""
    try:
        if type(text) is not str or len(text.encode("utf-8")) > MAX_COMMAND_BYTES:
            raise ValueError
        value = json.loads(text, object_pairs_hook=_unique_object, parse_constant=_invalid_constant)
        if type(value) is not dict or value.get("protocol") != COMMAND_PROTOCOL:
            raise ValueError
        if value.get("command") == "submit" and set(value) == {"protocol", "command", "operation_id", "player_input"}:
            return "submit", validate_source_player_action_request({
                "operation_id": value["operation_id"], "player_input": value["player_input"],
            })
        if value.get("command") == "query" and set(value) == {"protocol", "command", "operation_id"}:
            identity = value["operation_id"]
            if (type(identity) is not str or not 1 <= len(identity) <= MAX_OPERATION_ID_CHARS
                    or identity != identity.strip()):
                raise ValueError
            identity.encode("utf-8")
            return "query", identity
        raise ValueError
    except (ValueError, TypeError, AttributeError, RecursionError, OverflowError):
        raise SourceLocalHandlerError() from None


def _checked_selection(value: object) -> SourceLocalSelection:
    if type(value) is not SourceLocalSelection:
        raise SourceLocalHandlerError()
    checked = SourceLocalSelection.model_validate(value)
    if checked.destination != "source_local_trial":
        raise SourceLocalHandlerError()
    return checked


async def _settle(task: asyncio.Task | None, *, cancel: bool) -> None:
    """Cancel a transport-owned task once, then await its existing cleanup."""
    if task is None:
        return
    if cancel and not task.done():
        task.cancel()
    while not task.done():
        try:
            await asyncio.shield(task)
        except asyncio.CancelledError:
            continue
        except Exception:
            break
    try:
        task.result()
    except (asyncio.CancelledError, Exception):
        pass


def create_source_local_handler(*, gateway: LLMGateway, action_timeout_seconds: float,
        admit_submit: Callable[[SourcePlayerActionRequest], bool] | None = None):
    """Return an async handler; gateway and bounded duration belong to the server."""
    if (not isinstance(gateway, LLMGateway) or type(action_timeout_seconds) not in (int, float)
            or not math.isfinite(action_timeout_seconds) or not 0 < action_timeout_seconds <= 60):
        raise SourceLocalHandlerError()
    if admit_submit is not None and (not callable(admit_submit)
            or inspect.iscoroutinefunction(admit_submit)
            or inspect.iscoroutinefunction(getattr(admit_submit, "__call__", None))):
        raise SourceLocalHandlerError()

    def admitted(request):
        # This trusted synchronous gate precedes P, token and deadline. A false
        # result is only unavailable observation, never a fabricated P terminal.
        if admit_submit is None:
            return True
        try:
            result = admit_submit(request)
            if inspect.iscoroutine(result):
                result.close()
            return result is True
        except Exception:
            return False

    async def handle(websocket: WebSocket, selected: SourceLocalSelection) -> None:
        chosen = _checked_selection(selected)
        binding = chosen.binding
        send_lock = asyncio.Lock()
        active = None
        receiver = None
        token = None

        async def emit(event):
            async with send_lock:
                await websocket.send_json(event.model_dump(mode="json"))

        async def read(operation_id=None):
            current = _checked_selection(chosen).binding
            observed = await current.store.read_source_player_observation(current.session_id, operation_id=operation_id)
            checked = validate_source_player_observation(observed, session_id=current.session_id, operation_id=operation_id)
            after = _checked_selection(chosen).binding
            if checked.manifest != after.expected_manifest:
                raise SourceLocalHandlerError()
            return checked

        async def query(operation_id):
            try:
                observed = await read(operation_id)
                item = observed.requested
                if item.preparation is not None:
                    await emit(project_source_preparation(item.preparation, session_id=binding.session_id, operation_id=operation_id))
                if item.narrative is not None:
                    await emit(project_source_operation(item.narrative, session_id=binding.session_id,
                        operation_id=operation_id, confirmed_envelope=item.confirmed))
                elif item.preparation is None:
                    await emit(project_source_unavailable(operation_id=operation_id, phase="preparation"))
            except (WebSocketDisconnect, asyncio.CancelledError):
                raise
            except Exception:
                await emit(project_source_unavailable(operation_id=operation_id, phase="preparation"))

        async def submit(request, cancellation, deadline):
            phase = "preparation"
            try:
                await read(request.operation_id)
                claim = await prepare_source_player_action(session_id=binding.session_id, request=request,
                    store=binding.store, producer_config=binding.producer_config,
                    deadline=deadline, cancellation=cancellation)
                await emit(project_source_preparation(claim, session_id=binding.session_id, operation_id=request.operation_id))
                if claim.status != "completed":
                    return
                phase = "narrative"
                async def provisional_chunk(_):
                    # This callback precedes commit. No provisional text, event
                    # or server-side history entry is published from it.
                    return None
                await execute_retained_source_turn(session_id=binding.session_id, operation_id=request.operation_id,
                    store=binding.store, gateway=gateway, deadline=deadline,
                    cancellation=cancellation, on_chunk=provisional_chunk)
                observed = await read(request.operation_id)
                item = observed.requested
                if item.narrative is None:
                    raise SourceLocalHandlerError()
                await emit(project_source_operation(item.narrative, session_id=binding.session_id,
                    operation_id=request.operation_id, confirmed_envelope=item.confirmed))
            except (WebSocketDisconnect, asyncio.CancelledError):
                raise
            except Exception:
                await emit(project_source_unavailable(operation_id=request.operation_id, phase=phase))

        try:
            try:
                initial = await read()
            except asyncio.CancelledError:
                raise
            except Exception:
                await websocket.close(code=1011)
                return
            await emit(project_source_briefing(initial.manifest, session_id=binding.session_id))
            if initial.latest_completed is not None:
                latest = initial.latest_completed
                await emit(project_source_operation(latest.operation, session_id=binding.session_id,
                    operation_id=latest.operation.operation_id, confirmed_envelope=latest.envelope))
            receiver = asyncio.create_task(websocket.receive_text())
            while True:
                waiting = {receiver} if active is None else {receiver, active}
                completed, _ = await asyncio.wait(waiting, return_when=asyncio.FIRST_COMPLETED)
                if active is not None and active in completed:
                    await active
                    active = None
                    token = None
                if receiver not in completed:
                    continue
                try:
                    raw = receiver.result()
                    command, payload = decode_source_local_command(raw)
                except (SourceLocalHandlerError, KeyError):
                    # Starlette receive_text raises KeyError for a binary frame.
                    # Reject that frame before it can become a handler exception.
                    await websocket.close(code=1008)
                    return
                if command == "query":
                    await query(payload)
                elif active is not None:
                    await emit(project_source_unavailable(operation_id=payload.operation_id, phase="preparation"))
                elif not admitted(payload):
                    await emit(project_source_unavailable(operation_id=payload.operation_id, phase="preparation"))
                else:
                    token = CancellationToken()
                    deadline = datetime.now(timezone.utc) + timedelta(seconds=action_timeout_seconds)
                    active = asyncio.create_task(submit(payload, token, deadline))
                receiver = asyncio.create_task(websocket.receive_text())
        except WebSocketDisconnect:
            return
        finally:
            if token is not None:
                token.cancel("local source connection closed")
            await _settle(active, cancel=True)
            await _settle(receiver, cancel=True)

    return handle
