"""A2 v1: closed expression choices; editorial truth remains application-owned."""
from __future__ import annotations
from datetime import datetime
import hashlib
import json
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator
from ... import rules_service as rules
from ...campaign_progression_catalog import CampaignIntentKind, classify_campaign_intent
from ...campaign_progression_service import (
 CampaignProgressState, CampaignPreparedEffect, CampaignProgressionRequest,
 build_campaign_narrator_packet, resolve_campaign_progression, verify_campaign_prepared_effect,
)
from ...campaign_expression_rendering import RealizationPlan, compile_plan_v1
from ...llm.contract import GenerationParameters, InvocationEvidence, LLMTarget
from ...scene_resolution_service import mechanical_resolution_from_result

PROFILE="campaign-selection-local-v1"
CATALOG_VERSION="campaign-selection-catalog.v1"
RENDERER_VERSION="campaign-selection-renderer.v1"

def json_text(value):
 if isinstance(value,BaseModel):value=value.model_dump(mode="json")
 return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(",",":"),allow_nan=False)

def digest(value):return hashlib.sha256(json_text(value).encode()).hexdigest()

def identifier(session_id,operation_id,role):return role+"-"+digest([PROFILE,session_id,operation_id,role])

class Frozen(BaseModel):
 model_config=ConfigDict(extra="forbid",frozen=True,revalidate_instances="always",hide_input_in_errors=True)

class SelectionConfig(Frozen):
 profile:Literal["campaign-selection-local-v1"]=PROFILE
 mode:Literal["deterministic","model"]
 target:LLMTarget|None=None
 allow_emulated:bool=Field(default=False,strict=True)
 parameters:GenerationParameters=GenerationParameters(max_output_tokens=128)
 @model_validator(mode="after")
 def valid(self):
  if (self.mode=="model")!=(self.target is not None):raise ValueError("selection_target_mode")
  if self.mode=="deterministic" and self.allow_emulated:raise ValueError("selection_baseline_emulation")
  if self.parameters.max_output_tokens is None or not 1<=self.parameters.max_output_tokens<=256:raise ValueError("selection_output_budget")
  return self

class Choice(Frozen):
 utterance:Literal["original","variant"]
 atmosphere:Literal["none","position"]
 layout:Literal["inline","paragraph"]

def parse_choice(raw):
 if type(raw) is not str or len(raw.encode("utf-8"))>512:raise ValueError("selection_wire_size")
 def unique(pairs):
  value={}
  for key,item in pairs:
   if key in value:raise ValueError("selection_duplicate_key")
   value[key]=item
  return value
 return Choice.model_validate(json.loads(raw,object_pairs_hook=unique))

class Option(Frozen):
 option_id:str
 text:str
 actor:Literal["mara","environment"]
 speaker:Literal["mara"]|None=None
 effect_refs:tuple[str,...]
 fact_refs:tuple[str,...]

class Catalog(Frozen):
 version:Literal["campaign-selection-catalog.v1"]=CATALOG_VERSION
 condition_key:str
 source_plan_sha256:str
 utterances:tuple[Option,Option]
 atmospheres:tuple[Option,Option]
 @model_validator(mode="after")
 def valid(self):
  if tuple(x.option_id for x in self.utterances)!=("original","variant"):raise ValueError("selection_utterances")
  if tuple(x.option_id for x in self.atmospheres)!=("none","position"):raise ValueError("selection_atmospheres")
  if any(x.actor!="mara" or x.speaker!="mara" for x in self.utterances):raise ValueError("selection_speaker")
  if any(x.actor!="environment" or x.speaker is not None for x in self.atmospheres):raise ValueError("selection_atmosphere_actor")
  return self

_SPEECH_V1={
 "R-02":"Não vou revelar quem é a fundadora.",
 "R-03":"A água está se aproximando do registro.",
 "R-03B":"As páginas ficaram molhadas.",
 "R-04":"O conteúdo do registro se tornou irrecuperável.",
 "R-05":"O registro foi salvo intacto.",
 "R-06":"Só a parte ainda legível foi preservada.",
 "R-07":"Foi possível recuperar parte do conteúdo.",
 "R-08":"A tentativa de leitura do registro falhou.",
 "R-09":"Entendido. Sua tentativa de resgate terminou.",
}

def compile_catalog_v1(request,effect,plan):
 rule=effect.rule_id
 variant="plain"
 if rule=="R-01":
  if "mara.responds.to_rescue_request" in effect.beat.effect_keys:
   variant="help"
   speech="Posso orientar você sobre o resgate. A superfície seca para o registro fica na Galeria."
  elif "safe_surface" in request.state.known_information:
   variant="repeat"
   speech="Como eu disse, precisamos preservar o registro da água. A superfície seca fica na Galeria."
  else:
   variant="task"
   speech="A tarefa é proteger o registro da água. Você pode levá-lo até a superfície seca da Galeria."
 else:speech=_SPEECH_V1[rule]
 physical,essential=plan.critical
 refs={"effect_refs":essential.effect_refs,"fact_refs":essential.fact_refs}
 position={"bench":"na bancada baixa do Arquivo","dry_surface":"na superfície seca da Galeria"}[effect.after_state.record_location]
 return Catalog(condition_key="/".join((rule,variant,request.state.record,effect.after_state.record,str(effect.after_state.outcome))),
  source_plan_sha256=plan.plan_sha256,
  utterances=(Option(option_id="original",text=essential.text,actor="mara",speaker="mara",**refs),
              Option(option_id="variant",text="Mara diz: “"+speech+"”",actor="mara",speaker="mara",**refs)),
  atmospheres=(Option(option_id="none",text="",actor="environment",effect_refs=(),fact_refs=()),
   Option(option_id="position",text="O registro está "+position+".",actor="environment",effect_refs=physical.effect_refs,fact_refs=physical.fact_refs)))

