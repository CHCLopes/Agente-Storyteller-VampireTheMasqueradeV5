"""End-to-end opt-in campaign B, using only local fake responses."""
import asyncio
from datetime import timedelta
import sqlite3

import pytest

from api.campaign_source_capsule import CampaignSourceConfig
from api.campaign_source_execution_service import execute_campaign_source_turn
from api.campaign_source_input_service import prepare_campaign_source_player_action
from api.campaign_source_storage import (
    CampaignSourceStorageError, create_campaign_source_session,
    read_campaign_source_snapshot, claim_campaign_source_input,
    read_campaign_source_status, load_campaign_source_capsule, claim_campaign_narrative,
)
from api.llm.contract import (
    CAPABILITY_STRUCTURED_GENERATION, CAPABILITY_TEXT_GENERATION,
    CancellationToken, CapabilityDescriptor,
    CapabilitySet, CapabilitySupport, ErrorCategory, GenerationParameters, LLMTarget, utc_now,
)
from api.llm.testing import FakeLLMAdapter
from api.persistence import SQLitePersistence
from api.rules_service import ResolutionResult
from api.turn_models import NarrativeRecord, Visibility
from api.narrative_source_preparation import DeclaredActionPreparation, prepare_source_turn_draft
from test_narrative_source_input_service import state as eligible_state

N = (
    "A água pinga da infiltração acima da bancada e se aproxima do registro. "
    "Mara avisa que o risco aumentou, apontando a superfície seca na Galeria. "
    "O registro permanece seco por enquanto; nenhuma folha foi movida. "
    "O som das gotas torna claro que a escolha seguinte ainda pertence a você."
)
WET = (
    "A água da infiltração finalmente atinge o registro sobre a bancada. "
    "O papel fica molhado e parte da tinta começa a se espalhar pelas fibras. "
    "Mara aponta o dano sem tomar o documento por você; ainda há trechos legíveis. "
    "A superfície seca da Galeria permanece acessível, mas o estado anterior não volta."
)
LOST = (
    "A água continua caindo sobre o registro e o texto se torna irrecuperável. "
    "O documento está perdido; Mara reconhece a perda do acervo com voz baixa. "
    "As folhas permanecem na bancada, sem conteúdo legível para salvar. "
    "A tentativa termina aqui, com a consequência da espera explicitamente reconhecida."
)
RECOVERED = (
    "Durante o exame do registro, um trecho ainda legível permite recuperar parte do conteúdo. "
    "O papel sofreu dano, e a informação obtida é parcial; as demais linhas permanecem ilegíveis. "
    "Mara reconhece a descoberta e indica que o acervo conserva apenas esse fragmento. "
    "A investigação termina sem restaurar o documento inteiro nem acrescentar outra decisão obrigatória."
)


def config_and_gateway(n=N, effects=("campaign.warning.visible",), q="O que você faz agora?"):
    target = LLMTarget(profile="campaign-test", provider="fake", model="authored")
    caps = CapabilitySet(target=target, descriptors=tuple(CapabilityDescriptor(
        name=name, support=CapabilitySupport.NATIVE,
    ) for name in (CAPABILITY_TEXT_GENERATION, CAPABILITY_STRUCTURED_GENERATION)))
    adapter = FakeLLMAdapter(capability_set=caps, structured_payload={
        "n": n, "q": q, "realized_effects": effects,
    })
    config = CampaignSourceConfig(
        target=target, system_prompt="Narrador local de teste",
        parameters=GenerationParameters(temperature=.65, max_output_tokens=768),
    )
    return config, adapter


