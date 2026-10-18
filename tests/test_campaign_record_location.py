"""Versioned object position: offline authority, persistence and v1 compatibility."""
from datetime import timedelta
import json

import pytest
from pydantic import ValidationError

from api.campaign_progression_service import (
    CampaignProgressState, LegacyCampaignProgressState, read_campaign_progress_state,
    build_campaign_narrator_packet,
)
from api.campaign_source_context import create_campaign_source_origin
from api.campaign_source_storage import (
    ORIGIN_KEY, create_campaign_source_session, read_campaign_source_snapshot,
    load_campaign_source_capsule,
)
from api.campaign_source_input_service import prepare_campaign_source_player_action
from api.campaign_source_execution_service import execute_campaign_source_turn
from api.campaign_source_profile import build_campaign_source_context
from api.campaign_source_offline_corpus import PROSE
from api.narrative_source_context import create_source_context_origin
from api.scene_service import SceneState
from api.persistence import SQLitePersistence
from api.llm.contract import CancellationToken, ErrorCategory, utc_now
from test_campaign_progression_service import step, receipt
from test_campaign_source_integration import config_and_gateway
from test_narrative_source_input_service import state as eligible_state


@pytest.mark.parametrize("text,condition,success,rule,position", [
    ("Qual é a tarefa?", "threatened", None, "R-01", "bench"),
    ("Quem é a fundadora?", "threatened", None, "R-02", "bench"),
    ("Aguardo", "threatened", None, "R-03", "bench"),
    ("Aguardo", "warned", None, "R-03B", "bench"),
    ("Aguardo", "wet", None, "R-04", "bench"),
    ("Retiro o registro", "threatened", None, "R-05", "dry_surface"),
    ("Retiro o registro", "wet", None, "R-06", "dry_surface"),
    ("Examino o registro", "threatened", True, "R-07", "bench"),
    ("Examino o registro", "threatened", False, "R-08", "bench"),
    ("Examino o registro", "wet", False, "R-08", "bench"),
    ("Desisto", "wet", None, "R-09", "bench"),
])
def test_position_follows_only_authorized_rescue(text, condition, success, rule, position):
    before = CampaignProgressState(revision=0, record=condition)
    effect = step(text, before, mechanical=None if success is None else receipt(success))
    assert effect.rule_id == rule
    assert before.record_location == "bench"
    assert effect.after_state.record_location == position
    assert effect.after_state.location == before.location == "Arquivo"


def test_retained_v2_position_cannot_be_missing_or_invented():
    initial = CampaignProgressState(revision=0).model_dump(mode="json")
    for changed in ({key: value for key, value in initial.items() if key != "record_location"},
                    {**initial, "record_location": "dry_surface"},
                    {**initial, "record_location": "elsewhere"},
                    {**initial, "policy_version": "campaign-progression.v1"}):
        with pytest.raises(ValidationError):
            read_campaign_progress_state(changed)
    legacy = LegacyCampaignProgressState(revision=0).model_dump(mode="json")
    assert read_campaign_progress_state(legacy).model_dump(mode="json") == legacy
    with pytest.raises(ValidationError):
        read_campaign_progress_state({**legacy, "record_location": "bench"})


@pytest.mark.asyncio
@pytest.mark.parametrize("version", ["v1", "v2"])
@pytest.mark.parametrize("failure", ["provider", "delivery"])
async def test_rescue_restart_resume_replay_keeps_version_and_atomic_position(
        tmp_path, monkeypatch, version, failure):
    def no_rng(*args, **kwargs):
        pytest.fail("rescue/resume/replay must not roll dice")
    monkeypatch.setattr("api.rules_service.calculate_resolution", no_rng)
    db = tmp_path / "campaign.sqlite3"
    store = SQLitePersistence(db)
    if version == "v2":
        await create_campaign_source_session(store, "position", initial_state=eligible_state())
    else:
        # Synthetic legacy seed with the exact old shape, not a migrated save.
        await store.initialize()
        origin = create_campaign_source_origin(create_source_context_origin(
            "position", SceneState(location="Arquivo", npcs_present=("Mara",))),
            content_version="record-at-risk.v1")
        state = eligible_state()
        state["campaign_progression"] = LegacyCampaignProgressState(revision=0).model_dump(mode="json")
        with store._connect() as connection:
            store._insert_campaign_if_missing(connection, "position", "test", state, {},
                                              {ORIGIN_KEY: origin.model_dump(mode="json")})
            connection.commit()
    initial = await read_campaign_source_snapshot(store, "position")
    config, gateway = config_and_gateway(PROSE["R-05"], ("placeholder",), "")
    prepared = await prepare_campaign_source_player_action(
        store=store, session_id="position", operation_id="original", player_input="Retiro o registro",
        config=config, deadline=utc_now() + timedelta(seconds=30), cancellation=CancellationToken())
    capsule = prepared.capsule
    assert capsule is not None, prepared.error_code
    original_bytes = capsule.model_dump_json()
    packet = build_campaign_narrator_packet(capsule.campaign_request, capsule.campaign_effect)
    context = build_campaign_source_context(capsule.snapshot, packet)
    assert packet.state_after.content_version == f"record-at-risk.{version}"
    if version == "v2":
        assert context["record_position"]["before"] == "bench"
        assert context["record_position"]["after"] == "dry_surface"
        assert context["record_position"]["locations"]["bench"] == "bancada baixa no Arquivo"
    else:
        assert "record_position" not in context and "record_location" not in original_bytes
    gateway.structured_payload["realized_effects"] = packet.required_effects
    if failure == "provider":
        gateway.failure_category = ErrorCategory.PROVIDER_UNAVAILABLE
    async def fail_delivery(text):
        raise RuntimeError("synthetic delivery failure")
    delivered = []
    async def collect(text):
        delivered.append(text)
    failed = await execute_campaign_source_turn(
        store=store, capsule=capsule, operation_id="original", gateway=gateway,
        deadline=utc_now() + timedelta(seconds=30), cancellation=CancellationToken(),
        on_chunk=fail_delivery if failure == "delivery" else collect)
    assert failed.status == "failed"
    store = SQLitePersistence(db)
    assert (await read_campaign_source_snapshot(store, "position")).progression == initial.progression
    retained = await load_campaign_source_capsule(store, "position", "original")
    # Storage sorts dictionary keys; identity is the canonical payload/hash,
    # not the incidental insertion order of untyped fact dictionaries.
    assert retained.model_dump(mode="json") == json.loads(original_bytes)
    assert retained.fingerprint_sha256 == capsule.fingerprint_sha256
    gateway.failure_category = None
    resumed = await execute_campaign_source_turn(
        store=store, capsule=retained, operation_id="resume", resumes_operation_id="original",
        gateway=gateway, deadline=utc_now() + timedelta(seconds=30),
        cancellation=CancellationToken(), on_chunk=collect)
    assert resumed.status == "completed", resumed.error_code
    assert resumed.envelope.original_operation_id == "original"
    final = await read_campaign_source_snapshot(SQLitePersistence(db), "position")
    assert final.progression == packet.state_after and final.current_turn == 1
    if version == "v2":
        assert final.progression.record_location == "dry_surface"
    else:
        assert "record_location" not in final.progression.model_dump()
    calls = len(gateway.requests)
    replay = await execute_campaign_source_turn(
        store=SQLitePersistence(db), capsule=retained, operation_id="resume",
        resumes_operation_id="original", gateway=gateway,
        deadline=utc_now() - timedelta(seconds=1), cancellation=CancellationToken(), on_chunk=collect)
    assert replay.envelope == resumed.envelope
    assert len(gateway.requests) == calls and len(delivered) == 1
