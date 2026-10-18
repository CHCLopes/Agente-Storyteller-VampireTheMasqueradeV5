"""Four independent Qwen length observations; no campaign, SQLite, commit or UI.

The original policy stays unchanged. Requested per-field budgets are measured
separately. Frozen local artifacts prove consistency, not provider authenticity.
"""
from __future__ import annotations

import argparse
import asyncio
import copy
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
import hashlib
import os
from pathlib import Path
import re
import sys
from uuid import NAMESPACE_URL, UUID, uuid5

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
os.environ["STORYTELLER_DISABLE_DOTENV"] = "1"

from pydantic import SecretStr
from api import narrative_source_profile as profile
from api.llm.adapters.groq import GroqAdapter, GROQ_OFFICIAL_BASE_URL, GROQ_QWEN_MODEL_ID, _normalize_groq_strict_schema
from api.llm.contract import CancellationToken, GenerationParameters, LLMInvocationError, LLMMessage, LLMTarget, MessageRole, StructuredGenerationRequest, utc_now
from api.scene_director_service import SceneProposalError
from api.scene_service import SceneState
from scripts import evaluate_narrator_models as shared
from scripts import evaluate_progressing_source as retained
from scripts.evaluate_source_context import _verify_evidence
from scripts.evaluate_narrator_source import _route_status
from scripts.narrator_record_budget_observer import _unavailable_observation

_json, _sha, _same, _loads, _read_json = retained._json, retained._sha, retained._same, retained._loads, retained._read_json
PROBE_KIND = "source_word_budget_probe"
EXPERIMENT_VERSION = "source-word-budget-v1"
CANDIDATE_ID = "qwen-3.8-27b-groq-free-synthetic-nonthink"
TARGET_PROFILE = "source-word-budget-" + CANDIDATE_ID
KEY_ENV = "STORYTELLER_SOURCE_WORD_BUDGET_GROQ_KEY"
OPERATION = "evaluation.source_word_budget"
OUTPUT_ROOT = PROJECT_ROOT / "eval-results"
CORPUS_PATH = PROJECT_ROOT / "evals/narrator/source_word_budget_v1.json"
PROTOCOL_PATH = PROJECT_ROOT / "evals/narrator/source_word_budget_protocol_v1.md"
BASELINE_PATH = PROJECT_ROOT / "evals/narrator/prompts/narrative-source-progress-v1.md"
MARGIN_PATH = PROJECT_ROOT / "evals/narrator/prompts/narrative-source-word-budget-v1.md"
MANIFEST_PATH = PROJECT_ROOT / "evals/narrator/groq_candidates_2026-09-05.json"
EXPECTED_INPUT_HASHES = {'evals/narrator/source_word_budget_v1.json': 'd68fe07680844c76b88d8ff401311ef1f0c54a0441da945da55ca509463cc52e', 'evals/narrator/source_word_budget_protocol_v1.md': '96a2cad0260f718c1021c6771692b71fb8bc1352b9b7abaaa2663b5865035a33', 'evals/narrator/prompts/narrative-source-progress-v1.md': '87b9cbcd67a67b9d25b97c2b25276e83af56d48c09f53843a64b8e77303b1a0e', 'evals/narrator/prompts/narrative-source-word-budget-v1.md': '18428fef897a31dda7b27ba472bbdaf4a5c988bf4bd0f836c4f4ce790e9d5067', 'evals/narrator/groq_candidates_2026-09-05.json': 'de31691d9562e7cc8abe2b13d004098967976cda321c975d2f3ed7a147a15de6'}
ORIGINAL_LENGTH = "Use de 30 a 150 palavras no total de n e q;"
MARGIN_LENGTH = "Use de 70 a 110 palavras em n e no máximo 10 palavras em q, mantendo o total de n e q entre 30 e 120 palavras para deixar margem até o limite de 150;"
SLOTS = (("slot-1", "C1", "A"), ("slot-2", "C1", "B"), ("slot-3", "C2", "B"), ("slot-4", "C2", "A"))
MAX_CALLS = 4
MAX_JSON_BYTES = 4 * 1024 * 1024
PARAMETERS = {"temperature": .65, "max_output_tokens": 768, "max_total_output_tokens": 3072,
    "reasoning_effort": "none", "initial_quiet_seconds": 60, "minimum_inter_call_delay_seconds": 60, "deadline_seconds": 60}