@pytest.mark.asyncio
async def test_one_campaign_turn_commits_effect_and_source_once(tmp_path):
    store = SQLitePersistence(tmp_path / "campaign.sqlite3")
    await create_campaign_source_session(store, "campaign-1", initial_state=eligible_state())
    config, gateway = config_and_gateway()
    claim = await prepare_campaign_source_player_action(
        store=store, session_id="campaign-1", operation_id="action-1",
        player_input="Aguardo", config=config,
        deadline=utc_now() + timedelta(seconds=30), cancellation=CancellationToken(),
    )
    assert claim.capsule is not None
    chunks = []
    async def on_chunk(text):
        chunks.append(text)
    result = await execute_campaign_source_turn(
        store=store, capsule=claim.capsule, operation_id="action-1",
        gateway=gateway, deadline=utc_now() + timedelta(seconds=30),
        cancellation=CancellationToken(), on_chunk=on_chunk,
    )
    assert result.status == "completed", result.error_code
    assert len(chunks) == len(gateway.requests) == 1
    campaign = await store.load_campaign("campaign-1")
    assert campaign["current_turn"] == campaign["state_revision"] == 1
    assert campaign["state"]["campaign_progression"]["record"] == "warned"
    assert (await read_campaign_source_snapshot(store, "campaign-1")).progression.record == "warned"
    replay = await execute_campaign_source_turn(
        store=store, capsule=claim.capsule, operation_id="action-1",
        gateway=gateway, deadline=utc_now() - timedelta(seconds=1),
        cancellation=CancellationToken(), on_chunk=on_chunk,
    )
    assert replay.status == "completed" and replay.envelope == result.envelope
    assert len(chunks) == len(gateway.requests) == 1


@pytest.mark.asyncio
async def test_three_waits_progress_to_terminal_epilogue_and_preserve_sources(tmp_path):
    db = tmp_path / "campaign.sqlite3"
    store = SQLitePersistence(db)
    await create_campaign_source_session(store, "campaign-1", initial_state=eligible_state())
    for number, (text, narrative, effects, q, expected) in enumerate((
        ("Aguardo", N, ("campaign.warning.visible",), "O que você faz agora?", "warned"),
        ("Espero", WET, ("campaign.record.wet",), "O que você faz agora?", "wet"),
        ("Aguardo", LOST, ("campaign.record.lost",), "", "lost"),
    ), 1):
        store = SQLitePersistence(db)  # restart/reconnect; never rely on memory cache
        config, gateway = config_and_gateway(narrative, effects, q)
        claim = await prepare_campaign_source_player_action(
            store=store, session_id="campaign-1", operation_id=f"action-{number}",
            player_input=text, config=config, deadline=utc_now() + timedelta(seconds=30),
            cancellation=CancellationToken(),
        )
        assert claim.capsule is not None
        chunks = []
        async def collect(value):
            chunks.append(value)
        result = await execute_campaign_source_turn(
            store=store, capsule=claim.capsule, operation_id=f"action-{number}",
            gateway=gateway, deadline=utc_now() + timedelta(seconds=30),
            cancellation=CancellationToken(), on_chunk=collect,
        )
        assert result.status == "completed", (number, result.error_code)
        assert len(chunks) == 1
        snapshot = await read_campaign_source_snapshot(store, "campaign-1")
        assert snapshot.progression.record == expected
        assert snapshot.current_turn == number
        assert len(snapshot.sources) == min(number, 2)
        assert len(gateway.requests) == 1
    assert snapshot.progression.outcome == "lost"
    assert result.envelope.question == ""


