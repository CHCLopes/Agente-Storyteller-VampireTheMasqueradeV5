"""Study-only adapter characterization, not admission of a real model."""
import asyncio
from datetime import timedelta
import json
from typing import Literal
import httpx
import pytest
from pydantic import BaseModel, ConfigDict
from api.llm.adapters.openai_compatible import OpenAICompatibleAdapter
from api.llm.contract import (
 CapabilityDescriptor, CapabilityRequirement, CapabilitySet, CapabilitySupport,
 LLMInvocationError, LLMMessage, LLMTarget, StructuredGenerationRequest, utc_now,
)

class Choice(BaseModel):
 model_config=ConfigDict(extra="forbid",strict=True)
 utterance:Literal["R-06.original","R-06.variant"]
 atmosphere:Literal["none","position"]
 layout:Literal["inline","paragraph"]

@pytest.mark.parametrize("support",[CapabilitySupport.NATIVE,CapabilitySupport.EMULATED])
@pytest.mark.parametrize("case",["valid","extra_prose","unknown_id","duplicate_key"])
def test_selection_adapter_characterization(support,case):
 target=LLMTarget(profile="selection-study",provider="synthetic-provider",model="synthetic-model")
 capture=[]
 choice={"utterance":"R-06.variant","atmosphere":"none","layout":"inline"}
 raw=json.dumps(choice)
 if case=="extra_prose":raw=json.dumps(dict(choice,narrative="As páginas já secaram."))
 if case=="unknown_id":raw=json.dumps(dict(choice,utterance="another-scene.secret"))
 if case=="duplicate_key":raw=raw[:-1]+',"layout":"paragraph"}'
 def handler(request):
  capture.append(json.loads(request.content))
  assert request.headers.get("authorization") is None
  return httpx.Response(200,json={"model":target.model,"choices":[{"message":{"content":raw},"finish_reason":"stop"}]})
 capabilities=CapabilitySet(target=target,descriptors=(
  CapabilityDescriptor(name="text_generation",support=CapabilitySupport.NATIVE),
  CapabilityDescriptor(name="structured_generation",support=support,source="synthetic transport only"),))
 adapter=OpenAICompatibleAdapter(base_url="https://offline.invalid/v1",capability_set=capabilities,transport=httpx.MockTransport(handler))
 request=StructuredGenerationRequest(operation="selection.study",target=target,
  messages=(LLMMessage(role="user",content="Use only the supplied choices. "+json.dumps(Choice.model_json_schema())),),
  deadline=utc_now()+timedelta(seconds=5),response_model=Choice,
  required_capabilities=(CapabilityRequirement(name="text_generation"),CapabilityRequirement(name="structured_generation",allow_emulated=True)))
 if case in {"extra_prose","unknown_id"}:
  with pytest.raises(LLMInvocationError):asyncio.run(adapter.generate_structured(request))
 else:
  result=asyncio.run(adapter.generate_structured(request))
  assert result.value.layout==("paragraph" if case=="duplicate_key" else "inline")
  # Existing JSON parser takes the last duplicate. This is a portability gap,
  # explicitly observed here, not silently fixed or claimed to be protected.
 assert len(capture)==1
 assert ("response_format" in capture[0])==(support is CapabilitySupport.NATIVE)
 assert capture[0]["model"]==target.model
