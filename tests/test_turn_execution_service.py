from __future__ import annotations

from datetime import datetime, timezone

import pytest

from api.context_service import (
    ContextItem,
    ContextLayer,
    LayeredContext,
    ScoreBreakdown,
    SelectedContextItem,
)
from api.llm.contract import (
    CAPABILITY_STRUCTURED_GENERATION,
    CAPABILITY_TEXT_GENERATION,
    CancellationToken,
    CapabilityDescriptor,
    CapabilitySet,
    CapabilitySupport,
    ErrorCategory,
    LLMInvocationError,
    StreamEvent,
    StreamEventKind,
    LLMTarget,
)
from api.llm.testing import FakeLLMAdapter
from api.orchestrator_service import TurnPipelineResult
from api.persistence import SQLitePersistence
from api.relationship_service import RelationshipState
from api.rules_service import PlayerSheetModel
from api.scene_director_service import SceneContinuationProposal
from api.scene_resolution_integration import attach_scene_resolution
from api.scene_resolution_service import (
    SceneBeatKind,
    SceneConsequenceOption,
    SceneIntentOutcome,
    SceneResolutionInput,
    SceneTurnKind,
    mechanical_resolution_from_result,
)
from api.scene_service import SceneState
from api.state_service import sync_event_from_context
from api.turn_execution_service import (
    NarrativeContractError,
    build_resolution_receipt,
    execute_prepared_turn,
    restore_prepared_turn_from_capsule,
    validate_narrative_contract,
)
from api.turn_models import (
    CanonicalEvent,
    CanonicalFact,
    StateChange,
    TurnDraft,
    Visibility,
    NarrationResumeCapsule,
)


def test_resume_restores_frozen_prepared_turn_with_only_a_new_attempt_identity():
    prepared = _prepared("source")
    capsule = NarrationResumeCapsule(
        capsule_id="capsule-1", session_id="session",
        source_operation_id="source", source_attempt_id="attempt-source",
        turn_id="turn-source", requested_turn=1, state_revision=0,
        request_hash="a" * 64, action="Eu avanço.", draft=prepared.draft,
        resolution={"display": "Rolagem concluída."},
        frozen_context={
            "system_log": prepared.system_log,
            "updated_context": prepared.updated_context,
            "relationships_state": prepared.relationships_state.model_dump(mode="json"),
            "relationships_for_frontend": [],
            "context_packet": prepared.context_packet.model_dump(mode="json"),
        },
        requested_target={"profile": "narrator", "provider": "fake", "model": "fixed"},
        normalized_reason={"category": "timeout", "retryable": True},
    )
    restored = restore_prepared_turn_from_capsule(
        capsule.model_dump(mode="json"), resume_operation_id="resume-1",
    )
    assert restored.system_log == prepared.system_log
    assert restored.updated_context == prepared.updated_context
    assert restored.draft.facts == prepared.draft.facts
    assert restored.draft.state_changes == prepared.draft.state_changes
    assert restored.draft.attempt_id == "attempt-resume-1"
    assert restored.llm_invocations == []


VALID_PROPOSAL = SceneContinuationProposal.model_validate(
    {
        "narrative": (
            "As lâmpadas do galpão piscam quando a porta cede, revelando marcas "
            "recentes no piso e um rádio ainda ligado sobre a bancada; do mezanino, "
            "passos lentos respondem ao ruído e fazem a situação avançar."
        ),
        "outcome": "success",
        "location": "Galpão abandonado",
        "scene_summary": (
            "A entrada foi vencida, marcas recentes cruzam o piso e alguém se move "
            "no mezanino."
        ),
        "npcs_present": [],
        "new_facts": [
            {
                "kind": "clue",
                "summary": "Marcas recentes atravessam o piso em direção ao mezanino.",
                "visibility": "player",
                "importance": 0.8,
                "pending": False,
            },
            {
                "kind": "hook",
                "summary": "Passos lentos soam no mezanino.",
                "visibility": "player",
                "importance": 0.7,
                "pending": True,
            },
        ],
        "open_threads": ["Descobrir quem está no mezanino"],
        "player_prompt": "Os passos param acima de você; o que faz?",
    }
)
VALID_PLAYER_TEXT = VALID_PROPOSAL.player_text


def test_narrative_contract_accepts_a_complete_multisentence_scene_beat() -> None:
    text = VALID_PLAYER_TEXT

    assert validate_narrative_contract(text) == text


@pytest.mark.parametrize(
    ("text", "code"),
    (
        ("A resposta continua sem terminar", "narrative_not_declarative"),
        (
            "Primeiro parágrafo com palavras suficientes para compor um beat.\n\n"
            "Segundo parágrafo mantém a cena em movimento e termina.\n\n"
            "Terceiro parágrafo preserva a agência do personagem presente.\n\n"
            "Quarto parágrafo ultrapassa o limite estrutural permitido.",
            "narrative_paragraph_limit",
        ),
        (" ".join(["palavra"] * 24) + ".", "narrative_word_minimum"),
        (" ".join(["palavra"] * 151) + ".", "narrative_word_limit"),
        (
            "FATOS CANÔNICOS indicam que esta frase possui vinte e cinco palavras "
            "sem expor nenhuma outra informação relevante ao jogador durante a cena atual.",
            "narrative_internal_content",
        ),
    ),
)
def test_narrative_contract_rejects_invalid_model_output(text, code) -> None:
    with pytest.raises(NarrativeContractError) as caught:
        validate_narrative_contract(text)

    assert caught.value.code == code