@pytest.mark.asyncio
async def test_failed_h_pauses_original_preparation_and_explicit_resume_commits_once(tmp_path):
    db = tmp_path / "campaign.sqlite3"
    store = SQLitePersistence(db)
    await create_campaign_source_session(store, "campaign-1", initial_state=eligible_state())
    config, failing = config_and_gateway()
    failing.failure_category = ErrorCategory.PROVIDER_UNAVAILABLE
    claim = await prepare_campaign_source_player_action(
        store=store, session_id="campaign-1", operation_id="action-1",
        player_input="Aguardo", config=config,
        deadline=utc_now() + timedelta(seconds=30), cancellation=CancellationToken(),
    )
    chunks = []
    async def collect(value):
        chunks.append(value)
    failed = await execute_campaign_source_turn(
        store=store, capsule=claim.capsule, operation_id="action-1",
        gateway=failing, deadline=utc_now() + timedelta(seconds=30),
        cancellation=CancellationToken(), on_chunk=collect,
    )
    assert failed.status == "failed" and failed.error_code == "campaign_source_provider_failure"
    assert chunks == []
    assert (await read_campaign_source_snapshot(store, "campaign-1")).progression.record == "threatened"
    status = await read_campaign_source_status(store, "campaign-1", "action-1")
    assert status.narrative_status == "failed" and status.resume_from_operation_id == "action-1"
    assert not hasattr(status, "system_prompt")
    with pytest.raises(ValueError, match="campaign_source_session_busy"):
        await prepare_campaign_source_player_action(
            store=store, session_id="campaign-1", operation_id="other-action",
            player_input="Espero", config=config,
            deadline=utc_now() + timedelta(seconds=30), cancellation=CancellationToken(),
        )
    store = SQLitePersistence(db)  # process restart; retain the original K
    assert await load_campaign_source_capsule(store, "campaign-1", "action-1") == claim.capsule
    good_config, good_gateway = config_and_gateway()
    assert good_config == config
    resumed = await execute_campaign_source_turn(
        store=store, capsule=claim.capsule, operation_id="resume-1",
        resumes_operation_id="action-1", gateway=good_gateway,
        deadline=utc_now() + timedelta(seconds=30),
        cancellation=CancellationToken(), on_chunk=collect,
    )
    assert resumed.status == "completed", resumed.error_code
    assert resumed.envelope.original_operation_id == "action-1"
    assert resumed.envelope.operation_id == "resume-1"
    assert (await read_campaign_source_snapshot(store, "campaign-1")).progression.record == "warned"
    assert len(chunks) == 1 and len(good_gateway.requests) == 1
    assert (await read_campaign_source_status(store, "campaign-1", "action-1")).narrative_status == "completed"
    replay = await execute_campaign_source_turn(
        store=store, capsule=claim.capsule, operation_id="resume-1",
        resumes_operation_id="action-1", gateway=good_gateway,
        deadline=utc_now() - timedelta(seconds=1),
        cancellation=CancellationToken(), on_chunk=collect,
    )
    assert replay.status == "completed" and replay.envelope == resumed.envelope
    assert len(chunks) == len(good_gateway.requests) == 1
    next_claim = await prepare_campaign_source_player_action(
        store=store, session_id="campaign-1", operation_id="action-2",
        player_input="Espero", config=config,
        deadline=utc_now() + timedelta(seconds=30), cancellation=CancellationToken(),
    )
    assert next_claim.capsule is not None
    assert next_claim.capsule.snapshot.progression.record == "warned"


@pytest.mark.asyncio
async def test_concurrent_claims_and_generic_commit_cannot_bypass_campaign_contract(tmp_path):
    db = tmp_path / "campaign.sqlite3"
    store = SQLitePersistence(db)
    await create_campaign_source_session(store, "campaign-1", initial_state=eligible_state())
    config, _ = config_and_gateway()
    async def claim(name):
        return await claim_campaign_source_input(
            SQLitePersistence(db), session_id="campaign-1", operation_id=name,
            player_input="Aguardo", config=config,
        )
    outcomes = await asyncio.gather(claim("action-1"), claim("action-2"),
                                    return_exceptions=True)
    assert sum(getattr(item, "newly_claimed", False) for item in outcomes) == 1
    assert sum(isinstance(item, CampaignSourceStorageError)
               and item.code == "campaign_source_session_busy" for item in outcomes) == 1
    accepted = next(item for item in outcomes if getattr(item, "newly_claimed", False))
    assert accepted.request.snapshot.current_turn == 0
    draft = prepare_source_turn_draft(
        accepted.request.snapshot, operation_id=accepted.request.operation_id,
        created_at=accepted.request.created_at, player_input="Aguardo",
        preparation=DeclaredActionPreparation(),
    )
    with pytest.raises(CampaignSourceStorageError, match="campaign_source_commit_contract_required"):
        await store.commit_turn(
            session_id="campaign-1", operation_id="bypass", turn_id=draft.turn_id,
            attempt_id="bypass-attempt", turn_number=1, base_revision=0,
            base_state_revision=0, state=accepted.request.state,
            narrative=NarrativeRecord(
                narrative_id="bypass-narrative", session_id="campaign-1",
                turn_id=draft.turn_id, created_at=utc_now(), text=N,
                source_event_ids=(draft.events[0].event_id,), invocation_id="bypass-invocation",
                visibility=Visibility.PLAYER,
            ),
            facts=draft.facts, events=draft.events, user_input="Aguardo", relationships={},
        )
    assert (await read_campaign_source_snapshot(store, "campaign-1")).current_turn == 0


