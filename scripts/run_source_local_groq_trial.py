"""Explicit, finite synthetic Groq interaction through the existing local B path.

Preflight reads frozen inputs only. No default runtime, campaign, key discovery,
retry, fallback or narrative-policy change is performed. All waiting belongs to
admission/UI; a generation request keeps the handler's original absolute deadline.
"""
from __future__ import annotations

import argparse
import asyncio
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import signal
import sys
import tempfile
import threading
import time
from urllib.parse import urlencode
from uuid import UUID

os.environ["STORYTELLER_DISABLE_DOTENV"] = "1"
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from pydantic import SecretStr
from api.llm.contract import GenerationParameters, LLMTarget, StructuredGenerationRequest, utc_now
from api.narrative_source_action_producer import _family
from api.narrative_source_context import SourceContextSnapshot
from api.narrative_source_input import create_source_input_request, create_source_producer_config
from api.narrative_source_local_app import create_source_local_app
from api.narrative_source_local_handler import create_source_local_handler
from api.narrative_source_local_selection import create_source_local_trial_binding
from api.narrative_source_setup import create_source_setup_manifest
from api.narrative_source_setup_service import create_source_trial_setup
from api.persistence import SQLitePersistence
from scripts import evaluate_source_player as player

retained, shared, profile = player.retained, player.shared, player.profile
PROTOCOL = "source-local-groq-trial-v1"
PURPOSE = "source_local_groq_trial"
KEY_ENV = "STORYTELLER_SOURCE_LOCAL_TRIAL_GROQ_KEY"
TARGET_PROFILE = "source-local-groq-trial-qwen-3.8-27b-groq-free-synthetic-nonthink"
SETUP = dict(player.SETUP)
MAX_CALLS, OUTPUT_TOKENS, DELAY_SECONDS = 4, 768, 60
_CLASSIFICATION_TIME = datetime(2026, 9, 12, tzinfo=timezone.utc)
EXTRA_INPUTS = (
    "scripts/run_source_local_groq_trial.py", "scripts/run_groq_source_local_trial.ps1",
    "api/narrative_source_local_handler.py", "api/narrative_source_local_app.py",
    "api/narrative_source_local_selection.py", "api/narrative_source_observation.py",
    "api/narrative_source_transport.py", "api/narrative_source_input.py",
    "client/source-player-trial.html", "client/src/sourcePlayerTrialMain.tsx",
    "client/vite.source-player-trial.config.ts", "client/src/components/SourcePlayerTrial.tsx",
    "client/src/index.css",
    "client/src/components/SourceTrialView.tsx", "client/src/sourceNarrativeProtocol.ts",
    "client/src/hooks/useSourceTrialConnection.ts",
)


class TrialError(ValueError):
    def __init__(self, code="source_local_groq_trial_invalid"):
        self.code = code
        super().__init__(code)


def require(condition, code="source_local_groq_trial_invalid"):
    if not condition:
        raise TrialError(code)


