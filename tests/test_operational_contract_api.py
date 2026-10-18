from __future__ import annotations

import asyncio
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from api import main
from api.llm.contract import (
    CAPABILITY_STREAMING,
    CAPABILITY_STRUCTURED_GENERATION,
    CAPABILITY_TEXT_GENERATION,
    CapabilityDescriptor,
    CapabilitySet,
    CapabilitySupport,
    ErrorCategory,
    InvocationEvidence,
    LLMTarget,
    StreamEvent,
    StreamEventKind,
    SYNTHETIC_PROBE_PROMPT,
)
from api.llm.diagnostics import (
    STREAMING_PROBE_PROMPT,
    STRUCTURED_PROBE_EXPECTED,
    STRUCTURED_PROBE_PROMPT,
)
from api.llm.runtime import LLMRuntime, LLMRuntimeConfigurationError
from api.llm.testing import FakeLLMAdapter
from api.persistence import SQLitePersistence
from api.state_service import configure_persistence_for_tests, get_persistence
from api.turn_models import (
    CandidateValidationStatus,
    CanonicalEvent,
    CanonicalFact,
    EpisodicMemory,
    MemoryCandidate,
    NarrativeRecord,
    Visibility,
)


def test_static_catchall_cannot_escape_compiled_frontend_root(
    tmp_path, monkeypatch
) -> None:
    dist_root = tmp_path / "dist"
    dist_root.mkdir()
    (dist_root / "favicon.svg").write_text("<svg></svg>", encoding="utf-8")
    monkeypatch.setattr(main, "DIST_ROOT", dist_root.resolve())
    monkeypatch.setattr(main, "DIST_DIR", str(dist_root.resolve()))

    with TestClient(main.app) as client:
        traversal = client.get("/%2e%2e/%2e%2e/README.md")
        encoded_separator = client.get("/..%2F..%2FREADME.md")
        inside = client.get("/favicon.svg")

    assert traversal.status_code == 404
    assert encoded_separator.status_code == 404
    assert "README" not in traversal.text
    assert "README" not in encoded_separator.text
    assert inside.status_code == 200


def _runtime() -> tuple[LLMRuntime, FakeLLMAdapter]:
    target = LLMTarget(profile="test-profile", provider="fake", model="test-model")
    capabilities = CapabilitySet(
        target=target,
        descriptors=(
            CapabilityDescriptor(
                name=CAPABILITY_TEXT_GENERATION,
                support=CapabilitySupport.NATIVE,
            ),
            CapabilityDescriptor(
                name=CAPABILITY_STRUCTURED_GENERATION,
                support=CapabilitySupport.EMULATED,
                source="local schema validation",
            ),
            CapabilityDescriptor(
                name=CAPABILITY_STREAMING,
                support=CapabilitySupport.NATIVE,
            ),
        ),
    )
    adapter = FakeLLMAdapter(
        capability_set=capabilities,
        structured_payload={"status": STRUCTURED_PROBE_EXPECTED},
        stream_deltas=("STORYTELLER_", "STREAM_OK"),
    )
    return LLMRuntime(target=target, gateway=adapter), adapter


def _incompatible_evidence(
    evidence: InvocationEvidence,
    mismatch: str,
) -> tuple[InvocationEvidence, str]:
    if mismatch == "requested_target":
        marker = "foreign-readiness-profile"
        provenance_update = {
            "requested_target": LLMTarget(
                profile=marker,
                provider="foreign-provider",
                model="foreign-model",
            )
        }
    else:
        marker = "foreign-readiness-invocation"
        provenance_update = {"invocation_id": marker}
    provenance = evidence.provenance.model_copy(update=provenance_update)
    return evidence.model_copy(update={"provenance": provenance}), marker