CONTENT_ERRORS = frozenset({"invalid_structured_output", "malformed_response", "content_rejected"})
STAGES = frozenset({"preflight", "transport", "policy"})
# Same lexical counter as scene_director_service's n+q and q gates.
WORDS = re.compile(r"[^\W_]+(?:[-’'][^\W_]+)*", re.UNICODE)
IMPLEMENTATION_FILES = tuple(dict.fromkeys((
    "scripts/evaluate_source_word_budget.py", "scripts/evaluate_source_context.py",
    *retained.IMPLEMENTATION_FILES,
    "scripts/narrator_source_profile.py", "api/narrative_source_action_producer.py",
)))


def _require(ok, code="source_word_budget_artifact_invalid"):
    if not ok:
        raise ValueError(code)


def _batch(value):
    _require(type(value) is str and str(UUID(value)) == value, "source_word_budget_batch_invalid")
    return value


def run_path(batch_id):
    return OUTPUT_ROOT / ("source-word-budget-" + _batch(batch_id))


def _scope():
    return dict(purpose=PROBE_KIND, probe_kind=PROBE_KIND, experiment_version=EXPERIMENT_VERSION,
        protocol=profile.VERSION, selected_candidate_id=CANDIDATE_ID, synthetic_only=True,
        campaign_data_eligible=False, cap_001_approved=False, runtime_default_eligible=False,
        semantic_not_evaluated=True, max_calls=MAX_CALLS)


@dataclass(frozen=True)
class PreparedExperiment:
    candidate: shared.Candidate
    target: LLMTarget
    prompts: dict
    corpus: dict
    metadata: dict


def _prompt(path):
    text = path.read_text(encoding="utf-8")
    front = re.match(r"\A---\r?\n.*?\r?\n---(?:\r?\n)+", text, re.DOTALL)
    _require(front is not None)
    return text[front.end():].strip()


def _case(prepared, index):
    _require(type(index) is int and 0 <= index < MAX_CALLS)
    return prepared.corpus["contexts"][SLOTS[index][1]]


def _identity(context_id, kind):
    return "fixture-" + kind + "-" + str(uuid5(NAMESPACE_URL, EXPERIMENT_VERSION + "." + context_id + "." + kind))


def authored_projection(prepared, index):
    case = _case(prepared, index)
    if case["source_text"] is None:
        return None
    context_id = SLOTS[index][1]
    return profile.create_source_projection({"n": case["source_text"], "q": "O que você faz agora?"},
        source_id=_identity(context_id, "source"), session_id=_identity(context_id, "session"),
        turn_id=_identity(context_id, "source-turn"), invocation_id=_identity(context_id, "authorship"),
        current_scene=SceneState.model_validate(case["scene"]), facts=(), player_input=case["player_input"])


def build_user_packet(prepared, index):
    case = _case(prepared, index)
    source = authored_projection(prepared, index)
    packet = _json({"context": profile.build_source_context(session_id=_identity(SLOTS[index][1], "session"),
        current_scene=SceneState.model_validate(case["scene"]), attributed_sources=() if source is None else (source,)),
        "player_input": case["player_input"], "server_facts": [], "turn": _identity(SLOTS[index][1], "output-turn")})
    _require(len(packet) <= profile.MAX_CONTEXT_CHARACTERS, "source_word_budget_user_limit")
    return packet


def make_request(prepared, index, batch_id, *, deadline=None, cancellation=None):
    _batch(batch_id)
    _case(prepared, index)
    return StructuredGenerationRequest(operation=OPERATION,
        invocation_id=str(uuid5(UUID(batch_id), SLOTS[index][0])), target=prepared.target,
        messages=(LLMMessage(role=MessageRole.SYSTEM, content=prepared.prompts[SLOTS[index][2]]),
                  LLMMessage(role=MessageRole.USER, content=build_user_packet(prepared, index))),
        parameters=GenerationParameters(temperature=.65, max_output_tokens=768),
        response_model=profile.NarrativeSourceProposal, deadline=deadline or datetime(2000, 1, 1, tzinfo=timezone.utc),
        cancellation=cancellation or CancellationToken())


def _body(request):
    return retained._body(request)


def _request_record(request):
    return {**retained._request_record(request), "deadline": request.deadline.isoformat()}


