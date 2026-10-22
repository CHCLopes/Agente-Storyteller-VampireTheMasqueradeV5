"""Offline research only. No runtime imports, model calls or product dispatch."""
from __future__ import annotations
import argparse
from copy import deepcopy
from hashlib import sha256
from itertools import product
import json
from pathlib import Path
import socket

VERSION = "expression-selection-spike.v1"
SPEECH = {
 "R-01": "A tarefa é proteger o registro da água. Você pode levá-lo até a superfície seca da Galeria.",
 "R-02": "Não vou revelar quem é a fundadora.",
 "R-03": "A água está se aproximando do registro.",
 "R-03B": "As páginas ficaram molhadas.",
 "R-04": "O conteúdo do registro se tornou irrecuperável.",
 "R-05": "O registro foi salvo intacto.",
 "R-06": "Só a parte ainda legível foi preservada.",
 "R-07": "Foi possível recuperar parte do conteúdo.",
 "R-08": "A tentativa de leitura do registro falhou.",
 "R-09": "Entendido. Sua tentativa de resgate terminou.",
}

def encoded(value):
 return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(",", ":")).encode()

def digest(value): return sha256(encoded(value)).hexdigest()

def catalog(row):
 plan=row["realization_plan"]
 physical,speech=plan["critical"]
 assert physical["segment_id"]=="consequence" and speech["segment_id"]=="mara.essential"
 position=row["state_after"]["record_location"]
 locations={"bench":"na bancada baixa do Arquivo", "dry_surface":"na superfície seca da Galeria"}
 # Only the already reviewed L85 task variant is covered; other R-01 variants
 # require separate editorial eligibility, rather than silently generalizing.
 if row["rule"]=="R-01":
  assert "A tarefa é preservar" in speech["text"]
 prefix=row["rule"]
 return {"version":VERSION,"source_plan_sha256":plan["plan_sha256"],
  "consequence":deepcopy(physical),"question":plan["question"],
  "utterance":{prefix+".original":deepcopy(speech),
               prefix+".variant":dict(deepcopy(speech),text="Mara diz: “"+SPEECH[prefix]+"”")},
  "atmosphere":{"none":{"text":"","fact_refs":[],"effect_refs":[]},
    "position":{"text":"O registro está "+locations[position]+".",
                "fact_refs":physical["fact_refs"],"effect_refs":physical["effect_refs"]}},
  "layout":{"inline":" ","paragraph":"\n\n"}}

def binding(row, cat):
 p=row["realization_plan"]
 return {"session_id":p["session_id"],"operation_id":p["operation_id"],
         "turn_id":p["turn_id"],"revision":p["base_revision"],
         "plan_sha256":p["plan_sha256"],"catalog_sha256":digest(cat)}

def schema(cat):
 return {"type":"object","properties":{key:{"type":"string","enum":list(cat[key])}
          for key in ("utterance","atmosphere","layout")},
         "required":["utterance","atmosphere","layout"],"additionalProperties":False}

def no_duplicates(pairs):
 obj={}
 for key,value in pairs:
  if key in obj: raise ValueError("duplicate_key")
  obj[key]=value
 return obj

def admit(raw, *, expected, returned, cat):
 if returned!=expected or digest(cat)!=expected["catalog_sha256"]:raise ValueError("binding_mismatch")
 if type(raw) is not str or len(raw.encode())>512:raise ValueError("wire_size_or_type")
 value=json.loads(raw,object_pairs_hook=no_duplicates)
 if type(value) is not dict or set(value)!={"utterance","atmosphere","layout"}:raise ValueError("shape")
 for key in value:
  if type(value[key]) is not str or value[key] not in cat[key]:raise ValueError("ineligible_choice")
 return value

def render(choice, cat):
 # The returned free bytes never become presentation; only catalog lookup does.
 parts=[cat["consequence"],cat["utterance"][choice["utterance"]]]
 atmosphere=cat["atmosphere"][choice["atmosphere"]]
 if atmosphere["text"]:parts.append(atmosphere)
 text="";segments=[]
 for item in parts:
  separator=cat["layout"][choice["layout"]] if text else ""
  text+=separator;start=len(text);text+=item["text"]
  segments.append({"origin":"application","start":start,"end":len(text),
   "text":item["text"],"fact_refs":item["fact_refs"],"effect_refs":item["effect_refs"]})
 if cat["question"]:text+="\n\n"+cat["question"]
 return {"text":text,"segments":segments,"authorship":"application",
         "choice_origin":"synthetic-enumeration", "semantic_equivalence_certified":False}