@pytest.mark.asyncio
async def test_second_gate_blocks_rng_and_leaves_no_campaign_effect(tmp_path, monkeypatch):
    import api.campaign_source_input_service as service
    import api.rules_service as rules
    store = SQLitePersistence(tmp_path / "campaign.sqlite3")
    await create_campaign_source_session(store, "campaign-1", initial_state=eligible_state())
    checks = []
    async def gate(*_args):
        checks.append(1)
        return len(checks) == 1
    monkeypatch.setattr(service, "_gate_allows", gate)
    monkeypatch.setattr(rules, "calculate_resolution", lambda *_a, **_kw: pytest.fail("RNG"))
    config, _ = config_and_gateway()
    result = await prepare_campaign_source_player_action(
        store=store, session_id="campaign-1", operation_id="inspect-1",
        player_input="Examino o registro", config=config,
        deadline=utc_now() + timedelta(seconds=30), cancellation=CancellationToken(),
    )
    assert len(checks) == 2
    assert result.status == "failed" and result.error_code == "campaign_source_gate_blocked"
    assert result.capsule is None
    assert (await read_campaign_source_snapshot(store, "campaign-1")).progression.record == "threatened"


@pytest.mark.asyncio
async def test_mechanical_receipt_is_not_rolled_again_after_h_failure_or_resume(tmp_path, monkeypatch):
    import api.rules_service as rules
    calls = []
    def calculate(_action, *, current_hunger, dice_pool):
        calls.append((current_hunger, dice_pool))
        return ResolutionResult(
            successes=3, is_success=True, bestial_failure=False,
            messy_critical=False, summary="Investigação bem-sucedida.",
            normal_rolls=[8, 8, 8, 5, 4], hunger_rolls=[], margin=0,
        )
    monkeypatch.setattr(rules, "calculate_resolution", calculate)
    db = tmp_path / "campaign.sqlite3"
    store = SQLitePersistence(db)
    await create_campaign_source_session(store, "campaign-1", initial_state=eligible_state())
    config, bad = config_and_gateway(RECOVERED, ("campaign.content.recovered",), "")
    bad.failure_category = ErrorCategory.PROVIDER_UNAVAILABLE
    prepared = await prepare_campaign_source_player_action(
        store=store, session_id="campaign-1", operation_id="inspect-1",
        player_input="Examino o registro", config=config,
        deadline=utc_now() + timedelta(seconds=30), cancellation=CancellationToken(),
    )
    assert calls == [(0, 5)] and prepared.capsule.campaign_effect.rule_id == "R-07"
    async def collect(_text):
        pass
    failed = await execute_campaign_source_turn(
        store=store, capsule=prepared.capsule, operation_id="inspect-1", gateway=bad,
        deadline=utc_now() + timedelta(seconds=30), cancellation=CancellationToken(),
        on_chunk=collect,
    )
    assert failed.status == "failed"
    assert (await prepare_campaign_source_player_action(
        store=store, session_id="campaign-1", operation_id="inspect-1",
        player_input="Examino o registro", config=config,
        deadline=utc_now() + timedelta(seconds=30), cancellation=CancellationToken(),
    )).capsule == prepared.capsule
    store = SQLitePersistence(db)
    _, good = config_and_gateway(RECOVERED, ("campaign.content.recovered",), "")
    resumed = await execute_campaign_source_turn(
        store=store, capsule=prepared.capsule, operation_id="resume-1",
        resumes_operation_id="inspect-1", gateway=good,
        deadline=utc_now() + timedelta(seconds=30), cancellation=CancellationToken(),
        on_chunk=collect,
    )
    assert resumed.status == "completed", resumed.error_code
    assert calls == [(0, 5)]
    assert (await read_campaign_source_snapshot(store, "campaign-1")).progression.outcome == "partial"