def test_narrative_contract_rejects_result_that_contradicts_failed_roll() -> None:
    text = (
        "O galpão abandonado não existia, apenas um vazio que latejava com o som "
        "de ossos quebrados e o cheiro de terra queimada durante toda a investigação."
    )

    with pytest.raises(NarrativeContractError) as caught:
        validate_narrative_contract(
            text,
            facts=(
                {
                    "fact_type": "mechanics.resolution",
                    "value": {"is_success": False},
                },
            ),
        )

    assert caught.value.code == "narrative_outcome_mismatch"


def test_narrative_contract_accepts_improvised_prose_without_a_literal_allowlist() -> None:
    assert validate_narrative_contract(
        VALID_PLAYER_TEXT,
        facts=(
            {
                "fact_type": "mechanics.resolution",
                "value": {"is_success": True},
            },
        ),
    ) == VALID_PLAYER_TEXT


def test_narrative_contract_rejects_negated_success_for_successful_roll() -> None:
    text = (
        "A investigação não teve sucesso e nenhum detalhe novo foi confirmado; "
        "a cena permaneceu inalterada, sem qualquer descoberta canônica durante "
        "o turno atual nem qualquer avanço adicional verificável."
    )

    with pytest.raises(NarrativeContractError) as caught:
        validate_narrative_contract(
            text,
            facts=(
                {
                    "fact_type": "mechanics.resolution",
                    "value": {"is_success": True},
                },
            ),
        )

    assert caught.value.code == "narrative_outcome_mismatch"


def _target_and_capabilities() -> tuple[LLMTarget, CapabilitySet]:
    target = LLMTarget(profile="test", provider="fake", model="model")
    return target, CapabilitySet(
        target=target,
        descriptors=(
            CapabilityDescriptor(
                name=CAPABILITY_TEXT_GENERATION,
                support=CapabilitySupport.NATIVE,
            ),
            CapabilityDescriptor(
                name=CAPABILITY_STRUCTURED_GENERATION,
                support=CapabilitySupport.EMULATED,
                source="test validator",
            ),
        ),
    )


def _prepared(operation_id: str, session_id: str = "session") -> TurnPipelineResult:
    sheet = PlayerSheetModel(
        clan="brujah",
        attributes={"Strength": 3},
        skills={"Brawl": 2},
        disciplines={},
        status={
            "blood_potency": 1,
            "current_hunger": 1,
            "humanity": 7,
            "health_tracker": {"size": 7, "superficial": 0, "aggravated": 0},
            "willpower_tracker": {"size": 5, "superficial": 0, "aggravated": 0},
        },
    )
    context = {
        "player_sheet": sheet.model_dump(mode="json"),
        "last_action_cache": None,
        "pre_roll_snapshot": None,
    }
    occurred_at = datetime.now(timezone.utc)
    turn_id = f"turn-{operation_id}"
    fact = CanonicalFact(
        fact_id=f"fact-{operation_id}",
        fact_type="mechanics.resolution",
        predicate="resolved",
        value={
            "attribute": "Wits",
            "skill": "Investigation",
            "dice_pool": 3,
            "hunger_dice": 1,
            "difficulty": 2,
            "successes": 2,
            "is_success": True,
            "bestial_failure": False,
            "messy_critical": False,
            "summary": "Rolagem concluída.",
            "normal_rolls": [7, 4],
            "hunger_rolls": [6],
            "margin": 0,
        },
        occurred_at=occurred_at,
    )
    event = CanonicalEvent(
        event_id=f"event-{operation_id}",
        session_id=session_id,
        turn_id=turn_id,
        sequence=0,
        event_type="player_action_resolved",
        occurred_at=occurred_at,
        summary="O personagem venceu o obstáculo.",
        fact_ids=(fact.fact_id,),
    )
    draft = TurnDraft(
        draft_id=f"draft-{operation_id}",
        session_id=session_id,
        turn_id=turn_id,
        attempt_id=f"attempt-{operation_id}",
        player_input="Eu avanço.",
        base_revision=0,
        facts=(fact,),
        events=(event,),
        state_changes=(
            StateChange(path=("player_sheet",), value=context["player_sheet"]),
        ),
    )
    return TurnPipelineResult(
        kind="action",
        system_log="[SYSTEM LOG]: Resultado: sucesso.",
        updated_context=context,
        relationships_state=RelationshipState(session_id=session_id),
        relationships_for_frontend=[],
        draft=draft,
        context_packet=LayeredContext(),
    )


