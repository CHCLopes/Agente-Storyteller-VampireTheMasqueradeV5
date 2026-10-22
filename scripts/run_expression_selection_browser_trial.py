"""Isolated, deterministic A2 browser trial; no model gateway or product mounting."""
from __future__ import annotations
import argparse
from hashlib import sha256
from datetime import timedelta
import json
from pathlib import Path
import secrets
from uuid import uuid4
from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, ConfigDict, Field
from api.campaign_progression_catalog import classify_campaign_intent
from api.experiments.expression_selection.contract import SelectionConfig
from api.experiments.expression_selection.service import execute
from api.experiments.expression_selection.store import SelectionStore
from api.experiments.intent_interpretation_catalog import APPROVED_PARAPHRASES, VERSION
from api.experiments.intent_paraphrase_boundary import ExactParaphraseBoundary
from api.llm.contract import CancellationToken, utc_now
from api.local_request_security import LocalRequestBoundary
from api.rules_service import PlayerSheetModel
from scripts.run_campaign_source_offline_trial import _initial_state

OPENING = "Você está no Arquivo. Mara está presente. O registro está sobre uma bancada baixa, ameaçado pela infiltração. O que você faz?"

class Resume(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    session_id: str = Field(min_length=1, max_length=160)
    operation_id: str = Field(min_length=1, max_length=160)

class Action(Resume):
    player_input: str = Field(min_length=1, max_length=500)

PAGE = r"""<!doctype html><html lang="pt-BR"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Registro em risco · A2</title>
<style>body{font:17px/1.6 system-ui;max-width:780px;margin:2rem auto;padding:0 1rem;background:#faf7f1;color:#292b2d}article{white-space:pre-wrap;border:1px solid #b9afa3;border-radius:8px;padding:1rem;margin:1rem 0}button,input{font:inherit;padding:.5rem}button{cursor:pointer;margin:.3rem 0}input{box-sizing:border-box;width:100%}#error{color:#963a26}small{color:#595750}</style>
<h1>Registro em risco</h1><p>Ensaio A2 · texto autorado · sem modelo ou API · custo de provedor: USD 0.</p>
<button id="start">Nova sessão sintética</button><p id="status"></p><article id="scene">Inicie uma sessão para entrar no Arquivo.</article>
<form id="action"><label for="input">Sua ação</label><input id="input" required maxlength="500" autocomplete="off"><button id="send" disabled>Enviar</button></form>
<button id="resume" hidden>Retomar ação conservada</button><button id="cancel" hidden>Encerrar ação sem resultado</button>
<p id="error" role="alert"></p><small>Catálogo fechado. Exemplos: “Como posso ajudar?”, “Mara, leve o registro”, “Aguardo”, “Retiro o registro”, “Examino o registro”, “Desisto”. Métodos fora do catálogo não avançam a história. Recarregar recupera a sessão e seu histórico.</small>
<script>
const token=__TOKEN__,key='selection-a2-session',opKey='selection-a2-operation';
const $=id=>document.getElementById(id);let session=localStorage.getItem(key),pending=null,busy=false,ended=false,serverPending=null;
try{pending=JSON.parse(localStorage.getItem(opKey)||'null')}catch{localStorage.removeItem(opKey)}
function remember(v){pending=v;if(v)localStorage.setItem(opKey,JSON.stringify(v));else localStorage.removeItem(opKey)}
function controls(){ $('start').disabled=busy;$('send').disabled=busy||!session||ended||!!serverPending;$('input').disabled=busy||!session||ended||!!serverPending;$('resume').disabled=busy;$('cancel').disabled=busy;}
async function api(path,body){const r=await fetch(path,{method:body?'POST':'GET',headers:{'X-Trial-Token':token,...(body?{'Content-Type':'application/json'}:{})},body:body?JSON.stringify(body):undefined});const v=await r.json();if(!r.ok)throw Object.assign(Error(typeof v.detail==='string'?v.detail:'Solicitação local inválida.'),{status:r.status});return v;}
function show(v){session=v.session_id;ended=!!v.outcome;serverPending=v.pending;localStorage.setItem(key,session);
$('status').textContent=`Turno ${v.turn}`+(ended?' · Sessão encerrada':'');
$('scene').textContent=v.opening+v.history.map(n=>`\n\nSua ação: ${n.input}\n${n.text}`).join('');
if(pending&&v.history.some(n=>n.operation_id===pending.operation_id)){remember(null);$('input').value='';}
if(serverPending){remember({session_id:session,operation_id:serverPending.id,player_input:serverPending.input});$('input').value=serverPending.input;}
else if(pending&&pending.session_id===session){$('input').value=pending.player_input;}
$('resume').hidden=!serverPending||serverPending.phase!=='prepared';$('cancel').hidden=!serverPending||serverPending.phase!=='preparing';controls();}
async function task(fn){if(busy)return;busy=true;controls();$('error').textContent='';try{await fn()}catch(e){$('error').textContent=e.message;if(e.status===404){session=null;remember(null);localStorage.removeItem(key);serverPending=null;} }finally{busy=false;controls();}}
$('start').onclick=()=>task(async()=>{const v=await api('/api/start',{});remember(null);$('input').value='';show(v)});
$('action').onsubmit=e=>{e.preventDefault();task(async()=>{const text=$('input').value.trim();if(!text)return;if(pending&&pending.player_input!==text)throw Error('Reenvie primeiro a ação anterior ou recarregue para verificar seu resultado.');if(!pending)remember({session_id:session,operation_id:crypto.randomUUID(),player_input:text});try{show(await api('/api/action',pending));remember(null);$('input').value='';}catch(e){if(e.status===422)remember(null);throw e;}})};
$('resume').onclick=()=>task(async()=>{show(await api('/api/resume',{session_id:session,operation_id:pending.operation_id}));remember(null);$('input').value='';});
$('cancel').onclick=()=>task(async()=>{show(await api('/api/cancel',{session_id:session,operation_id:pending.operation_id}));remember(null);});
if(session)task(async()=>show(await api('/api/session/'+encodeURIComponent(session))));else controls();
</script></html>"""

def create_app(db_path: Path, *, access_token: str | None = None,
               exact_paraphrases: bool = False) -> FastAPI:
    db_path = Path(db_path)
    creating = not db_path.exists()
    receipt_path = db_path.with_name(db_path.name + '.paraphrases.sqlite3')
    if exact_paraphrases and creating and receipt_path.exists():
        raise ValueError('paraphrase_receipts_already_exist')
    store = SelectionStore(db_path, create=creating)
    boundary = ExactParaphraseBoundary(receipt_path, create=creating) if exact_paraphrases else None
    if boundary and not creating:
        # Never adopt a baseline session or reroll a partially claimed operation.
        with store._connection() as c:
            for row in c.execute('SELECT session_id,id,input FROM operations'):
                boundary.raw_input(row['session_id'], row['id'], row['input'])
    token = access_token or secrets.token_urlsafe(24)
    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
    app.add_middleware(LocalRequestBoundary)
    app.state.selection_store = store
    app.state.paraphrase_boundary = boundary

    def authorize(value):
        if not value or not secrets.compare_digest(value, token):
            raise HTTPException(403, "Acesso local inválido. Recarregue a página.")

    def view(sid):
        with store._connection() as c:
            try:
                s = store._session(c, sid)
            except ValueError as exc:
                if str(exc) == 'selection_session_missing':
                    raise HTTPException(404, "Sessão indisponível neste ensaio.") from None
                raise
            if s.config.mode != 'deterministic':
                raise HTTPException(409, "Este ensaio aceita apenas sessões determinísticas.")
            store._history(c, s)
            rows = c.execute("SELECT id,input,presentation FROM operations WHERE session_id=? AND phase='completed' ORDER BY rowid", (sid,)).fetchall()
            pending = c.execute("SELECT id,input,phase FROM operations WHERE session_id=? AND phase IN ('preparing','prepared')", (sid,)).fetchone()
            history = [dict(operation_id=r['id'], input=r['input'], text=json.loads(r['presentation'])['text']) for r in rows]
            pending = dict(pending) if pending else None
            if boundary:
                for row in history:
                    row['input'] = boundary.raw_input(sid, row['operation_id'], row['input'])
                if pending:
                    pending['input'] = boundary.raw_input(sid, pending['id'], pending['input'])
            return dict(session_id=sid, turn=s.state.revision, outcome=s.state.outcome,
                opening=OPENING, history=history, pending=pending, provider_calls=0)

    @app.exception_handler(ValueError)
    async def invalid(_request, _exc):
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=409, content={'detail':'A ação não foi confirmada. Recarregue para verificar ou retomar a sessão.'})

    async def finish(value, *, resume=False):
        view(value.session_id)  # Validate mode and retained history before mutation.
        if not resume:
            if boundary:
                if value.player_input not in APPROVED_PARAPHRASES:
                    raise HTTPException(422, "Esta ação ainda não é coberta neste ensaio. Sua sessão não avançou.")
                canonical = boundary.admit(value.session_id, value.operation_id, value.player_input)
            else:
                canonical = value.player_input
            if classify_campaign_intent(canonical) is None:
                raise HTTPException(422, "Esta ação ainda não é coberta neste ensaio. Sua sessão não avançou.")
            store.prepare(value.session_id, value.operation_id, canonical)
        attempts = store.attempts(value.session_id, value.operation_id)
        previous = None
        attempt_id = 'web-' + sha256(value.operation_id.encode('utf-8')).hexdigest()
        if resume and attempts:
            last = attempts[-1]
            if last['status'] in ('pending','ready'):
                store.recover_interrupted(value.session_id, value.operation_id, last['id'], expected_invocation_id=last['invocation_id'])
            if last['status'] != 'completed':
                previous = last['id']; attempt_id = str(uuid4())
            else:
                attempt_id = last['id']
        result = await execute(store=store, session_id=value.session_id, operation_id=value.operation_id,
            attempt_id=attempt_id, resumes_attempt_id=previous, deadline=utc_now()+timedelta(seconds=15), cancellation=CancellationToken())
        if result.status != 'completed':
            raise HTTPException(409, "Ação conservada sem conclusão. Recarregue para retomar explicitamente.")
        return view(value.session_id)

    @app.get('/', response_class=HTMLResponse)
    async def home():
        page = PAGE
        if boundary:
            page = page.replace("selection-a2-session", "selection-a2-exact-session").replace("selection-a2-operation", "selection-a2-exact-operation")
            page = page.replace("const text=$('input').value.trim();if(!text)return;", "const text=$('input').value;if(!text.trim())return;")
            start = page.index('<small>Catálogo fechado.')
            end = page.index('</small>', start)
            page = page[:start] + '<small>Catálogo exato E (' + VERSION + '). Aceita somente: ' + ' / '.join(APPROVED_PARAPHRASES) + '. Pontuação, espaços e maiúsculas precisam coincidir. Recarregar recupera a sessão e seu histórico.' + page[end:]
        return HTMLResponse(page.replace('__TOKEN__', json.dumps(token)), headers={'Cache-Control':'no-store','Referrer-Policy':'no-referrer'})

    @app.post('/api/start')
    async def start(x_trial_token: str | None = Header(default=None)):
        authorize(x_trial_token)
        sid = str(uuid4())
        store.create_session(sid, config=SelectionConfig(mode='deterministic'), sheet=PlayerSheetModel.model_validate(_initial_state()['player_sheet']))
        return view(sid)

    @app.get('/api/session/{sid}')
    async def session(sid: str, x_trial_token: str | None = Header(default=None)):
        authorize(x_trial_token); return view(sid)

    @app.post('/api/action')
    async def action(value: Action, x_trial_token: str | None = Header(default=None)):
        authorize(x_trial_token); return await finish(value)

    @app.post('/api/resume')
    async def resume(value: Resume, x_trial_token: str | None = Header(default=None)):
        authorize(x_trial_token); return await finish(value, resume=True)

    @app.post('/api/cancel')
    async def cancel(value: Resume, x_trial_token: str | None = Header(default=None)):
        authorize(x_trial_token); view(value.session_id)
        store.recover_preparation(value.session_id, value.operation_id)
        return view(value.session_id)

    return app


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--db', type=Path, required=True, help='Banco exclusivo do ensaio A2; não usar banco do produto.')
    parser.add_argument('--port', type=int, default=8032)
    parser.add_argument('--exact-paraphrases', action='store_true', help='Opt-in E: somente seis frases exatas; usar banco novo exclusivo.')
    args = parser.parse_args()
    import uvicorn
    uvicorn.run(create_app(args.db, exact_paraphrases=args.exact_paraphrases), host='127.0.0.1', port=args.port, log_level='warning')

if __name__ == '__main__':
    main()