def prepare_experiment():
    _require(len(EXPECTED_INPUT_HASHES) == 5, "source_word_budget_unfrozen_inputs")
    for relative, digest in EXPECTED_INPUT_HASHES.items():
        _require(shared._sha256(PROJECT_ROOT / relative) == digest, "source_word_budget_input_changed")
    corpus = _read_json(CORPUS_PATH)
    _require(corpus["version"] == EXPERIMENT_VERSION and corpus["source_origin"] == "authored_synthetic_fixture"
        and corpus["contexts_independent"] is True and corpus["generation_parameters"] == PARAMETERS
        and corpus["slots"] == [dict(slot_id=s, context_id=c, arm_id=a) for s, c, a in SLOTS]
        and set(corpus["contexts"]) == {"C1", "C2"} and corpus["contexts"]["C1"]["source_text"] is None)
    prompts = {"A": _prompt(BASELINE_PATH), "B": _prompt(MARGIN_PATH)}
    _require(prompts["A"].count(ORIGINAL_LENGTH) == 1
        and prompts["B"] == prompts["A"].replace(ORIGINAL_LENGTH, MARGIN_LENGTH), "source_word_budget_prompt_delta_invalid")
    candidate = shared.load_candidates(MANIFEST_PATH)[CANDIDATE_ID]
    _require(candidate.adapter_kind == "groq" and candidate.model == GROQ_QWEN_MODEL_ID
        and candidate.provider_label == candidate.effective_provider == "Groq" and candidate.upstream_provider is None
        and candidate.reasoning_effort == "none" and candidate.structured_mode == "native"
        and candidate.campaign_data_eligible is False, "source_word_budget_target_invalid")
    target = LLMTarget(profile=TARGET_PROFILE, provider="Groq", model=GROQ_QWEN_MODEL_ID)
    prepared = PreparedExperiment(candidate, target, prompts, corpus, {})
    frozen = []
    for index, (slot, context, arm) in enumerate(SLOTS):
        request = make_request(prepared, index, "00000000-0000-0000-0000-000000000000")
        projection = authored_projection(prepared, index)
        body = _body(request)
        frozen.append(dict(slot_id=slot, context_id=context, arm_id=arm, request=body, body_sha256=_sha(body),
            user_packet=request.messages[1].content, authored_source={"origin": "authored_synthetic_fixture",
                "provider_evidence": None, "application_commit": False,
                "projection": projection.model_dump(mode="json") if projection is not None else None}))
    _require(frozen[0]["user_packet"] == frozen[1]["user_packet"]
        and frozen[2]["user_packet"] == frozen[3]["user_packet"], "source_word_budget_pairing_invalid")
    schema = profile.NarrativeSourceProposal.model_json_schema()
    inputs = {name: {"file": path.relative_to(PROJECT_ROOT).as_posix(), "sha256": shared._sha256(path)}
        for name, path in (("corpus", CORPUS_PATH), ("protocol", PROTOCOL_PATH), ("manifest", MANIFEST_PATH))}
    inputs.update(prompts={arm: {"file": path.relative_to(PROJECT_ROOT).as_posix(), "file_sha256": shared._sha256(path),
        "sha256": hashlib.sha256(prompts[arm].encode()).hexdigest()} for arm, path in (("A", BASELINE_PATH), ("B", MARGIN_PATH))},
        response_schema_sha256=_sha(schema), provider_schema_sha256=_sha(_normalize_groq_strict_schema(schema)),
        implementation=[{"file": f, "sha256": shared._sha256(PROJECT_ROOT / f)} for f in IMPLEMENTATION_FILES])
    metadata = {**_scope(), "target": target.model_dump(mode="json"), "generation_parameters": copy.deepcopy(PARAMETERS),
        "slots": corpus["slots"], "evaluator": {**shared._evaluator_provenance(),
            "file": "scripts/evaluate_source_word_budget.py", "sha256": shared._sha256(Path(__file__)), "version": EXPERIMENT_VERSION},
        "inputs": inputs, "frozen_requests": frozen,
        "length_policy": {"original_total_min": 30, "original_total_max": 150, "original_q_max": 15,
            "margin_n_min": 70, "margin_n_max": 110, "margin_q_max": 10, "margin_total_max": 120,
            "counter": WORDS.pattern, "request_budget_is_not_policy": True},
        "source_policy": {"origin": "authored_synthetic_fixture", "application_commit": False,
            "canonical_truth_confirmed": False, "question_is_source": False, "server_facts": [],
            "contexts_independent": True, "normalization": profile.TEXT_NORMALIZATION},
        "timing_policy": {"clock": "local_utc", "tolerance_seconds": .01, "remote_arrival_measured": False}}
    return PreparedExperiment(candidate, target, prompts, corpus, metadata)


def _check_prepared(prepared):
    _require(type(prepared) is PreparedExperiment)
    current = prepare_experiment()
    _require(current.target == prepared.target and _same(current.prompts, prepared.prompts)
        and _same(current.corpus, prepared.corpus) and _same(current.metadata, prepared.metadata)
        and _same(asdict(current.candidate), asdict(prepared.candidate)), "source_word_budget_prepared_drift")


