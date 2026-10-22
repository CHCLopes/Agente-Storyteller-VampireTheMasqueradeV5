"""Raw selection boundary; protocol and evidence reuse the agnostic LLM contract."""
from dataclasses import dataclass
from typing import Protocol
import asyncio
from ...llm.contract import CapabilitySet, InvocationEvidence, LLMInvocationError, LLMTarget, NormalizedError, StructuredGenerationRequest
from ...llm.adapters.openai_compatible import OpenAICompatibleAdapter, _CALLER_CANCELLED

@dataclass(frozen=True)
class SelectionResponse:
 raw:str
 evidence:InvocationEvidence

class SelectionGateway(Protocol):
 def capabilities(self,target:LLMTarget)->CapabilitySet: ...
 async def select(self,request:StructuredGenerationRequest)->SelectionResponse: ...

class OpenAISelectionGateway(OpenAICompatibleAdapter):
 """Provider-specific mechanics stay at this opt-in adapter boundary.

 Raw bytes are preserved so duplicate keys are checked before typed parsing.
 The existing generic adapter and its legacy parser remain untouched.
 """
 async def select(self,request):
  support=self.capabilities(request.target).support_for('structured_generation')
  from ...llm.contract import CapabilitySupport
  response_format=self._native_response_format(request) if support is CapabilitySupport.NATIVE else self._emulated_response_format(request)
  outcome=await self._post_chat(request,response_format=response_format)
  if outcome is _CALLER_CANCELLED:raise asyncio.CancelledError
  if isinstance(outcome,NormalizedError):raise LLMInvocationError(outcome)
  raw,evidence=outcome
  return SelectionResponse(raw=raw,evidence=evidence)