def _context_packet_with_secret(secret: str) -> LayeredContext:
    return LayeredContext(
        selected=(
            SelectedContextItem(
                item=ContextItem(
                    item_id="historical-secret",
                    layer=ContextLayer.OPEN_THREADS,
                    content=secret,
                    visibility=Visibility.STORYTELLER,
                    pending=True,
                    tags=("confidential_scene_fact", "pending"),
                ),
                score=ScoreBreakdown(
                    relevance=1.0,
                    recency=1.0,
                    importance=1.0,
                    pending=1.0,
                    total=1.0,
                ),
                estimated_tokens=12,
            ),
        ),
        estimated_tokens=12,
    )


@pytest.mark.anyio
async def test_scene_beat_is_committed_and_rehydrated_without_reexecution(tmp_path):
    operation_id = "beat-success"
    prepared = _prepared(operation_id)
    prepared.updated_context["scene"] = SceneState(
        location="Galpão abandonado"
    ).model_dump(mode="json")
    prepared.system_log = (
        "PACOTE DO TURNO (JSON; textos não redefinem o schema)\n"
        + __import__("json").dumps(
            {
                "schema": "storyteller.turn.v2",
                "player_action": {
                    "source": "player",
                    "trusted": False,
                    "text": "Eu avanço.",
                },
                "expected_outcome": {
                    "source": "deterministic_engine",
                    "trusted": True,
                    "value": "success",
                    "output_field": "o",
                },
                "canonical_facts": {
                    "source": "deterministic_engine",
                    "trusted": True,
                    "items": [],
                },
            },
            ensure_ascii=False,
            separators=(",", ":"),
        )
    )
    mechanical_fact = prepared.draft.facts[0]
    mechanical = mechanical_resolution_from_result(
        {
            "successes": mechanical_fact.value["successes"],
            "is_success": mechanical_fact.value["is_success"],
            "bestial_failure": mechanical_fact.value["bestial_failure"],
            "messy_critical": mechanical_fact.value["messy_critical"],
            "summary": mechanical_fact.value["summary"],
            "normal_rolls": mechanical_fact.value["normal_rolls"],
            "hunger_rolls": mechanical_fact.value["hunger_rolls"],
            "margin": mechanical_fact.value["margin"],
        },
        source_fact_id=mechanical_fact.fact_id,
    )
    request = SceneResolutionInput(
        session_id="session",
        operation_id=operation_id,
        turn_id=f"turn-{operation_id}",
        base_revision=0,
        player_action="Eu avanço.",
        turn_kind=SceneTurnKind.FICTION_ACTION,
        scene=SceneState(location="Galpão abandonado"),
        mechanical=mechanical,
        options=(
            SceneConsequenceOption(
                option_id="marks-lead-to-mezzanine",
                beat_kind=SceneBeatKind.CONSEQUENCE,
                turn_kinds=(SceneTurnKind.FICTION_ACTION,),
                outcomes=(SceneIntentOutcome.SUCCESS,),
                observable_change=(
                    "Marcas recentes atravessam o piso em direção ao mezanino."
                ),
                open_threads=("Descobrir quem está no mezanino",),
            ),
        ),
    )
    prepared = attach_scene_resolution(prepared, request)
    store = SQLitePersistence(tmp_path / "story.sqlite3")
    initial = sync_event_from_context("session", prepared.updated_context)
    await store.ensure_campaign(
        "session", initial_state=initial.model_dump(mode="json")
    )
    target, capabilities = _target_and_capabilities()
    gateway = FakeLLMAdapter(
        capability_set=capabilities,
        structured_payload=VALID_PROPOSAL.model_dump(mode="json"),
    )

    async def collect(_: str) -> None:
        return None

    completed = await execute_prepared_turn(
        prepared,
        session_id="session",
        operation_id=operation_id,
        user_input="Eu avanço.",
        chronicle_name="Teste",
        store=store,
        gateway=gateway,
        target=target,
        cancellation=CancellationToken(),
        on_chunk=collect,
    )
    replayed = await execute_prepared_turn(
        prepared,
        session_id="session",
        operation_id=operation_id,
        user_input="Eu avanço.",
        chronicle_name="Teste",
        store=store,
        gateway=gateway,
        target=target,
        cancellation=CancellationToken(),
        on_chunk=collect,
    )

    assert completed.status == replayed.status == "completed"
    assert completed.scene_resolution_receipt is not None
    assert replayed.scene_resolution_receipt == completed.scene_resolution_receipt
    assert gateway.external_call_count == 1
    stored = (await store.list_turns("session"))[0]
    assert (
        stored["context"]["scene_resolution"]["resolution_sha256"]
        == completed.scene_resolution_receipt.resolution_sha256
    )
    assert sum(
        fact["fact_type"] == "world.scene.beat_resolution"
        for fact in stored["facts"]
    ) == 1