def _expected(path, digest):
    _require(type(digest) is str and re.fullmatch(r"[0-9a-f]{64}", digest) is not None
        and shared._sha256(Path(path)) == digest, "source_word_budget_preflight_hash_invalid")
    prepared = prepare_experiment()
    _require(_same(_read_json(Path(path)), prepared.metadata), "source_word_budget_preflight_changed")
    return prepared


class DispatchBudget:
    def __init__(self, *, _clock=None, _sleeper=None):
        arguments = {}
        if _clock is not None:
            arguments["_clock"] = _clock
        if _sleeper is not None:
            arguments["_sleeper"] = _sleeper
        self.pacer = shared._CallPacer(60, **arguments)
        self.calls, self.slots = 0, set()
        self.last_dispatch = self.pacer._last_call_started_at = self.pacer._clock()

    async def wait(self):
        await self.pacer.before_call(PROBE_KIND)

    def consume(self, slot):
        now = self.pacer._clock()
        _require(self.calls < MAX_CALLS and slot == SLOTS[self.calls][0] and slot not in self.slots,
            "source_word_budget_http_limit")
        _require(now - self.last_dispatch >= 60, "source_word_budget_http_spacing")
        self.calls += 1
        self.slots.add(slot)
        self.last_dispatch = self.pacer._last_call_started_at = now


class ObservationAdapter(retained.RetainedObservationAdapter):
    """Reuse known-key filtering and evidence capture; bind slot/deadline before HTTP."""
    def __init__(self, *, prepared, request, api_key, budget, slot, transport=None):
        super().__init__(prepared=prepared, request=request, api_key=api_key, budget=budget, transport=transport)
        self.approved = _request_record(request)
        self.slot, self.http_started_at = slot, None

    def _payload(self, request, *, stream, response_format):
        payload = GroqAdapter._payload(self, request, stream=stream, response_format=response_format)
        _require(not stream and not self._dispatch_started and _same(_request_record(request), self.approved)
            and _sha(payload) == self.approved["body_sha256"], "source_word_budget_request_changed")
        self._dispatch_started = True
        return payload

    async def _dispatch(self, request):
        _require(not self.http_sent and request.method == "POST"
            and str(request.url) == GROQ_OFFICIAL_BASE_URL + "/chat/completions"
            and _sha(_loads(request.content)) == self.approved["body_sha256"], "source_word_budget_http_invalid")
        now = utc_now()
        _require(now <= _aware(self.approved["deadline"]), "source_word_budget_expired_dispatch")
        self.budget.consume(self.slot)
        self.http_sent = True
        self.http_started_at = now.isoformat()


def measurements(proposal):
    if proposal is None:
        return None
    n, q = proposal["n"], proposal["q"]
    nw, qw = len(WORDS.findall(n)), len(WORDS.findall(q))
    return {"n_words": nw, "q_words": qw, "total_words": nw + qw,
        "n_characters": len(n), "q_characters": len(q),
        "original_length_passed": 30 <= nw + qw <= 150 and qw <= 15,
        "margin_budget_met": 70 <= nw <= 110 and qw <= 10 and 30 <= nw + qw <= 120}


def _new_row(prepared, index, batch):
    slot, context, arm = SLOTS[index]
    return {"kind": "source_word_budget_call", "slot_id": slot, "context_id": context, "arm_id": arm,
        "request": _request_record(make_request(prepared, index, batch)), "request_created_at": None,
        "authored_source": copy.deepcopy(prepared.metadata["frozen_requests"][index]["authored_source"]),
        "call_made": False, "schema_valid": False, "policy_valid": False, "route_status": "unavailable",
        "provider_observation": _unavailable_observation(), "response_structure": None, "evidence": None,
        "llm_error": None, "credential_echo_blocked": False, "http_started_at": None,
        "outcome": "local_error", "policy_error": None, "local_error": None, "measurements": None,
        "operational_error": None}


def _output_tokens(row):
    observation = row["provider_observation"]["usage"]["output_tokens"]
    evidence = (row["evidence"] or {}).get("usage", {}).get("output_tokens")
    available = [value for value in (observation, evidence) if value is not None]
    return max(available) if available else None


