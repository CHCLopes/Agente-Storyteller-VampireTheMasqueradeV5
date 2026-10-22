"""Dedicated A2 SQLite store. No migration or access to product saves."""
from __future__ import annotations
from contextlib import contextmanager
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sqlite3
from uuid import uuid4
from pydantic import Field
from ...campaign_progression_service import CampaignProgressState
from ...narrative_source_action_producer import _eligible_sheet
from ...rules_service import PlayerSheetModel
from .contract import (Frozen, PROFILE, Preparation, Selection, SelectionConfig,
 digest, json_text, produce_preparation, validate_retained_presentation, validate_selection)

APPLICATION_ID=0x41533231
STORE_VERSION="selection-experiment-store.v1"

class Session(Frozen):
 profile:str=PROFILE
 synthetic:bool=Field(default=True,strict=True)
 session_id:str=Field(min_length=1,max_length=160)
 config:SelectionConfig
 sheet:PlayerSheetModel
 state:CampaignProgressState

class SelectionStore:
 def __init__(self,path,*,create=False):
  self.path=Path(path).resolve()
  if create:
   handle=os.open(self.path,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600);os.close(handle)
   with sqlite3.connect(self.path) as c:
    c.executescript(f"""
     PRAGMA application_id={APPLICATION_ID};
     CREATE TABLE selection_meta(version TEXT NOT NULL);
     INSERT INTO selection_meta VALUES('{STORE_VERSION}');
     CREATE TABLE sessions(id TEXT PRIMARY KEY,revision INTEGER NOT NULL,payload TEXT NOT NULL,hash TEXT NOT NULL);
     CREATE TABLE operations(session_id TEXT NOT NULL,id TEXT NOT NULL,phase TEXT NOT NULL,input TEXT NOT NULL,
      capsule TEXT,capsule_hash TEXT,selection TEXT,presentation TEXT,error TEXT,
      PRIMARY KEY(session_id,id),FOREIGN KEY(session_id) REFERENCES sessions(id));
     CREATE UNIQUE INDEX one_prepared_operation ON operations(session_id) WHERE phase IN ('preparing','prepared');
     CREATE TABLE attempts(session_id TEXT NOT NULL,id TEXT NOT NULL,operation_id TEXT NOT NULL,status TEXT NOT NULL,
      invocation_id TEXT,error TEXT,PRIMARY KEY(session_id,id),
      FOREIGN KEY(session_id,operation_id) REFERENCES operations(session_id,id));
    """)
  elif not self.path.is_file():raise ValueError("selection_database_missing")
  with self._connection():pass

 @contextmanager
 def _connection(self,*,write=False):
  c=sqlite3.connect(self.path,timeout=2);c.row_factory=sqlite3.Row
  try:
   if c.execute("PRAGMA application_id").fetchone()[0]!=APPLICATION_ID:raise ValueError("selection_database_not_experimental")
   tables={r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'")}
   if tables!={'selection_meta','sessions','operations','attempts'}:raise ValueError("selection_database_shape")
   if [r[0] for r in c.execute("SELECT version FROM selection_meta")]!=[STORE_VERSION]:raise ValueError("selection_database_version")
   c.execute("PRAGMA foreign_keys=ON")
   c.execute("BEGIN IMMEDIATE" if write else "BEGIN")
   yield c
   if write:c.commit()
  except BaseException:
   if write:c.rollback()
   raise
  finally:c.close()

 def _session(self,c,session_id):
  row=c.execute("SELECT * FROM sessions WHERE id=?",(session_id,)).fetchone()
  if row is None:raise ValueError("selection_session_missing")
  s=Session.model_validate_json(row['payload'])
  if s.profile!=PROFILE or not s.synthetic or s.session_id!=session_id or s.state.revision!=row['revision'] or digest(s)!=row['hash']:raise ValueError("selection_session_invalid")
  return s

 def _capsule(self,row,session):
  if row is None or row['capsule'] is None:raise ValueError("selection_preparation_unavailable")
  p=Preparation.model_validate_json(row['capsule'])
  if (p.fingerprint_sha256!=row['capsule_hash'] or p.request.session_id!=row['session_id'] or p.request.operation_id!=row['id']
   or p.request.player_input!=row['input'] or p.config!=session.config or p.sheet!=session.sheet):raise ValueError("selection_operation_binding")
  return p

 def _selection(self,c,row,p):
  if row['selection'] is None:return None
  selected=Selection.model_validate_json(row['selection'])
  source=c.execute("SELECT * FROM attempts WHERE session_id=? AND id=?",(row['session_id'],selected.source_attempt_id)).fetchone()
  if source is None or source['operation_id']!=row['id']:raise ValueError("selection_source_attempt")
  validate_selection(p,selected,source['invocation_id'])
  if selected.origin=='model' and source['invocation_id'] is None:raise ValueError("selection_source_invocation")
  return selected

 def _history(self,c,session):
  state=CampaignProgressState(revision=0)
  rows=c.execute("SELECT * FROM operations WHERE session_id=? AND phase='completed' ORDER BY rowid",(session.session_id,)).fetchall()
  for row in rows:
   p=self._capsule(row,session)
   if p.request.state!=state:raise ValueError("selection_history_causality")
   result=validate_retained_presentation(p,json.loads(row['presentation']))
   if self._selection(c,row,p)!=result.selection:raise ValueError("selection_history_selection")
   finished=c.execute("SELECT COUNT(*) FROM attempts WHERE session_id=? AND operation_id=? AND status='completed'",(session.session_id,row['id'])).fetchone()[0]
   if finished!=1:raise ValueError("selection_history_completion")
   state=p.effect.after_state
  if session.state!=state:raise ValueError("selection_history_state")

 def create_session(self,session_id,*,config,sheet,synthetic=True):
  if synthetic is not True:raise ValueError("selection_synthetic_only")
  config=SelectionConfig.model_validate(config);sheet=PlayerSheetModel.model_validate(sheet)
  if _eligible_sheet({'player_sheet':sheet.model_dump(mode='json')},session_id) is None:raise ValueError("selection_sheet_out_of_scope")
  s=Session(session_id=session_id,config=config,sheet=sheet,state=CampaignProgressState(revision=0))
  with self._connection(write=True) as c:c.execute("INSERT INTO sessions VALUES(?,?,?,?)",(session_id,0,json_text(s),digest(s)))
  return s

 def session(self,session_id):
  with self._connection() as c:
   s=self._session(c,session_id);self._history(c,s);return s

 def prepare(self,session_id,operation_id,player_input):
  if not operation_id or operation_id!=operation_id.strip() or len(operation_id)>160:raise ValueError("selection_operation_id")
  if not player_input or player_input!=player_input.strip() or len(player_input)>500:raise ValueError("selection_player_input")
  with self._connection(write=True) as c:
   s=self._session(c,session_id);self._history(c,s)
   old=c.execute("SELECT * FROM operations WHERE session_id=? AND id=?",(session_id,operation_id)).fetchone()
   if old:
    if old['input']!=player_input:raise ValueError("selection_operation_reuse")
    return self._capsule(old,s)
   if s.state.outcome is not None:raise ValueError("selection_terminal_session")
   if c.execute("SELECT 1 FROM operations WHERE session_id=? AND phase IN ('preparing','prepared')",(session_id,)).fetchone():raise ValueError("selection_operation_pending")
   c.execute("INSERT INTO operations(session_id,id,phase,input) VALUES(?,?,'preparing',?)",(session_id,operation_id,player_input))
  # Durable input claim precedes RNG. The same operation cannot silently roll twice.
  try:p=produce_preparation(session_id,operation_id,player_input,s.state,s.sheet,s.config,datetime.now(timezone.utc))
  except BaseException:
   with self._connection(write=True) as c:c.execute("UPDATE operations SET phase='preparation_failed',error='production_failed' WHERE session_id=? AND id=? AND phase='preparing'",(session_id,operation_id))
   raise
  with self._connection(write=True) as c:
   if self._session(c,session_id).state!=p.request.state:raise ValueError("selection_prepare_revision")
   changed=c.execute("UPDATE operations SET phase='prepared',capsule=?,capsule_hash=? WHERE session_id=? AND id=? AND phase='preparing'",(json_text(p),p.fingerprint_sha256,session_id,operation_id)).rowcount
   if changed!=1:raise ValueError("selection_preparation_claim_lost")
  return p

 def preparation(self,session_id,operation_id):
  with self._connection() as c:
   s=self._session(c,session_id);self._history(c,s)
   row=c.execute("SELECT * FROM operations WHERE session_id=? AND id=?",(session_id,operation_id)).fetchone()
   return self._capsule(row,s)

 def claim(self,session_id,operation_id,attempt_id,*,resumes_attempt_id=None):
  if not attempt_id or attempt_id!=attempt_id.strip() or len(attempt_id)>160:raise ValueError("selection_attempt_id")
  with self._connection(write=True) as c:
   s=self._session(c,session_id);self._history(c,s)
   op=c.execute("SELECT * FROM operations WHERE session_id=? AND id=?",(session_id,operation_id)).fetchone();p=self._capsule(op,s)
   old=c.execute("SELECT * FROM attempts WHERE session_id=? AND id=?",(session_id,attempt_id)).fetchone()
   if old and old['operation_id']!=operation_id:raise ValueError("selection_attempt_reuse")
   if op['phase']=='completed':return {'status':'completed','presentation':validate_retained_presentation(p,json.loads(op['presentation'])),'preparation':p}
   if p.request.state!=s.state or op['phase']!='prepared':raise ValueError("selection_claim_revision")
   if old:return {'status':old['status'],'preparation':p,'error':old['error']}
   latest=c.execute("SELECT * FROM attempts WHERE session_id=? AND operation_id=? ORDER BY rowid DESC LIMIT 1",(session_id,operation_id)).fetchone()
   if latest:
    if resumes_attempt_id!=latest['id'] or latest['status'] not in ('failed','cancelled','interrupted'):raise ValueError("selection_explicit_resume_required")
   elif resumes_attempt_id is not None:raise ValueError("selection_resume_missing")
   selected=self._selection(c,op,p)
   invocation=str(uuid4()) if p.config.mode=='model' and selected is None else None
   c.execute("INSERT INTO attempts VALUES(?,?,?,'pending',?,NULL)",(session_id,attempt_id,operation_id,invocation))
   return {'status':'claimed','preparation':p,'selection':selected,'invocation_id':invocation}

 def save_selection(self,session_id,operation_id,attempt_id,selection):
  with self._connection(write=True) as c:
   s=self._session(c,session_id)
   op=c.execute("SELECT * FROM operations WHERE session_id=? AND id=?",(session_id,operation_id)).fetchone();p=self._capsule(op,s)
   attempt=c.execute("SELECT * FROM attempts WHERE session_id=? AND id=?",(session_id,attempt_id)).fetchone()
   if attempt is None or attempt['operation_id']!=operation_id or attempt['status']!='pending' or op['phase']!='prepared':raise ValueError("selection_attempt_claim_lost")
   selection=validate_selection(p,selection,attempt['invocation_id'])
   if selection.source_attempt_id!=attempt_id:raise ValueError("selection_source_claim")
   if op['selection'] is not None:raise ValueError("selection_already_retained")
   c.execute("UPDATE operations SET selection=? WHERE session_id=? AND id=?",(json_text(selection),session_id,operation_id))
   c.execute("UPDATE attempts SET status='ready' WHERE session_id=? AND id=?",(session_id,attempt_id))

 def commit(self,session_id,operation_id,attempt_id,presentation):
  with self._connection(write=True) as c:
   s=self._session(c,session_id);self._history(c,s)
   op=c.execute("SELECT * FROM operations WHERE session_id=? AND id=?",(session_id,operation_id)).fetchone();p=self._capsule(op,s)
   attempt=c.execute("SELECT * FROM attempts WHERE session_id=? AND id=?",(session_id,attempt_id)).fetchone()
   if attempt is None or attempt['operation_id']!=operation_id or attempt['status'] not in ('pending','ready') or op['phase']!='prepared':raise ValueError("selection_attempt_claim_lost")
   if s.state!=p.request.state:raise ValueError("selection_commit_revision")
   result=validate_retained_presentation(p,presentation)
   if result.selection!=self._selection(c,op,p):raise ValueError("selection_commit_selection")
   after=s.model_copy(update={'state':p.effect.after_state})
   changed=c.execute("UPDATE sessions SET revision=?,payload=?,hash=? WHERE id=? AND revision=?",(after.state.revision,json_text(after),digest(after),session_id,p.request.base_revision)).rowcount
   if changed!=1:raise ValueError("selection_commit_cas")
   c.execute("UPDATE operations SET phase='completed',presentation=? WHERE session_id=? AND id=?",(json_text(result),session_id,operation_id))
   c.execute("UPDATE attempts SET status='completed',error=NULL WHERE session_id=? AND id=?",(session_id,attempt_id))
  return result

 def fail(self,session_id,operation_id,attempt_id,*,status,error):
  if status not in ('failed','cancelled'):raise ValueError("selection_failure_status")
  with self._connection(write=True) as c:c.execute("UPDATE attempts SET status=?,error=? WHERE session_id=? AND operation_id=? AND id=? AND status IN ('pending','ready')",(status,error,session_id,operation_id,attempt_id))

 def recover_preparation(self,session_id,operation_id):
  """Explicitly terminate an interrupted input claim; never recreate its RNG."""
  with self._connection(write=True) as c:
   changed=c.execute("UPDATE operations SET phase='preparation_failed',error='explicit_preparation_recovery' WHERE session_id=? AND id=? AND phase='preparing' AND capsule IS NULL",(session_id,operation_id)).rowcount
   if changed!=1:raise ValueError("selection_preparation_recovery_cas")

 def recover_interrupted(self,session_id,operation_id,attempt_id,*,expected_invocation_id):
  """Explicit CAS invalidates a prior claim; it does not cancel remote billing."""
  with self._connection(write=True) as c:
   attempt=c.execute("SELECT * FROM attempts WHERE session_id=? AND id=?",(session_id,attempt_id)).fetchone()
   if (attempt is None or attempt['operation_id']!=operation_id or attempt['invocation_id']!=expected_invocation_id
    or attempt['status'] not in ('pending','ready')):raise ValueError("selection_recovery_cas")
   c.execute("UPDATE attempts SET status='interrupted',error='explicit_recovery' WHERE session_id=? AND id=?",(session_id,attempt_id))

 def attempts(self,session_id,operation_id):
  with self._connection() as c:return [dict(row) for row in c.execute("SELECT * FROM attempts WHERE session_id=? AND operation_id=? ORDER BY rowid",(session_id,operation_id))]