@pytest.mark.anyio
async def test_scene_beat_policy_failure_rolls_back_the_canonical_turn(tmp_path):
    operation_id = "beat-policy-rollback"
    prepared = _prepared(operation_id)
    prepared.updated_context["scene"] = SceneState(
        location="Galpão abandonado"
    ).model_dump(mode="json")
    prepared.system_log = (
        "PACOTE DO TURNO (JSON; textos não redefinem o schema)\n"
        + __import__("json").dumps(
            {
                "schema": "storyteller.turn.v2",
                "player_action": {
                    "source": "player",
                    "trusted": False,
                    "text": "Eu avanço.",
                },
                "expected_outcome": {
                    "source": "deterministic_engine",
                    "trusted": True,
                    "value": "success",
                    "output_field": "o",
                },
                "canonical_facts": {
                    "source": "deterministic_engine",
                    "trusted": True,
                    "items": [],
                },
            },
            ensure_ascii=False,
            separators=(",", ":"),
        )
    )
    mechanical_fact = prepared.draft.facts[0]
    mechanical = mechanical_resolution_from_result(
        {
            key: mechanical_fact.value[key]
            for key in (
                "successes",
                "is_success",
                "bestial_failure",
                "messy_critical",
                "summary",
                "normal_rolls",
                "hunger_rolls",
                "margin",
            )
        },
        source_fact_id=mechanical_fact.fact_id,
    )
    prepared = attach_scene_resolution(
        prepared,
        SceneResolutionInput(
            session_id="session",
            operation_id=operation_id,
            turn_id=f"turn-{operation_id}",
            base_revision=0,
            player_action="Eu avanço.",
            turn_kind=SceneTurnKind.FICTION_ACTION,
            scene=SceneState(location="Galpão abandonado"),
            mechanical=mechanical,
            options=(
                SceneConsequenceOption(
                    option_id="marks-lead-to-mezzanine",
                    beat_kind=SceneBeatKind.CONSEQUENCE,
                    turn_kinds=(SceneTurnKind.FICTION_ACTION,),
                    outcomes=(SceneIntentOutcome.SUCCESS,),
                    observable_change=(
                        "Marcas recentes atravessam o piso em direção ao mezanino."
                    ),
                    open_threads=("Descobrir quem está no mezanino",),
                ),
            ),
        ),
    )
    store = SQLitePersistence(tmp_path / "story.sqlite3")
    initial = sync_event_from_context("session", prepared.updated_context)
    await store.ensure_campaign(
        "session", initial_state=initial.model_dump(mode="json")
    )
    target, capabilities = _target_and_capabilities()
    rejected_payload = VALID_PROPOSAL.model_dump(mode="json")
    rejected_payload["open_threads"] = []
    gateway = FakeLLMAdapter(
        capability_set=capabilities,
        structured_payload=rejected_payload,
    )

    async def collect(_: str) -> None:
        return None

    result = await execute_prepared_turn(
        prepared,
        session_id="session",
        operation_id=operation_id,
        user_input="Eu avanço.",
        chronicle_name="Teste",
        store=store,
        gateway=gateway,
        target=target,
        cancellation=CancellationToken(),
        on_chunk=collect,
    )

    assert result.status == "failed"
    assert result.error is not None
    assert result.error.code == "scene_beat_open_thread_omitted"
    assert result.scene_resolution_receipt is None
    assert gateway.external_call_count == 1
    assert (await store.load_campaign("session"))["current_turn"] == 0
    assert await store.list_turns("session") == []
    assert await store.list_events("session") == []
    attempt = (await store.list_attempts("session"))[0]
    assert attempt["status"] == "failed"
    assert attempt["error"]["code"] == "scene_beat_open_thread_omitted"


@pytest.mark.anyio
async def test_completed_turn_commits_narrative_events_and_memory(tmp_path):
    store = SQLitePersistence(tmp_path / "story.sqlite3")
    initial = sync_event_from_context("session", _prepared("seed").updated_context)
    await store.ensure_campaign("session", initial_state=initial.model_dump(mode="json"))
    target, capabilities = _target_and_capabilities()
    gateway = FakeLLMAdapter(
        capability_set=capabilities,
        structured_payload=VALID_PROPOSAL.model_dump(mode="json"),
    )
    chunks: list[str] = []

    async def collect(chunk: str) -> None:
        chunks.append(chunk)

    result = await execute_prepared_turn(
        _prepared("success"),
        session_id="session",
        operation_id="success",
        user_input="Eu avanço.",
        chronicle_name="Teste",
        store=store,
        gateway=gateway,
        target=target,
        cancellation=CancellationToken(),
        on_chunk=collect,
    )
    repeated = await execute_prepared_turn(
        _prepared("success"),
        session_id="session",
        operation_id="success",
        user_input="Eu avanço.",
        chronicle_name="Teste",
        store=store,
        gateway=gateway,
        target=target,
        cancellation=CancellationToken(),
        on_chunk=collect,
    )

    assert result.status == "completed", result.error
    assert repeated.status == "completed"
    assert repeated.narrative is not None
    assert result.narrative is not None
    assert repeated.narrative.narrative_id == result.narrative.narrative_id
    assert repeated.narrative.text == result.narrative.text
    assert set(repeated.narrative.source_event_ids) == set(result.narrative.source_event_ids)
    assert chunks == [VALID_PLAYER_TEXT]
    assert result.resolution_receipt is not None
    assert result.resolution_receipt["display"].startswith(
        "Raciocínio + Investigação"
    )
    assert result.narrative_mode == "llm"
    assert gateway.external_call_count == 1
    assert (await store.load_campaign("session"))["current_turn"] == 1
    assert len(await store.list_turns("session")) == 1
    events = await store.list_events("session")
    assert [event["event_type"] for event in events] == [
        "player_action_resolved",
        "scene_established",
    ]
    assert result.state_event is not None
    assert result.state_event.context.scene is not None
    assert result.state_event.context.scene.location == "Galpão abandonado"
    turn = (await store.list_turns("session"))[0]
    assert {fact["fact_type"] for fact in turn["facts"]} == {
        "mechanics.resolution",
        "world.scene",
        "world.scene.clue",
        "world.scene.hook",
        "world.scene.thread_opened",
    }
    assert turn["context"]["scene_direction"] == {
        "outcome": "success",
        "location": "Galpão abandonado",
        "open_threads": ["Descobrir quem está no mezanino"],
        "resolved_threads": [],
        "player_prompt": "Os passos param acima de você; o que faz?",
        "admitted_fact_count": 2,
        "policy": "scene_director_admission.v1",
    }
    candidates = await store.list_memory_candidates("session")
    memories = await store.list_episodic_memories("session")
    assert candidates[0]["validation_status"] == "accepted"
    assert candidates[0]["proposed_by"] == "llm"
    assert memories[0]["summary"] == VALID_PROPOSAL.scene_summary


