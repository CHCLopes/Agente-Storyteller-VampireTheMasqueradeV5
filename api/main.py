from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from enum import Enum
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
import json
import os
import uuid
import asyncio
import time
from copy import deepcopy
from pathlib import Path
from anyio import CancelScope
from .rules_service import PlayerSheetModel
from .orchestrator_service import (
    NARRATOR_CONTEXT_BUDGET_MESSAGE,
    NarratorContextBudgetError,
    prepare_turn_pipeline,
    turn_requires_llm_runtime,
)
from .llm.contract import (
    CancellationToken,
    ConnectionTestRequest,
    InvocationRecord,
    LLMTarget,
    utc_now,
)
from .llm.diagnostics import ReadinessDiagnosticResult, run_readiness_diagnostics
from .llm.runtime import LLMRuntimeConfigurationError, get_llm_runtime
from .core.config import settings
from .persistence import IdempotencyConflictError
from .narration_resume_service import (
    AvailabilityGatedGateway,
    NarratorGateBlockedError,
    applicable_gates_allow,
    exact_target_scope_key,
    gate_from_error,
    scope_key_for_target,
    validate_resume_preconditions,
)
from .scene_service import scene_opening_response, seed_scene_context
from .turn_execution_service import (
    _await_under_shield,
    build_invocation_audit,
    execute_prepared_lore_turn,
    execute_prepared_turn,
    restore_prepared_turn_from_capsule,
)
from .turn_models import (
    NarrationResumeState,
    NarratorAvailabilityGate,
    NarratorGateScope,
    NarratorGateState,
)
from .state_service import (
    save_session_state,
    load_session_state,
    StateUpdateEvent,
    CharacterModel,
    TrackersModel,
    TrackerDetail,
    CharacterAttributes,
    ContextModel,
    PendingRollModel,
    sync_event_from_context,
    get_persistence,
)

PROCESS_STARTED_AT = datetime.now(timezone.utc)
LLM_READINESS_CACHE_TTL_SECONDS = 60.0
LLM_READINESS_FAILURE_CACHE_TTL_SECONDS = 5.0
_LLMReadinessCacheKey = tuple[int, str, str, str, float]
_llm_readiness_cache: dict[
    _LLMReadinessCacheKey,
    tuple[float, ReadinessDiagnosticResult],
] = {}
_llm_readiness_inflight: dict[
    _LLMReadinessCacheKey,
    asyncio.Task[ReadinessDiagnosticResult],
] = {}


def reset_llm_readiness_state_for_tests() -> None:
    """Clear process-local readiness state without touching external systems."""

    _llm_readiness_cache.clear()
    _llm_readiness_inflight.clear()


async def _run_and_cache_llm_readiness(
    *,
    key: _LLMReadinessCacheKey,
    runtime,
    deadline_seconds: float,
) -> ReadinessDiagnosticResult:
    """Own one diagnostic execution and publish even a negative result briefly."""

    try:
        diagnostics = await run_readiness_diagnostics(
            runtime.gateway,
            ConnectionTestRequest(
                target=runtime.target,
                deadline=utc_now() + timedelta(seconds=deadline_seconds),
                cancellation=CancellationToken(),
            ),
        )
        _llm_readiness_cache[key] = (time.monotonic(), diagnostics)
        return diagnostics
    finally:
        current = asyncio.current_task()
        if _llm_readiness_inflight.get(key) is current:
            _llm_readiness_inflight.pop(key, None)


async def _get_llm_readiness(
    *,
    runtime,
    deadline_seconds: float,
) -> tuple[ReadinessDiagnosticResult, bool]:
    """Return a short cached result or share one in-flight remote diagnostic."""

    key: _LLMReadinessCacheKey = (
        id(runtime.gateway),
        runtime.target.profile,
        runtime.target.provider,
        runtime.target.model,
        deadline_seconds,
    )
    now = time.monotonic()
    cached = _llm_readiness_cache.get(key)
    if cached is not None:
        cached_at, diagnostics = cached
        cache_ttl = (
            LLM_READINESS_CACHE_TTL_SECONDS
            if diagnostics.success
            else LLM_READINESS_FAILURE_CACHE_TTL_SECONDS
        )
        if now - cached_at < cache_ttl:
            return diagnostics, True
        _llm_readiness_cache.pop(key, None)

    task = _llm_readiness_inflight.get(key)
    if task is None:
        task = asyncio.create_task(
            _run_and_cache_llm_readiness(
                key=key,
                runtime=runtime,
                deadline_seconds=deadline_seconds,
            )
        )
        _llm_readiness_inflight[key] = task

    # A disconnected caller must not cancel the shared diagnostic for every
    # other caller.  The owner task removes itself and caches the result.
    return await asyncio.shield(task), False


@asynccontextmanager
async def _lifespan(_: FastAPI):
    """Recover only work that predates this single-worker process."""

    store = get_persistence()
    await store.recover_pending_attempts(
        started_before=PROCESS_STARTED_AT
    )
    await store.recover_narration_resume_trials(started_before=PROCESS_STARTED_AT)
    yield


def _gate_models(rows: list[dict]) -> tuple[NarratorAvailabilityGate, ...]:
    gates: list[NarratorAvailabilityGate] = []
    for row in rows:
        payload = row.get("payload") if isinstance(row.get("payload"), dict) else None
        if payload is not None:
            gates.append(NarratorAvailabilityGate.model_validate(payload))
    return tuple(gates)


async def _assert_narrator_gate(
    store,
    *,
    session_id: str,
    target: LLMTarget,
    direct_resume_operation_id: str | None = None,
) -> None:
    gates = _gate_models(await store.load_narrator_availability_gates(session_id))
    if not applicable_gates_allow(
        gates,
        server_now=utc_now(),
        exact_target=target,
        direct_resume_operation_id=direct_resume_operation_id,
    ):
        raise NarratorGateBlockedError("O Narrador permanece bloqueado pelo gate local.")


async def _record_narrator_available(store, *, session_id: str, target: LLMTarget) -> None:
    now = utc_now()
    rows = await store.load_narrator_availability_gates(session_id)
    gates = _gate_models(rows)
    for gate in gates:
        if applicable_gates_allow((gate,), server_now=now, exact_target=target):
            continue
        if gate.scope_key != scope_key_for_target(gate.scope, target):
            continue
        await store.upsert_narrator_availability_gate(
            session_id=session_id,
            gate=gate.model_copy(update={
                "state": NarratorGateState.AVAILABLE,
                "observed_at": now,
                "retry_not_before": None,
                "lease_operation_id": None,
                "timing_source": "completed_call",
                "timing_confidence": "observed",
            }),
        )
    key = exact_target_scope_key(target)
    await store.upsert_narrator_availability_gate(
        session_id=session_id,
        gate=NarratorAvailabilityGate(
            gate_id=f"gate-{key[:24]}",
            state=NarratorGateState.AVAILABLE,
            scope=NarratorGateScope.EXACT_TARGET,
            scope_key=key,
            target=target.model_dump(mode="json"),
            observed_at=now,
            evidence_scope="exact_target",
            timing_source="completed_call",
            timing_confidence="observed",
        ),
    )


async def _mark_direct_resume_trial(
    store,
    *,
    session_id: str,
    target: LLMTarget,
    operation_id: str,
) -> None:
    now = utc_now()
    gates = _gate_models(await store.load_narrator_availability_gates(session_id))
    applicable = [
        gate for gate in gates
        if gate.scope_key == scope_key_for_target(gate.scope, target)
    ]
    if not applicable:
        key = exact_target_scope_key(target)
        applicable = [NarratorAvailabilityGate(
            gate_id=f"gate-{key[:24]}", state=NarratorGateState.UNAVAILABLE,
            scope=NarratorGateScope.EXACT_TARGET, scope_key=key,
            target=target.model_dump(mode="json"), observed_at=now,
            evidence_scope="exact_target", timing_source="none",
            timing_confidence="unknown",
        )]
    for gate in applicable:
        await store.upsert_narrator_availability_gate(
            session_id=session_id,
            gate=gate.model_copy(update={
                "state": NarratorGateState.DIRECT_RESUME_TRIAL,
                "observed_at": now,
                "lease_operation_id": operation_id,
            }),
        )