@pytest.mark.asyncio
async def test_delivery_failure_rolls_back_source_effect_and_can_resume(tmp_path):
    db = tmp_path / "campaign.sqlite3"
    store = SQLitePersistence(db)
    await create_campaign_source_session(store, "campaign-1", initial_state=eligible_state())
    config, gateway = config_and_gateway()
    prepared = await prepare_campaign_source_player_action(
        store=store, session_id="campaign-1", operation_id="action-1",
        player_input="Aguardo", config=config,
        deadline=utc_now() + timedelta(seconds=30), cancellation=CancellationToken(),
    )
    async def broken(_text):
        assert (await read_campaign_source_snapshot(store, "campaign-1")).current_turn == 0
        raise RuntimeError("transport disconnected")
    failed = await execute_campaign_source_turn(
        store=store, capsule=prepared.capsule, operation_id="action-1",
        gateway=gateway, deadline=utc_now() + timedelta(seconds=30),
        cancellation=CancellationToken(), on_chunk=broken,
    )
    assert failed.status == "failed" and failed.error_code == "campaign_source_delivery_failed"
    assert (await read_campaign_source_snapshot(store, "campaign-1")).progression.record == "threatened"
    assert await store.list_turns("campaign-1") == []
    store = SQLitePersistence(db)
    _, retry_gateway = config_and_gateway()
    chunks = []
    async def collect(text):
        chunks.append(text)
    resumed = await execute_campaign_source_turn(
        store=store, capsule=prepared.capsule, operation_id="resume-1",
        resumes_operation_id="action-1", gateway=retry_gateway,
        deadline=utc_now() + timedelta(seconds=30),
        cancellation=CancellationToken(), on_chunk=collect,
    )
    assert resumed.status == "completed", resumed.error_code
    assert (await read_campaign_source_snapshot(store, "campaign-1")).progression.record == "warned"
    assert len(chunks) == 1


@pytest.mark.asyncio
async def test_restart_recovers_pending_h_and_resumes_same_capsule(tmp_path):
    db = tmp_path / "campaign.sqlite3"
    store = SQLitePersistence(db)
    await create_campaign_source_session(store, "campaign-1", initial_state=eligible_state())
    config, gateway = config_and_gateway()
    prepared = await prepare_campaign_source_player_action(
        store=store, session_id="campaign-1", operation_id="action-1",
        player_input="Aguardo", config=config,
        deadline=utc_now() + timedelta(seconds=30), cancellation=CancellationToken(),
    )
    pending = await claim_campaign_narrative(
        store, capsule=prepared.capsule, operation_id="action-1",
    )
    assert pending.status == "pending"
    reopened = SQLitePersistence(db)
    assert await reopened.recover_pending_attempts(
        started_before=utc_now() + timedelta(seconds=5)) == 1
    status = await read_campaign_source_status(reopened, "campaign-1", "action-1")
    assert status.narrative_status == "cancelled"
    assert status.resume_from_operation_id == "action-1"
    assert await load_campaign_source_capsule(reopened, "campaign-1", "action-1") == prepared.capsule
    async def collect(_text):
        pass
    resumed = await execute_campaign_source_turn(
        store=reopened, capsule=prepared.capsule, operation_id="resume-1",
        resumes_operation_id="action-1", gateway=gateway,
        deadline=utc_now() + timedelta(seconds=30), cancellation=CancellationToken(),
        on_chunk=collect,
    )
    assert resumed.status == "completed", resumed.error_code
    assert (await read_campaign_source_snapshot(reopened, "campaign-1")).progression.record == "warned"


@pytest.mark.asyncio
async def test_sqlite_event_failure_rolls_back_turn_effect_and_source(tmp_path, monkeypatch):
    store = SQLitePersistence(tmp_path / "campaign.sqlite3")
    await create_campaign_source_session(store, "campaign-1", initial_state=eligible_state())
    config, gateway = config_and_gateway()
    prepared = await prepare_campaign_source_player_action(
        store=store, session_id="campaign-1", operation_id="action-1",
        player_input="Aguardo", config=config,
        deadline=utc_now() + timedelta(seconds=30), cancellation=CancellationToken(),
    )
    def fail_insert(*_args):
        raise RuntimeError("synthetic insert failure")
    monkeypatch.setattr(store, "_insert_event", fail_insert)
    chunks = []
    async def collect(text):
        chunks.append(text)
    result = await execute_campaign_source_turn(
        store=store, capsule=prepared.capsule, operation_id="action-1",
        gateway=gateway, deadline=utc_now() + timedelta(seconds=30),
        cancellation=CancellationToken(), on_chunk=collect,
    )
    assert result.status == "failed" and result.error_code == "campaign_source_commit_failed"
    assert len(chunks) == 1  # provisional delivery, not canonical confirmation
    assert await store.list_turns("campaign-1") == []
    assert await store.list_events("campaign-1") == []
    snapshot = await read_campaign_source_snapshot(store, "campaign-1")
    assert snapshot.current_turn == 0 and snapshot.progression.record == "threatened"
    status = await read_campaign_source_status(store, "campaign-1", "action-1")
    assert status.narrative_status == "failed" and status.resume_from_operation_id == "action-1"