@pytest.mark.anyio
async def test_historical_context_secret_is_rejected_before_delivery_or_commit(
    tmp_path,
):
    operation_id = "historical-secret-leak"
    secret = "O Xerife armou uma emboscada no cais."
    prepared = _prepared(operation_id)
    prepared.context_packet = _context_packet_with_secret(secret)
    store = SQLitePersistence(tmp_path / "historical-secret-leak.sqlite3")
    initial = sync_event_from_context("session", prepared.updated_context)
    await store.ensure_campaign("session", initial_state=initial.model_dump(mode="json"))
    target, capabilities = _target_and_capabilities()
    payload = VALID_PROPOSAL.model_dump(mode="json")
    payload["narrative"] = (
        "A porta cede e as lâmpadas revelam marcas recentes no piso do galpão. "
        f"{secret} O rádio chia sobre a bancada enquanto passos lentos cruzam o "
        "mezanino e transformam o silêncio numa ameaça imediata."
    )
    gateway = FakeLLMAdapter(
        capability_set=capabilities,
        structured_payload=payload,
    )
    chunks: list[str] = []

    async def collect(chunk: str) -> None:
        chunks.append(chunk)

    result = await execute_prepared_turn(
        prepared,
        session_id="session",
        operation_id=operation_id,
        user_input="Eu avanço.",
        chronicle_name="Teste",
        store=store,
        gateway=gateway,
        target=target,
        cancellation=CancellationToken(),
        on_chunk=collect,
    )

    assert result.status == "failed"
    assert result.error is not None
    assert result.error.code == "scene_secret_disclosed"
    assert chunks == []
    assert (await store.load_campaign("session"))["current_turn"] == 0
    assert await store.list_turns("session") == []


@pytest.mark.anyio
async def test_invalid_scene_schema_fails_without_consuming_the_turn(tmp_path):
    operation_id = "invalid-scene-schema"
    store = SQLitePersistence(tmp_path / "invalid-scene-schema.sqlite3")
    prepared = _prepared(operation_id)
    initial = sync_event_from_context("session", prepared.updated_context)
    await store.ensure_campaign("session", initial_state=initial.model_dump(mode="json"))
    target, capabilities = _target_and_capabilities()
    gateway = FakeLLMAdapter(
        capability_set=capabilities,
        structured_payload={"narrative": "Payload incompleto."},
    )
    delivered: list[str] = []

    async def consume(chunk: str) -> None:
        delivered.append(chunk)

    result = await execute_prepared_turn(
        prepared,
        session_id="session",
        operation_id=operation_id,
        user_input="Eu avanço.",
        chronicle_name="Teste",
        store=store,
        gateway=gateway,
        target=target,
        cancellation=CancellationToken(),
        on_chunk=consume,
    )

    assert result.status == "failed"
    assert result.narrative is None
    assert result.narrative_mode is None
    assert delivered == []
    assert (await store.load_campaign("session"))["current_turn"] == 0
    assert await store.list_turns("session") == []
    assert await store.list_events("session") == []
    attempts = await store.list_attempts("session")
    assert attempts[0]["status"] == "failed"
    assert attempts[0]["error"]["code"] == "structured_output_schema_mismatch"
    assert [
        (invocation["operation"], invocation["status"])
        for invocation in attempts[0]["provenance"]["invocations"]
    ] == [("H6.direct_scene", "failed")]