async def _release_direct_resume_trial(
    store,
    *,
    session_id: str,
    target: LLMTarget,
    operation_id: str,
) -> None:
    """Fail closed when a locally claimed direct trial does not reach H6."""

    now = utc_now()
    gates = _gate_models(await store.load_narrator_availability_gates(session_id))
    for gate in gates:
        if (
            gate.scope_key == scope_key_for_target(gate.scope, target)
            and gate.state is NarratorGateState.DIRECT_RESUME_TRIAL
            and gate.lease_operation_id == operation_id
        ):
            await store.upsert_narrator_availability_gate(
                session_id=session_id,
                gate=gate.model_copy(update={
                    "state": NarratorGateState.UNAVAILABLE,
                    "observed_at": now,
                    "lease_operation_id": None,
                }),
            )


def _gated_gateway(
    store,
    *,
    session_id: str,
    gateway,
    direct_resume_operation_id: str | None = None,
):
    async def before_dispatch(_operation: str, target: LLMTarget) -> None:
        await _assert_narrator_gate(
            store,
            session_id=session_id,
            target=target,
            direct_resume_operation_id=direct_resume_operation_id,
        )

    async def after_success(target: LLMTarget) -> None:
        await _record_narrator_available(store, session_id=session_id, target=target)

    async def after_failure(error) -> None:
        gate = gate_from_error(error, server_now=utc_now())
        if gate is not None:
            await store.upsert_narrator_availability_gate(
                session_id=session_id, gate=gate,
            )

    return AvailabilityGatedGateway(
        gateway,
        before_dispatch=before_dispatch,
        after_success=after_success,
        after_failure=after_failure,
    )


app = FastAPI(title="Agente Storyteller Motor V5", lifespan=_lifespan)
from .local_request_security import LocalRequestBoundary

app.add_middleware(LocalRequestBoundary, frontend_origins=(
    settings.frontend_url, 'http://localhost:5173', 'http://127.0.0.1:5173',
))
MAX_PLAYER_INPUT_CHARS = 500
MAX_OPERATION_ID_CHARS = 128


def _decode_turn_input(raw_input: str) -> tuple[str, str, bool]:
    """Decode the client envelope while retaining the legacy text protocol."""

    try:
        payload = json.loads(raw_input)
    except json.JSONDecodeError:
        payload = None
    if isinstance(payload, dict) and (
        "operation_id" in payload or "input" in payload
    ):
        operation_id = payload.get("operation_id")
        user_input = payload.get("input")
        if not isinstance(operation_id, str) or not operation_id.strip():
            raise ValueError("O envelope da ação requer operation_id não vazio.")
        operation_id = operation_id.strip()
        if len(operation_id) > MAX_OPERATION_ID_CHARS:
            raise ValueError(
                "O operation_id excede o limite de "
                f"{MAX_OPERATION_ID_CHARS} caracteres."
            )
        if not isinstance(user_input, str):
            raise ValueError("O envelope da ação requer input textual.")
        return operation_id, user_input.strip(), True
    return f"op-{uuid.uuid4()}", raw_input.strip(), False


def _decode_narration_command(raw_input: str) -> dict | None:
    try:
        payload = json.loads(raw_input)
    except (TypeError, json.JSONDecodeError):
        return None
    if not isinstance(payload, dict) or payload.get("command") not in {
        "resume_narration", "abandon_narration",
    }:
        return None
    capsule_id = payload.get("capsule_id")
    operation_id = payload.get("operation_id")
    revision = payload.get("expected_state_revision")
    if (
        not isinstance(capsule_id, str) or not capsule_id.strip()
        or not isinstance(operation_id, str) or not operation_id.strip()
        or not isinstance(revision, int) or isinstance(revision, bool) or revision < 0
    ):
        raise ValueError("Comando de retomada inválido.")
    return {
        "command": payload["command"], "capsule_id": capsule_id.strip(),
        "operation_id": operation_id.strip(), "expected_state_revision": revision,
    }


def _pause_payload(row: dict) -> dict:
    payload = row.get("payload") if isinstance(row.get("payload"), dict) else {}
    reason = payload.get("normalized_reason") if isinstance(payload.get("normalized_reason"), dict) else {}
    resolution = payload.get("resolution") if isinstance(payload.get("resolution"), dict) else None
    return {
        "action": "narration_paused", "status": "paused",
        "capsule_id": row.get("capsule_id") or payload.get("capsule_id"),
        "source_operation_id": payload.get("source_operation_id"),
        "expected_state_revision": payload.get("state_revision", 0),
        "action_summary": payload.get("action"),
        "resolution_summary": resolution.get("display") if resolution else None,
        "category": reason.get("category", "unknown"),
        "safe_message": reason.get("safe_message", "A narração está pausada."),
        "retryable": bool(reason.get("retryable", True)),
        "retry_not_before": reason.get("retry_not_before"),
        "server_now": reason.get("server_now") or utc_now().isoformat(),
        "rate_limit_origin": (
            (reason.get("rate_limit") or {}).get("origin")
            if isinstance(reason.get("rate_limit"), dict) else None
        ),
        "gate_scope": reason.get("gate_scope"),
        "evidence_scope": reason.get("evidence_scope"),
        "allowed_actions": ["resume", "abandon"],
    }


def _turn_error(
    message: str,
    *,
    operation_id: str | None = None,
    terminal: bool = False,
) -> dict[str, object]:
    payload: dict[str, object] = {"action": "error", "message": message}
    if operation_id is not None:
        payload["operation_id"] = operation_id
        payload["terminal"] = terminal
    return payload


def _user_safe_turn_failure_message(error: object) -> str:
    if not isinstance(error, dict):
        return "Esta operação terminou sem alterar o estado."
    code = error.get("code")
    localized = {
        "scene_npc_roster_changed_without_event": (
            "Não foi possível validar a continuidade dos personagens presentes; "
            "este turno não foi salvo."
        ),
        "scene_secret_disclosed": (
            "Não foi possível validar a separação das informações reservadas; "
            "a resposta não foi exibida e este turno não foi salvo."
        ),
        "generation_truncated": (
            "A resposta do Narrador ultrapassou o limite e foi descartada com "
            "segurança. Tente novamente."
        ),
        "structured_output_schema_mismatch": (
            "O Narrador não concluiu uma continuação válida; este turno não foi "
            "salvo. Tente novamente."
        ),
        "operation_deadline_exceeded": (
            "O Narrador demorou além do limite; este turno não foi salvo. "
            "Tente novamente."
        ),
    }
    if code in localized:
        return localized[code]
    if isinstance(code, str) and code.startswith("scene_"):
        return (
            "A continuação proposta contrariou a cena, a agência ou o resultado "
            "mecânico; este turno não foi salvo. Tente novamente."
        )
    safe_message = error.get("safe_message")
    if isinstance(safe_message, str) and safe_message.strip():
        return safe_message.strip()
    return "Esta operação terminou sem alterar o estado."


def _turn_failure_payloads(
    *,
    operation_id: str,
    attempt: dict,
    expose_operation: bool,
) -> tuple[dict[str, object], dict[str, object] | None]:
    """Build the same terminal failure sequence for first delivery and replay."""

    error = attempt.get("error") or {}
    is_clarification = isinstance(error, dict) and (
        error.get("category") == "clarification"
        or error.get("code") == "roll_pool_required"
    )
    if is_clarification:
        error_payload: dict[str, object] = {
            "action": "clarification",
            "message": _user_safe_turn_failure_message(error),
            "code": str(error.get("code") or "clarification_required"),
        }
        if expose_operation:
            error_payload.update(
                {"operation_id": operation_id, "terminal": True}
            )
    else:
        error_payload = _turn_error(
            _user_safe_turn_failure_message(error),
            operation_id=(operation_id if expose_operation else None),
            terminal=expose_operation,
        )
    if not expose_operation:
        return error_payload, None

    terminal: dict[str, object] = {
        "action": "stream_end",
        "operation_id": operation_id,
        "status": str(attempt.get("status") or "failed"),
        "partial": bool(attempt.get("partial_narrative")),
    }
    metadata = attempt.get("metadata") or {}
    turn_id = metadata.get("turn_id") if isinstance(metadata, dict) else None
    if isinstance(turn_id, str) and turn_id:
        terminal["turn_id"] = turn_id
    return error_payload, terminal


async def _send_recorded_turn_failure(
    websocket: WebSocket,
    *,
    session_id: str,
    operation_id: str,
    store,
    expose_operation: bool,
    attempt: dict | None = None,
) -> None:
    persisted = attempt or await store.load_attempt_by_operation(
        session_id, operation_id
    )
    if persisted is None:
        persisted = {
            "status": "failed",
            "error": {
                "safe_message": (
                    "A operação falhou com segurança; o estado não mudou."
                )
            },
            "partial_narrative": "",
            "metadata": {},
        }
    error_payload, terminal = _turn_failure_payloads(
        operation_id=operation_id,
        attempt=persisted,
        expose_operation=expose_operation,
    )
    await websocket.send_json(error_payload)
    if terminal is not None:
        await websocket.send_json(terminal)


