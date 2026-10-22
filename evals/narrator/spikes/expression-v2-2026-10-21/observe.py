"""One offline A1 residual-risk observation. Labels fixed before execution."""
import asyncio, gc, hashlib, json, os, socket, sys, tempfile
from pathlib import Path
os.environ['STORYTELLER_DISABLE_DOTENV']='1'
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[4]
sys.path[:0]=[str(ROOT),str(ROOT/'tests')]
def deny(*a,**kw): raise RuntimeError('network_forbidden')
from test_campaign_expression_v2 import setup, prepare, execute, eligible_state
from api.persistence import SQLitePersistence
from api.campaign_expression_storage import create_campaign_expression_session
from api.campaign_expression_profile import validate_campaign_expression_proposal
from api.campaign_progression_service import build_campaign_narrator_packet
CASES=[
 ('task', ['Qual é a tarefa?'], [
  ('goal',False,'mara.reaction','Sua missão é investigar o conteúdo, não preservar o registro.'),
  ('lore',False,'mara.reaction','A fundadora me fez jurar que jamais revelaria seu nome.'),
  ('optional',True,'mara.reaction','Examinar é uma opção; o objetivo continua sendo preservar o registro.')]),
 ('refusal',['Quem é a fundadora?'],[
  ('oath',False,'mara.reaction','Fiz um juramento de silêncio à fundadora.'),
  ('simple',True,'mara.reaction','Essa identidade eu não revelo.')]),
 ('warning',['Aguardo'],[
  ('denied',False,'mara.reaction','Não há risco para o documento.'),
  ('agency',False,'atmosphere','Você abre a porta.'),
  ('brief',True,'mara.reaction','Ainda dá tempo.')]),
 ('preserved',['Retiro o registro'],[
  ('care',False,'mara.reaction','Falta embrulhar as folhas antes de terminarmos.'),
  ('move',False,'mara.reaction','Agora leve o documento para a outra mesa.'),
  ('complete',True,'mara.reaction','O registro está salvo.')]),
 ('partial',['Aguardo','Espero','Retiro o registro'],[
  ('dry',False,'mara.reaction','As folhas já secaram por completo.'),
  ('restored',False,'mara.reaction','Todas as linhas voltaram a ficar legíveis.'),
  ('wet',True,'mara.reaction','As folhas continuam molhadas.'),
  ('not_dry',True,'mara.reaction','As folhas não secaram por completo.')]),
 ('abandoned',['Desisto'],[
  ('emotion',False,'atmosphere','Você sente vergonha da própria decisão.'),
  ('ack',True,'mara.reaction','Entendido.')]),
]
async def main():
 socket.socket.connect=deny
 socket.create_connection=deny
 output=Path(__file__).with_name('observation.json')
 if output.exists(): raise RuntimeError('observation_exists')
 rows=[]
 with tempfile.TemporaryDirectory(prefix='storyteller-a1-residual-') as directory:
  for name,actions,variants in CASES:
   store=SQLitePersistence(Path(directory)/(name+'.sqlite3'))
   await create_campaign_expression_session(store,'expression',initial_state=eligible_state())
   config,gateway=setup()
   for i,action in enumerate(actions):
    cap=await prepare(store,config,action,str(i))
    if i<len(actions)-1:
     assert (await execute(store,cap,gateway,[])).status=='completed'
   packet=build_campaign_narrator_packet(cap.campaign_request,cap.campaign_effect)
   for label,valid,slot,text in [('empty',True,'mara.reaction',''),*variants]:
    raw={'protocol':'campaign-source-expression-v2','plan_sha256':cap.realization_plan.plan_sha256,
         'slots':[{'slot_id':s.slot_id,'text':text if s.slot_id==slot else ''} for s in cap.realization_plan.slots]}
    try:
     result=validate_campaign_expression_proposal(raw,plan=cap.realization_plan,packet=packet,facts=cap.draft.facts,snapshot=cap.snapshot,invocation_id='synthetic')
     accepted=True; narrative=result.narrative
    except ValueError:
     accepted=False;narrative=None
    rows.append(dict(id=name+'.'+label,authored_valid=valid,accepted=accepted,slot=slot,text=text,narrative=narrative))
  gc.collect();await asyncio.sleep(0)
 data={'protocol':'a1-residual-observation-v1','provider_calls':0,'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
       'implementation_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (ROOT/'api').glob('campaign_expression_*.py')},
       'invalid_accepted':sum(not r['authored_valid'] and r['accepted'] for r in rows),
       'valid_rejected':sum(r['authored_valid'] and not r['accepted'] for r in rows),'observations':rows}
 output.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 print(json.dumps({k:v for k,v in data.items() if k not in ('observations','implementation_sha256')},ensure_ascii=False))
asyncio.run(main())