@pytest.mark.anyio
async def test_policy_rejected_scene_proposal_fails_without_consuming_the_turn(
    tmp_path,
):
    operation_id = "invalid-scene-policy"
    store = SQLitePersistence(tmp_path / "invalid-scene-policy.sqlite3")
    prepared = _prepared(operation_id)
    initial = sync_event_from_context("session", prepared.updated_context)
    await store.ensure_campaign("session", initial_state=initial.model_dump(mode="json"))
    target, capabilities = _target_and_capabilities()
    rejected = VALID_PROPOSAL.model_copy(update={"outcome": "failure"})
    gateway = FakeLLMAdapter(
        capability_set=capabilities,
        structured_payload=rejected.model_dump(mode="json"),
    )
    delivered: list[str] = []

    async def consume(chunk: str) -> None:
        delivered.append(chunk)

    result = await execute_prepared_turn(
        prepared,
        session_id="session",
        operation_id=operation_id,
        user_input="Eu avanço.",
        chronicle_name="Teste",
        store=store,
        gateway=gateway,
        target=target,
        cancellation=CancellationToken(),
        on_chunk=consume,
    )

    assert result.status == "failed"
    assert result.narrative is None
    assert result.narrative_mode is None
    assert delivered == []
    assert (await store.load_campaign("session"))["current_turn"] == 0
    assert await store.list_turns("session") == []
    assert await store.list_events("session") == []
    attempts = await store.list_attempts("session")
    assert attempts[0]["status"] == "failed"
    assert attempts[0]["error"]["code"] == "scene_outcome_mismatch"


@pytest.mark.anyio
async def test_generation_truncation_fails_without_consuming_the_turn(tmp_path):
    operation_id = "truncated-safe-fallback"
    store = SQLitePersistence(tmp_path / "truncated.sqlite3")
    prepared = _prepared(operation_id)
    initial = sync_event_from_context("session", prepared.updated_context)
    await store.ensure_campaign(
        "session", initial_state=initial.model_dump(mode="json")
    )
    target, capabilities = _target_and_capabilities()

    class TruncatedAdapter(FakeLLMAdapter):
        async def generate_structured(self, request):
            try:
                return await super().generate_structured(request)
            except LLMInvocationError as exc:
                raise LLMInvocationError(
                    exc.error.model_copy(update={"code": "generation_truncated"})
                ) from exc

    gateway = TruncatedAdapter(
        capability_set=capabilities,
        structured_payload=VALID_PROPOSAL.model_dump(mode="json"),
        failure_category=ErrorCategory.MALFORMED_RESPONSE,
    )
    delivered: list[str] = []

    async def collect(chunk: str) -> None:
        delivered.append(chunk)

    result = await execute_prepared_turn(
        prepared,
        session_id="session",
        operation_id=operation_id,
        user_input="Investigo o local.",
        chronicle_name="Teste",
        store=store,
        gateway=gateway,
        target=target,
        cancellation=CancellationToken(),
        on_chunk=collect,
    )

    assert result.status == "failed"
    assert result.narrative is None
    assert result.narrative_mode is None
    assert delivered == []
    assert (await store.load_campaign("session"))["current_turn"] == 0
    assert await store.list_turns("session") == []
    assert await store.list_events("session") == []
    attempts = await store.list_attempts("session")
    assert attempts[0]["status"] == "failed"
    assert attempts[0]["error"]["code"] == "generation_truncated"


def test_resolution_receipt_requires_a_complete_player_visible_projection() -> None:
    assert build_resolution_receipt(
        [{"fact_type": "mechanics.resolution", "value": {"successes": 2}}],
        turn_id="turn-incomplete",
    ) is None


def test_resolution_receipt_uses_singular_success_label() -> None:
    facts = (
        {
            "fact_type": "mechanics.resolution",
            "value": {
                "attribute": "Wits",
                "skill": "Investigation",
                "dice_pool": 2,
                "hunger_dice": 1,
                "difficulty": 3,
                "normal_rolls": [10],
                "hunger_rolls": [1],
                "successes": 1,
                "margin": -2,
                "is_success": False,
            },
        },
    )

    receipt = build_resolution_receipt(facts, turn_id="turn-singular")

    assert receipt is not None
    assert "1 sucesso ·" in receipt["display"]
    assert "1 sucessos" not in receipt["display"]