def sha_file(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def encoded(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


class _Parser(argparse.ArgumentParser):
    def error(self, message):
        raise TrialError("source_local_groq_trial_arguments_invalid")


@dataclass(frozen=True)
class TrialSpec:
    run_id: str
    port: int
    origin_port: int
    run_directory: Path
    status_directory: Path

    @property
    def session_id(self):
        return "source-groq-trial." + self.run_id

    @property
    def database(self):
        return self.run_directory / "storyteller.sqlite3"

    def paths(self):
        query = urlencode({"backendPort": self.port, "session": self.session_id})
        return dict(run_directory=str(self.run_directory), database=str(self.database),
            status_directory=str(self.status_directory), status_file=str(self.status_directory / "status.json"),
            frontend_url=f"http://127.0.0.1:{self.origin_port}/source-player-trial.html?" + query,
            websocket_url=f"ws://127.0.0.1:{self.port}/ws/source-local/{self.session_id}")


def configuration(argv=None):
    parser = _Parser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--preflight-only", action="store_true")
    mode.add_argument("--live", action="store_true")
    parser.add_argument("--run-id", required=True, type=UUID)
    parser.add_argument("--port", required=True, type=int)
    parser.add_argument("--origin-port", required=True, type=int)
    parser.add_argument("--allow-synthetic-only", action="store_true")
    parser.add_argument("--expected-preflight", type=Path)
    parser.add_argument("--expected-preflight-sha256")
    parser.add_argument("--api-key-env")
    parser.add_argument("--managed-stdin-stop", action="store_true")
    args = parser.parse_args(argv)
    require((args.port, args.origin_port) == (8018, 5178), "source_local_groq_trial_ports_invalid")
    live_options = (args.allow_synthetic_only, args.expected_preflight, args.expected_preflight_sha256,
                    args.api_key_env, args.managed_stdin_stop)
    if args.preflight_only:
        require(not any(live_options), "source_local_groq_trial_mode_invalid")
    else:
        require(args.allow_synthetic_only and args.expected_preflight is not None
            and args.expected_preflight_sha256 is not None and args.api_key_env == KEY_ENV,
            "source_local_groq_trial_live_arguments_invalid")
    root = PROJECT_ROOT.resolve()
    parent = (root / "eval-results").resolve()
    require(parent.is_relative_to(root), "source_local_groq_trial_directory_invalid")
    identity = str(args.run_id)
    spec = TrialSpec(identity, args.port, args.origin_port,
        parent / ("source-local-groq-trial-" + identity),
        Path(tempfile.gettempdir()) / ("storyteller-source-local-groq-trial-" + identity))
    ensure_unused(spec)
    return spec, args


def ensure_unused(spec):
    require(not any(path.exists() or path.is_symlink()
        for path in (spec.run_directory, spec.status_directory)), "source_local_groq_trial_run_exists")


@dataclass(frozen=True)
class PreparedTrial:
    candidate: object
    target: LLMTarget
    prompt: str
    metadata: dict
    metadata_sha256: str


def prepare(spec):
    previous = player.prepare_experiment()
    target = LLMTarget(profile=TARGET_PROFILE, provider="Groq", model="qwen/qwen3.8-27b")
    manifest = create_source_setup_manifest(SETUP, session_id=spec.session_id)
    files = sorted(set(player.IMPLEMENTATION_FILES + EXTRA_INPUTS + (
        str(player.MANIFEST_PATH.relative_to(PROJECT_ROOT)).replace("\\", "/"),
        str(player.PROMPT_PATH.relative_to(PROJECT_ROOT)).replace("\\", "/"))))
    metadata = dict(status="preflight_passed", purpose=PURPOSE, protocol=PROTOCOL,
        profile=profile.VERSION, run_id=spec.run_id, session_id=spec.session_id,
        target=target.model_dump(mode="json"), selected_candidate_id=player.CANDIDATE_ID,
        generation_parameters=dict(temperature=.65, max_output_tokens=768, reasoning_effort="none"),
        budget=dict(max_calls=4, max_total_output_tokens=3072, initial_quiet_seconds=60,
                    minimum_inter_call_delay_seconds=60, deadline_seconds=60),
        synthetic_only=True, campaign_data_eligible=False, runtime_default_eligible=False,
        cap_001_approved=False, semantic_approval=None, external_provider_calls=0,
        backend_port=spec.port, origin_port=spec.origin_port, expected_host=f"127.0.0.1:{spec.port}",
        expected_origin=f"http://127.0.0.1:{spec.origin_port}", paths=spec.paths(),
        setup=manifest.model_dump(mode="json"), initial_state=player._state(),
        producer_context=dict(npc_aliases=["Mara"], player_aliases=[], profile="source-local-ordinary-v1"),
        action_scope="existing_declared_dialogue_or_wait_only",
        prompt=dict(version="narrative-source-progress-v1",
            file="evals/narrator/prompts/narrative-source-progress-v1.md",
            file_sha256=player.PROMPT_FILE_SHA256, sha256=player.PROMPT_SHA256),
        response_schema_sha256=previous.metadata["inputs"]["response_schema_sha256"],
        provider_schema_sha256=previous.metadata["inputs"]["provider_schema_sha256"],
        inputs=[dict(file=file, sha256=sha_file(PROJECT_ROOT / file)) for file in files])
    return PreparedTrial(previous.candidate, target, previous.prompt, metadata,
        hashlib.sha256(encoded(metadata).encode()).hexdigest())


def check_prepared(prepared):
    require(hashlib.sha256(encoded(prepared.metadata).encode()).hexdigest() == prepared.metadata_sha256,
        "source_local_groq_trial_preflight_mutated")
    require(all(sha_file(PROJECT_ROOT / item["file"]) == item["sha256"] for item in prepared.metadata["inputs"]),
        "source_local_groq_trial_input_drift")
    require(hashlib.sha256(prepared.prompt.encode()).hexdigest() == player.PROMPT_SHA256
        and prepared.target.model_dump(mode="json") == prepared.metadata["target"],
        "source_local_groq_trial_target_drift")


def config(prepared):
    return create_source_producer_config(target=prepared.target, system_prompt=prepared.prompt,
        parameters=GenerationParameters(temperature=.65, max_output_tokens=768), npc_aliases=("Mara",))


def declared_input(spec, prepared, public):
    """Use the existing pure grammar, not a copied parser or a forged claim.

    Only text and fixed seed labels are consulted by _family. This synthetic
    classification envelope is never persisted or passed to production; P will
    construct its own current request in the existing claim transaction.
    """
    manifest = create_source_setup_manifest(SETUP, session_id=spec.session_id)
    seed = SourceContextSnapshot(origin=manifest.origin, current_turn=0, state_revision=0,
        sources=(), selected_turn_ids=(), omitted_turn_ids=())
    classification = create_source_input_request(spec.session_id, public, created_at=_CLASSIFICATION_TIME,
        snapshot=seed, state=player._state(), relationships={}, producer_config=config(prepared))
    return _family(classification) == "declared"


class TrialControl:
    """Process-local resource counters, never a persisted action permission."""
    delay_seconds = DELAY_SECONDS

    def __init__(self, spec, prepared, *, clock=time.monotonic, key=None):
        self.spec, self.prepared, self.clock = spec, prepared, clock
        self.key = key
        self.calls = 0
        self.last_dispatch = clock()
        self.eligible = True
        self.reason = None
        self.active_operation = None
        self.denied_operation = None
        self.stop = asyncio.Event()
        self.stdin_failed = False
        self.socket_active = False

    def block(self, reason):
        self.eligible = False
        if self.reason is None:
            self.reason = reason

    def admit(self, public):
        try:
            check_prepared(self.prepared)
            admitted = (self.eligible and self.calls < MAX_CALLS
                and self.clock() - self.last_dispatch >= self.delay_seconds
                and (self.key is None or self.key.get_secret_value() not in encoded(public.model_dump(mode="json")))
                and declared_input(self.spec, self.prepared, public))
        except Exception:
            admitted = False
        if not admitted:
            self.block("admission_unavailable")
            self.denied_operation = public.operation_id
            return False
        self.active_operation = public.operation_id
        return True

    def consume(self):
        # No await separates the last check and update: all connections of this
        # one-worker process share the same final HTTP dispatch authority.
        now = self.clock()
        if not self.eligible or self.calls >= MAX_CALLS or now - self.last_dispatch < self.delay_seconds:
            self.block("http_admission_failed")
            raise TrialError("source_local_groq_trial_http_admission_failed")
        self.calls += 1
        self.last_dispatch = now

    def delivered(self, event):
        operation = event.get("operation_id")
        if event.get("event") == "unavailable" and operation == self.denied_operation:
            self.stop.set()
        if operation != self.active_operation:
            return
        if event.get("event") == "unavailable":
            self.block("operation_unavailable")
            self.stop.set()
        if event.get("event") in ("narrative_complete", "narrative_rejected", "preparation_rejected"):
            if event.get("event") == "preparation_rejected" or event.get("code") in ("narrative_failed", "timeout", "cancelled"):
                self.block("operational_failure")
            if self.calls >= MAX_CALLS:
                self.block("budget_completed")
            if not self.eligible:
                self.stop.set()


class TrialAdapter(retained.RetainedObservationAdapter):
    def __init__(self, *, prepared, request, **kwargs):
        super().__init__(prepared=prepared, request=request, **kwargs)
        self.prepared, self.deadline = prepared, request.deadline

    async def _dispatch(self, request):
        check_prepared(self.prepared)
        require(not self.http_sent and request.method == "POST"
            and str(request.url) == retained.GROQ_OFFICIAL_BASE_URL + "/chat/completions"
            and retained._sha(json.loads(request.content)) == self.approved["body_sha256"],
            "source_local_groq_trial_http_request_invalid")
        require(utc_now() < self.deadline,
            "source_local_groq_trial_expired_dispatch")
        self.budget.consume()
        self.http_sent = True
        self.capture["http_started_at"] = utc_now().isoformat()


class TrialGateway:
    def __init__(self, spec, prepared, control, key, *, transport=None, record=None):
        self.spec, self.prepared, self.control = spec, prepared, control
        self.key, self.transport, self.record = key, transport, record
        self._capabilities = shared._capabilities(prepared.candidate, prepared.target)

    def capabilities(self, target):
        require(target == self.prepared.target)
        return self._capabilities

    async def generate_text(self, request):
        raise TrialError("source_local_groq_trial_operation_forbidden")

    async def test_connection(self, request):
        raise TrialError("source_local_groq_trial_operation_forbidden")

    def stream_text(self, request):
        raise TrialError("source_local_groq_trial_operation_forbidden")

    async def generate_structured(self, request):
        adapter = None
        row = dict(kind="generation_attempt", call_made=False, outcome="local_failure")
        try:
            check_prepared(self.prepared)
            remaining = (request.deadline - utc_now()).total_seconds()
            require(type(request) is StructuredGenerationRequest and request.target == self.prepared.target
                and request.response_model is profile.NarrativeSourceProposal
                and request.parameters == GenerationParameters(temperature=.65, max_output_tokens=768)
                and 0 < remaining <= 60 and len(request.messages) == 2
                and request.messages[0].role.value == "system" and request.messages[0].content == self.prepared.prompt
                and request.messages[1].role.value == "user", "source_local_groq_trial_request_invalid")
            adapter = TrialAdapter(prepared=self.prepared, request=request, api_key=self.key,
                budget=self.control, transport=self.transport)
            adapter._reject_echo(retained._request_record(request))
            row["request"] = retained._request_record(request)
            row["deadline"] = request.deadline.isoformat()
            result = await adapter.generate_structured(request)
            usage = result.evidence.usage.output_tokens
            require(usage is None or usage <= OUTPUT_TOKENS, "source_local_groq_trial_reported_budget_exceeded")
            row["outcome"] = "generated"
            return result
        except asyncio.CancelledError:
            row["outcome"] = "cancelled"
            self.control.block("operational_failure")
            raise
        except Exception:
            self.control.block("operational_failure")
            raise
        finally:
            if adapter is not None:
                row.update(call_made=adapter.http_sent, credential_echo_blocked=adapter.credential_echo_blocked,
                    observation=adapter.observation, capture=dict(adapter.capture))
            if self.record is not None:
                try:
                    self.record(row)
                except Exception:
                    self.control.block("artifact_write_failed")
                    raise TrialError("source_local_groq_trial_artifact_write_failed") from None


def application(spec, store, prepared, control, gateway):
    manifest = create_source_setup_manifest(SETUP, session_id=spec.session_id)
    binding = create_source_local_trial_binding(session_id=spec.session_id, store=store,
        expected_manifest=manifest, producer_config=config(prepared),
        expected_host=f"127.0.0.1:{spec.port}", expected_origin=f"http://127.0.0.1:{spec.origin_port}")
    base_handler = create_source_local_handler(gateway=gateway, action_timeout_seconds=60, admit_submit=control.admit)

    async def handler(websocket, selected):
        # One interactive connection avoids independent operators racing the
        # same synthetic session. Reconnection waits for completed cleanup.
        if control.socket_active:
            await websocket.close(code=1008)
            return
        control.socket_active = True
        try:
            await base_handler(websocket, selected)
        finally:
            control.socket_active = False

    app = create_source_local_app(binding=binding, handler=handler, enabled=True)

    async def observed_app(scope, receive, send):
        async def observed_send(message):
            await send(message)
            if message.get("type") == "websocket.send" and "text" in message:
                event = json.loads(message["text"])
                control.delivered(event)
        await app(scope, receive, observed_send)
    return observed_app


def write_status(spec, control, status):
    # Snapshot at lifecycle transitions, not a live counter during generation.
    # A final stopped status certifies cleanup only; terminal_reason and the
    # persisted attempts keep operational/narrative outcomes separate.
    payload = dict(protocol=PROTOCOL, purpose=PURPOSE, run_id=spec.run_id, session_id=spec.session_id,
        status=status, pid=os.getpid(), paths=spec.paths(), calls_started=control.calls,
        admission_allowed=control.eligible, terminal_reason=control.reason)
    target = spec.status_directory / "status.json"
    temporary = target.with_suffix(".json.tmp")
    temporary.write_text(encoded(payload) + "\n", encoding="utf-8")
    temporary.replace(target)


def stdin_shutdown(control, stream, loop):
    def consume():
        try:
            line = stream.readline()
            valid = line in ("", "stop\n", "stop\r\n")
        except Exception:
            valid = False
        def finish():
            control.stdin_failed = not valid
            control.block("operator_stop" if valid else "managed_stdin_invalid")
            control.stop.set()
        try:
            loop.call_soon_threadsafe(finish)
        except RuntimeError:
            pass  # The owned daemon reader cannot keep a completed loop alive.
    thread = threading.Thread(target=consume, name="source-trial-owned-stdin", daemon=True)
    thread.start()


async def serve(spec, app, control, *, managed_stdin=False):
    import uvicorn
    from uvicorn.server import HANDLED_SIGNALS

    class TrialServer(uvicorn.Server):
        @contextmanager
        def capture_signals(self):
            if threading.current_thread() is not threading.main_thread():
                yield
                return
            previous = {sig: signal.signal(sig, self.handle_exit) for sig in HANDLED_SIGNALS}
            try:
                yield
            finally:
                for sig, callback in previous.items():
                    signal.signal(sig, callback)
            # Same local lifecycle policy as the reviewed fixture: keep
            # handle_exit, restore handlers, omit only post-shutdown replay.

    server = TrialServer(uvicorn.Config(app, host="127.0.0.1", port=spec.port, reload=False,
        workers=1, proxy_headers=False, access_log=False, log_level="critical",
        lifespan="on", timeout_graceful_shutdown=65))
    if managed_stdin:
        stdin_shutdown(control, sys.stdin, asyncio.get_running_loop())
    task = asyncio.create_task(server.serve())
    stopper = asyncio.create_task(control.stop.wait())
    try:
        while not server.started and not task.done():
            await asyncio.sleep(.05)
        if server.started:
            write_status(spec, control, "running")
        done, _ = await asyncio.wait({task, stopper}, return_when=asyncio.FIRST_COMPLETED)
        if stopper in done:
            server.should_exit = True
        await task
        require(server.started and not server.force_exit and not server.server_state.tasks
            and not server.server_state.connections and not server.lifespan.shutdown_failed
            and not server.lifespan.error_occured and not control.stdin_failed,
            "source_local_groq_trial_shutdown_incomplete")
    finally:
        stopper.cancel()
        try:
            await stopper
        except asyncio.CancelledError:
            pass
        if not task.done():
            server.should_exit = True
            await asyncio.shield(task)


async def run(spec, prepared, key, *, managed_stdin=False):
    ensure_unused(spec)
    check_prepared(prepared)
    require(type(key) is SecretStr and bool(key.get_secret_value().strip())
        and key.get_secret_value() not in encoded(prepared.metadata), "source_local_groq_trial_credential_invalid")
    spec.status_directory.mkdir(exist_ok=False)
    control = TrialControl(spec, prepared, key=key)
    try:
        spec.run_directory.mkdir(parents=True, exist_ok=False)
        write_status(spec, control, "preparing")
        (spec.run_directory / "preflight.json").write_text(encoded(prepared.metadata) + "\n", encoding="utf-8")
        def record(row):
            with (spec.run_directory / "records.jsonl").open("a", encoding="utf-8") as output:
                output.write(encoded(row) + "\n")
        gateway = TrialGateway(spec, prepared, control, key, record=record)
        store = SQLitePersistence(spec.database)
        await store.initialize()
        actual = await create_source_trial_setup(session_id=spec.session_id, request=SETUP,
            store=store, initial_state=player._state(), relationships={})
        require(actual == create_source_setup_manifest(SETUP, session_id=spec.session_id))
        app = application(spec, store, prepared, control, gateway)
        write_status(spec, control, "prepared")
        await serve(spec, app, control, managed_stdin=managed_stdin)
        control.block("operator_stop")
        write_status(spec, control, "stopped")
    except BaseException:
        control.block("runtime_failed")
        write_status(spec, control, "failed")
        raise


def main(argv=None):
    try:
        spec, args = configuration(argv)
        prepared = prepare(spec)
        if args.preflight_only:
            print(encoded(prepared.metadata))
            return 0
        require(sha_file(args.expected_preflight) == args.expected_preflight_sha256,
            "source_local_groq_trial_binding_changed")
        expected = json.loads(args.expected_preflight.read_text(encoding="utf-8-sig"))
        require(expected == prepared.metadata, "source_local_groq_trial_preflight_changed")
        check_prepared(prepared)
        raw = os.environ.pop(KEY_ENV, None)
        require(type(raw) is str and bool(raw.strip()), "source_local_groq_trial_credential_missing")
        key = SecretStr(raw.strip())
        raw = None
        asyncio.run(run(spec, prepared, key, managed_stdin=args.managed_stdin_stop))
        return 0
    except (Exception, KeyboardInterrupt):
        print(encoded({"status": "failed", "code": "source_local_groq_trial_failed"}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
