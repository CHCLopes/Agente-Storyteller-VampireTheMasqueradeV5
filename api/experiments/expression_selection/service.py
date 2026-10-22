"""Explicit A2 execution; one choice per claimed attempt, no fallback or repair."""
from __future__ import annotations
import asyncio
from dataclasses import dataclass
from datetime import datetime,timezone
from . import contract
from .contract import Choice, Presentation, Selection, parse_choice, validate_selection
from .store import SelectionStore
from .transport import SelectionGateway
from ...llm.contract import (CancellationToken,CapabilityRequirement,InvocationEvidence,
 LLMInvocationError,LLMMessage,StructuredGenerationRequest)

SYSTEM_PROMPT=("Escolha apenas uma opcao de cada campo do catalogo publico preparado. "
 "As consequencias ja foram decididas pela aplicacao. Escolha a forma mais natural e evite redundancia. "
 "Retorne somente um objeto JSON com utterance, atmosphere e layout usando os IDs fornecidos. "
 "Nao escreva narrativa, explicacoes, Markdown ou campos extras.")

@dataclass(frozen=True)
class ExecutionResult:
 status:str
 presentation:Presentation|None=None
 error_code:str|None=None

class _Stop(Exception):
 def __init__(self,status,code):self.status,self.code=status,code

def build_request(preparation,invocation_id,deadline,cancellation):
 c=preparation.catalog
 payload={'consequence':preparation.plan.critical[0].text,'question':preparation.plan.question,
  'options':{'utterance':{x.option_id:x.text for x in c.utterances},
             'atmosphere':{x.option_id:x.text for x in c.atmospheres},
             'layout':{'inline':'Paragrafo unico.','paragraph':'Separar consequencia e fala.'}},
  'response_schema':Choice.model_json_schema()}
 raw=contract.json_text(payload)
 if len(raw.encode())>10000:raise ValueError('selection_context_limit')
 return StructuredGenerationRequest(invocation_id=invocation_id,operation='H6.expression_selection.v1',
  target=preparation.config.target,messages=(LLMMessage(role='system',content=SYSTEM_PROMPT),LLMMessage(role='user',content=raw)),
  deadline=deadline,cancellation=cancellation,parameters=preparation.config.parameters,response_model=Choice,
  required_capabilities=(CapabilityRequirement(name='text_generation'),CapabilityRequirement(name='structured_generation',allow_emulated=preparation.config.allow_emulated)))

async def execute(*,store:SelectionStore,session_id:str,operation_id:str,attempt_id:str,
 deadline:datetime,cancellation:CancellationToken,gateway:SelectionGateway|None=None,resumes_attempt_id:str|None=None):
 if type(deadline) is not datetime or deadline.utcoffset() is None or type(cancellation) is not CancellationToken:raise ValueError('selection_execution_arguments')
 claimed=store.claim(session_id,operation_id,attempt_id,resumes_attempt_id=resumes_attempt_id)
 if claimed['status']=='completed':return ExecutionResult('completed',claimed['presentation'])
 if claimed['status']!='claimed':return ExecutionResult(claimed['status'],error_code=claimed.get('error') or 'selection_attempt_pending')
 p=claimed['preparation']
 try:
  if cancellation.is_cancelled:raise _Stop('cancelled','selection_cancelled')
  remaining=(deadline-datetime.now(timezone.utc)).total_seconds()
  if remaining<=0:raise _Stop('failed','selection_deadline')
  selected=claimed['selection']
  if selected is None:
   if p.config.mode=='deterministic':
    selected=Selection(choice=Choice(utterance='original',atmosphere='none',layout='inline'),origin='deterministic',source_attempt_id=attempt_id)
   else:
    if gateway is None:raise _Stop('failed','selection_gateway_missing')
    request=build_request(p,claimed['invocation_id'],deadline,cancellation)
    if gateway.capabilities(p.config.target).unmet(request.required_capabilities):raise _Stop('failed','selection_capability_missing')
    async with asyncio.timeout(remaining):response=await gateway.select(request)
    evidence=InvocationEvidence.model_validate(response.evidence.model_dump(mode='json'))
    selected=Selection(choice=parse_choice(response.raw),origin='model',source_attempt_id=attempt_id,raw_output=response.raw,evidence=evidence)
    validate_selection(p,selected,claimed['invocation_id'])
   # Retain a validated choice before checking post-generation cancellation.
   # Explicit resume then reuses this evidence without paying for another choice.
   store.save_selection(session_id,operation_id,attempt_id,selected)
  if cancellation.is_cancelled:raise _Stop('cancelled','selection_cancelled')
  if datetime.now(timezone.utc)>=deadline:raise _Stop('failed','selection_deadline')
  presentation=contract.render(p,selected)
  # No text leaves this function until state, presentation and attempt commit.
  committed=store.commit(session_id,operation_id,attempt_id,presentation)
  return ExecutionResult('completed',committed)
 except asyncio.CancelledError:
  store.fail(session_id,operation_id,attempt_id,status='cancelled',error='selection_task_cancelled')
  raise
 except _Stop as exc:
  store.fail(session_id,operation_id,attempt_id,status=exc.status,error=exc.code)
  return ExecutionResult(exc.status,error_code=exc.code)
 except LLMInvocationError:
  store.fail(session_id,operation_id,attempt_id,status='failed',error='selection_provider_failure')
  return ExecutionResult('failed',error_code='selection_provider_failure')
 except TimeoutError:
  store.fail(session_id,operation_id,attempt_id,status='failed',error='selection_deadline')
  return ExecutionResult('failed',error_code='selection_deadline')
 except Exception:
  # Do not persist invalid raw prose, exception locals, provider payloads or secrets.
  store.fail(session_id,operation_id,attempt_id,status='failed',error='selection_validation_or_commit_failed')
  return ExecutionResult('failed',error_code='selection_validation_or_commit_failed')