@pytest.mark.anyio
async def test_preclaimed_attempt_is_not_claimed_again(tmp_path):
    store = SQLitePersistence(tmp_path / "preclaimed.sqlite3")
    prepared = _prepared("preclaimed")
    initial = sync_event_from_context("session", prepared.updated_context)
    await store.ensure_campaign("session", initial_state=initial.model_dump(mode="json"))
    preclaimed = await store.start_attempt(
        session_id="session",
        operation_id="preclaimed",
        attempt_id="attempt-preclaimed",
        requested_turn=1,
        user_input="Eu avanço.",
        chronicle_name="Teste",
    )
    target, capabilities = _target_and_capabilities()
    gateway = FakeLLMAdapter(
        capability_set=capabilities,
        structured_payload=VALID_PROPOSAL.model_dump(mode="json"),
    )

    async def consume(_: str) -> None:
        return None

    result = await execute_prepared_turn(
        prepared,
        session_id="session",
        operation_id="preclaimed",
        user_input="Eu avanço.",
        chronicle_name="Teste",
        store=store,
        gateway=gateway,
        target=target,
        cancellation=CancellationToken(),
        on_chunk=consume,
        preclaimed_attempt=preclaimed,
    )

    assert result.status == "completed", result.error
    attempts = await store.list_attempts("session")
    assert [(attempt["attempt_id"], attempt["status"]) for attempt in attempts] == [
        ("attempt-preclaimed", "completed")
    ]


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("failure_category", "expected_retryable"),
    (
        (ErrorCategory.PROVIDER_UNAVAILABLE, True),
        (ErrorCategory.AUTHENTICATION_FAILED, False),
    ),
)
async def test_structured_generation_failure_audits_without_promoting_state(
    tmp_path, failure_category, expected_retryable,
):
    store = SQLitePersistence(tmp_path / "story.sqlite3")
    prepared = _prepared("failure")
    initial = sync_event_from_context("session", prepared.updated_context)
    await store.ensure_campaign("session", initial_state=initial.model_dump(mode="json"))
    target, capabilities = _target_and_capabilities()

    class RetryAwareAdapter(FakeLLMAdapter):
        async def generate_structured(self, request):
            try:
                return await super().generate_structured(request)
            except LLMInvocationError as exc:
                raise LLMInvocationError(exc.error.model_copy(
                    update={"retryable": expected_retryable},
                )) from exc

    gateway = RetryAwareAdapter(
        capability_set=capabilities,
        structured_payload=VALID_PROPOSAL.model_dump(mode="json"),
        failure_category=failure_category,
    )

    async def consume(_: str) -> None:
        return None

    result = await execute_prepared_turn(
        prepared,
        session_id="session",
        operation_id="failure",
        user_input="Eu avanço.",
        chronicle_name="Teste",
        store=store,
        gateway=gateway,
        target=target,
        cancellation=CancellationToken(),
        on_chunk=consume,
    )

    assert result.status == "failed"
    assert result.partial_narrative == ""
    assert (await store.load_campaign("session"))["current_turn"] == 0
    assert await store.list_turns("session") == []
    attempts = await store.list_attempts("session")
    assert attempts[0]["status"] == "failed"
    assert attempts[0]["partial_narrative"] == ""
    assert attempts[0]["metadata"]["discarded_output_chars"] == 0
    assert attempts[0]["metadata"]["discarded_output_sha256"] is None
    assert attempts[0]["error"]["code"] == "scripted_failure"
    assert result.narration_pause is not None
    assert result.narration_pause.category == failure_category.value
    assert result.narration_pause.retryable is expected_retryable
    active = await store.load_active_narration_resume_capsule("session")
    assert active is not None
    assert active["payload"]["draft"]["facts"] == [
        fact.model_dump(mode="json") for fact in prepared.draft.facts
    ]


@pytest.mark.anyio
async def test_callback_disconnect_cancels_and_preserves_revision(tmp_path):
    store = SQLitePersistence(tmp_path / "story.sqlite3")
    prepared = _prepared("cancel")
    initial = sync_event_from_context("session", prepared.updated_context)
    await store.ensure_campaign("session", initial_state=initial.model_dump(mode="json"))
    target, capabilities = _target_and_capabilities()
    gateway = FakeLLMAdapter(
        capability_set=capabilities,
        structured_payload=VALID_PROPOSAL.model_dump(mode="json"),
    )

    async def disconnect(_: str) -> None:
        raise RuntimeError("socket closed")

    result = await execute_prepared_turn(
        prepared,
        session_id="session",
        operation_id="cancel",
        user_input="Eu avanço.",
        chronicle_name="Teste",
        store=store,
        gateway=gateway,
        target=target,
        cancellation=CancellationToken(),
        on_chunk=disconnect,
    )

    assert result.status == "cancelled"
    assert (await store.load_campaign("session"))["current_turn"] == 0
    assert (await store.list_attempts("session"))[0]["status"] == "cancelled"


@pytest.mark.anyio
async def test_disconnect_after_completed_terminal_still_prevents_commit(tmp_path):
    store = SQLitePersistence(tmp_path / "story.sqlite3")
    prepared = _prepared("cancel-after-terminal")
    initial = sync_event_from_context("session", prepared.updated_context)
    await store.ensure_campaign("session", initial_state=initial.model_dump(mode="json"))
    target, capabilities = _target_and_capabilities()
    cancellation = CancellationToken()

    class CancelAfterTerminalGateway(FakeLLMAdapter):
        async def generate_structured(self, request):
            result = await super().generate_structured(request)
            cancellation.cancel("transport closed after structured result")
            return result

    gateway = CancelAfterTerminalGateway(
        capability_set=capabilities,
        structured_payload=VALID_PROPOSAL.model_dump(mode="json"),
    )

    async def consume(_: str) -> None:
        return None

    result = await execute_prepared_turn(
        prepared,
        session_id="session",
        operation_id="cancel-after-terminal",
        user_input="Eu avanço.",
        chronicle_name="Teste",
        store=store,
        gateway=gateway,
        target=target,
        cancellation=cancellation,
        on_chunk=consume,
    )

    assert result.status == "cancelled"
    assert await store.list_turns("session") == []
    assert (await store.load_campaign("session"))["current_turn"] == 0
    attempt = (await store.list_attempts("session"))[0]
    assert attempt["status"] == "cancelled"
    assert attempt["error"]["code"] == "client_turn_cancelled"