def _operational_error(row, previous_rows=()):
    """Keep original captured fields; a separate closed diagnostic stops dispatch.

    Response metadata can arrive before finish/schema rejection, so its usage may
    exist while error evidence has no usage. A completed structure has both paths
    available and must agree, including availability. Unknown usage stays unknown.
    """
    codes = []
    observation, evidence, error = row["provider_observation"], row["evidence"], row["llm_error"]
    status, finish = observation["http_status"], observation["finish_reason"]
    proposal = row["response_structure"] is not None
    content = row["outcome"] == "schema_rejected"
    successful_http = status is not None and 200 <= status < 300
    empty = _unavailable_observation()
    mismatch = any(observation[field]["status"] == "unavailable"
        and not _same(observation[field], empty[field]) for field in ("error_body", "failed_generation"))
    if proposal or content:
        expected_finish = "content_filter" if (error or {}).get("code") == "generation_content_filtered" else "stop"
        mismatch = mismatch or (not successful_http or observation["model"] != GROQ_QWEN_MODEL_ID
            or observation["provider_code"] is not None
            or observation["error_body"]["status"] != "unavailable"
            or observation["failed_generation"]["status"] != "unavailable")
        if finish != expected_finish:
            # Length/missing/unknown finish is not a schema retry permission.
            codes.append("incomplete_generation")
            mismatch = mismatch or proposal
    if error is not None:
        if error.get("status_code") is not None and error["status_code"] != status:
            mismatch = True
        if status is not None and status >= 400:
            mismatch = mismatch or error.get("status_code") != status
            mismatch = mismatch or error["category"] != GroqAdapter._http_category(status).value
        if observation["provider_code"] == "rate_limit_exceeded":
            mismatch = mismatch or error["category"] != "rate_limited"
    elif status is not None and status >= 400 and row["local_error"] is None:
        mismatch = True
    if mismatch:
        codes.append("observer_outcome_mismatch")
    if evidence is not None:
        reported = evidence["usage"]
        fields = ("input_tokens", "output_tokens", "total_tokens")
        if any((reported[field] is not None or proposal) and reported[field] != observation["usage"][field]
               for field in fields):
            codes.append("usage_mismatch")
        if _aware(evidence["finished_at"]) > _aware(row["request"]["deadline"]):
            codes.append("deadline_exceeded")
    tokens = _output_tokens(row)
    if tokens is not None and tokens > PARAMETERS["max_output_tokens"]:
        codes.append("output_limit_exceeded")
    known = [value for item in (*previous_rows, row) if item["kind"] == "source_word_budget_call"
             if (value := _output_tokens(item)) is not None]
    if sum(known) > PARAMETERS["max_total_output_tokens"]:
        codes.append("batch_output_limit_exceeded")
    return {"codes": codes} if codes else None


def _continue(row):
    return row["kind"] == "source_word_budget_call" and row["operational_error"] is None \
        and row["route_status"] == "verified" and row["outcome"] in (
            "accepted", "schema_rejected", "policy_rejected")


def _skip(index, reason):
    slot, context, arm = SLOTS[index]
    return dict(kind="source_word_budget_skip", slot_id=slot, context_id=context, arm_id=arm, reason=reason)