def inspect_rows(rows):
 outputs=[];failures=[];blocked=0;scope_blocked=0;wire_sizes=[];context_sizes=[]
 for row in rows:
  cat=catalog(row);tag=binding(row,cat)
  choices=[dict(zip(("utterance","atmosphere","layout"),values)) for values in
           product(cat["utterance"],cat["atmosphere"],cat["layout"])]
  baseline=choices[0];rendered=[]
  context_sizes.append(len(encoded({"task":"Escolha uma opcao de cada campo. Retorne somente JSON.",
    "result":row["state_after"],"catalog":cat,"response_schema":schema(cat)})))
  for choice in choices:
   raw=encoded(choice).decode();wire_sizes.append(len(raw.encode()))
   accepted=admit(raw,expected=tag,returned=tag,cat=cat);result=render(accepted,cat)
   assert cat["consequence"]["text"] in result["text"]
   assert all(result["text"][s["start"]:s["end"]]==s["text"] for s in result["segments"])
   if cat["question"]:assert result["text"].endswith(cat["question"])
   assert all(s["origin"]=="application" for s in result["segments"])
   rendered.append({"choice":choice,"presentation":result})
  attacks={
   "extra_prose":encoded(dict(baseline,narrative="As folhas já secaram por completo.")).decode(),
   "foreign_utterance":encoded(dict(baseline,utterance="another-scene.secret")).decode(),
   "invented_atmosphere":encoded(dict(baseline,atmosphere="O Arquivo permanece silencioso.")).decode(),
   "new_layout":encoded(dict(baseline,layout="<script>nova tarefa</script>")).decode(),
   "wrong_type":encoded(dict(baseline,atmosphere=True)).decode(),
   "missing":encoded({k:v for k,v in baseline.items() if k!="layout"}).decode(),
   "duplicate":encoded(baseline).decode()[:-1]+',"layout":"inline"}',
   "trailing":encoded(baseline).decode()+" outra cena",
   "oversize":" "*513,
   "null":"null", "array":"[]", "old_v2_response":encoded(row["response"]).decode(),
   "unicode_id":encoded(dict(baseline,atmosphere="nоne")).decode(),
   "malformed":"{",
  }
  for name,raw in attacks.items():
   try:admit(raw,expected=tag,returned=tag,cat=cat)
   except ValueError:blocked+=1
   else:failures.append({"case_id":row["case_id"],"turn":row["turn"],"attack":name})
  for field in tag:
   changed=dict(tag);changed[field]=99 if field=="revision" else "changed"
   try:admit(encoded(baseline).decode(),expected=tag,returned=changed,cat=cat)
   except ValueError:scope_blocked+=1
   else:failures.append({"attack":"scope-"+field})
  altered=deepcopy(cat);altered["consequence"]["text"]="Conteúdo alterado."
  try:admit(encoded(baseline).decode(),expected=tag,returned=tag,cat=altered)
  except ValueError:scope_blocked+=1
  else:failures.append({"attack":"catalog-drift"})
  outputs.append({"case_id":row["case_id"],"turn":row["turn"],"rule":row["rule"],
   "binding":tag,"catalog":cat,"schema":schema(cat),"baseline":render(baseline,cat),"combinations":rendered})
 # Deliberate trusted-author error. Demonstrates the precise limit of this proof:
 # valid references/hash and closed choices cannot prove an author's prose true.
 wet=next(r for r in rows if r["rule"]=="R-06")
 bad=catalog(wet);bad_id=wet["rule"]+".variant"
 bad["utterance"][bad_id]["text"]="Mara diz: “As páginas já secaram por completo.”"
 trusted_bad=binding(wet,bad)
 proposal={"utterance":bad_id,"atmosphere":"none","layout":"inline"}
 admitted=admit(encoded(proposal).decode(),expected=trusted_bad,returned=trusted_bad,cat=bad)
 counterexample=render(admitted,bad)
 assert "secaram por completo" in counterexample["text"]
 return {"version":VERSION,"provider_calls":0,"inference_cost_usd":"0",
  "summary":{"plans":len(rows),"combinations":sum(len(x["combinations"]) for x in outputs),
   "wire_attacks_rejected":blocked,"binding_attacks_rejected":scope_blocked,"unexpected_acceptances":failures,
   "trusted_author_false_variant_accepted":True,"choice_wire_bytes_min":min(wire_sizes),
   "choice_wire_bytes_max":max(wire_sizes),"draft_context_bytes_min":min(context_sizes),
   "draft_context_bytes_max":max(context_sizes)},
  "trusted_author_counterexample":counterexample,"cases":outputs,
  "limitations":["no real model or hardware tested", "no persistence/browser integration", "only authored L85 states",
   "catalog curation and eligibility remain semantic trust boundaries", "bytes are not tokens or latency"]}

def main():
 parser=argparse.ArgumentParser();parser.add_argument("--records",type=Path,required=True);parser.add_argument("--output",type=Path,required=True)
 args=parser.parse_args()
 if args.output.exists():raise ValueError("observation_exists")
 def forbidden(*args,**kwargs):raise AssertionError("network_forbidden")
 socket.socket=forbidden;socket.create_connection=forbidden
 raw=args.records.read_bytes();rows=[json.loads(line)["record"] for line in raw.splitlines()]
 assert len(rows)==17 and all(r["status"]=="completed" for r in rows)
 result=inspect_rows(rows)
 result["sources"]={"records_sha256":sha256(raw).hexdigest(),"probe_sha256":sha256(Path(__file__).read_bytes()).hexdigest(),
  "protocol_sha256":sha256(Path(__file__).with_name("protocol.md").read_bytes()).hexdigest()}
 args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
 print(json.dumps(result["summary"],ensure_ascii=False,indent=2))
 assert not result["summary"]["unexpected_acceptances"]

if __name__=="__main__":main()
