"""Safe structural diagnostics survive the real adapter normalization boundary."""

import asyncio
import json

import httpx
import pytest
from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from api.llm.contract import (
    ErrorCategory, LLMInvocationError, NormalizedError, OperationPhase,
    StructuredGenerationRequest, StructureValidationEvidence, StructureValidationIssue,
)
from . import test_gemini_adapter as gemini
from . import test_groq_adapter as groq
from .test_openai_compatible_adapter import _traceback_locals


_PRIVATE = "syntheticPrivateKeyShouldNeverLeaveAdapter"


class _Answer(BaseModel):
    model_config = ConfigDict(extra="forbid")
    text: str = Field(min_length=4)

    @model_validator(mode="after")
    def product_invariant(self):
        if self.text == _PRIVATE:
            raise ValueError(f"private validator data: {self.text}")
        return self


@pytest.mark.parametrize("provider", [groq, gemini], ids=["groq", "gemini"])
@pytest.mark.parametrize(("content", "stage", "code", "path"), [
    (_PRIVATE, "json_parse", "json_invalid", ()),
    (json.dumps({}), "schema_validation", "missing", ("text",)),
    (json.dumps({"text": "x"}), "schema_validation", "string_too_short", ("text",)),
    (json.dumps({"text": _PRIVATE}), "schema_validation", "value_error", ()),
    (json.dumps({"text": "valid", _PRIVATE: _PRIVATE}), "schema_validation", "extra_forbidden", ("?",)),
])
def test_adapter_reports_safe_issue_without_repair_or_raw_exception(
    provider, content, stage, code, path,
):
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(200, json=provider._success_payload(content), request=request)

    values = provider._request().model_dump()
    values.pop("required_capabilities")
    request = StructuredGenerationRequest(**values, response_model=_Answer)
    with pytest.raises(LLMInvocationError) as caught:
        asyncio.run(provider._adapter(handler).generate_structured(request))

    error = caught.value.error
    assert error.category is ErrorCategory.INVALID_STRUCTURED_OUTPUT
    assert error.code == "structured_output_schema_mismatch"
    assert error.phase is OperationPhase.STRUCTURE_VALIDATION
    assert error.structure_validation.stage == stage
    issue, = error.structure_validation.issues
    assert issue.code == code
    assert issue.path == path
    assert error.structure_validation.truncated is False
    assert len(calls) == 1
    assert caught.value.__cause__ is None
    assert caught.value.__context__ is None
    for serialized in (error.model_dump_json(), repr(caught.value), _traceback_locals(caught.value)):
        assert _PRIVATE not in serialized
        assert provider._SECRET not in serialized
        assert "entrada sintética" not in serialized

    # A schema failure must not be recast as an ordinary HTTP/transport error.
    payload = error.model_dump()
    payload["category"] = ErrorCategory.TRANSPORT_FAILURE
    with pytest.raises(ValidationError):
        NormalizedError.model_validate(payload)


@pytest.mark.parametrize("path", [(True,), (-1,), (10_001,), ("bad field",), ("x",) * 9])
def test_structural_issue_contract_bounds_locations(path):
    with pytest.raises(ValidationError):
        StructureValidationIssue(path=path, code="missing")


def test_structural_contract_rejects_messages_arbitrary_codes_and_oversized_lists():
    with pytest.raises(ValidationError):
        StructureValidationIssue(code=_PRIVATE)
    with pytest.raises(ValidationError):
        StructureValidationIssue(code="missing", message=_PRIVATE)
    with pytest.raises(ValidationError):
        StructureValidationEvidence(stage="unknown", issues=())
    with pytest.raises(ValidationError):
        StructureValidationEvidence(stage="schema_validation", issues=(
            StructureValidationIssue(code="missing"),
        ) * 9)