def _records(session_id: str = "session-api"):
    occurred_at = datetime.now(timezone.utc)
    fact = CanonicalFact(
        fact_id="fact-api",
        fact_type="mechanics.resolution",
        predicate="resolved",
        value={"successes": 2},
        occurred_at=occurred_at,
    )
    event = CanonicalEvent(
        event_id="event-api",
        session_id=session_id,
        turn_id="turn-api",
        sequence=0,
        event_type="player_action_resolved",
        occurred_at=occurred_at,
        summary="O Xerife reconheceu a dívida.",
        fact_ids=(fact.fact_id,),
    )
    narrative = NarrativeRecord(
        narrative_id="narrative-api",
        session_id=session_id,
        turn_id=event.turn_id,
        text="O Xerife fecha o livro-caixa e confirma a dívida.",
        source_event_ids=(event.event_id,),
    )
    player_memory = EpisodicMemory(
        memory_id="memory-player",
        session_id=session_id,
        summary="O Xerife confirmou a dívida.",
        source_event_ids=(event.event_id,),
        tags=("xerife", "dívida"),
        importance=0.9,
        pending=True,
    )
    secret_memory = EpisodicMemory(
        memory_id="memory-secret",
        session_id=session_id,
        summary="O Xerife planeja uma emboscada.",
        source_event_ids=(event.event_id,),
        visibility=Visibility.STORYTELLER,
        importance=1.0,
    )
    return fact, event, narrative, player_memory, secret_memory


def _accepted_candidate(memory: EpisodicMemory, turn_id: str) -> MemoryCandidate:
    return MemoryCandidate(
        candidate_id=f"candidate-{memory.memory_id}",
        session_id=memory.session_id,
        turn_id=turn_id,
        created_at=memory.created_at,
        summary=memory.summary,
        source_event_ids=memory.source_event_ids,
        tags=memory.tags,
        actors=memory.actors,
        place=memory.place,
        occurred_at=memory.occurred_at,
        importance=memory.importance,
        visibility=memory.visibility,
        pending=memory.pending,
        validation_status=CandidateValidationStatus.ACCEPTED,
    )


@pytest.mark.anyio
async def test_synthetic_probe_and_capabilities_are_explicit_and_campaign_free(
    monkeypatch,
):
    runtime, adapter = _runtime()
    monkeypatch.setattr(main, "get_llm_runtime", lambda: runtime)

    capabilities = await main.llm_capabilities()
    probe = await main.test_llm_connection()

    assert capabilities["configured"] is True
    assert capabilities["target"] == {
        "profile": "test-profile",
        "provider": "fake",
        "model": "test-model",
    }
    assert probe["configured"] is True
    assert probe["cached"] is False
    assert probe["ready"] is True
    assert probe["success"] is True
    assert adapter.external_call_count == 3
    assert [request.messages[0].content for request in adapter.requests] == [
        SYNTHETIC_PROBE_PROMPT,
        STRUCTURED_PROBE_PROMPT,
        STREAMING_PROBE_PROMPT,
    ]
    assert len({request.deadline for request in adapter.requests}) == 1
    assert [item["status"] for item in probe["diagnostics"]["probes"]] == [
        "passed",
        "passed",
        "passed",
    ]
    assert "connection_result" not in probe["diagnostics"]
    serialized_probe = str(probe)
    assert "session-api" not in serialized_probe
    assert "Xerife" not in serialized_probe


@pytest.mark.anyio
async def test_successful_readiness_reuses_a_short_cache(monkeypatch):
    runtime, adapter = _runtime()
    monkeypatch.setattr(main, "get_llm_runtime", lambda: runtime)

    first = await main.test_llm_connection()
    cached = await main.test_llm_connection()

    assert first["cached"] is False
    assert cached["cached"] is True
    assert adapter.external_call_count == 3


@pytest.mark.anyio
async def test_failed_readiness_expires_quickly_before_retry(monkeypatch):
    runtime, adapter = _runtime()
    adapter.failure_category = ErrorCategory.PROVIDER_UNAVAILABLE
    clock = [0.0]
    monkeypatch.setattr(main, "get_llm_runtime", lambda: runtime)
    monkeypatch.setattr(main.time, "monotonic", lambda: clock[0])

    first = await main.test_llm_connection()
    cached = await main.test_llm_connection()
    adapter.failure_category = None
    clock[0] = main.LLM_READINESS_FAILURE_CACHE_TTL_SECONDS + 0.01
    recovered = await main.test_llm_connection()

    assert first["ready"] is False and first["cached"] is False
    assert cached["ready"] is False and cached["cached"] is True
    assert recovered["ready"] is True and recovered["cached"] is False
    assert adapter.external_call_count == 4