async def _terminalize_unexpected_claimed_turn(
    *,
    session_id: str,
    operation_id: str,
    attempt_id: str,
    requested_turn: int,
    user_input: str,
    chronicle_name: str,
    turn_id: str,
    store,
    status: str = "failed",
) -> dict | None:
    """Fail a claimed turn only while it is still pending.

    The diagnostic is deliberately fixed: exception text, tracebacks, prompts,
    provider payloads, and credentials must never enter persistence or the
    player-facing protocol through this last-resort boundary.
    """

    persisted = await _await_under_shield(
        store.load_attempt_by_operation(session_id, operation_id)
    )
    if persisted is not None and persisted.get("status") != "pending":
        return persisted

    diagnostic = {
        "timeout": {
            "category": "timeout",
            "code": "operation_deadline_exceeded",
            "safe_message": (
                "O Narrador demorou além do limite; este turno não foi salvo."
            ),
        },
        "cancelled": {
            "category": "cancelled",
            "code": "request_task_cancelled",
            "safe_message": "A solicitação terminou antes da conclusão do turno.",
        },
    }.get(
        status,
        {
            "category": "application",
            "code": "unexpected_turn_execution_failure",
            "safe_message": (
                "A execução do turno falhou; o estado confirmado foi preservado."
            ),
        },
    )
    await _await_under_shield(
        store.record_failed_attempt(
            session_id=session_id,
            operation_id=operation_id,
            attempt_id=attempt_id,
            requested_turn=requested_turn,
            user_input=user_input,
            status=status,
            error=diagnostic,
            metadata={
                "boundary": "websocket_turn_execution",
                "turn_id": turn_id,
            },
            chronicle_name=chronicle_name,
        )
    )
    return await _await_under_shield(
        store.load_attempt_by_operation(session_id, operation_id)
    )


async def _replay_turn_attempt(
    websocket: WebSocket,
    *,
    session_id: str,
    operation_id: str,
    attempt: dict,
    store,
) -> None:
    status = str(attempt["status"])
    if status == "pending":
        await websocket.send_json(
            {
                "action": "operation_pending",
                "operation_id": operation_id,
                "status": "pending",
                "message": "Esta ação já está em processamento.",
            }
        )
        return

    metadata = attempt.get("metadata") or {}
    websocket_terminal = (
        metadata.get("websocket_terminal") if isinstance(metadata, dict) else None
    )
    if isinstance(websocket_terminal, dict):
        await websocket.send_json(websocket_terminal)
        if metadata.get("include_state"):
            state = await load_session_state(session_id)
            if state is not None:
                await websocket.send_json(state.model_dump(mode="json"))
        return

    if status == "completed":
        turn = await store.load_turn_by_operation(session_id, operation_id)
        state = await load_session_state(session_id)
        if turn is None or state is None:
            await websocket.send_json(
                _turn_error(
                    "A operação concluída não pôde ser reidratada.",
                    operation_id=operation_id,
                    terminal=True,
                )
            )
            return
        await websocket.send_json(state.model_dump(mode="json"))
        turn_context = turn.get("context") or {}
        resolution_receipt = (
            turn_context.get("resolution_receipt")
            if isinstance(turn_context, dict)
            else None
        )
        terminal_payload = (
            {
                "action": "stream_end",
                "operation_id": operation_id,
                "turn_id": turn["turn_id"],
                "status": "completed",
                "narrative": turn["narrative"],
                "replayed": True,
            }
        )
        if isinstance(resolution_receipt, dict):
            terminal_payload["resolution_receipt"] = resolution_receipt
        await websocket.send_json(terminal_payload)
        return

    await _send_recorded_turn_failure(
        websocket,
        session_id=session_id,
        operation_id=operation_id,
        store=store,
        expose_operation=True,
        attempt=attempt,
    )

# --- GERENCIADOR DE INICIALIZAÇÃO (WS & LOGS) ---
class InitializationManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []
        self._last_message: dict | None = None
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        async with self._lock:
            self.active_connections.append(websocket)
            if self._last_message is not None:
                try:
                    await websocket.send_json(dict(self._last_message))
                except Exception:
                    self.active_connections.remove(websocket)
                    raise

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        async with self._lock:
            self._last_message = dict(message)
            for connection in list(self.active_connections):
                try:
                    await connection.send_json(message)
                except Exception:
                    if connection in self.active_connections:
                        self.active_connections.remove(connection)

    async def clear_last_message(self):
        async with self._lock:
            self._last_message = None

initialization_manager = InitializationManager()

class InitLogPayload(BaseModel):
    status: str
    message: str
    phase: int
    timestamp: float

@app.post("/api/initialization/logs")
async def receive_init_log(payload: InitLogPayload):
    data = payload.model_dump()
    data["id"] = f"{payload.timestamp}-{hash(payload.message)}"
    await initialization_manager.broadcast(data)
    return {"status": "ok", "log_id": data["id"]}

@app.websocket("/ws/initialization")
async def websocket_initialization(websocket: WebSocket):
    await initialization_manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        initialization_manager.disconnect(websocket)
    except Exception:
        initialization_manager.disconnect(websocket)

@app.post("/api/initialization/retry")
async def retry_initialization():
    import subprocess
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    script_path = os.path.join(project_root, "scripts", "initialize_game.py")
    venv_python = os.path.join(project_root, ".venv", "Scripts", "python.exe") if os.name == 'nt' else os.path.join(project_root, ".venv", "bin", "python")
    if not os.path.exists(venv_python):
        venv_python = "python"
        
    cmd = [venv_python, script_path, "--no-browser"]
    try:
        await initialization_manager.clear_last_message()
        subprocess.Popen(
            cmd,
            cwd=project_root,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == 'nt' else 0
        )
        return {"status": "ok"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


SHEETS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "sheets")
os.makedirs(SHEETS_DIR, exist_ok=True)

def load_player_sheet(character_id: str) -> PlayerSheetModel:
    path = os.path.join(SHEETS_DIR, f"{character_id}.json")
    if not os.path.exists(path):
        path = os.path.join(SHEETS_DIR, "base_player.json")
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return PlayerSheetModel(**data)
    except Exception as e:
        raise ValueError(f"Ficha de jogador corrompida: {str(e)}")

class StateEnum(Enum):
    MENU = "MENU"
    PLAYING = "PLAYING"

class SessionData:
    def __init__(self):
        self.state = StateEnum.MENU
        self.active_campaign_id = None
        self.turn = 1
        self.chronicle_name = "Noites de Sangue"
        
        try:
            sheet_model = load_player_sheet("base_player")
            self.context = {
                "player_sheet": sheet_model.model_dump(),
                "last_action_cache": None,
                "pre_roll_snapshot": None
            }
        except Exception:
            self.context = {}

active_sessions = {}

def create_new_campaign() -> str:
    new_session = f"chronicle_{uuid.uuid4().hex[:8]}"
    return new_session


@app.get("/health")
async def health_check():
    return {"status": "ok"}


@app.get("/api/llm/capabilities")
async def llm_capabilities():
    """Expose only the configured target contract, never endpoint or secrets."""

    try:
        runtime = get_llm_runtime()
    except LLMRuntimeConfigurationError as exc:
        return {"configured": False, "message": str(exc)}
    return {
        "configured": True,
        "target": runtime.target.model_dump(mode="json"),
        "capabilities": runtime.gateway.capabilities(runtime.target).model_dump(
            mode="json"
        ),
    }


@app.post("/api/llm/test-connection")
async def test_llm_connection():
    """Exercise the configured target with fixed, campaign-free MVP probes."""

    try:
        runtime = get_llm_runtime()
    except LLMRuntimeConfigurationError as exc:
        return {"configured": False, "success": False, "message": str(exc)}

    # One shared deadline bounds the complete three-probe sequence.  Sixty
    # seconds is enough for the local initializer while still respecting a
    # smaller explicitly configured product timeout.
    deadline_seconds = min(float(settings.llm_timeout_seconds), 60.0)
    diagnostics, cache_hit = await _get_llm_readiness(
        runtime=runtime,
        deadline_seconds=deadline_seconds,
    )
    public_diagnostics = diagnostics.model_dump(mode="json")
    result = diagnostics.connection_result
    if result is None:
        return {
            "configured": True,
            "cached": cache_hit,
            "ready": False,
            "success": False,
            "message": diagnostics.message,
            "diagnostics": public_diagnostics,
        }

    return {
        "configured": True,
        "cached": cache_hit,
        "ready": diagnostics.success,
        **result.model_dump(mode="json"),
        "diagnostics": public_diagnostics,
    }