@pytest.mark.anyio
async def test_timeout_terminal_is_audited_without_promoting_state(tmp_path):
    store = SQLitePersistence(tmp_path / "story.sqlite3")
    prepared = _prepared("timeout")
    initial = sync_event_from_context("session", prepared.updated_context)
    await store.ensure_campaign("session", initial_state=initial.model_dump(mode="json"))
    target, capabilities = _target_and_capabilities()
    gateway = FakeLLMAdapter(
        capability_set=capabilities,
        failure_category=ErrorCategory.TIMEOUT,
    )

    async def consume(_: str) -> None:
        return None

    result = await execute_prepared_turn(
        prepared,
        session_id="session",
        operation_id="timeout",
        user_input="Eu avanço.",
        chronicle_name="Teste",
        store=store,
        gateway=gateway,
        target=target,
        cancellation=CancellationToken(),
        on_chunk=consume,
    )

    assert result.status == "timeout"
    assert (await store.load_campaign("session"))["current_turn"] == 0
    assert await store.list_turns("session") == []
    attempts = await store.list_attempts("session")
    assert attempts[0]["status"] == "timeout"


@pytest.mark.anyio
async def test_event_after_structured_terminal_fails_closed_without_committing(
    tmp_path, monkeypatch
):
    store = SQLitePersistence(tmp_path / "story.sqlite3")
    prepared = _prepared("invalid-stream")
    initial = sync_event_from_context("session", prepared.updated_context)
    await store.ensure_campaign("session", initial_state=initial.model_dump(mode="json"))
    target, capabilities = _target_and_capabilities()

    from api.orchestrator_service import run_narrator_events as real_run_narrator_events

    async def event_after_terminal(*args, **kwargs):
        terminal = None
        async for event in real_run_narrator_events(*args, **kwargs):
            yield event
            if event.is_terminal:
                terminal = event
        assert terminal is not None
        yield StreamEvent(
            sequence=terminal.sequence + 1,
            kind=StreamEventKind.DELTA,
            delta="evento proibido",
        )

    monkeypatch.setattr(
        "api.turn_execution_service.run_narrator_events", event_after_terminal
    )
    gateway = FakeLLMAdapter(
        capability_set=capabilities,
        structured_payload=VALID_PROPOSAL.model_dump(mode="json"),
    )

    async def consume(_: str) -> None:
        return None

    result = await execute_prepared_turn(
        prepared,
        session_id="session",
        operation_id="invalid-stream",
        user_input="Eu avanço.",
        chronicle_name="Teste",
        store=store,
        gateway=gateway,
        target=target,
        cancellation=CancellationToken(),
        on_chunk=consume,
    )

    assert result.status == "failed"
    assert result.error.category is ErrorCategory.MALFORMED_RESPONSE
    assert await store.list_turns("session") == []
    assert (await store.load_campaign("session"))["current_turn"] == 0
    attempt = (await store.list_attempts("session"))[0]
    assert attempt["status"] == "failed"
    assert attempt["error"]["code"] == "invalid_stream_event_sequence"


@pytest.mark.anyio
async def test_out_of_sequence_structured_delta_drains_evidence_without_publishing(
    tmp_path, monkeypatch
):
    store = SQLitePersistence(tmp_path / "story.sqlite3")
    prepared = _prepared("invalid-first-sequence")
    initial = sync_event_from_context("session", prepared.updated_context)
    await store.ensure_campaign("session", initial_state=initial.model_dump(mode="json"))
    target, capabilities = _target_and_capabilities()

    from api.orchestrator_service import run_narrator_events as real_run_narrator_events

    async def out_of_sequence(*args, **kwargs):
        first = True
        async for event in real_run_narrator_events(*args, **kwargs):
            if first and event.kind is StreamEventKind.DELTA:
                first = False
                yield event.model_copy(update={"sequence": event.sequence + 1})
            else:
                yield event

    monkeypatch.setattr(
        "api.turn_execution_service.run_narrator_events", out_of_sequence
    )
    gateway = FakeLLMAdapter(
        capability_set=capabilities,
        structured_payload=VALID_PROPOSAL.model_dump(mode="json"),
    )
    chunks: list[str] = []

    async def consume(chunk: str) -> None:
        chunks.append(chunk)

    result = await execute_prepared_turn(
        prepared,
        session_id="session",
        operation_id="invalid-first-sequence",
        user_input="Eu avanço.",
        chronicle_name="Teste",
        store=store,
        gateway=gateway,
        target=target,
        cancellation=CancellationToken(),
        on_chunk=consume,
    )

    assert result.status == "failed"
    assert chunks == []
    assert result.partial_narrative == ""
    assert result.error.category is ErrorCategory.MALFORMED_RESPONSE
    assert result.error.code == "invalid_stream_event_sequence"
    assert result.error.evidence.provenance.invocation_id
    assert await store.list_turns("session") == []
    attempt = (await store.list_attempts("session"))[0]
    assert attempt["status"] == "failed"
    assert attempt["error"]["code"] == "invalid_stream_event_sequence"
    assert [
        (item["operation"], item["status"])
        for item in attempt["provenance"]["invocations"]
    ] == [("H6.direct_scene", "failed")]