@pytest.mark.anyio
async def test_concurrent_readiness_calls_share_one_remote_sequence(monkeypatch):
    runtime, adapter = _runtime()
    adapter.step_delay_seconds = 0.01
    monkeypatch.setattr(main, "get_llm_runtime", lambda: runtime)

    first, second = await asyncio.gather(
        main.test_llm_connection(),
        main.test_llm_connection(),
    )

    assert first["ready"] is True
    assert second["ready"] is True
    assert first["cached"] is False
    assert second["cached"] is False
    assert adapter.external_call_count == 3


@pytest.mark.anyio
async def test_cancelling_one_waiter_does_not_cancel_shared_readiness(monkeypatch):
    runtime, adapter = _runtime()
    adapter.step_delay_seconds = 0.02
    monkeypatch.setattr(main, "get_llm_runtime", lambda: runtime)

    cancelled_waiter = asyncio.create_task(main.test_llm_connection())
    await asyncio.sleep(0)
    surviving_waiter = asyncio.create_task(main.test_llm_connection())
    cancelled_waiter.cancel()

    with pytest.raises(asyncio.CancelledError):
        await cancelled_waiter
    result = await surviving_waiter

    assert result["ready"] is True
    assert result["cached"] is False
    assert adapter.external_call_count == 3


@pytest.mark.anyio
@pytest.mark.parametrize("probe_name", ("text", "structured", "streaming"))
@pytest.mark.parametrize("mismatch", ("requested_target", "invocation_id"))
async def test_readiness_rejects_incompatible_evidence_without_exposing_it(
    monkeypatch,
    probe_name,
    mismatch,
):
    runtime, adapter = _runtime()
    marker: str

    if probe_name == "text":
        original_text_probe = adapter.test_connection

        async def incompatible_text_probe(request):
            nonlocal marker
            result = await original_text_probe(request)
            evidence, marker = _incompatible_evidence(result.evidence, mismatch)
            return result.model_copy(update={"evidence": evidence})

        monkeypatch.setattr(adapter, "test_connection", incompatible_text_probe)
    elif probe_name == "structured":
        original_structured_probe = adapter.generate_structured

        async def incompatible_structured_probe(request):
            nonlocal marker
            result = await original_structured_probe(request)
            evidence, marker = _incompatible_evidence(result.evidence, mismatch)
            return result.model_copy(update={"evidence": evidence})

        monkeypatch.setattr(
            adapter,
            "generate_structured",
            incompatible_structured_probe,
        )
    else:
        original_streaming_probe = adapter.stream_text

        async def incompatible_streaming_probe(request):
            nonlocal marker
            async for event in original_streaming_probe(request):
                if event.is_terminal:
                    assert event.evidence is not None
                    evidence, marker = _incompatible_evidence(
                        event.evidence,
                        mismatch,
                    )
                    yield event.model_copy(update={"evidence": evidence})
                else:
                    yield event

        monkeypatch.setattr(
            adapter,
            "stream_text",
            incompatible_streaming_probe,
        )

    monkeypatch.setattr(main, "get_llm_runtime", lambda: runtime)
    probe = await main.test_llm_connection()

    failed_index = {"text": 0, "structured": 1, "streaming": 2}[probe_name]
    expected_statuses = {
        "text": ["failed", "skipped", "skipped"],
        "structured": ["passed", "failed", "skipped"],
        "streaming": ["passed", "passed", "failed"],
    }[probe_name]
    failed = probe["diagnostics"]["probes"][failed_index]

    assert probe["configured"] is True
    assert probe["ready"] is False
    assert probe["success"] is False
    assert "error" not in probe
    assert [item["status"] for item in probe["diagnostics"]["probes"]] == (
        expected_statuses
    )
    assert failed["evidence"] is None
    assert failed["error"] is None
    assert marker not in str(probe)
    assert adapter.external_call_count == failed_index + 1


@pytest.mark.anyio
async def test_readiness_fails_fast_after_text_probe_failure(monkeypatch):
    runtime, adapter = _runtime()
    adapter.failure_category = ErrorCategory.PROVIDER_UNAVAILABLE
    monkeypatch.setattr(main, "get_llm_runtime", lambda: runtime)

    probe = await main.test_llm_connection()

    assert probe["ready"] is False
    assert probe["success"] is False
    assert adapter.external_call_count == 1
    assert [item["status"] for item in probe["diagnostics"]["probes"]] == [
        "failed",
        "skipped",
        "skipped",
    ]