async def evaluate_probe(prepared, *, api_key, batch_id, run_directory, transport=None, budget=None):
    _batch(batch_id)
    _check_prepared(prepared)
    _require(type(api_key) is SecretStr and bool(api_key.get_secret_value().strip())
        and api_key.get_secret_value().strip() not in _json(prepared.metadata), "source_word_budget_credential_invalid")
    directory = Path(run_directory)
    _require(directory.resolve() == run_path(batch_id).resolve(), "source_word_budget_output_invalid")
    directory.mkdir(parents=True, exist_ok=False)
    started = utc_now().isoformat()
    budget = budget if budget is not None else DispatchBudget()
    _require(type(budget) is DispatchBudget and budget.calls == 0 and not budget.slots)
    rows, status = [], "completed"
    for index in range(MAX_CALLS):
        row, adapter, stage = _new_row(prepared, index, batch_id), None, "preflight"
        try:
            _check_prepared(prepared)
            await budget.wait()
            _check_prepared(prepared)
            created = utc_now()
            request = make_request(prepared, index, batch_id, deadline=created + timedelta(seconds=60))
            row.update(request=_request_record(request), request_created_at=created.isoformat())
            stage = "transport"
            adapter = ObservationAdapter(prepared=prepared, request=request, api_key=api_key,
                budget=budget, slot=SLOTS[index][0], transport=transport)
            result = await adapter.generate_structured(request)
            stage = "policy"
            case = _case(prepared, index)
            profile.validate_source_proposal(result.value, current_scene=SceneState.model_validate(case["scene"]),
                facts=(), player_input=case["player_input"])
            row.update(policy_valid=True, outcome="accepted")
        except SceneProposalError as exc:
            row.update(policy_error=exc.code, outcome="policy_rejected")
        except LLMInvocationError as exc:
            row["outcome"] = "schema_rejected" if exc.error.category.value in CONTENT_ERRORS else "provider_failed"
        except asyncio.CancelledError:
            status = "cancelled"
            row.update(outcome=status, local_error={"code": "source_word_budget_cancelled", "stage": stage})
        except Exception:
            status = "local_error"
            row.update(outcome=status, local_error={"code": "source_word_budget_local_error", "stage": stage})
        finally:
            if adapter is not None:
                row.update({key: copy.deepcopy(adapter.capture.get(key)) for key in ("response_structure", "evidence", "llm_error")})
                row.update(provider_observation=adapter.observation, call_made=adapter.http_sent,
                    credential_echo_blocked=adapter.credential_echo_blocked, http_started_at=adapter.http_started_at)
                row["schema_valid"] = row["response_structure"] is not None
                row["route_status"] = _route_status(row["evidence"], prepared.target, row["request"]["invocation_id"])
                row["measurements"] = measurements(row["response_structure"])
        row["operational_error"] = _operational_error(row, rows)
        rows.append(row)
        if status != "completed" or not _continue(row):
            break
    rows.extend(_skip(index, status if status != "completed" else "previous_operational_failure")
        for index in range(len(rows), MAX_CALLS))
    _require(budget.calls == sum(row.get("call_made", False) for row in rows))
    summary = summarize(rows, status)
    raw = "".join(_json({"metadata": prepared.metadata, "batch_id": batch_id, "record": row}) + "\n" for row in rows)
    raw_path = directory / "records.jsonl"
    raw_path.write_text(raw, encoding="utf-8")
    document = {"metadata": copy.deepcopy(prepared.metadata), "batch_id": batch_id, "started_at": started,
        "finished_at": utc_now().isoformat(), "evaluation_status": status, "summary": summary,
        "artifacts": {"records": {"file": raw_path.name, "sha256": shared._sha256(raw_path)}},
        "process_exit_code": summary["process_exit_code"]}
    (directory / "summary.json").write_text(_json(document) + "\n", encoding="utf-8")
    return rows


def summarize(rows, status="completed"):
    _require(type(rows) is list and len(rows) == MAX_CALLS and status in ("completed", "local_error", "cancelled"))
    calls, stopped = [], False
    for index, row in enumerate(rows):
        _require((row["slot_id"], row["context_id"], row["arm_id"]) == SLOTS[index])
        if row["kind"] == "source_word_budget_skip":
            _require(stopped and _same(row, _skip(index, status if status != "completed" else "previous_operational_failure")))
        else:
            _require(not stopped and row["kind"] == "source_word_budget_call")
            for key in ("call_made", "schema_valid", "policy_valid", "credential_echo_blocked"):
                _require(type(row[key]) is bool)
            calls.append(row)
            stopped = not _continue(row)
    _require(bool(calls))
    if status == "completed":
        _require(all(row["local_error"] is None for row in calls))
    else:
        _require(calls[-1]["outcome"] == status and calls[-1]["local_error"] is not None)
    success = len(calls) == MAX_CALLS and all(row["outcome"] == "accepted" and _continue(row) for row in calls)
    unavailable = any((row["llm_error"] or {}).get("category") in {
        "rate_limited", "quota_exceeded", "timeout", "provider_unavailable", "transport_failure"} for row in calls)
    code = 130 if status == "cancelled" else 3 if status == "local_error" or any(row["operational_error"] for row in calls) else 0 if success else 2 if unavailable else 1
    return {**_scope(), "slots_processed": len(calls), "slots_skipped": MAX_CALLS - len(calls),
        "calls_made": sum(row["call_made"] for row in calls), "schema_valid": sum(row["schema_valid"] for row in calls),
        "policy_valid": sum(row["policy_valid"] for row in calls), "route_verified": sum(row["route_status"] == "verified" for row in calls),
        "length_measurements": [{"slot_id": row["slot_id"], "arm_id": row["arm_id"], "measurements": row["measurements"]} for row in calls],
        "operational_probe_passed": success, "semantic_fidelity_review": {"status": "not_performed", "approval": None},
        "process_exit_code": code}


def _aware(value):
    _require(type(value) is str)
    parsed = datetime.fromisoformat(value)
    _require(parsed.tzinfo is not None)
    return parsed