# Retained version implementations are independent from the current builders.
_CATALOG_COMPILERS={CATALOG_VERSION:compile_catalog_v1}
_PLAN_COMPILER_V1=compile_plan_v1

def build_catalog(request,effect,plan):return compile_catalog_v1(request,effect,plan)

class Preparation(Frozen):
 protocol:Literal["campaign-selection-preparation.v1"]="campaign-selection-preparation.v1"
 created_at:datetime
 config:SelectionConfig
 request:CampaignProgressionRequest
 effect:CampaignPreparedEffect
 sheet:rules.PlayerSheetModel
 resolution:rules.ResolutionResult|None
 plan:RealizationPlan
 catalog:Catalog
 fingerprint_sha256:str
 @model_validator(mode="after")
 def valid(self):
  if self.created_at.utcoffset() is None:raise ValueError("selection_time")
  if type(self.request.state) is not CampaignProgressState:raise ValueError("selection_requires_record_v2")
  effect=verify_campaign_prepared_effect(self.request,self.effect)
  if self.request.turn_id!=identifier(self.request.session_id,self.request.operation_id,"turn"):raise ValueError("selection_turn_binding")
  receipt_id=identifier(self.request.session_id,self.request.operation_id,"mechanical")
  mechanical=mechanical_resolution_from_result(self.resolution,source_fact_id=receipt_id) if self.resolution else None
  if self.request.mechanical!=mechanical:raise ValueError("selection_receipt_binding")
  if (classify_campaign_intent(self.request.player_input) is CampaignIntentKind.INSPECT)!=(self.resolution is not None):raise ValueError("selection_receipt_required")
  refs=("effect-"+effect.effect_sha256,)+( (receipt_id,) if self.resolution else ())
  packet=build_campaign_narrator_packet(self.request,effect)
  if self.plan!=_PLAN_COMPILER_V1(packet,refs):raise ValueError("selection_plan_binding")
  if self.catalog!=_CATALOG_COMPILERS[self.catalog.version](self.request,effect,self.plan):raise ValueError("selection_catalog_binding")
  if self.fingerprint_sha256!=digest(self.model_dump(mode="json",exclude={"fingerprint_sha256"})):raise ValueError("selection_preparation_hash")
  return self

def produce_preparation(session_id,operation_id,player_input,state,sheet,config,created_at):
 intent=classify_campaign_intent(player_input)
 if intent is None:raise ValueError("selection_out_of_scope")
 receipt=None
 if intent is CampaignIntentKind.INSPECT:
  wits=sheet.attributes.get("Wits");investigation=sheet.skills.get("Investigation")
  if type(wits) is not int or not 1<=wits<=5 or type(investigation) is not int or not 0<=investigation<=5:raise ValueError("selection_sheet_out_of_scope")
  action=rules.V5ActionPayload(intent=player_input,attribute=rules.V5Attribute.Wits,skill=rules.V5Skill.INVESTIGATION,
   requires_roll=True,is_aggressive=False,inferred_difficulty=3,action_target=rules.V5ActionTarget.UNOPPOSED,weapon_category=rules.V5WeaponCategory.UNARMED)
  receipt=rules.calculate_resolution(action,current_hunger=0,dice_pool=wits+investigation)
 mechanical=mechanical_resolution_from_result(receipt,source_fact_id=identifier(session_id,operation_id,"mechanical")) if receipt else None
 request=CampaignProgressionRequest(session_id=session_id,operation_id=operation_id,turn_id=identifier(session_id,operation_id,"turn"),
  base_revision=state.revision,player_input=player_input,state=state,mechanical=mechanical)
 effect=resolve_campaign_progression(request)
 refs=("effect-"+effect.effect_sha256,)+((identifier(session_id,operation_id,"mechanical"),) if receipt else ())
 plan=_PLAN_COMPILER_V1(build_campaign_narrator_packet(request,effect),refs)
 payload=dict(created_at=created_at,config=config,request=request,effect=effect,sheet=sheet,resolution=receipt,
  plan=plan,catalog=build_catalog(request,effect,plan))
 raw=Preparation.model_construct(**payload,fingerprint_sha256="").model_dump(mode="json",exclude={"fingerprint_sha256"})
 return Preparation.model_validate(dict(raw,fingerprint_sha256=digest(raw)))

