"""Network-free, keyless rehearsal of the proposed HYP-007 campaign schedule.

This intentionally cannot dispatch paid inference or authorize a narrator.
"""
from __future__ import annotations

import asyncio
from datetime import timedelta
import gc
import hashlib
import json
import os
from pathlib import Path
import tempfile

os.environ["STORYTELLER_DISABLE_DOTENV"] = "1"

import httpx
from pydantic import SecretStr

from api import rules_service
from api.campaign_source_capsule import CampaignSourceConfig
from api.campaign_source_execution_service import execute_campaign_source_turn
from api.campaign_source_input_service import prepare_campaign_source_player_action
from api.campaign_source_offline_corpus import PROSE
from api.campaign_source_profile import CampaignSourceProposal
from api.campaign_source_storage import create_campaign_source_session, read_campaign_source_snapshot
from api.llm.contract import (
    CAPABILITY_STRUCTURED_GENERATION, CAPABILITY_TEXT_GENERATION,
    CancellationToken, CapabilityDescriptor, CapabilitySet, CapabilitySupport,
    GenerationParameters, LLMTarget, utc_now,
)
from api.llm.testing import FakeLLMAdapter
from api.persistence import SQLitePersistence
from api.rules_service import ResolutionResult
from scripts.evaluate_openai_luna_low_live import OpenAIResponsesAdapter
from scripts.run_campaign_source_offline_trial import _initial_state


ROOT = Path(__file__).resolve().parent.parent
PROMPT = ROOT / "evals/narrator/prompts/hybrid-campaign-source-v6.md"
TARGET = LLMTarget(profile="campaign-luna-hyp-007", provider="OpenAI", model="gpt-5.6-luna")
CASES = (
    ("CAMP-EVAL-01", ("Como posso ajudar?", "Retiro o registro"), ("R-01", "R-05"), "preserved"),
    ("CAMP-EVAL-02", ("Aguardo", "Espero", "O que precisamos fazer?", "Retiro o registro"), ("R-03", "R-03B", "R-01", "R-06"), "partial"),
    ("CAMP-EVAL-03", ("Aguardo", "Espero", "Aguardo"), ("R-03", "R-03B", "R-04"), "lost"),
    ("CAMP-EVAL-04", ("Desisto",), ("R-09",), "abandoned"),
    ("CAMP-EVAL-05", ("Levo o registro até a superfície seca",), ("R-05",), "preserved"),
    ("CAMP-EVAL-06", ("Examino o registro",), ("R-07",), "partial"),
    ("CAMP-EVAL-07", ("Examino o registro", "Retiro o registro"), ("R-08", "R-06"), "partial"),
    ("CAMP-EVAL-08", ("Quem é a fundadora?", "Qual é a tarefa?", "Retiro o registro"), ("R-02", "R-01", "R-05"), "preserved"),
)
MAX_CALLS = 17
MAX_OUTPUT_TOKENS = 768
MAX_REQUEST_BYTES = 20_000
DEADLINE_SECONDS = 60


def _fixed_resolution(success: bool) -> ResolutionResult:
    return ResolutionResult(
        successes=3 if success else 0, is_success=success,
        bestial_failure=False, messy_critical=False,
        summary="Investigação resolvida.",
        normal_rolls=[8, 8, 8, 5, 4] if success else [2, 2, 2, 3, 4],
        hunger_rolls=[], margin=0 if success else -3,
    )