@app.websocket("/ws/session/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    await websocket.accept()
    input_queue: asyncio.Queue[str | None] = asyncio.Queue(
        maxsize=settings.queue_max_size
    )
    reader_task: asyncio.Task | None = None
    current_cancellation: CancellationToken | None = None

    async def read_client_inputs() -> None:
        nonlocal current_cancellation
        try:
            while True:
                message = await websocket.receive_text()
                try:
                    input_queue.put_nowait(message)
                except asyncio.QueueFull:
                    if current_cancellation is not None:
                        current_cancellation.cancel("client input queue overflow")
                    try:
                        await websocket.close(
                            code=1008,
                            reason="too many queued actions",
                        )
                    except Exception:
                        pass
                    break
        except (WebSocketDisconnect, RuntimeError):
            if current_cancellation is not None:
                current_cancellation.cancel("client transport disconnected")
        except Exception:
            if current_cancellation is not None:
                current_cancellation.cancel("client transport failed")
        finally:
            while not input_queue.empty():
                try:
                    input_queue.get_nowait()
                except asyncio.QueueEmpty:
                    break
            input_queue.put_nowait(None)

    from .relationship_service import (
        get_relationships_for_frontend,
        load_relationships,
        save_relationships,
    )
    from .state_service import acquire_session_lock, get_persistence

    try:
        event_data = await load_session_state(session_id)
        created = event_data is None
        if created:
            try:
                sheet_model = load_player_sheet("base_player")
                initial_context = {
                    "player_sheet": sheet_model.model_dump(),
                    "last_action_cache": None,
                    "pre_roll_snapshot": None,
                }
            except Exception:
                initial_context = {}
            seed_scene_context(initial_context)
            event_data = sync_event_from_context(session_id, initial_context)
            await save_session_state(session_id, event_data)

        rel_state = await load_relationships(session_id)
        if created:
            await save_relationships(rel_state)
        event_data.relationships = get_relationships_for_frontend(rel_state)

        session = active_sessions.setdefault(session_id, SessionData())
        session.active_campaign_id = session.active_campaign_id or create_new_campaign()
        session.state = StateEnum.PLAYING
        session.context = event_data.player_sheet or {}
        session.turn = event_data.turn_number + 1
        campaign = await get_persistence().load_campaign(session_id)
        stored_chronicle_name = (
            campaign.get("chronicle_name") if campaign is not None else None
        )
        if isinstance(stored_chronicle_name, str) and stored_chronicle_name.strip():
            session.chronicle_name = stored_chronicle_name

        # Every connection, including a reconnection, receives a complete snapshot.
        await websocket.send_json(event_data.model_dump(mode="json"))
        active_pause = await get_persistence().load_active_narration_resume_capsule(session_id)
        if active_pause is not None:
            await websocket.send_json(_pause_payload(active_pause))
        if created:
            await websocket.send_json({
                "action": "chat_response",
                "message": scene_opening_response(event_data.context.scene),
            })

        reader_task = asyncio.create_task(read_client_inputs())
        while True:
            raw_input = await input_queue.get()
            if raw_input is None:
                break
            try:
                narration_command = _decode_narration_command(raw_input)
            except ValueError as exc:
                await websocket.send_json(_turn_error(str(exc), terminal=True))
                continue
            if narration_command is not None:
                async with acquire_session_lock(session_id):
                    store = get_persistence()
                    existing_resume_attempt = await store.load_attempt_by_operation(
                        session_id, narration_command["operation_id"]
                    )
                    if existing_resume_attempt is not None:
                        await _replay_turn_attempt(
                            websocket,
                            session_id=session_id,
                            operation_id=narration_command["operation_id"],
                            attempt=existing_resume_attempt,
                            store=store,
                        )
                        if existing_resume_attempt.get("status") != "completed":
                            still_active = await store.load_active_narration_resume_capsule(
                                session_id
                            )
                            if still_active is not None:
                                await websocket.send_json(_pause_payload(still_active))
                        continue
                    active_pause = await store.load_active_narration_resume_capsule(session_id)
                    if active_pause is None or active_pause.get("capsule_id") != narration_command["capsule_id"]:
                        await websocket.send_json(_turn_error("A pausa não está mais ativa.", operation_id=narration_command["operation_id"], terminal=True))
                        continue
                    if narration_command["command"] == "abandon_narration":
                        abandoned = await store.transition_narration_resume(
                            session_id=session_id, capsule_id=narration_command["capsule_id"],
                            from_state="paused", to_state="abandoned",
                        )
                        await websocket.send_json({
                            "action": "narration_abandoned", "terminal": True,
                            "operation_id": narration_command["operation_id"],
                            "capsule_id": narration_command["capsule_id"],
                            "status": "abandoned" if abandoned else "conflict",
                        })
                        continue

                    event_data = await load_session_state(session_id)
                    if event_data is None:
                        await websocket.send_json(_turn_error("Sessão canônica indisponível.", operation_id=narration_command["operation_id"], terminal=True))
                        continue
                    claimed_resume = False
                    try:
                        runtime = get_llm_runtime()
                        payload = active_pause.get("payload") or {}
                        frozen_target = payload.get("requested_target")
                        if runtime.target.model_dump(mode="json") != frozen_target:
                            raise ValueError("O alvo do Narrador mudou desde a pausa.")
                        validate_resume_preconditions(
                            state=NarrationResumeState(active_pause.get("state")),
                            capsule_revision=int(payload.get("state_revision", -1)),
                            expected_revision=narration_command["expected_state_revision"],
                            source_target=frozen_target,
                            requested_target=runtime.target.model_dump(mode="json"),
                            retry_not_before=None,
                            server_now=utc_now(),
                        )
                        source_attempt = await store.load_attempt_by_operation(
                            session_id, str(payload.get("source_operation_id") or "")
                        )
                        if (
                            source_attempt is None
                            or source_attempt.get("request_hash") != payload.get("request_hash")
                        ):
                            raise ValueError("A integridade da ação preservada não pôde ser confirmada.")
                        await _assert_narrator_gate(
                            store,
                            session_id=session_id,
                            target=runtime.target,
                            direct_resume_operation_id=narration_command["operation_id"],
                        )
                        claimed = await store.claim_narration_resume(
                            session_id=session_id, capsule_id=narration_command["capsule_id"],
                            resume_operation_id=narration_command["operation_id"],
                            expected_state_revision=narration_command["expected_state_revision"],
                        )
                        claimed_resume = True
                        await _mark_direct_resume_trial(
                            store,
                            session_id=session_id,
                            target=runtime.target,
                            operation_id=narration_command["operation_id"],
                        )
                        guarded_gateway = _gated_gateway(
                            store,
                            session_id=session_id,
                            gateway=runtime.gateway,
                            direct_resume_operation_id=narration_command["operation_id"],
                        )
                        prepared = restore_prepared_turn_from_capsule(
                            claimed["payload_json"],
                            resume_operation_id=narration_command["operation_id"],
                        )
                        attempt = await store.start_attempt(
                            session_id=session_id,
                            operation_id=narration_command["operation_id"],
                            attempt_id=prepared.draft.attempt_id,
                            requested_turn=prepared.draft.base_revision + 1,
                            user_input=prepared.draft.player_input,
                            metadata={"resumes_operation_id": payload.get("source_operation_id"), "capsule_id": narration_command["capsule_id"]},
                            chronicle_name=session.chronicle_name,
                        )
                    except Exception:
                        if claimed_resume:
                            await store.transition_narration_resume(
                                session_id=session_id,
                                capsule_id=narration_command["capsule_id"],
                                from_state="direct_resume_trial",
                                to_state="paused",
                                resume_operation_id=narration_command["operation_id"],
                            )
                            await _release_direct_resume_trial(
                                store,
                                session_id=session_id,
                                target=runtime.target,
                                operation_id=narration_command["operation_id"],
                            )
                        await websocket.send_json(_turn_error("A retomada não pôde ser iniciada com o alvo e a revisão preservados.", operation_id=narration_command["operation_id"], terminal=True))
                        continue

                    cancellation = CancellationToken()
                    current_cancellation = cancellation
                    await websocket.send_json({
                        "action": "stream_start", "operation_id": narration_command["operation_id"],
                        "turn_id": prepared.draft.turn_id, "resumes_operation_id": payload.get("source_operation_id"),
                    })

                    async def send_resume_chunk(chunk: str) -> None:
                        await websocket.send_json({
                            "action": "stream_chunk", "operation_id": narration_command["operation_id"],
                            "turn_id": prepared.draft.turn_id, "chunk": chunk, "provisional": True,
                        })

                    try:
                        result = await execute_prepared_turn(
                            prepared, session_id=session_id,
                            operation_id=narration_command["operation_id"],
                            user_input=prepared.draft.player_input,
                            chronicle_name=session.chronicle_name, store=store,
                            gateway=guarded_gateway, target=runtime.target,
                            cancellation=cancellation, on_chunk=send_resume_chunk,
                            preclaimed_attempt=attempt,
                            resumes_operation_id=payload.get("source_operation_id"),
                            resume_capsule_id=narration_command["capsule_id"],
                        )
                    except BaseException:
                        await _await_under_shield(store.transition_narration_resume(
                            session_id=session_id,
                            capsule_id=narration_command["capsule_id"],
                            from_state="direct_resume_trial",
                            to_state="paused",
                            resume_operation_id=narration_command["operation_id"],
                        ))
                        await _await_under_shield(_release_direct_resume_trial(
                            store,
                            session_id=session_id,
                            target=runtime.target,
                            operation_id=narration_command["operation_id"],
                        ))
                        current_cancellation = None
                        raise
                    current_cancellation = None
                    if result.status == "completed":
                        assert result.state_event is not None and result.narrative is not None
                        result.state_event.narrative_history = [
                            *event_data.narrative_history,
                            *([{
                                "id": result.resolution_receipt["receipt_id"], "turn_id": result.turn_id,
                                "turn_number": result.turn_number, "type": "mechanics",
                                "content": result.resolution_receipt["display"],
                                "narrative_mode": result.resolution_receipt["narrative_mode"],
                                "timestamp": result.narrative.created_at.isoformat(),
                            }] if result.resolution_receipt else []),
                            {"id": result.narrative.narrative_id, "turn_id": result.turn_id,
                             "turn_number": result.turn_number, "type": "narrator",
                             "content": result.narrative.text,
                             "timestamp": result.narrative.created_at.isoformat()},
                        ]
                        await websocket.send_json(result.state_event.model_dump(mode="json"))
                        terminal = {"action": "stream_end", "operation_id": result.operation_id,
                                    "turn_id": result.turn_id, "status": "completed",
                                    "narrative": result.narrative.model_dump(mode="json")}
                        if result.resolution_receipt:
                            terminal["resolution_receipt"] = result.resolution_receipt
                        await websocket.send_json(terminal)
                    elif result.narration_pause is not None:
                        await websocket.send_json({"action": "narration_paused", **result.narration_pause.model_dump(mode="json")})
                    else:
                        await store.transition_narration_resume(
                            session_id=session_id,
                            capsule_id=narration_command["capsule_id"],
                            from_state="direct_resume_trial",
                            to_state="paused",
                            resume_operation_id=narration_command["operation_id"],
                        )
                        await _release_direct_resume_trial(
                            store,
                            session_id=session_id,
                            target=runtime.target,
                            operation_id=narration_command["operation_id"],
                        )
                        await _send_recorded_turn_failure(
                            websocket, session_id=session_id,
                            operation_id=narration_command["operation_id"], store=store,
                            expose_operation=True,
                        )
                continue
            try:
                operation_id, user_input, client_operation_id = _decode_turn_input(
                    raw_input
                )
            except ValueError as exc:
                await websocket.send_json(_turn_error(str(exc)))
                continue
            if not user_input:
                await websocket.send_json(
                    _turn_error(
                        "A ação não pode estar vazia.",
                        operation_id=(operation_id if client_operation_id else None),
                        terminal=True,
                    )
                )
                continue
            if len(user_input) > MAX_PLAYER_INPUT_CHARS:
                await websocket.send_json(
                    _turn_error(
                        "A ação excede o limite de "
                        f"{MAX_PLAYER_INPUT_CHARS} caracteres.",
                        operation_id=(operation_id if client_operation_id else None),
                        terminal=True,
                    )
                )
                continue

            async with acquire_session_lock(session_id):
                event_data = await load_session_state(session_id)
                if event_data is None:
                    await websocket.send_json(
                        _turn_error(
                            "Sessão canônica indisponível.",
                            operation_id=(
                                operation_id if client_operation_id else None
                            ),
                            terminal=True,
                        )
                    )
                    continue
                session.context = event_data.player_sheet or {}
                session.turn = event_data.turn_number + 1

                store = get_persistence()
                active_pause = await store.load_active_narration_resume_capsule(session_id)
                if active_pause is not None:
                    await websocket.send_json({
                        "action": "error", "terminal": True,
                        "operation_id": operation_id,
                        "message": "Conclua ou descarte a narração pausada antes de enviar outra ação.",
                    })
                    await websocket.send_json(_pause_payload(active_pause))
                    continue
                existing_attempt = await store.load_attempt_by_operation(
                    session_id, operation_id
                )
                if existing_attempt is not None:
                    if existing_attempt["user_input"] != user_input:
                        await websocket.send_json(
                            _turn_error(
                                "O operation_id já pertence a outra ação.",
                                operation_id=(
                                    operation_id if client_operation_id else None
                                ),
                                terminal=True,
                            )
                        )
                    else:
                        await _replay_turn_attempt(
                            websocket,
                            session_id=session_id,
                            operation_id=operation_id,
                            attempt=existing_attempt,
                            store=store,
                        )
                    continue

                cancellation = CancellationToken()
                current_cancellation = cancellation
                try:
                    attempt_result = await _await_under_shield(
                        store.start_attempt(
                            session_id=session_id,
                            operation_id=operation_id,
                            attempt_id=f"attempt-{operation_id}",
                            requested_turn=event_data.turn_number + 1,
                            user_input=user_input,
                            chronicle_name=session.chronicle_name,
                        )
                    )
                except IdempotencyConflictError:
                    await websocket.send_json(
                        _turn_error(
                            "O operation_id já pertence a outra ação.",
                            operation_id=(
                                operation_id if client_operation_id else None
                            ),
                            terminal=True,
                        )
                    )
                    continue

                if attempt_result.idempotent:
                    existing_attempt = await store.load_attempt_by_operation(
                        session_id, operation_id
                    )
                    if existing_attempt is None:
                        await websocket.send_json(
                            _turn_error(
                                "A tentativa idempotente não pôde ser reidratada.",
                                operation_id=(
                                    operation_id if client_operation_id else None
                                ),
                                terminal=True,
                            )
                        )
                    else:
                        await _replay_turn_attempt(
                            websocket,
                            session_id=session_id,
                            operation_id=operation_id,
                            attempt=existing_attempt,
                            store=store,
                        )
                    continue

                if event_data.character.status == "TORPOR":
                    blocked_message = (
                        "[BLOQUEIO DE FLUXO] O personagem está em TORPOR e "
                        "não pode realizar ações físicas ou narrativas."
                    )
                    blocked_event = _turn_error(
                        blocked_message,
                        operation_id=(operation_id if client_operation_id else None),
                        terminal=True,
                    )
                    await _await_under_shield(
                        store.record_failed_attempt(
                            session_id=session_id,
                            operation_id=operation_id,
                            attempt_id=attempt_result.attempt_id,
                            requested_turn=event_data.turn_number + 1,
                            user_input=user_input,
                            error={
                                "category": "flow_interceptor",
                                "code": "character_in_torpor",
                                "safe_message": blocked_message,
                            },
                            metadata={
                                "interceptor": "torpor",
                                "websocket_terminal": blocked_event,
                                "include_state": True,
                            },
                            chronicle_name=session.chronicle_name,
                        )
                    )
                    await websocket.send_json(blocked_event)
                    await websocket.send_json(event_data.model_dump(mode="json"))
                    continue

                if event_data.character.status == "FRENZY_CHECK":
                    try:
                        frenzy_runtime = get_llm_runtime()
                        await _assert_narrator_gate(
                            store,
                            session_id=session_id,
                            target=frenzy_runtime.target,
                        )
                        pool_size = (
                            event_data.character.attributes.self_control
                            + event_data.character.attributes.resolve
                        )
                        from .rules_service import _roll_v5_dice

                        roll_result = _roll_v5_dice(
                            dice_pool=pool_size,
                            hunger=event_data.character.fome,
                            difficulty=3,
                        )
                        if roll_result.is_success:
                            event_data.character.status = "ACTIVE"
                            event_data.context.current_state = "ACTIVE"
                            event_data.context.blocking = False
                            event_data.context.pending_roll = None
                            message = "Sucesso! Você manteve o controle."
                        else:
                            message = (
                                "Falha! A Besta mantém o personagem à beira do "
                                "Frenesi."
                            )
                        frenzy_message = (
                            f"[TESTE DE FRENESI] {message} {roll_result.summary}"
                        )
                        frenzy_event = {
                            "action": "chat_response",
                            "message": frenzy_message,
                            **(
                                {
                                    "operation_id": operation_id,
                                    "terminal": True,
                                }
                                if client_operation_id
                                else {}
                            ),
                        }
                        completion = await _await_under_shield(
                            store.complete_control_attempt(
                                session_id=session_id,
                                operation_id=operation_id,
                                attempt_id=attempt_result.attempt_id,
                                requested_turn=event_data.turn_number + 1,
                                user_input=user_input,
                                state=(
                                    event_data.model_dump(mode="json")
                                    if roll_result.is_success
                                    else None
                                ),
                                expected_turn=event_data.turn_number,
                                expected_state_revision=event_data.state_revision,
                                metadata={
                                    "interceptor": "frenzy_check",
                                    "roll": roll_result.model_dump(mode="json"),
                                    "websocket_terminal": frenzy_event,
                                    "include_state": True,
                                },
                                chronicle_name=session.chronicle_name,
                            )
                        )
                    except Exception as exc:
                        failure_message = (
                            "O teste de frenesi não pôde ser confirmado; o estado "
                            "anterior foi preservado."
                        )
                        await _await_under_shield(
                            store.record_failed_attempt(
                                session_id=session_id,
                                operation_id=operation_id,
                                attempt_id=attempt_result.attempt_id,
                                requested_turn=event_data.turn_number + 1,
                                user_input=user_input,
                                error={
                                    "category": "flow_interceptor",
                                    "code": type(exc).__name__,
                                    "safe_message": failure_message,
                                },
                                metadata={"interceptor": "frenzy_check"},
                                chronicle_name=session.chronicle_name,
                            )
                        )
                        await _send_recorded_turn_failure(
                            websocket,
                            session_id=session_id,
                            operation_id=operation_id,
                            store=store,
                            expose_operation=client_operation_id,
                        )
                        continue
                    if completion.state_revision is not None:
                        event_data.state_revision = completion.state_revision
                    await websocket.send_json(frenzy_event)
                    await websocket.send_json(event_data.model_dump(mode="json"))
                    continue

                runtime = None
                guarded_gateway = None
                if turn_requires_llm_runtime(user_input, session.context):
                    try:
                        runtime = get_llm_runtime()
                        guarded_gateway = _gated_gateway(
                            store,
                            session_id=session_id,
                            gateway=runtime.gateway,
                        )
                    except LLMRuntimeConfigurationError as exc:
                        await _await_under_shield(store.record_failed_attempt(
                            session_id=session_id,
                            operation_id=operation_id,
                            attempt_id=attempt_result.attempt_id,
                            requested_turn=event_data.turn_number + 1,
                            user_input=user_input,
                            status=(
                                "cancelled" if cancellation.is_cancelled else "failed"
                            ),
                            error={
                                "category": "configuration_invalid",
                                "code": "llm_target_not_configured",
                                "safe_message": str(exc),
                            },
                            chronicle_name=session.chronicle_name,
                        ))
                        await _send_recorded_turn_failure(
                            websocket,
                            session_id=session_id,
                            operation_id=operation_id,
                            store=store,
                            expose_operation=client_operation_id,
                        )
                        continue

                try:
                    invocation_records: list[InvocationRecord] = []
                    with CancelScope(shield=True):
                        prepared = await prepare_turn_pipeline(
                            user_input=user_input,
                            session_id=session_id,
                            context=deepcopy(session.context),
                            turn=event_data.turn_number + 1,
                            chronicle_name=session.chronicle_name,
                            operation_id=operation_id,
                            state_revision=event_data.state_revision,
                            gateway=guarded_gateway,
                            target=(runtime.target if runtime is not None else None),
                            cancellation=cancellation,
                            llm_invocations=invocation_records,
                            before_rng=(
                                (lambda: _assert_narrator_gate(
                                    store,
                                    session_id=session_id,
                                    target=runtime.target,
                                ))
                                if runtime is not None else None
                            ),
                        )
                except asyncio.CancelledError as exc:
                    cancellation.cancel("request task cancelled during turn preparation")
                    provenance_audit, usage_audit = build_invocation_audit(
                        invocation_records
                    )
                    try:
                        await _await_under_shield(
                            store.record_failed_attempt(
                                session_id=session_id,
                                operation_id=operation_id,
                                requested_turn=event_data.turn_number + 1,
                                user_input=user_input,
                                status="cancelled",
                                error={
                                    "category": "cancelled",
                                    "code": "request_task_cancelled",
                                    "safe_message": "Client request ended during turn preparation.",
                                },
                                provenance=provenance_audit,
                                usage=usage_audit,
                                chronicle_name=session.chronicle_name,
                            )
                        )
                    except Exception as audit_exc:
                        exc.add_note(
                            f"Cancellation audit failed: {type(audit_exc).__name__}"
                        )
                    raise
                except Exception as exc:
                    provenance_audit, usage_audit = build_invocation_audit(
                        invocation_records
                    )
                    preparation_failure_message = (
                        NARRATOR_CONTEXT_BUDGET_MESSAGE
                        if isinstance(exc, NarratorContextBudgetError)
                        else "A preparação do turno falhou; o estado não mudou."
                    )
                    preparation_failure_code = (
                        exc.code if isinstance(exc, NarratorContextBudgetError)
                        else type(exc).__name__
                    )
                    await _await_under_shield(store.record_failed_attempt(
                        session_id=session_id,
                        operation_id=operation_id,
                        requested_turn=event_data.turn_number + 1,
                        user_input=user_input,
                        status="cancelled" if cancellation.is_cancelled else "failed",
                        error={
                            "category": "application",
                            "code": preparation_failure_code,
                            "safe_message": preparation_failure_message,
                        },
                        provenance=provenance_audit,
                        usage=usage_audit,
                        chronicle_name=session.chronicle_name,
                    ))
                    await _send_recorded_turn_failure(
                        websocket,
                        session_id=session_id,
                        operation_id=operation_id,
                        store=store,
                        expose_operation=client_operation_id,
                    )
                    continue

                if prepared.is_clarification:
                    provenance_audit, usage_audit = build_invocation_audit(
                        prepared.llm_invocations
                    )
                    await _await_under_shield(store.record_failed_attempt(
                        session_id=session_id,
                        operation_id=operation_id,
                        attempt_id=attempt_result.attempt_id,
                        requested_turn=event_data.turn_number + 1,
                        user_input=user_input,
                        error={
                            "category": "clarification",
                            "code": prepared.code or "clarification_required",
                            "safe_message": (
                                prepared.message or prepared.system_log
                            ),
                        },
                        metadata={
                            "llm_diagnostics": [
                                item.model_dump(mode="json")
                                if hasattr(item, "model_dump")
                                else item
                                for item in prepared.llm_diagnostics
                            ]
                        },
                        provenance=provenance_audit,
                        usage=usage_audit,
                        chronicle_name=session.chronicle_name,
                    ))
                    await _send_recorded_turn_failure(
                        websocket,
                        session_id=session_id,
                        operation_id=operation_id,
                        store=store,
                        expose_operation=client_operation_id,
                    )
                    continue

                if prepared.is_lore_query or prepared.is_direct_response:
                    result = await execute_prepared_lore_turn(
                        prepared,
                        session_id=session_id,
                        operation_id=operation_id,
                        user_input=user_input,
                        chronicle_name=session.chronicle_name,
                        store=store,
                        cancellation=cancellation,
                        preclaimed_attempt=attempt_result,
                    )
                    if result.status != "completed":
                        await _send_recorded_turn_failure(
                            websocket,
                            session_id=session_id,
                            operation_id=operation_id,
                            store=store,
                            expose_operation=client_operation_id,
                        )
                        continue
                    assert result.state_event is not None and result.narrative is not None
                    session.context = prepared.updated_context
                    session.turn = result.turn_number + 1
                    result.state_event.narrative_history = [
                        *event_data.narrative_history,
                        {
                            "id": result.narrative.narrative_id,
                            "turn_id": result.turn_id,
                            "turn_number": result.turn_number,
                            "type": "narrator",
                            "content": result.narrative.text,
                            "timestamp": result.narrative.created_at.isoformat(),
                        },
                    ]
                    await websocket.send_json(result.state_event.model_dump(mode="json"))
                    if client_operation_id:
                        await websocket.send_json(
                            {
                                "action": "stream_end",
                                "operation_id": operation_id,
                                "turn_id": result.turn_id,
                                "status": "completed",
                                "narrative": result.narrative.model_dump(mode="json"),
                            }
                        )
                    else:
                        await websocket.send_json(
                            {
                                "action": "chat_response",
                                "message": f"📜 {result.narrative.text}",
                            }
                        )
                    continue
                if prepared.is_error:
                    provenance_audit, usage_audit = build_invocation_audit(
                        prepared.llm_invocations
                    )
                    await _await_under_shield(store.record_failed_attempt(
                        session_id=session_id,
                        operation_id=operation_id,
                        requested_turn=event_data.turn_number + 1,
                        user_input=user_input,
                        status="cancelled" if cancellation.is_cancelled else "failed",
                        error={
                            "category": "turn_preparation",
                            "code": "pipeline_rejected",
                            "safe_message": prepared.system_log,
                        },
                        metadata={
                            "llm_diagnostics": [
                                item.model_dump(mode="json")
                                if hasattr(item, "model_dump")
                                else item
                                for item in prepared.llm_diagnostics
                            ]
                        },
                        provenance=provenance_audit,
                        usage=usage_audit,
                        chronicle_name=session.chronicle_name,
                    ))
                    await _send_recorded_turn_failure(
                        websocket,
                        session_id=session_id,
                        operation_id=operation_id,
                        store=store,
                        expose_operation=client_operation_id,
                    )
                    continue

                assert prepared.draft is not None
                try:
                    await websocket.send_json(
                        {
                            "action": "stream_start",
                            "operation_id": operation_id,
                            "turn_id": prepared.draft.turn_id,
                            "status": "provisional",
                        }
                    )
                except Exception:
                    cancellation.cancel("client transport disconnected")
                    provenance_audit, usage_audit = build_invocation_audit(
                        prepared.llm_invocations
                    )
                    await _await_under_shield(store.record_failed_attempt(
                        session_id=session_id,
                        operation_id=operation_id,
                        attempt_id=prepared.draft.attempt_id,
                        requested_turn=event_data.turn_number + 1,
                        user_input=user_input,
                        status="cancelled",
                        error={
                            "category": "cancelled",
                            "code": "client_disconnected_before_stream",
                            "safe_message": "Client disconnected before provisional streaming began.",
                        },
                        provenance=provenance_audit,
                        usage=usage_audit,
                        chronicle_name=session.chronicle_name,
                    ))
                    break

                async def send_chunk(chunk: str) -> None:
                    await websocket.send_json(
                        {
                            "action": "stream_chunk",
                            "operation_id": operation_id,
                            "turn_id": prepared.draft.turn_id,
                            "chunk": chunk,
                            "provisional": True,
                        }
                    )

                try:
                    if runtime is None:
                        raise RuntimeError(
                            "Action pipeline reached narration without an LLM runtime."
                        )
                    result = await execute_prepared_turn(
                        prepared,
                        session_id=session_id,
                        operation_id=operation_id,
                        user_input=user_input,
                        chronicle_name=session.chronicle_name,
                        store=store,
                        gateway=guarded_gateway,
                        target=runtime.target,
                        cancellation=cancellation,
                        on_chunk=send_chunk,
                        preclaimed_attempt=attempt_result,
                    )
                except asyncio.CancelledError as exc:
                    cancellation.cancel("request task cancelled during turn execution")
                    try:
                        await _terminalize_unexpected_claimed_turn(
                            session_id=session_id,
                            operation_id=operation_id,
                            attempt_id=attempt_result.attempt_id,
                            requested_turn=event_data.turn_number + 1,
                            user_input=user_input,
                            chronicle_name=session.chronicle_name,
                            turn_id=prepared.draft.turn_id,
                            store=store,
                            status="cancelled",
                        )
                    except Exception as audit_exc:
                        exc.add_note(
                            "Terminal turn audit failed: "
                            f"{type(audit_exc).__name__}"
                        )
                    raise
                except Exception as exc:
                    unexpected_status = (
                        "timeout" if isinstance(exc, TimeoutError) else "failed"
                    )
                    persisted = await _terminalize_unexpected_claimed_turn(
                        session_id=session_id,
                        operation_id=operation_id,
                        attempt_id=attempt_result.attempt_id,
                        requested_turn=event_data.turn_number + 1,
                        user_input=user_input,
                        chronicle_name=session.chronicle_name,
                        turn_id=prepared.draft.turn_id,
                        store=store,
                        status=unexpected_status,
                    )
                    if persisted is not None and persisted.get("status") == "completed":
                        await _replay_turn_attempt(
                            websocket,
                            session_id=session_id,
                            operation_id=operation_id,
                            attempt=persisted,
                            store=store,
                        )
                    else:
                        await _send_recorded_turn_failure(
                            websocket,
                            session_id=session_id,
                            operation_id=operation_id,
                            store=store,
                            expose_operation=True,
                            attempt=persisted,
                        )
                    continue

                if result.status == "completed":
                    assert result.state_event is not None and result.narrative is not None
                    session.context = prepared.updated_context
                    session.turn = result.turn_number + 1
                    completed_history = [*event_data.narrative_history]
                    if result.resolution_receipt is not None:
                        completed_history.append(
                            {
                                "id": result.resolution_receipt["receipt_id"],
                                "turn_id": result.turn_id,
                                "turn_number": result.turn_number,
                                "type": "mechanics",
                                "content": result.resolution_receipt["display"],
                                "narrative_mode": result.resolution_receipt[
                                    "narrative_mode"
                                ],
                                "timestamp": result.narrative.created_at.isoformat(),
                            }
                        )
                    completed_history.append(
                        {
                            "id": result.narrative.narrative_id,
                            "turn_id": result.turn_id,
                            "turn_number": result.turn_number,
                            "type": "narrator",
                            "content": result.narrative.text,
                            "timestamp": result.narrative.created_at.isoformat(),
                        }
                    )
                    result.state_event.narrative_history = completed_history
                    await websocket.send_json(
                        result.state_event.model_dump(mode="json")
                    )
                    terminal_payload = {
                            "action": "stream_end",
                            "operation_id": operation_id,
                            "turn_id": result.turn_id,
                            "status": "completed",
                            "narrative": result.narrative.model_dump(mode="json"),
                        }
                    if result.resolution_receipt is not None:
                        terminal_payload["resolution_receipt"] = (
                            result.resolution_receipt
                        )
                    await websocket.send_json(terminal_payload)
                else:
                    if result.narration_pause is not None:
                        await websocket.send_json({
                            "action": "narration_paused",
                            **result.narration_pause.model_dump(mode="json"),
                        })
                    else:
                        await _send_recorded_turn_failure(
                            websocket,
                            session_id=session_id,
                            operation_id=operation_id,
                            store=store,
                            # Streaming already exposes the generated operation id
                            # to legacy clients in stream_start/chunks.
                            expose_operation=True,
                        )
    except WebSocketDisconnect:
        pass
    except Exception:
        try:
            await websocket.send_json(
                {
                    "action": "error",
                    "message": "A sessão foi interrompida com segurança; o último estado confirmado foi preservado.",
                }
            )
        except Exception:
            pass
    finally:
        if current_cancellation is not None:
            current_cancellation.cancel("websocket session closed")
        if reader_task is not None:
            reader_task.cancel()
            await asyncio.gather(reader_task, return_exceptions=True)


class UpgradeRequest(BaseModel):
    trait_category: str
    trait_name: str
    new_level: int


class ConsolidationRequest(BaseModel):
    summary: str = Field(
        description=(
            "Non-canonical proposal; the durable consolidation is derived from "
            "the selected episodic memories."
        )
    )
    source_memory_ids: list[str] = Field(default_factory=list)


@app.get("/session/{session_id}/memory/context")
async def retrieve_player_context(
    session_id: str,
    query: str = "",
    token_budget: int = 1200,
):
    """Player-facing retrieval never includes storyteller or system secrets."""

    from .state_service import get_persistence

    selected = await get_persistence().retrieve_memories(
        session_id,
        query=query,
        allowed_visibilities=("public", "player"),
        token_budget=max(0, min(token_budget, 8192)),
        limit=50,
    )
    consolidation_rows = await get_persistence().list_consolidations(session_id)
    from .turn_models import Consolidation, Visibility

    latest: dict[str, Consolidation] = {}
    for row in consolidation_rows:
        try:
            consolidation = Consolidation.model_validate(row.get("payload") or {})
        except Exception:
            continue
        if consolidation.visibility not in {Visibility.PUBLIC, Visibility.PLAYER}:
            continue
        current = latest.get(consolidation.scope.value)
        if current is None or consolidation.version > current.version:
            latest[consolidation.scope.value] = consolidation
    return {
        "session_id": session_id,
        "memories": selected,
        "consolidations": [
            latest[scope].model_dump(mode="json") for scope in sorted(latest)
        ],
    }


@app.post("/session/{session_id}/memory/consolidate/{scope}")
async def consolidate_memory(
    session_id: str,
    scope: str,
    request: ConsolidationRequest,
):
    """Explicitly consolidate a scene or session without deleting sources."""

    from .memory_service import create_consolidation
    from .state_service import get_persistence
    from .turn_models import Consolidation, ConsolidationScope, EpisodicMemory, Visibility

    try:
        consolidation_scope = ConsolidationScope(scope)
    except ValueError:
        return {"success": False, "error": "scope deve ser 'scene' ou 'session'"}
    if not request.summary.strip():
        return {"success": False, "error": "summary não pode estar vazio"}

    store = get_persistence()
    rows = await store.list_episodic_memories(session_id)
    # This endpoint is player-facing, including its returned grounded summary.
    # Filter before validating requested IDs so private and missing IDs behave alike.
    rows = [row for row in rows if (row.get('payload') or {}).get('visibility')
            in {Visibility.PUBLIC.value, Visibility.PLAYER.value}]
    requested_ids = set(request.source_memory_ids)
    available_ids = {row["memory_id"] for row in rows}
    missing_ids = requested_ids - available_ids
    if missing_ids:
        return {
            "success": False,
            "error": (
                "Memórias-fonte inexistentes: " + ", ".join(sorted(missing_ids))
            ),
        }
    memories: list[EpisodicMemory] = []
    for row in rows:
        if requested_ids and row["memory_id"] not in requested_ids:
            continue
        payload = row.get("payload") or {}
        try:
            memories.append(EpisodicMemory.model_validate(payload))
        except Exception:
            # Legacy unreferenced snippets remain preserved, but cannot become
            # a source-bearing consolidation until linked to canonical events.
            continue
    if not memories:
        return {
            "success": False,
            "error": "Nenhuma memória episódica canônica elegível foi encontrada.",
        }

    existing = await store.list_consolidations(
        session_id, scope=consolidation_scope.value
    )
    previous = (
        Consolidation.model_validate(existing[-1]["payload"]) if existing else None
    )
    # Versions share one canonical chain per session/scope. Do not supersede a
    # private chain or expose its ID/version through a player response.
    if previous is not None and previous.visibility not in {Visibility.PUBLIC, Visibility.PLAYER}:
        return {'success': False, 'error': 'Consolidação indisponível para o jogador.'}
    consolidation = create_consolidation(
        memories,
        consolidation_id=f"consolidation-{uuid.uuid4()}",
        scope=consolidation_scope,
        proposed_summary=request.summary.strip(),
        previous=previous,
    )
    if previous is None or consolidation != previous:
        await store.save_consolidation(consolidation)
    return {
        "success": True,
        "consolidation": consolidation.model_dump(mode="json"),
        "summary_grounding": {
            "source": "episodic_memories",
            "proposal_status": "not_persisted",
        },
    }

@app.post("/session/{session_id}/xp/award")
async def award_xp(session_id: str, amount: int = 1):
    from .progression_service import award_session_xp
    from .rules_service import PlayerSheetModel
    from .state_service import acquire_session_lock

    async with acquire_session_lock(session_id):
        event_data = await load_session_state(session_id)
        if not event_data:
            return {"error": "Sessão não encontrada"}
        if not event_data.player_sheet:
            return {"error": "Ficha do jogador ausente"}

        current_turn = event_data.turn_number
        # Suporte ao envelope herdado do player_sheet.
        player_sheet_dict = (
            event_data.player_sheet.get("player_sheet", {})
            if "player_sheet" in event_data.player_sheet
            else event_data.player_sheet
        )
        sheet = award_session_xp(PlayerSheetModel(**player_sheet_dict), amount)
        new_context = deepcopy(event_data.player_sheet)
        new_context["player_sheet"] = sheet.model_dump()

        event_data = sync_event_from_context(
            session_id,
            new_context,
            turn_number=current_turn,
            state_revision=event_data.state_revision,
            narrative_history=event_data.narrative_history,
        )
        await save_session_state(session_id, event_data, turn=current_turn)

        if session_id in active_sessions:
            active_sessions[session_id].context = event_data.player_sheet or {}
        return event_data.model_dump()

@app.post("/session/{session_id}/xp/upgrade")
async def upgrade_trait(session_id: str, req: UpgradeRequest):
    from .progression_service import ProgressionValidationError, purchase_upgrade
    from .rules_service import PlayerSheetModel
    from .state_service import acquire_session_lock

    async with acquire_session_lock(session_id):
        event_data = await load_session_state(session_id)
        if not event_data:
            return {"success": False, "error": "Sessão não encontrada"}
        if not event_data.player_sheet:
            return {"success": False, "error": "Ficha do jogador ausente"}

        current_turn = event_data.turn_number
        player_sheet_dict = (
            event_data.player_sheet.get("player_sheet", {})
            if "player_sheet" in event_data.player_sheet
            else event_data.player_sheet
        )
        sheet = PlayerSheetModel(**player_sheet_dict)
        try:
            success, updated_sheet = purchase_upgrade(
                sheet,
                req.trait_category,
                req.trait_name,
                req.new_level,
            )
        except ProgressionValidationError as exc:
            return {"success": False, "error": str(exc), "code": exc.code}
        if not success:
            return {"success": False, "error": "XP insuficiente ou melhoria inválida"}

        new_context = deepcopy(event_data.player_sheet)
        new_context["player_sheet"] = updated_sheet.model_dump()
        event_data = sync_event_from_context(
            session_id,
            new_context,
            turn_number=current_turn,
            state_revision=event_data.state_revision,
            narrative_history=event_data.narrative_history,
        )
        await save_session_state(session_id, event_data, turn=current_turn)

        if session_id in active_sessions:
            active_sessions[session_id].context = event_data.player_sheet or {}
        return {"success": True, "state": event_data.model_dump()}


# --- SERVIR FRONTEND E ARQUIVOS ESTÁTICOS COMPILADOS ---

DIST_ROOT = (
    Path(__file__).resolve().parent.parent / "client" / "dist"
).resolve()
DIST_DIR = str(DIST_ROOT)

# Rota para o index.html principal
@app.get("/")
async def serve_index():
    index_path = os.path.join(DIST_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return HTMLResponse("<h1>Agente Storyteller V5</h1><p>Aguardando compilação do frontend React...</p>")

# Montar a pasta de assets se ela existir
assets_dir = os.path.join(DIST_DIR, "assets")
if os.path.exists(assets_dir):
    app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

# Rota curinga para arquivos avulsos no dist (favicon, etc) ou index.html para SPA router
@app.get("/{catchall:path}")
async def serve_static_or_spa(catchall: str):
    # Ignora caminhos que começam com rotas da api ou ws
    if catchall.startswith("api/") or catchall.startswith("ws/") or catchall.startswith("session/"):
        return {"error": "Not Found"}
        
    candidate = (DIST_ROOT / catchall).resolve()
    if not candidate.is_relative_to(DIST_ROOT):
        return HTMLResponse(
            "<h1>Agente Storyteller V5</h1><p>Arquivo não encontrado.</p>",
            status_code=404,
        )
    if candidate.is_file():
        return FileResponse(candidate)
        
    index_path = os.path.join(DIST_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return HTMLResponse("<h1>Agente Storyteller V5</h1><p>Arquivo não encontrado.</p>", status_code=404)