class Selection(Frozen):
 choice:Choice
 origin:Literal["deterministic","model"]
 source_attempt_id:str
 raw_output:str|None=None
 evidence:InvocationEvidence|None=None
 @model_validator(mode="after")
 def valid(self):
  if (self.origin=="model")!=(self.evidence is not None):raise ValueError("selection_evidence_required")
  if self.origin=="model" and parse_choice(self.raw_output)!=self.choice:raise ValueError("selection_raw_binding")
  if self.origin=="deterministic" and (self.raw_output is not None or self.choice!=Choice(utterance="original",atmosphere="none",layout="inline")):raise ValueError("selection_baseline_binding")
  return self

def validate_selection(preparation,selection,invocation_id=None):
 selected=Selection.model_validate(selection)
 if selected.origin!=preparation.config.mode:raise ValueError("selection_mode_mismatch")
 if selected.evidence:
  p=selected.evidence.provenance
  if (p.requested_target!=preparation.config.target or (invocation_id is not None and p.invocation_id!=invocation_id)
   or p.effective_model.value not in (None,preparation.config.target.model)
   or p.effective_provider.value not in (None,preparation.config.target.provider)):raise ValueError("selection_target_mismatch")
 return selected

class Segment(Frozen):
 origin:Literal["application"]="application"
 text:str
 start:int=Field(ge=0,strict=True)
 end:int=Field(ge=0,strict=True)
 separator_before:Literal[""," ","\n\n"]
 actor:Literal["player","environment","record","mara"]
 speaker:Literal["mara"]|None=None
 effect_refs:tuple[str,...]
 fact_refs:tuple[str,...]

class Presentation(Frozen):
 protocol:Literal["campaign-selection-presentation.v1"]="campaign-selection-presentation.v1"
 renderer_version:Literal["campaign-selection-renderer.v1"]=RENDERER_VERSION
 preparation_sha256:str
 catalog_sha256:str
 text:str
 segments:tuple[Segment,...]
 question:str
 selection:Selection
 realized_effects:tuple[str,...]
 semantic_truth_assessed:Literal[False]=False
 fingerprint_sha256:str
 @model_validator(mode="after")
 def valid(self):
  offset=0;parts=[]
  for s in self.segments:
   offset+=len(s.separator_before)
   if s.start!=offset or s.end!=offset+len(s.text) or self.text[s.start:s.end]!=s.text:raise ValueError("selection_segment_offsets")
   parts.append(s.separator_before+s.text);offset=s.end
  if self.text!="".join(parts)+("\n\n"+self.question if self.question else ""):raise ValueError("selection_text_segments")
  if self.fingerprint_sha256!=digest(self.model_dump(mode="json",exclude={"fingerprint_sha256"})):raise ValueError("selection_presentation_hash")
  return self

def _selected_parts(preparation,choice):
 c=preparation.catalog;physical=preparation.plan.critical[0]
 return [physical,next(x for x in c.utterances if x.option_id==choice.utterance)]+[
  x for x in c.atmospheres if x.option_id==choice.atmosphere and x.text]

def render_v1(preparation,selection):
 selection=validate_selection(preparation,selection)
 segments=[];text="";separator=" " if selection.choice.layout=="inline" else "\n\n"
 for part in _selected_parts(preparation,selection.choice):
  sep=separator if segments else "";text+=sep;start=len(text);text+=part.text
  segments.append(Segment(text=part.text,start=start,end=len(text),separator_before=sep,
   actor=part.actor,speaker=part.speaker,effect_refs=part.effect_refs,fact_refs=part.fact_refs))
 question=preparation.plan.question
 if question:text+="\n\n"+question
 payload=dict(preparation_sha256=preparation.fingerprint_sha256,catalog_sha256=digest(preparation.catalog),text=text,
  segments=tuple(segments),question=question,selection=selection,realized_effects=preparation.effect.beat.effect_keys)
 raw=Presentation.model_construct(**payload,fingerprint_sha256="").model_dump(mode="json",exclude={"fingerprint_sha256"})
 return Presentation.model_validate(dict(raw,fingerprint_sha256=digest(raw)))

def render(preparation,selection):return render_v1(preparation,selection)

def validate_retained_presentation(preparation,value):
 p=Presentation.model_validate(value);validate_selection(preparation,p.selection)
 if p.preparation_sha256!=preparation.fingerprint_sha256 or p.catalog_sha256!=digest(preparation.catalog):raise ValueError("selection_presentation_binding")
 parts=_selected_parts(preparation,p.selection.choice)
 if (len(p.segments)!=len(parts) or p.question!=preparation.plan.question or p.realized_effects!=preparation.effect.beat.effect_keys):raise ValueError("selection_presentation_parts")
 for s,part in zip(p.segments,parts):
  if any(getattr(s,key)!=getattr(part,key) for key in ("text","actor","speaker","effect_refs","fact_refs")):raise ValueError("selection_retained_text")
 expected_separator=" " if p.selection.choice.layout=="inline" else "\n\n"
 if tuple(s.separator_before for s in p.segments)!=("",)+(expected_separator,)*(len(parts)-1):raise ValueError("selection_retained_layout")
 return p