def _verify_row(prepared, index, batch, row, *, previous_rows=()):
    if row["kind"] == "source_word_budget_skip":
        _require(set(row) == set(_skip(index, "")))
        return
    expected = _new_row(prepared, index, batch)
    _require(set(row) == set(expected) and row["kind"] == expected["kind"])
    created = row["request_created_at"]
    request = make_request(prepared, index, batch, deadline=_aware(created) + timedelta(seconds=60) if created is not None else None)
    _require(_same(row["request"], _request_record(request)) and _same(row["authored_source"], expected["authored_source"]))
    _verify_evidence(row, request)
    _require(_same(row["operational_error"], _operational_error(row, previous_rows)))
    _require(row["schema_valid"] == (row["response_structure"] is not None)
        and _same(row["measurements"], measurements(row["response_structure"])))
    _require(row["call_made"] == (row["http_started_at"] is not None))
    local, proposal, policy_error = row["local_error"], None, None
    if local is not None:
        _require(type(local) is dict and set(local) == {"code", "stage"} and local["stage"] in STAGES)
        _require(row["outcome"] in ("local_error", "cancelled") and local["code"] ==
            ("source_word_budget_cancelled" if row["outcome"] == "cancelled" else "source_word_budget_local_error"))
    if created is None:
        _require(local is not None and local["stage"] == "preflight")
    if not row["call_made"]:
        _require(row["response_structure"] is None
            and not row["schema_valid"] and not row["policy_valid"] and not row["credential_echo_blocked"]
            and row["policy_error"] is None and _same(row["provider_observation"], _unavailable_observation()))
        if row["llm_error"] is None:
            _require(row["evidence"] is None and local is not None and local["stage"] in ("preflight", "transport"))
        else:
            _require(row["evidence"] is not None and row["route_status"] == "unavailable"
                and row["outcome"] == "provider_failed" and row["llm_error"]["category"] == "timeout")
    if local is not None and local["stage"] == "preflight":
        _require(not row["call_made"] and created is None)
    if row["credential_echo_blocked"]:
        _require(row["call_made"] and local is not None and local["stage"] == "transport")
        _require(row["response_structure"] is row["evidence"] is row["llm_error"] is None
            and not row["policy_valid"] and row["policy_error"] is None
            and _same(row["provider_observation"], _unavailable_observation()))
    if row["schema_valid"]:
        _require(row["call_made"] and row["route_status"] == "verified" and row["llm_error"] is None)
        proposal = profile.NarrativeSourceProposal.model_validate(row["response_structure"])
        _require(_same(proposal.model_dump(mode="json", by_alias=True), row["response_structure"]))
        case = _case(prepared, index)
        try:
            profile.validate_source_proposal(proposal, current_scene=SceneState.model_validate(case["scene"]),
                facts=(), player_input=case["player_input"])
        except SceneProposalError as exc:
            policy_error = exc.code
    _require(row["policy_error"] == policy_error)
    if row["policy_valid"]:
        _require(proposal is not None and policy_error is None)
    if local is not None:
        _require(not row["policy_valid"])
        if local["stage"] == "policy":
            _require(proposal is not None and policy_error is None)
        elif local["stage"] == "transport":
            _require(proposal is None)
        return
    if row["outcome"] == "accepted":
        _require(row["call_made"] and row["policy_valid"] and proposal is not None)
    elif row["outcome"] == "policy_rejected":
        _require(proposal is not None and policy_error is not None and not row["policy_valid"])
    else:
        _require(row["outcome"] in ("schema_rejected", "provider_failed") and proposal is None
            and not row["policy_valid"] and row["llm_error"] is not None)
        _require((row["outcome"] == "schema_rejected") == (row["llm_error"]["category"] in CONTENT_ERRORS))


def _verify_times(document, rows):
    start, end = (_aware(document[key]) for key in ("started_at", "finished_at"))
    _require(start <= end)
    tolerance, last_http, last_finished = timedelta(seconds=.01), None, None
    for row in rows:
        if row["kind"] == "source_word_budget_skip":
            continue
        if row["request_created_at"] is not None:
            created = _aware(row["request_created_at"])
            deadline = _aware(row["request"]["deadline"])
            _require(start <= created <= end and created + tolerance >= start + timedelta(seconds=60))
            if last_http is not None:
                _require(created + tolerance >= last_http + timedelta(seconds=60))
            if last_finished is not None:
                _require(created >= last_finished)
        if row["http_started_at"] is not None:
            _require(row["request_created_at"] is not None)
            http = _aware(row["http_started_at"])
            _require(created <= http <= deadline and start <= http <= end)
            if last_http is not None:
                _require(http + tolerance >= last_http + timedelta(seconds=60))
            last_http = http
        if row["evidence"] is not None:
            began, finished = (_aware(row["evidence"][key]) for key in ("started_at", "finished_at"))
            _require(start <= created <= began <= finished <= end)
            if row["http_started_at"] is not None:
                _require(began <= http <= finished and began <= deadline)
            else:
                _require((row["llm_error"] or {}).get("category") == "timeout")
            _require(finished <= deadline or "deadline_exceeded" in (row["operational_error"] or {}).get("codes", []))
            last_finished = finished