@pytest.mark.asyncio
async def test_competing_resume_clicks_obtain_at_most_one_h_claim(tmp_path):
    db = tmp_path / "campaign.sqlite3"
    store = SQLitePersistence(db)
    await create_campaign_source_session(store, "campaign-1", initial_state=eligible_state())
    config, gateway = config_and_gateway()
    gateway.failure_category = ErrorCategory.PROVIDER_UNAVAILABLE
    prepared = await prepare_campaign_source_player_action(
        store=store, session_id="campaign-1", operation_id="action-1",
        player_input="Aguardo", config=config,
        deadline=utc_now() + timedelta(seconds=30), cancellation=CancellationToken(),
    )
    async def collect(_text):
        pass
    failed = await execute_campaign_source_turn(
        store=store, capsule=prepared.capsule, operation_id="action-1",
        gateway=gateway, deadline=utc_now() + timedelta(seconds=30),
        cancellation=CancellationToken(), on_chunk=collect,
    )
    assert failed.status == "failed"
    async def resume(name):
        return await claim_campaign_narrative(
            SQLitePersistence(db), capsule=prepared.capsule,
            operation_id=name, resumes_operation_id="action-1",
        )
    results = await asyncio.gather(resume("resume-a"), resume("resume-b"),
                                   return_exceptions=True)
    assert sum(getattr(item, "newly_claimed", False) for item in results) == 1
    assert sum(isinstance(item, CampaignSourceStorageError)
               and item.code == "campaign_source_session_busy" for item in results) == 1
    assert (await read_campaign_source_snapshot(store, "campaign-1")).current_turn == 0


@pytest.mark.asyncio
async def test_repeated_h_failures_form_one_explicit_chain_without_repreparing(tmp_path):
    db = tmp_path / "campaign.sqlite3"
    store = SQLitePersistence(db)
    await create_campaign_source_session(store, "campaign-1", initial_state=eligible_state())
    config, bad = config_and_gateway()
    bad.failure_category = ErrorCategory.PROVIDER_UNAVAILABLE
    prepared = await prepare_campaign_source_player_action(
        store=store, session_id="campaign-1", operation_id="action-1",
        player_input="Aguardo", config=config,
        deadline=utc_now() + timedelta(seconds=30), cancellation=CancellationToken(),
    )
    async def collect(_text):
        pass
    for operation, previous in (("action-1", None), ("resume-1", "action-1")):
        result = await execute_campaign_source_turn(
            store=SQLitePersistence(db), capsule=prepared.capsule, operation_id=operation,
            resumes_operation_id=previous, gateway=bad,
            deadline=utc_now() + timedelta(seconds=30),
            cancellation=CancellationToken(), on_chunk=collect,
        )
        assert result.status == "failed"
        assert (await read_campaign_source_status(store, "campaign-1", "action-1")).resume_from_operation_id == operation
        assert (await read_campaign_source_snapshot(store, "campaign-1")).current_turn == 0
    _, good = config_and_gateway()
    finished = await execute_campaign_source_turn(
        store=SQLitePersistence(db), capsule=prepared.capsule, operation_id="resume-2",
        resumes_operation_id="resume-1", gateway=good,
        deadline=utc_now() + timedelta(seconds=30),
        cancellation=CancellationToken(), on_chunk=collect,
    )
    assert finished.status == "completed"
    assert finished.envelope.original_operation_id == "action-1"
    assert (await read_campaign_source_snapshot(store, "campaign-1")).current_turn == 1
    assert len(bad.requests) == 2 and len(good.requests) == 1


