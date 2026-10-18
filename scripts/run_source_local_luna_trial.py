"""Bounded manual Luna trial through the existing isolated source-player UI."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import sys
import tempfile
from typing import Any

from pydantic import SecretStr

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from api.llm.contract import GenerationParameters, LLMInvocationError, LLMTarget, StructuredGenerationRequest, utc_now
from scripts import run_source_local_groq_trial as base
from scripts.evaluate_openai_luna_low_live import OpenAIResponsesAdapter

BASE_PREPARE = base.prepare
BASE_CONFIGURATION = base.configuration
BASE_CONTROL = base.TrialControl


PROTOCOL = "source-local-luna-trial-v2"
PURPOSE = "source_local_luna_trial"
KEY_ENV = "STORYTELLER_SOURCE_LOCAL_TRIAL_LUNA_KEY"
TARGET_PROFILE = "source-local-luna-trial-gpt-5.6-luna-low-synthetic"
MODEL = "gpt-5.6-luna"


@dataclass(frozen=True)
class LunaTrialSpec(base.TrialSpec):
    @property
    def session_id(self):
        return "source-luna-trial." + self.run_id


def configuration(argv=None):
    inherited, args = BASE_CONFIGURATION(argv)
    identity = inherited.run_id
    spec = LunaTrialSpec(
        identity,
        inherited.port,
        inherited.origin_port,
        ROOT / "eval-results" / ("source-local-luna-trial-" + identity),
        Path(tempfile.gettempdir()) / ("storyteller-source-local-luna-trial-" + identity),
    )
    base.ensure_unused(spec)
    return spec, args


def prepare(spec: LunaTrialSpec) -> base.PreparedTrial:
    prepared = BASE_PREPARE(spec)
    target = LLMTarget(profile=TARGET_PROFILE, provider="OpenAI", model=MODEL)
    metadata = json.loads(json.dumps(prepared.metadata))
    metadata["budget"].update(initial_quiet_seconds=0, minimum_inter_call_delay_seconds=0)
    metadata.update(
        purpose=PURPOSE,
        protocol=PROTOCOL,
        target=target.model_dump(mode="json"),
        selected_candidate_id="gpt-5.6-luna-openai-low-synthetic",
        generation_parameters=dict(
            temperature=0.65, max_output_tokens=768, reasoning_effort="low"
        ),
    )
    return base.PreparedTrial(
        prepared.candidate,
        target,
        prepared.prompt,
        metadata,
        hashlib.sha256(base.encoded(metadata).encode()).hexdigest(),
    )


class LunaTrialControl(BASE_CONTROL):
    """No synthetic cooldown; concurrency is enforced independently of time."""
    delay_seconds = 0

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.in_flight = False

    def consume(self):
        if self.in_flight:
            self.block("http_admission_failed")
            raise base.TrialError("source_local_luna_trial_concurrent_dispatch")
        super().consume()
        self.in_flight = True

    def release_dispatch(self):
        self.in_flight = False


class LunaTrialGateway:
    def __init__(self, spec, prepared, control, key, *, transport=None, record=None):
        self.spec, self.prepared, self.control = spec, prepared, control
        self.key, self.transport, self.record = key, transport, record

    def capabilities(self, target):
        base.require(target == self.prepared.target)
        return base.shared._capabilities(self.prepared.candidate, self.prepared.target)

    async def generate_text(self, request):
        raise base.TrialError("source_local_luna_trial_operation_forbidden")

    async def test_connection(self, request):
        raise base.TrialError("source_local_luna_trial_operation_forbidden")

    def stream_text(self, request):
        raise base.TrialError("source_local_luna_trial_operation_forbidden")

    async def generate_structured(self, request):
        row: dict[str, Any] = dict(
            kind="generation_attempt", call_made=False, outcome="local_failure"
        )
        owns_dispatch = False
        try:
            base.check_prepared(self.prepared)
            remaining = (request.deadline - utc_now()).total_seconds()
            base.require(
                type(request) is StructuredGenerationRequest
                and request.target == self.prepared.target
                and request.response_model is base.profile.NarrativeSourceProposal
                and request.parameters
                == GenerationParameters(temperature=0.65, max_output_tokens=768)
                and 0 < remaining <= 60
                and len(request.messages) == 2
                and request.messages[0].role.value == "system"
                and request.messages[0].content == self.prepared.prompt
                and request.messages[1].role.value == "user",
                "source_local_luna_trial_request_invalid",
            )
            self.control.consume()
            owns_dispatch = True
            row["call_made"] = True
            row["request"] = base.retained._request_record(request)
            row["deadline"] = request.deadline.isoformat()
            adapter = OpenAIResponsesAdapter(
                base_url="https://api.openai.com/v1",
                capability_set=self.capabilities(request.target),
                api_key=self.key,
                reasoning_effort="low",
                transport=self.transport,
            )
            result = await adapter.generate_structured(request)
            usage = result.evidence.usage.output_tokens
            base.require(
                usage is None or usage <= base.OUTPUT_TOKENS,
                "source_local_luna_trial_reported_budget_exceeded",
            )
            public = {
                "response": result.value.model_dump(mode="json", by_alias=True),
                "evidence": result.evidence.model_dump(mode="json"),
            }
            base.require(
                self.key.get_secret_value() not in base.encoded(public),
                "source_local_luna_trial_credential_echo",
            )
            row.update(outcome="generated", evidence=public["evidence"])
            return result
        except asyncio.CancelledError:
            row["outcome"] = "cancelled"
            self.control.block("operational_failure")
            raise
        except LLMInvocationError as exc:
            if exc.error.evidence is not None:
                evidence = exc.error.evidence.model_dump(mode="json")
                if self.key.get_secret_value() not in base.encoded(evidence):
                    row["evidence"] = evidence
            self.control.block("operational_failure")
            raise
        except Exception:
            self.control.block("operational_failure")
            raise
        finally:
            if owns_dispatch:
                self.control.release_dispatch()
            if self.record is not None:
                try:
                    self.record(row)
                    # Unlike the lifecycle-only snapshot used by the original
                    # Groq probe, the manual Luna lane exposes its completed
                    # provider-call count while the browser session is live.
                    base.write_status(self.spec, self.control, "running")
                except Exception:
                    self.control.block("artifact_write_failed")
                    raise base.TrialError(
                        "source_local_luna_trial_artifact_write_failed"
                    ) from None


def configure() -> None:
    base.PROTOCOL = PROTOCOL
    base.PURPOSE = PURPOSE
    base.KEY_ENV = KEY_ENV
    base.TARGET_PROFILE = TARGET_PROFILE
    base.TrialSpec = LunaTrialSpec
    base.TrialGateway = LunaTrialGateway
    base.TrialControl = LunaTrialControl
    base.configuration = configuration
    base.prepare = prepare
    base.EXTRA_INPUTS = tuple(
        item
        for item in base.EXTRA_INPUTS
        if item
        not in {
            "scripts/run_source_local_groq_trial.py",
            "scripts/run_groq_source_local_trial.ps1",
        }
    ) + (
        "scripts/run_source_local_groq_trial.py",
        "scripts/run_source_local_luna_trial.py",
        "scripts/report_luna_test_cost.py",
        "scripts/run_openai_luna_source_local_trial.ps1",
        "scripts/evaluate_openai_luna_low_live.py",
    )


def main(argv=None) -> int:
    configure()
    return base.main(argv)


if __name__ == "__main__":
    raise SystemExit(main())