def verify_artifacts(summary_path, expected_preflight, batch_id, *, expected_preflight_sha256):
    prepared = _expected(expected_preflight, expected_preflight_sha256)
    path = Path(summary_path)
    _require(path.resolve() == (run_path(batch_id) / "summary.json").resolve() and not path.is_symlink())
    before, document = shared._sha256(path), _read_json(path)
    _require(set(document) == {"metadata", "batch_id", "started_at", "finished_at", "evaluation_status", "summary", "artifacts", "process_exit_code"}
        and _same(document["metadata"], prepared.metadata) and document["batch_id"] == batch_id)
    _require(type(document["artifacts"]) is dict and set(document["artifacts"]) == {"records"})
    raw_path, entry = path.parent / "records.jsonl", document["artifacts"]["records"]
    _require(type(entry) is dict and set(entry) == {"file", "sha256"} and entry["file"] == raw_path.name
        and not raw_path.is_symlink() and raw_path.stat().st_size <= MAX_JSON_BYTES
        and shared._sha256(raw_path) == entry["sha256"])
    lines = raw_path.read_text(encoding="utf-8").splitlines()
    _require(len(lines) == MAX_CALLS)
    rows = []
    for index, line in enumerate(lines):
        item = _loads(line.encode())
        _require(set(item) == {"metadata", "batch_id", "record"}
            and _same(item["metadata"], prepared.metadata) and item["batch_id"] == batch_id)
        _verify_row(prepared, index, batch_id, item["record"], previous_rows=rows)
        rows.append(item["record"])
    _verify_times(document, rows)
    summary = summarize(rows, document["evaluation_status"])
    _require(_same(summary, document["summary"]) and type(document["process_exit_code"]) is int
        and document["process_exit_code"] == summary["process_exit_code"])
    _require(shared._sha256(path) == before and shared._sha256(raw_path) == entry["sha256"])
    return dict(verified=True, batch_id=batch_id, summary_path=str(path.resolve()), process_exit_code=summary["process_exit_code"])


class _Parser(argparse.ArgumentParser):
    def error(self, message):
        raise ValueError("source_word_budget_arguments_invalid")


def main(argv=None):
    parser = _Parser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--preflight", action="store_true")
    modes.add_argument("--live", action="store_true")
    modes.add_argument("--verify-artifacts", type=Path)
    parser.add_argument("--batch-id")
    parser.add_argument("--expected-preflight", type=Path)
    parser.add_argument("--expected-preflight-sha256")
    parser.add_argument("--api-key-env", choices=(KEY_ENV,))
    parser.add_argument("--allow-synthetic-only", action="store_true")
    try:
        args = parser.parse_args(argv)
        if args.preflight:
            _require(args.batch_id is None and args.expected_preflight is None
                and args.expected_preflight_sha256 is None and args.api_key_env is None and not args.allow_synthetic_only)
            print(_json(prepare_experiment().metadata))
            return 0
        _batch(args.batch_id)
        _require(args.expected_preflight is not None and args.expected_preflight_sha256 is not None)
        if args.verify_artifacts:
            _require(args.api_key_env is None and not args.allow_synthetic_only)
            print(_json(verify_artifacts(args.verify_artifacts, args.expected_preflight, args.batch_id,
                expected_preflight_sha256=args.expected_preflight_sha256)))
            return 0
        _require(args.allow_synthetic_only and args.api_key_env == KEY_ENV)
        prepared = _expected(args.expected_preflight, args.expected_preflight_sha256)
        _require(not run_path(args.batch_id).exists(), "source_word_budget_run_exists")
    except Exception:
        print("source_word_budget_preflight_or_verification_failed", file=sys.stderr)
        return 3
    key = SecretStr(os.environ.get(KEY_ENV, "").strip())
    if not key.get_secret_value():
        print("source_word_budget_credential_missing", file=sys.stderr)
        return 3
    try:
        asyncio.run(evaluate_probe(prepared, api_key=key, batch_id=args.batch_id, run_directory=run_path(args.batch_id)))
        code = _read_json(run_path(args.batch_id) / "summary.json")["process_exit_code"]
        print(_json({"summary_path": str((run_path(args.batch_id) / "summary.json").resolve()), "process_exit_code": code}))
        return code
    except KeyboardInterrupt:
        return 130
    except Exception:
        print("source_word_budget_local_failure", file=sys.stderr)
        return 3
    finally:
        key = None


if __name__ == "__main__":
    raise SystemExit(main())
