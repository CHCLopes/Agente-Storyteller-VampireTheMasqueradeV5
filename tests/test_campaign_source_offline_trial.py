"""Browser-facing offline trial exercises the same P/K/H route without network calls."""
import re
import shutil
import subprocess

import pytest
from httpx import ASGITransport, AsyncClient

from scripts.run_campaign_source_offline_trial import create_app


def test_browser_controls_unlock_after_start_action_and_new_session(tmp_path):
    node = shutil.which("node")
    if not node:
        pytest.skip("Node.js unavailable for embedded browser-script regression")
    app = create_app(tmp_path / "trial.sqlite3", access_token="synthetic-test-token")
    from fastapi.testclient import TestClient

    with TestClient(app, base_url='http://127.0.0.1:8021') as client:
        page = client.get("/").text
    script = re.search(r"<script>(.*?)</script>", page, re.DOTALL)
    assert script is not None
    harness = r"""
const assert = require('node:assert/strict');
const vm = require('node:vm');
const fs = require('node:fs');
const code = fs.readFileSync(0, 'utf8');
const elements = Object.fromEntries(['start','status','scene','action','input','send','resume','error']
  .map(id => [id, {disabled:false, hidden:false, value:'', textContent:''}]));
const saved = new Map([['storyteller-campaign-offline-session','old-session']]);
let starts = 0, actions = 0, missingAction = false;
const fetch = async path => {
  if(path === '/api/session/old-session') return {ok:false,status:404,json:async()=>({detail:'Sessão sintética não encontrada'})};
  if(path === '/api/action' && missingAction) return {ok:false,status:409,json:async()=>({detail:'campaign_source_campaign_missing'})};
  return {ok:true,status:200,json:async () => {
  if(path === '/api/start') return {session_id:'session-'+(++starts),turn:0,record:'threatened',outcome:null,narratives:[]};
  if(path === '/api/action') return {session_id:'session-'+starts,turn:++actions,record:'warned',outcome:null,narratives:['Mara responde.'],result:{status:'completed'}};
  return {resume_from_operation_id:null};
  }};
};
vm.runInNewContext(code, {document:{getElementById:id=>elements[id]},
  localStorage:{getItem:key=>saved.get(key)||null,setItem:(key,value)=>saved.set(key,value),removeItem:key=>saved.delete(key)},
  fetch,crypto:{randomUUID:()=>`operation-${actions+1}`}});
(async()=>{
  await new Promise(setImmediate);
  assert.equal(saved.has('storyteller-campaign-offline-session'),false,'stale session must be forgotten');
  assert.equal(elements.input.disabled,true,'stale session must not accept an action');
  await elements.start.onclick();
  assert.equal(elements.input.disabled,false,'start must unlock action input');
  elements.input.value='Aguardo';
  await elements.action.onsubmit({preventDefault(){}});
  assert.equal(actions,1,'action must be submitted');
  assert.equal(elements.input.disabled,false,'action must unlock next input');
  await elements.start.onclick();
  assert.equal(starts,2,'new session must be created');
  assert.equal(elements.input.disabled,false,'new session must unlock action input');
  assert.equal(elements.send.disabled,false,'send must remain enabled');
  missingAction=true;
  elements.input.value='Aguardo';
  await elements.action.onsubmit({preventDefault(){}});
  assert.equal(saved.has('storyteller-campaign-offline-session'),false,'missing campaign must invalidate local session');
  assert.equal(elements.input.disabled,true,'missing campaign must block further submits');
  assert.match(elements.error.textContent,/Nova sessão sintética/);
  await elements.start.onclick();
  assert.equal(starts,3,'user can recover with a new session');
  assert.equal(elements.input.disabled,false,'recovered session accepts actions');
})().catch(error=>{console.error(error);process.exitCode=1});
"""
    checked = subprocess.run([node, "-e", harness], input=script.group(1),
                             text=True, capture_output=True, check=False)
    assert checked.returncode == 0, checked.stderr


@pytest.mark.asyncio
async def test_offline_trial_is_opt_in_token_gated_and_reconstructs_complete_ending(tmp_path):
    app = create_app(tmp_path / "trial.sqlite3", access_token="synthetic-test-token")
    async with app.router.lifespan_context(app), AsyncClient(
        transport=ASGITransport(app=app), base_url="http://127.0.0.1:8021",
    ) as client:
        assert (await client.post("/api/start")).status_code == 403
        headers = {"X-Trial-Token": "synthetic-test-token"}
        page = await client.get("/")
        assert page.status_code == 200
        assert "Prosa autorada, não Luna" in page.text
        if node := shutil.which("node"):
            script = re.search(r"<script>(.*?)</script>", page.text, re.DOTALL)
            assert script is not None
            checked = subprocess.run([node, "--check", "-"], input=script.group(1),
                                     text=True, capture_output=True, check=False)
            assert checked.returncode == 0, checked.stderr
        first = (await client.post("/api/start", json={}, headers=headers)).json()
        session = first["session_id"]
        assert first["turn"] == 0 and first["external_provider_calls"] == 0
        for number, (action, record) in enumerate((
            ("Aguardo", "warned"), ("Espero", "wet"), ("Aguardo", "lost"),
        ), 1):
            response = await client.post("/api/action", json={
                "session_id": session, "operation_id": f"action-{number}",
                "player_input": action,
            }, headers=headers)
            assert response.status_code == 200, response.text
            body = response.json()
            assert body["result"]["status"] == "completed"
            assert body["turn"] == number and body["record"] == record
            assert body["external_provider_calls"] == body["provider_cost_usd"] == 0
        assert body["outcome"] == "lost"
        assert len(body["narratives"]) == 3
        recovered = (await client.get(f"/api/session/{session}", headers=headers)).json()
        assert recovered["narratives"] == body["narratives"]
        assert (await client.post("/api/action", json={
            "session_id": session, "operation_id": "after-end",
            "player_input": "Aguardo",
        }, headers=headers)).status_code == 409
        status = (await client.get(
            f"/api/operation/{session}/action-3", headers=headers,
        )).json()
        assert status["narrative_status"] == "completed"


@pytest.mark.asyncio
async def test_out_of_catalog_method_is_not_narrated_as_failure(tmp_path):
    app = create_app(tmp_path / "trial.sqlite3", access_token="synthetic-test-token")
    headers = {"X-Trial-Token": "synthetic-test-token"}
    async with app.router.lifespan_context(app), AsyncClient(
        transport=ASGITransport(app=app), base_url="http://127.0.0.1:8021",
    ) as client:
        session = (await client.post("/api/start", json={}, headers=headers)).json()["session_id"]
        response = await client.post("/api/action", json={
            "session_id": session, "operation_id": "unknown-action",
            "player_input": "Uso uma lona para desviar a água",
        }, headers=headers)
        assert response.status_code == 200
        body = response.json()
        assert body["result"]["error_code"] == "campaign_source_out_of_scope"
        assert body["turn"] == 0 and body["narratives"] == []
