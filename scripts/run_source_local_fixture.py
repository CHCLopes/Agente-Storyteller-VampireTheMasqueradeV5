"""Opt-in browser fixture: authored FakeLLM replies, isolated new synthetic store.

This is a development fixture, not the product launcher or a model evaluation.
No credential, dotenv file, runtime target or external diagnostic is consulted.
Preflight only validates and describes the configuration; it creates no store,
status directory or listener. A real run never adopts an existing run directory.
"""
from __future__ import annotations

import argparse
import asyncio
from contextlib import contextmanager
from dataclasses import dataclass
import json
import os
import signal
from pathlib import Path
import sys
import tempfile
import threading
from urllib.parse import urlencode
from uuid import UUID

os.environ["STORYTELLER_DISABLE_DOTENV"] = "1"
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from api.llm.contract import (
    CAPABILITY_STRUCTURED_GENERATION, CAPABILITY_TEXT_GENERATION,
    CapabilityDescriptor, CapabilitySet, CapabilitySupport, GenerationParameters, LLMTarget,
)
from api.llm.testing import FakeLLMAdapter
from api.narrative_source_input import create_source_producer_config
from api.narrative_source_local_app import create_source_local_app
from api.narrative_source_local_handler import create_source_local_handler
from api.narrative_source_local_selection import create_source_local_trial_binding
from api.narrative_source_setup import create_source_setup_manifest
from api.narrative_source_setup_service import create_source_trial_setup
from api.persistence import SQLitePersistence
from api.rules_service import PlayerSheetModel, StatusModel, TrackerModel

QUESTION = "O que você faz agora?"
DIALOGUE = 'Pergunto a Mara: "Quero conhecer melhor este lugar por meio da conversa. O que você pode me contar?"'
REPLIES = (
    'Mara volta o rosto para a pergunta e indica com a mão as prateleiras próximas. '
    '"Este lugar reúne objetos que as pessoas deixaram por aqui", diz, sem sair de '
    'junto da janela. Ela aproxima um recipiente vazio da borda para mostrar os '
    'pequenos desenhos gravados na cerâmica. A luz atravessa o vidro e torna os '
    'traços mais visíveis. "Posso falar do que está nesta prateleira", acrescenta. '
    'O recipiente fica apoiado sobre a madeira enquanto Mara afasta a mão e espera. '
    'Atrás dela, a cortina se move com uma corrente de ar, e a chuva permanece '
    'audível do lado de fora. Há espaço livre diante da prateleira; os demais '
    'objetos seguem em seus lugares, sob a iluminação irregular da galeria.',
    'Mara permanece junto à prateleira e gira devagar o recipiente que mostrou. '
    'Outro desenho aparece na cerâmica: uma linha curva cercada por pequenos pontos. '
    '"Este traço está do outro lado também", comenta, mantendo o objeto apoiado '
    'sobre a madeira. O ruído da chuva preenche a pausa entre as palavras. '
    'A cortina continua em movimento diante da janela, sem esconder a prateleira.',
)
SETUP = {"location": "Galeria", "npcs_present": ["Mara"],
         "declared_objective": "conhecer melhor este lugar por meio da conversa"}


class FixtureError(ValueError):
    pass


class _Parser(argparse.ArgumentParser):
    def error(self, message):
        raise FixtureError("source_local_fixture_arguments_invalid")