@pytest.mark.anyio
async def test_readiness_skips_streaming_after_structured_probe_failure(monkeypatch):
    runtime, adapter = _runtime()
    adapter.structured_payload = {"status": "WRONG"}
    monkeypatch.setattr(main, "get_llm_runtime", lambda: runtime)

    probe = await main.test_llm_connection()

    assert probe["ready"] is False
    assert probe["success"] is False
    assert probe["error"]["category"] == "invalid_structured_output"
    assert adapter.external_call_count == 2
    assert [item["status"] for item in probe["diagnostics"]["probes"]] == [
        "passed",
        "failed",
        "skipped",
    ]


@pytest.mark.anyio
async def test_readiness_rejects_completed_stream_with_wrong_content(monkeypatch):
    runtime, adapter = _runtime()
    adapter.stream_deltas = ("WRONG",)
    monkeypatch.setattr(main, "get_llm_runtime", lambda: runtime)

    probe = await main.test_llm_connection()

    assert probe["ready"] is False
    assert probe["success"] is False
    assert probe["error"]["code"] == "readiness_stream_content_mismatch"
    assert adapter.external_call_count == 3
    assert [item["status"] for item in probe["diagnostics"]["probes"]] == [
        "passed",
        "passed",
        "failed",
    ]


@pytest.mark.anyio
async def test_readiness_does_not_fabricate_evidence_for_adapter_exception(
    monkeypatch,
):
    runtime, adapter = _runtime()

    async def unnormalized_structured_failure(_request):
        raise RuntimeError("provider detail that must not escape")

    monkeypatch.setattr(adapter, "generate_structured", unnormalized_structured_failure)
    monkeypatch.setattr(main, "get_llm_runtime", lambda: runtime)

    probe = await main.test_llm_connection()

    failed = probe["diagnostics"]["probes"][1]
    assert probe["ready"] is False
    assert probe["success"] is False
    assert "error" not in probe
    assert failed["status"] == "failed"
    assert failed["evidence"] is None
    assert failed["error"] is None
    assert "provider detail" not in str(probe)
    assert adapter.external_call_count == 1


@pytest.mark.anyio
async def test_readiness_does_not_reuse_prior_evidence_for_unterminated_stream(
    monkeypatch,
):
    runtime, adapter = _runtime()

    async def unterminated_stream(_request):
        yield StreamEvent(sequence=0, kind=StreamEventKind.DELTA, delta="partial")

    monkeypatch.setattr(adapter, "stream_text", unterminated_stream)
    monkeypatch.setattr(main, "get_llm_runtime", lambda: runtime)

    probe = await main.test_llm_connection()

    failed = probe["diagnostics"]["probes"][2]
    assert probe["ready"] is False
    assert probe["success"] is False
    assert "error" not in probe
    assert failed["status"] == "failed"
    assert failed["evidence"] is None
    assert failed["error"] is None
    assert adapter.external_call_count == 2


@pytest.mark.anyio
async def test_unconfigured_llm_operations_fail_without_selecting_a_target(monkeypatch):
    def missing_runtime():
        raise LLMRuntimeConfigurationError("explicit target required")

    monkeypatch.setattr(main, "get_llm_runtime", missing_runtime)

    assert await main.llm_capabilities() == {
        "configured": False,
        "message": "explicit target required",
    }
    assert await main.test_llm_connection() == {
        "configured": False,
        "success": False,
        "message": "explicit target required",
    }


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("structured", "streaming", "expected_fragment"),
    (
        (CapabilitySupport.UNKNOWN, CapabilitySupport.NATIVE, "structured_generation"),
        (CapabilitySupport.EMULATED, CapabilitySupport.EMULATED, "streaming"),
    ),
)
async def test_synthetic_probe_refuses_targets_missing_mvp_capabilities(
    monkeypatch, structured, streaming, expected_fragment
):
    target = LLMTarget(profile="not-ready", provider="fake", model="model")
    capabilities = CapabilitySet(
        target=target,
        descriptors=(
            CapabilityDescriptor(
                name=CAPABILITY_TEXT_GENERATION,
                support=CapabilitySupport.NATIVE,
            ),
            CapabilityDescriptor(
                name=CAPABILITY_STRUCTURED_GENERATION,
                support=structured,
                source="explicit test declaration" if structured is not CapabilitySupport.UNKNOWN else None,
            ),
            CapabilityDescriptor(
                name=CAPABILITY_STREAMING,
                support=streaming,
                source="explicit test declaration",
            ),
        ),
    )
    adapter = FakeLLMAdapter(capability_set=capabilities)
    monkeypatch.setattr(
        main,
        "get_llm_runtime",
        lambda: LLMRuntime(target=target, gateway=adapter),
    )

    probe = await main.test_llm_connection()

    assert probe["configured"] is True
    assert probe["ready"] is False
    assert probe["success"] is False
    assert expected_fragment in probe["message"]
    assert [item["status"] for item in probe["diagnostics"]["probes"]] == [
        "skipped",
        "skipped",
        "skipped",
    ]
    assert adapter.external_call_count == 0


