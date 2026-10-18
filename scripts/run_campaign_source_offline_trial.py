"""Opt-in, loopback-only authored campaign trial. No provider or credential use.

Run from the worktree with ``python -m scripts.run_campaign_source_offline_trial``.
This does not mount on the game app, select a narrator, or replace the v1 UI.
"""
from __future__ import annotations

import argparse
from contextlib import asynccontextmanager
from dataclasses import asdict
from datetime import timedelta
import json
from pathlib import Path
import secrets
import tempfile
from uuid import uuid4

from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, ConfigDict, Field, StrictStr

from api.campaign_source_capsule import CampaignSourceConfig
from api.campaign_source_execution_service import execute_campaign_source_turn
from api.campaign_source_input_service import prepare_campaign_source_player_action
from api.campaign_source_offline_corpus import PROSE
from api.campaign_source_storage import (
    CampaignSourceStorageError, create_campaign_source_session,
    load_campaign_source_capsule, read_campaign_source_snapshot,
    read_campaign_source_status,
)
from api.llm.contract import (
    CAPABILITY_STRUCTURED_GENERATION, CAPABILITY_TEXT_GENERATION,
    CancellationToken, CapabilityDescriptor, CapabilitySet, CapabilitySupport,
    GenerationParameters, LLMTarget, utc_now,
)
from api.llm.testing import FakeLLMAdapter
from api.persistence import SQLitePersistence
from api.rules_service import PlayerSheetModel, StatusModel, TrackerModel


TARGET = LLMTarget(profile="campaign-offline-authored", provider="fake", model="authored")
CONFIG = CampaignSourceConfig(
    target=TARGET, system_prompt="Ensaio sintético autorado; sem provedor externo.",
    parameters=GenerationParameters(temperature=0, max_output_tokens=768),
)
CAPABILITIES = CapabilitySet(target=TARGET, descriptors=tuple(CapabilityDescriptor(
    name=name, support=CapabilitySupport.NATIVE,
) for name in (CAPABILITY_TEXT_GENERATION, CAPABILITY_STRUCTURED_GENERATION)))


def _initial_state() -> dict:
    sheet = PlayerSheetModel(
        attributes={"Wits": 3}, skills={"Investigation": 2}, disciplines={},
        status=StatusModel(
            blood_potency=1, current_hunger=0, humanity=7,
            health_tracker=TrackerModel(size=5, superficial=0, aggravated=0),
            willpower_tracker=TrackerModel(size=5, superficial=0, aggravated=0),
        ),
    )
    return {"player_sheet": sheet.model_dump(mode="json")}