@pytest.mark.asyncio
async def test_unknown_method_is_not_an_in_world_failure_and_source_cannot_grant_delta(tmp_path):
    store = SQLitePersistence(tmp_path / "campaign.sqlite3")
    await create_campaign_source_session(store, "campaign-1", initial_state=eligible_state())
    config, _ = config_and_gateway()
    claim = await prepare_campaign_source_player_action(
        store=store, session_id="campaign-1", operation_id="unsupported-1",
        player_input="Uso uma lona para desviar a água", config=config,
        deadline=utc_now() + timedelta(seconds=30), cancellation=CancellationToken(),
    )
    assert claim.status == "failed" and claim.error_code == "campaign_source_out_of_scope"
    assert claim.capsule is None
    current = await store.load_campaign("campaign-1")
    changed = dict(current["state"])
    changed["campaign_progression"] = {
        **changed["campaign_progression"], "revision": 1,
        "record": "preserved", "outcome": "preserved",
        "resolved_objectives": ["record_rescue"],
    }
    with pytest.raises(CampaignSourceStorageError, match="campaign_source_snapshot_mutation_forbidden"):
        await store.update_campaign_snapshot(
            "campaign-1", state=changed, expected_turn=0, expected_revision=0,
        )
    assert (await read_campaign_source_snapshot(store, "campaign-1")).current_turn == 0


@pytest.mark.asyncio
async def test_reconstruction_detects_turn_or_failed_h_hash_tampering(tmp_path):
    db = tmp_path / "campaign.sqlite3"
    store = SQLitePersistence(db)
    await create_campaign_source_session(store, "campaign-1", initial_state=eligible_state())
    config, gateway = config_and_gateway()
    prepared = await prepare_campaign_source_player_action(
        store=store, session_id="campaign-1", operation_id="action-1",
        player_input="Aguardo", config=config,
        deadline=utc_now() + timedelta(seconds=30), cancellation=CancellationToken(),
    )
    gateway.failure_category = ErrorCategory.PROVIDER_UNAVAILABLE
    async def collect(_text):
        pass
    assert (await execute_campaign_source_turn(
        store=store, capsule=prepared.capsule, operation_id="action-1",
        gateway=gateway, deadline=utc_now() + timedelta(seconds=30),
        cancellation=CancellationToken(), on_chunk=collect,
    )).status == "failed"
    with sqlite3.connect(db) as connection:
        connection.execute(
            "UPDATE attempts SET result_hash=? WHERE session_id=? AND operation_id=?",
            ("0" * 64, "campaign-1", "action-1"),
        )
    with pytest.raises(CampaignSourceStorageError, match="campaign_source_h_chain_invalid"):
        await read_campaign_source_status(SQLitePersistence(db), "campaign-1", "action-1")
    with sqlite3.connect(db) as connection:
        connection.execute(
            "UPDATE attempts SET result_hash=NULL WHERE session_id=? AND operation_id=?",
            ("campaign-1", "action-1"),
        )
    # A fresh, independent session proves the committed-turn digest path.
    await create_campaign_source_session(store, "campaign-2", initial_state=eligible_state())
    _, good = config_and_gateway()
    retained = await prepare_campaign_source_player_action(
        store=store, session_id="campaign-2", operation_id="action-2",
        player_input="Aguardo", config=config,
        deadline=utc_now() + timedelta(seconds=30), cancellation=CancellationToken(),
    )
    assert (await execute_campaign_source_turn(
        store=store, capsule=retained.capsule, operation_id="action-2",
        gateway=good, deadline=utc_now() + timedelta(seconds=30),
        cancellation=CancellationToken(), on_chunk=collect,
    )).status == "completed"
    with sqlite3.connect(db) as connection:
        connection.execute(
            "UPDATE turns SET usage_json=? WHERE session_id=?",
            ('{"untrusted":true}', "campaign-2"),
        )
    with pytest.raises(CampaignSourceStorageError, match="campaign_source_history_invalid"):
        await read_campaign_source_snapshot(SQLitePersistence(db), "campaign-2")