async def preflight() -> dict:
    prompt_bytes = PROMPT.read_bytes()
    prompt = prompt_bytes.decode("utf-8").strip()
    if not prompt or len(CASES) != 8 or sum(len(row[1]) for row in CASES) != MAX_CALLS:
        raise ValueError("campaign_luna_schedule_invalid")
    config = CampaignSourceConfig(
        target=TARGET, system_prompt=prompt,
        parameters=GenerationParameters(max_output_tokens=MAX_OUTPUT_TOKENS),
        chronicle_name="Registro em risco — HYP-007 sintético",
    )
    caps = CapabilitySet(target=TARGET, descriptors=tuple(CapabilityDescriptor(
        name=name, support=CapabilitySupport.NATIVE,
    ) for name in (CAPABILITY_TEXT_GENERATION, CAPABILITY_STRUCTURED_GENERATION)))
    from scripts.evaluate_hybrid_campaign_luna_l31_live import CampaignLunaAdapter
    adapter = CampaignLunaAdapter(
        base_url="https://api.openai.com/v1", capability_set=caps,
        api_key=SecretStr(""), reasoning_effort="low",
    )
    rows = []
    original_resolution = rules_service.calculate_resolution
    try:
        with tempfile.TemporaryDirectory(prefix="storyteller-hyp-007-preflight-") as temp:
            for case_id, inputs, expected_rules, expected_outcome in CASES:
                store = SQLitePersistence(Path(temp) / f"{case_id}.sqlite3")
                await create_campaign_source_session(store, case_id, initial_state=_initial_state())
                rules_service.calculate_resolution = lambda *_a, **_kw: _fixed_resolution(case_id == "CAMP-EVAL-06")
                for number, (player_input, expected_rule) in enumerate(zip(inputs, expected_rules), 1):
                    operation_id = f"{case_id}-{number}"
                    prepared = await prepare_campaign_source_player_action(
                        store=store, session_id=case_id, operation_id=operation_id,
                        player_input=player_input, config=config,
                        deadline=utc_now() + timedelta(seconds=DEADLINE_SECONDS),
                        cancellation=CancellationToken(),
                    )
                    if prepared.capsule is None or prepared.capsule.campaign_effect.rule_id != expected_rule:
                        raise ValueError(f"campaign_luna_preparation_failed:{case_id}:{number}")
                    capsule = prepared.capsule
                    fake = FakeLLMAdapter(capability_set=caps, structured_payload={
                        "n": PROSE[expected_rule],
                        "q": "" if capsule.campaign_effect.after_state.outcome else "O que você faz agora?",
                        "realized_effects": capsule.campaign_effect.beat.effect_keys,
                    }, effective_provider="OpenAI", effective_model=TARGET.model)
                    async def deliver(_text: str) -> None:
                        return None
                    result = await execute_campaign_source_turn(
                        store=store, capsule=capsule, operation_id=operation_id,
                        gateway=fake, deadline=utc_now() + timedelta(seconds=DEADLINE_SECONDS),
                        cancellation=CancellationToken(), on_chunk=deliver,
                    )
                    if result.status != "completed" or len(fake.requests) != 1:
                        raise ValueError(f"campaign_luna_rehearsal_failed:{case_id}:{number}")
                    request = fake.requests[0]
                    context = json.loads(request.messages[1].content)["context"]
                    causal = context["causal_packet"]
                    position = context["record_position"]
                    expected_position = "dry_surface" if expected_rule in {"R-05", "R-06"} else "bench"
                    if (causal["state_before"]["content_version"] != "record-at-risk.v2"
                            or position["before"] != "bench"
                            or position["after"] != expected_position
                            or causal["state_after"]["record_location"] != expected_position):
                        raise ValueError("campaign_luna_position_mismatch")
                    body = adapter._payload(request, stream=False, response_format=adapter._native_response_format(request))
                    encoded = httpx.Request("POST", "https://api.openai.com/v1/responses",
                                            json=body).content
                    if len(encoded) > MAX_REQUEST_BYTES:
                        raise ValueError(f"campaign_luna_request_too_large:{case_id}:{number}")
                    rows.append({"case_id": case_id, "turn": number, "rule": expected_rule,
                                 "record_position_before": position["before"],
                                 "record_position_after": position["after"],
                                 "request_bytes": len(encoded),
                                 "request_sha256": hashlib.sha256(encoded).hexdigest()})
                snapshot = await read_campaign_source_snapshot(store, case_id)
                if snapshot.progression.outcome != expected_outcome:
                    raise ValueError(f"campaign_luna_outcome_mismatch:{case_id}")
            # sqlite3 context managers commit but do not close connections.
            # Collect the completed worker-thread references before Windows cleanup.
            gc.collect()
            await asyncio.sleep(0)
    finally:
        rules_service.calculate_resolution = original_resolution
    return {
        "hypothesis_id": "HYP-007", "lot_id": "HYP-007-L31",
        "content_version": "record-at-risk.v2", "policy_version": "campaign-progression.v2",
        "status": "keyless_fake_rehearsal_only",
        "model": TARGET.model, "reasoning_effort": "low", "store": False,
        "schema_sha256": hashlib.sha256(json.dumps(CampaignSourceProposal.model_json_schema(), sort_keys=True).encode()).hexdigest(),
        "prompt_sha256": hashlib.sha256(prompt_bytes).hexdigest(),
        "calls_planned": MAX_CALLS, "provider_calls": 0,
        "max_output_tokens_per_call": MAX_OUTPUT_TOKENS,
        "request_byte_limit": MAX_REQUEST_BYTES,
        "max_request_bytes_observed": max(row["request_bytes"] for row in rows),
        "requests": rows,
    }


def main() -> int:
    try:
        print(json.dumps(asyncio.run(preflight()), ensure_ascii=False, sort_keys=True))
        return 0
    except (OSError, ValueError) as exc:
        print(f"Preflight HYP-007 recusado: {str(exc).split(':')[0]}")
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
