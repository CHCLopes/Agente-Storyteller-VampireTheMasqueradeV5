from __future__ import annotations

import pytest

from api.main import InitializationManager


class _WebSocketStub:
    def __init__(self) -> None:
        self.accepted = False
        self.messages: list[dict] = []

    async def accept(self) -> None:
        self.accepted = True

    async def send_json(self, message: dict) -> None:
        self.messages.append(dict(message))


@pytest.mark.asyncio
async def test_late_initialization_connection_replays_latest_state() -> None:
    manager = InitializationManager()
    ready = {
        "id": "ready",
        "status": "success",
        "message": "[3/3] Sistema Pronto!",
        "phase": 3,
        "timestamp": 1.0,
    }

    await manager.broadcast(ready)
    late_connection = _WebSocketStub()
    await manager.connect(late_connection)  # type: ignore[arg-type]

    assert late_connection.accepted is True
    assert late_connection.messages == [ready]


@pytest.mark.asyncio
async def test_retry_clears_stale_initialization_state() -> None:
    manager = InitializationManager()
    await manager.broadcast(
        {
            "status": "success",
            "message": "[3/3] Sistema Pronto!",
            "phase": 3,
            "timestamp": 1.0,
        }
    )

    await manager.clear_last_message()
    late_connection = _WebSocketStub()
    await manager.connect(late_connection)  # type: ignore[arg-type]

    assert late_connection.accepted is True
    assert late_connection.messages == []