class Action(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    session_id: StrictStr = Field(min_length=1, max_length=240)
    operation_id: StrictStr = Field(min_length=1, max_length=240)
    player_input: StrictStr = Field(min_length=1, max_length=500)


class Resume(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    session_id: StrictStr = Field(min_length=1, max_length=240)
    original_operation_id: StrictStr = Field(min_length=1, max_length=240)
    operation_id: StrictStr = Field(min_length=1, max_length=240)
    resumes_operation_id: StrictStr = Field(min_length=1, max_length=240)


_PAGE = r"""<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Campanha offline autorada</title>
<style>body{font:16px/1.5 system-ui,sans-serif;max-width:780px;margin:2rem auto;padding:0 1rem;background:#171b22;color:#f0f2f5}button,input{font:inherit}button{margin:.25rem;padding:.45rem .7rem}input{padding:.5rem;width:min(100%,580px);box-sizing:border-box}article{border:1px solid #596171;border-radius:8px;padding:1rem;margin:1rem 0;white-space:pre-wrap}small{color:#b7c1d0}#error{color:#ffb5b5}#scene{min-height:5rem}</style></head><body>
<h1>Registro em risco — ensaio offline</h1><p><strong>Prosa autorada, não Luna.</strong> Este ensaio usa o mesmo resolvedor, cápsula, fonte e commit da rota B opt-in, mas um adaptador falso. Nenhuma API externa é chamada; custo de provedor: USD 0.</p>
<p><button id="start">Nova sessão sintética</button> <span id="status"></span></p>
<article id="scene">Inicie uma sessão para entrar no Arquivo. Mara está perto do registro público ameaçado pela infiltração.</article>
<form id="action"><label for="input">Sua ação</label><br><input id="input" autocomplete="off" required placeholder="Como posso ajudar?"><button id="send">Enviar</button></form><button id="resume" hidden>Retomar narração conservada</button>
<p id="error" role="alert"></p><p><small>Exemplos cobertos: “Como posso ajudar?”, “Quem é a fundadora?”, “Aguardo”, “Retiro o registro”, “Levo o registro até a superfície seca”, “Examino o registro”, “Desisto”. Outros métodos plausíveis são recusados como fora do catálogo, não como fracasso na ficção. Recarregar a página reconstrói o histórico desta sessão enquanto o servidor estiver ativo.</small></p>
<script>
const token=__TOKEN__,key='storyteller-campaign-offline-session',opKey='storyteller-campaign-offline-operation';
let session=localStorage.getItem(key),last=JSON.parse(localStorage.getItem(opKey)||'null'),busy=false,ended=false;
const $=id=>document.getElementById(id);
async function api(path,body){
  const r=await fetch(path,{method:body?'POST':'GET',headers:{'X-Trial-Token':token,...(body?{'Content-Type':'application/json'}:{})},body:body?JSON.stringify(body):undefined});
  const v=await r.json();if(!r.ok)throw Object.assign(Error(v.detail||'Falha local'),{status:r.status});return v;
}
function missingSession(e){return e.status===404||e.message==='campaign_source_campaign_missing';}
function forgetSession(){
  session=null;last=null;ended=false;localStorage.removeItem(key);localStorage.removeItem(opKey);
  $('status').textContent='';$('scene').textContent='A sessão anterior não está neste servidor. Inicie uma nova sessão sintética.';
  $('resume').hidden=true;$('send').disabled=true;$('input').disabled=true;
  $('error').textContent='Sessão anterior indisponível. Clique em “Nova sessão sintética”.';
}
function show(v){
  session=v.session_id;ended=!!v.outcome;localStorage.setItem(key,session);
  $('status').textContent=`Turno ${v.turn} · registro ${v.record}`+(v.outcome?` · desfecho ${v.outcome}`:'');
  $('scene').textContent=v.narratives.length?v.narratives.map((n,i)=>`Turno ${i+1}\n${n}`).join('\n\n'):
    'No Arquivo, Mara observa o registro público ameaçado pela infiltração. O que você faz?';
  $('send').disabled=ended||busy;$('input').disabled=ended||busy;
  if(v.result&&v.result.status!=='completed')$('error').textContent=`Ação não confirmada: ${v.result.error_code||v.result.status}`;
  else $('error').textContent='';
}
function finish(){busy=false;$('send').disabled=ended||!session;$('input').disabled=ended||!session;}
async function refreshResume(){
  $('resume').hidden=true;if(!session||!last||ended)return;
  const requestedSession=session,requestedOriginal=last.original;
  try{const status=await api(`/api/operation/${encodeURIComponent(requestedSession)}/${encodeURIComponent(requestedOriginal)}`);
    if(session!==requestedSession||last?.original!==requestedOriginal)return;
    if(status.resume_from_operation_id){last.latest=status.resume_from_operation_id;localStorage.setItem(opKey,JSON.stringify(last));$('resume').hidden=false;}
  }catch(e){if(session!==requestedSession)return;if(missingSession(e))forgetSession();else $('error').textContent=e.message;}
}
async function load(){if(!session)return;const requestedSession=session;
  try{const v=await api('/api/session/'+encodeURIComponent(requestedSession));if(session!==requestedSession)return;show(v);await refreshResume();}
  catch(e){if(session!==requestedSession)return;if(missingSession(e))forgetSession();else $('error').textContent=e.message;}
}
$('start').onclick=async()=>{if(busy)return;busy=true;try{const v=await api('/api/start',{});last=null;localStorage.removeItem(opKey);show(v);$('input').value='';}catch(e){$('error').textContent=e.message;}finally{finish();await refreshResume();}};
$('action').onsubmit=async e=>{e.preventDefault();if(!session||busy||ended)return;const value=$('input').value.trim();if(!value)return;
  busy=true;$('send').disabled=true;const operation=crypto.randomUUID();last={original:operation,latest:operation};localStorage.setItem(opKey,JSON.stringify(last));
  try{const v=await api('/api/action',{session_id:session,operation_id:operation,player_input:value});show(v);if(v.result?.status==='completed')$('input').value='';}
  catch(e){if(missingSession(e))forgetSession();else $('error').textContent=e.message;}finally{finish();await refreshResume();}
};
$('resume').onclick=async()=>{if(busy||!last)return;busy=true;$('resume').disabled=true;
  try{const operation=crypto.randomUUID();const v=await api('/api/resume',{session_id:session,original_operation_id:last.original,operation_id:operation,resumes_operation_id:last.latest});
    last.latest=operation;localStorage.setItem(opKey,JSON.stringify(last));show(v);
  }catch(e){if(missingSession(e))forgetSession();else $('error').textContent=e.message;}finally{finish();$('resume').disabled=false;await refreshResume();}
};$('send').disabled=!session;$('input').disabled=!session;load();
</script></body></html>"""


def create_app(db_path: Path, *, access_token: str | None = None) -> FastAPI:
    """Create an unmounted local trial; the caller must bind only to loopback."""
    token = access_token or secrets.token_urlsafe(24)
    store = SQLitePersistence(db_path)

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        await store.initialize()
        # Only operations left pending by a previous process are cancelled.
        # Retained P/K remains readable for explicit H-only resume.
        await store.recover_pending_attempts(started_before=utc_now())
        yield

    app = FastAPI(lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)
    from api.local_request_security import LocalRequestBoundary
    app.add_middleware(LocalRequestBoundary)

    def authorize(x_trial_token: str | None):
        if not secrets.compare_digest(x_trial_token or "", token):
            raise HTTPException(403, "Ensaio local indisponível")

    async def view(session_id: str, *, result: dict | None = None) -> dict:
        try:
            snapshot = await read_campaign_source_snapshot(store, session_id)
            turns = await store.list_turns(session_id)
        except CampaignSourceStorageError:
            raise HTTPException(404, "Sessão sintética não encontrada") from None
        return {
            "session_id": session_id, "turn": snapshot.current_turn,
            "record": snapshot.progression.record,
            "outcome": snapshot.progression.outcome,
            "narratives": [item["narrative"]["text"] for item in turns],
            "result": result,
            "external_provider_calls": 0,
            "provider_cost_usd": 0,
        }

    async def narrate(capsule, operation_id: str, resumes_operation_id: str | None):
        rule = capsule.campaign_effect.rule_id
        fake = FakeLLMAdapter(capability_set=CAPABILITIES, structured_payload={
            "n": PROSE[rule],
            "q": "" if capsule.campaign_effect.after_state.outcome else "O que você faz agora?",
            "realized_effects": capsule.campaign_effect.beat.effect_keys,
        })
        async def deliver(_text: str):
            return None
        return await execute_campaign_source_turn(
            store=store, capsule=capsule, operation_id=operation_id,
            resumes_operation_id=resumes_operation_id, gateway=fake,
            deadline=utc_now() + timedelta(seconds=30),
            cancellation=CancellationToken(), on_chunk=deliver,
        )

    @app.get("/", response_class=HTMLResponse)
    async def home():
        return HTMLResponse(_PAGE.replace("__TOKEN__", json.dumps(token)))

    @app.post("/api/start")
    async def start(x_trial_token: str | None = Header(default=None)):
        authorize(x_trial_token)
        session_id = "campaign-offline-" + uuid4().hex
        await create_campaign_source_session(
            store, session_id, initial_state=_initial_state(),
            relationships={}, chronicle_name="Registro em risco — ensaio autorado",
        )
        return await view(session_id)

    @app.get("/api/session/{session_id}")
    async def session_status(session_id: str, x_trial_token: str | None = Header(default=None)):
        authorize(x_trial_token)
        return await view(session_id)

    @app.post("/api/action")
    async def action(value: Action, x_trial_token: str | None = Header(default=None)):
        authorize(x_trial_token)
        current = await view(value.session_id)
        if current["outcome"] is not None:
            raise HTTPException(409, "A aventura já terminou")
        try:
            claim = await prepare_campaign_source_player_action(
                store=store, session_id=value.session_id, operation_id=value.operation_id,
                player_input=value.player_input, config=CONFIG,
                deadline=utc_now() + timedelta(seconds=30), cancellation=CancellationToken(),
            )
            result = (await narrate(claim.capsule, value.operation_id, None)
                      if claim.capsule is not None else None)
        except CampaignSourceStorageError as exc:
            raise HTTPException(409, exc.code) from None
        return await view(value.session_id, result={
            "status": result.status if result else claim.status,
            "error_code": result.error_code if result else claim.error_code,
            "original_operation_id": value.operation_id,
            "latest_operation_id": value.operation_id,
        })

    @app.post("/api/resume")
    async def resume(value: Resume, x_trial_token: str | None = Header(default=None)):
        authorize(x_trial_token)
        try:
            capsule = await load_campaign_source_capsule(
                store, value.session_id, value.original_operation_id,
            )
            result = await narrate(capsule, value.operation_id, value.resumes_operation_id)
        except CampaignSourceStorageError as exc:
            raise HTTPException(409, exc.code) from None
        return await view(value.session_id, result={
            "status": result.status, "error_code": result.error_code,
            "original_operation_id": value.original_operation_id,
            "latest_operation_id": value.operation_id,
        })

    @app.get("/api/operation/{session_id}/{operation_id}")
    async def operation_status(session_id: str, operation_id: str,
                               x_trial_token: str | None = Header(default=None)):
        authorize(x_trial_token)
        try:
            status = await read_campaign_source_status(store, session_id, operation_id)
        except CampaignSourceStorageError as exc:
            raise HTTPException(409, exc.code) from None
        return asdict(status) if status else {"status": "not_found"}

    return app


def main() -> None:
    parser = argparse.ArgumentParser(description="Ensaio local, autorado e sem API externa")
    parser.add_argument("--port", type=int, default=8021)
    options = parser.parse_args()
    if not 1024 <= options.port <= 65535:
        parser.error("--port deve estar entre 1024 e 65535")
    db_path = Path(tempfile.gettempdir()) / f"storyteller-campaign-offline-{uuid4().hex}.sqlite3"
    print(f"Ensaio sem provedor externo. Abra http://127.0.0.1:{options.port}/ no navegador externo.", flush=True)
    print(f"Banco sintético local: {db_path}", flush=True)
    import uvicorn
    uvicorn.run(create_app(db_path), host="127.0.0.1", port=options.port, log_level="warning")


if __name__ == "__main__":
    main()