@dataclass(frozen=True)
class FixtureSpec:
    run_id: str
    port: int
    origin_port: int
    run_directory: Path
    status_directory: Path

    @property
    def session_id(self):
        return "source-fixture." + self.run_id

    @property
    def database(self):
        return self.run_directory / "storyteller.sqlite3"

    def metadata(self, status: str):
        origin = f"http://127.0.0.1:{self.origin_port}"
        query = urlencode({"backendPort": self.port, "session": self.session_id})
        return {"status": status, "fixture": "authored-mara-gallery-v1", "synthetic_only": True,
            "external_provider_calls": 0, "run_id": self.run_id, "session_id": self.session_id,
            "backend_port": self.port, "origin_port": self.origin_port,
            "websocket_url": f"ws://127.0.0.1:{self.port}/ws/source-local/{self.session_id}",
            "frontend_url": origin + "/source-trial.html?" + query, "expected_origin": origin,
            "database": str(self.database), "status_file": str(self.status_directory / "status.json"),
            "suggested_actions": [DIALOGUE, "Aguardo."], "authored_replies": len(REPLIES),
            "after_script": "repeat_last_authored_reply", "pid": os.getpid()}


def configuration(argv=None) -> tuple[FixtureSpec, bool]:
    parser = _Parser(description=__doc__)
    parser.add_argument("--run-id", required=True, type=UUID)
    parser.add_argument("--port", required=True, type=int,
        help="Porta do backend loopback, 1..65535 exceto 80; diferente de origin-port.")
    parser.add_argument("--origin-port", required=True, type=int,
        help="Porta do Vite loopback, 1..65535 exceto 80; navegador omite :80.")
    parser.add_argument("--preflight-only", action="store_true")
    args = parser.parse_args(argv)
    if not 1 <= args.port <= 65535 or not 1 <= args.origin_port <= 65535:
        raise FixtureError("source_local_fixture_port_invalid")
    # Browsers omit :80, whereas the existing binding requires an explicit port.
    # The fixture frontend and backend are separate servers, with no proxy.
    if 80 in (args.port, args.origin_port) or args.port == args.origin_port:
        raise FixtureError("source_local_fixture_port_pair_unsupported")
    project = PROJECT_ROOT.resolve()
    parent = (project / "eval-results").resolve()
    if not parent.is_relative_to(project):
        raise FixtureError("source_local_fixture_directory_invalid")
    identity = str(args.run_id)
    spec = FixtureSpec(identity, args.port, args.origin_port,
        parent / ("source-local-fixture-" + identity),
        Path(tempfile.gettempdir()) / ("storyteller-source-local-fixture-" + identity))
    ensure_unused(spec)
    return spec, args.preflight_only


def ensure_unused(spec: FixtureSpec) -> None:
    if any(path.exists() or path.is_symlink() for path in (spec.run_directory, spec.status_directory)):
        raise FixtureError("source_local_fixture_run_exists")


class _AuthoredGateway(FakeLLMAdapter):
    def __init__(self, capability_set):
        super().__init__(capability_set=capability_set)
        self._script_lock = asyncio.Lock()

    async def generate_structured(self, request):
        async with self._script_lock:
            self.structured_payload = {"n": REPLIES[min(len(self.requests), len(REPLIES) - 1)], "q": QUESTION}
            return await super().generate_structured(request)


def components(spec: FixtureSpec):
    """Pure construction: an explicit fake target, synthetic sheet and authored setup."""
    target = LLMTarget(profile="source-local-browser-fixture", provider="synthetic", model="authored-mara-gallery-v1")
    capabilities = CapabilitySet(target=target, descriptors=tuple(
        CapabilityDescriptor(name=name, support=CapabilitySupport.NATIVE)
        for name in (CAPABILITY_TEXT_GENERATION, CAPABILITY_STRUCTURED_GENERATION)))
    gateway = _AuthoredGateway(capabilities)
    producer = create_source_producer_config(target=target,
        system_prompt="Fixture local autorada em português brasileiro; preserve fonte e agência.",
        parameters=GenerationParameters(temperature=.65, max_output_tokens=768), npc_aliases=("Mara",))
    sheet = PlayerSheetModel(attributes={"Wits": 3}, skills={"Investigation": 2}, disciplines={},
        status=StatusModel(blood_potency=1, current_hunger=0, humanity=7,
            health_tracker=TrackerModel(size=5, superficial=0, aggravated=0),
            willpower_tracker=TrackerModel(size=5, superficial=0, aggravated=0)))
    state = {"player_sheet": sheet.model_dump(mode="json")}
    store = SQLitePersistence(spec.database)
    manifest = create_source_setup_manifest(SETUP, session_id=spec.session_id)
    return store, gateway, manifest, state, producer