@pytest.mark.anyio
async def test_player_retrieval_filters_secret_memory_before_returning(tmp_path):
    previous = get_persistence()
    store = SQLitePersistence(tmp_path / "story.sqlite3")
    configure_persistence_for_tests(store)
    try:
        fact, event, narrative, player_memory, secret_memory = _records()
        await store.commit_turn(
            session_id="session-api",
            operation_id="operation-api",
            turn_id=event.turn_id,
            state={"revision": 1},
            narrative=narrative,
            facts=(fact,),
            events=(event,),
            memory_candidates=(
                _accepted_candidate(player_memory, event.turn_id),
                _accepted_candidate(secret_memory, event.turn_id),
            ),
            episodic_memories=(player_memory, secret_memory),
        )

        response = await main.retrieve_player_context(
            "session-api", query="xerife dívida", token_budget=100
        )

        assert [item["memory_id"] for item in response["memories"]] == [
            "memory-player"
        ]
        assert response["memories"][0]["visibility"] == "player"
    finally:
        configure_persistence_for_tests(previous)


@pytest.mark.anyio
async def test_consolidation_neutralizes_free_summary_and_preserves_grounded_sources(
    tmp_path,
):
    previous = get_persistence()
    store = SQLitePersistence(tmp_path / "story.sqlite3")
    configure_persistence_for_tests(store)
    try:
        fact, event, narrative, player_memory, _ = _records()
        await store.commit_turn(
            session_id="session-api",
            operation_id="operation-api",
            turn_id=event.turn_id,
            state={"revision": 1},
            narrative=narrative,
            facts=(fact,),
            events=(event,),
            memory_candidates=(_accepted_candidate(player_memory, event.turn_id),),
            episodic_memories=(player_memory,),
        )
        request = main.ConsolidationRequest(
            summary="A dívida com o Xerife continua pendente.",
            source_memory_ids=[player_memory.memory_id],
        )

        first = await main.consolidate_memory("session-api", "scene", request)
        repeated = await main.consolidate_memory("session-api", "scene", request)
        revised = await main.consolidate_memory(
            "session-api",
            "scene",
            main.ConsolidationRequest(
                summary="O Xerife morreu e a dívida deixou de existir.",
                source_memory_ids=[player_memory.memory_id],
            ),
        )
        missing = await main.consolidate_memory(
            "session-api",
            "scene",
            main.ConsolidationRequest(
                summary="Não deve ser criada.",
                source_memory_ids=["memory-inexistente"],
            ),
        )
        recovered = await main.retrieve_player_context(
            "session-api", query="xerife dívida", token_budget=100
        )

        assert first["success"] is True
        assert first["consolidation"]["version"] == 1
        assert repeated["consolidation"]["consolidation_id"] == first["consolidation"][
            "consolidation_id"
        ]
        assert repeated["consolidation"]["version"] == 1
        assert revised["consolidation"]["consolidation_id"] == first[
            "consolidation"
        ]["consolidation_id"]
        assert revised["consolidation"]["version"] == 1
        assert revised["consolidation"]["summary"] == (
            "- O Xerife confirmou a dívida."
        )
        assert "morreu" not in revised["consolidation"]["summary"]
        assert revised["summary_grounding"] == {
            "source": "episodic_memories",
            "proposal_status": "not_persisted",
        }
        assert missing["success"] is False
        assert [item["version"] for item in recovered["consolidations"]] == [1]
        assert recovered["consolidations"][0]["summary"] == (
            "- O Xerife confirmou a dívida."
        )
        assert len(await store.list_consolidations("session-api", scope="scene")) == 1
        assert len(await store.list_episodic_memories("session-api")) == 1
        assert len(await store.list_events("session-api")) == 1
    finally:
        configure_persistence_for_tests(previous)
