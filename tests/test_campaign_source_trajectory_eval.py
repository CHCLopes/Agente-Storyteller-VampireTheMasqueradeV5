"""Eight authored, offline trajectories from the frozen campaign protocol.

These fixtures prove the integration can carry each causal path. They are not
model outputs and do not constitute narrator admission or human acceptance.
"""
from datetime import timedelta

import pytest

from api.campaign_source_profile import CampaignSourceProfileError
from api.campaign_source_execution_service import execute_campaign_source_turn
from api.campaign_source_input_service import prepare_campaign_source_player_action
from api.campaign_progression_service import build_campaign_narrator_packet
from api.campaign_source_profile import _PolicyView, validate_campaign_source_proposal
from api.scene_director_service import expected_narrative_outcome, validate_scene_continuation
from api.campaign_source_storage import create_campaign_source_session, read_campaign_source_snapshot
from api.campaign_source_offline_corpus import PROSE
from api.llm.contract import CancellationToken, utc_now
from api.persistence import SQLitePersistence
from api.rules_service import ResolutionResult
from test_campaign_source_integration import config_and_gateway
from test_narrative_source_input_service import state as eligible_state


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

COUNTERPROOFS = {
    ("CAMP-EVAL-03", 1): ("NEG-01", "A luz muda de tom nas paredes do Arquivo. Mara contempla a poeira da bancada e escuta um ruído distante. O ar parece imóvel, e a cena não mostra qualquer mudança. Nada de relevante acontece durante esse intervalo."),
    ("CAMP-EVAL-02", 2): ("NEG-02", PROSE["R-03B"] + " O registro voltou a ficar intacto e seco."),
    ("CAMP-EVAL-07", 1): ("NEG-03", PROSE["R-08"] + " O exame recuperou o conteúdo integral."),
    ("CAMP-EVAL-01", 1): ("NEG-04", PROSE["R-01"] + " Você retira o registro da bancada."),
    ("CAMP-EVAL-08", 1): ("NEG-05", PROSE["R-02"] + " A fundadora é Helena."),
    ("CAMP-EVAL-01", 2): ("NEG-06", PROSE["R-05"] + " Agora precisa voltar a salvar o registro."),
    ("CAMP-EVAL-05", 1): ("NEG-09", PROSE["R-05"].replace("na superfície seca", "junto à bancada")),
}


@pytest.mark.asyncio
@pytest.mark.parametrize("case_id,inputs,rules,outcome", CASES, ids=[row[0] for row in CASES])
async def test_authored_campaign_trajectory(case_id, inputs, rules, outcome, tmp_path, monkeypatch):
    import api.rules_service as rules_service

    calls = []
    def roll(_action, *, current_hunger, dice_pool):
        calls.append((current_hunger, dice_pool))
        succeeded = case_id == "CAMP-EVAL-06"
        return ResolutionResult(
            successes=3 if succeeded else 0, is_success=succeeded,
            bestial_failure=False, messy_critical=False,
            summary="Investigação resolvida.", normal_rolls=[8, 8, 8, 5, 4]
            if succeeded else [2, 2, 2, 3, 4], hunger_rolls=[],
            margin=0 if succeeded else -3,
        )
    monkeypatch.setattr(rules_service, "calculate_resolution", roll)
    db = tmp_path / "campaign.sqlite3"
    store = SQLitePersistence(db)
    await create_campaign_source_session(store, case_id, initial_state=eligible_state())
    for number, (player_input, rule_id) in enumerate(zip(inputs, rules), 1):
        store = SQLitePersistence(db)  # reconstruct source and effect every turn
        snapshot = await read_campaign_source_snapshot(store, case_id)
        assert snapshot.current_turn == number - 1
        assert snapshot.progression.record_location == "bench"
        terminal = number == len(inputs)
        config, gateway = config_and_gateway(
            PROSE[rule_id], ("placeholder",), "" if terminal else "O que você faz agora?",
        )
        prepared = await prepare_campaign_source_player_action(
            store=store, session_id=case_id, operation_id=f"{case_id}-{number}",
            player_input=player_input, config=config,
            deadline=utc_now() + timedelta(seconds=30), cancellation=CancellationToken(),
        )
        assert prepared.capsule is not None, (case_id, number, prepared.error_code)
        assert prepared.capsule.campaign_effect.rule_id == rule_id
        packet = prepared.capsule.campaign_effect.beat
        gateway.structured_payload["realized_effects"] = packet.effect_keys
        validate_scene_continuation(
            _PolicyView(
                narrative=PROSE[rule_id],
                player_prompt="" if terminal else "O que você faz agora?",
                outcome=expected_narrative_outcome(prepared.capsule.draft.facts),
                location=prepared.capsule.snapshot.canonical_scene.location,
                npcs_present=prepared.capsule.snapshot.canonical_scene.npcs_present,
            ),
            facts=prepared.capsule.draft.facts,
            current_scene=prepared.capsule.snapshot.canonical_scene,
            player_input=player_input,
            require_player_prompt=not terminal,
        )
        validate_campaign_source_proposal(
            gateway.structured_payload,
            packet=build_campaign_narrator_packet(
                prepared.capsule.campaign_request, prepared.capsule.campaign_effect),
            facts=prepared.capsule.draft.facts, snapshot=prepared.capsule.snapshot,
        )
        counterproof = COUNTERPROOFS.get((case_id, number))
        if counterproof:
            negative_id, negative_narrative = counterproof
            try:
                validate_campaign_source_proposal(
                    {**gateway.structured_payload, "n": negative_narrative},
                    packet=build_campaign_narrator_packet(
                        prepared.capsule.campaign_request, prepared.capsule.campaign_effect),
                    facts=prepared.capsule.draft.facts, snapshot=prepared.capsule.snapshot,
                )
            except CampaignSourceProfileError:
                pass
            else:
                pytest.fail(f"{negative_id} was admitted")
        delivered = []
        async def on_chunk(text):
            delivered.append(text)
        result = await execute_campaign_source_turn(
            store=store, capsule=prepared.capsule, operation_id=f"{case_id}-{number}",
            gateway=gateway, deadline=utc_now() + timedelta(seconds=30),
            cancellation=CancellationToken(), on_chunk=on_chunk,
        )
        assert result.status == "completed", (case_id, number, result.error_code)
        assert len(delivered) == len(gateway.requests) == 1
    final = await read_campaign_source_snapshot(store, case_id)
    assert final.progression.outcome == outcome
    assert final.progression.record_location == (
        "dry_surface" if rules[-1] in {"R-05", "R-06"} else "bench")
    assert final.current_turn == len(inputs)
    assert len(calls) == sum(value == "Examino o registro" for value in inputs)