def application(spec: FixtureSpec, store, gateway, manifest, producer):
    """Compose only after the explicit runtime bootstrap/setup has succeeded."""
    binding = create_source_local_trial_binding(session_id=spec.session_id, store=store,
        expected_manifest=manifest, producer_config=producer,
        expected_host=f"127.0.0.1:{spec.port}", expected_origin=f"http://127.0.0.1:{spec.origin_port}")
    return create_source_local_app(binding=binding,
        handler=create_source_local_handler(gateway=gateway, action_timeout_seconds=60), enabled=True)


def write_status(spec: FixtureSpec, status: str):
    # Only called after this run atomically owns the status directory.
    temporary = spec.status_directory / "status.json.tmp"
    temporary.write_text(json.dumps(spec.metadata(status), ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(spec.status_directory / "status.json")


async def run_fixture(spec: FixtureSpec) -> None:
    ensure_unused(spec)
    spec.run_directory.parent.mkdir(parents=True, exist_ok=True)
    spec.status_directory.mkdir(exist_ok=False)
    try:
        spec.run_directory.mkdir(exist_ok=False)
        write_status(spec, "preparing")
        store, gateway, expected, state, producer = components(spec)
        await store.initialize()
        actual = await create_source_trial_setup(session_id=spec.session_id, request=SETUP,
            store=store, initial_state=state, relationships={})
        if actual != expected or gateway.requests:
            raise FixtureError("source_local_fixture_setup_invalid")
        app = application(spec, store, gateway, actual, producer)
        write_status(spec, "prepared")
        await serve(spec, app)
        write_status(spec, "stopped")
    except BaseException:
        write_status(spec, "failed")
        raise


async def serve(spec: FixtureSpec, app) -> None:
    import uvicorn
    from uvicorn.server import HANDLED_SIGNALS

    class FixtureServer(uvicorn.Server):
        @contextmanager
        def capture_signals(self):
            if threading.current_thread() is not threading.main_thread():
                yield
                return
            previous = {sig: signal.signal(sig, self.handle_exit) for sig in HANDLED_SIGNALS}
            try:
                yield
            finally:
                for sig, handler in previous.items():
                    signal.signal(sig, handler)
            # The fixture records the completed shutdown itself. Replaying a
            # handled SIGINT here would cancel asyncio.run's parent task after
            # shutdown and incorrectly turn that completed run into a failure.

    server = FixtureServer(uvicorn.Config(app, host="127.0.0.1", port=spec.port,
        reload=False, workers=1, proxy_headers=False, access_log=False,
        log_level="warning", lifespan="on", timeout_graceful_shutdown=65))
    task = asyncio.create_task(server.serve())
    try:
        while not server.started and not task.done():
            await asyncio.sleep(.05)
        if server.started:
            write_status(spec, "running")
        await task
        if not server.started:
            raise FixtureError("source_local_fixture_listener_unavailable")
        if (server.force_exit or server.server_state.tasks or server.server_state.connections
                or server.lifespan.shutdown_failed or server.lifespan.error_occured):
            raise FixtureError("source_local_fixture_shutdown_incomplete")
    finally:
        if not task.done():
            server.should_exit = True
            await asyncio.shield(task)


def main(argv=None) -> int:
    try:
        spec, preflight_only = configuration(argv)
        if preflight_only:
            components(spec)
            print(json.dumps(spec.metadata("preflight_passed"), ensure_ascii=False))
            return 0
        asyncio.run(run_fixture(spec))
        return 0
    except (Exception, KeyboardInterrupt) as error:
        code = str(error) if type(error) is FixtureError else "source_local_fixture_failed"
        print(json.dumps({"status": "failed", "code": code}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
