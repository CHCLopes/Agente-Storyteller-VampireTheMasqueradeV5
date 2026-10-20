"""L9: preserved document parts do not assert player departure."""
from datetime import timedelta

import pytest

from api import rules_service
from api.scene_director_service import _action_signature_matches
from api.campaign_source_execution_service import execute_campaign_source_turn
from api.campaign_source_input_service import prepare_campaign_source_player_action
from api.campaign_source_storage import create_campaign_source_session, read_campaign_source_snapshot
from api.llm.contract import CancellationToken, utc_now
from api.persistence import SQLitePersistence
from scripts.preflight_hybrid_campaign_luna_l9 import _fixed_resolution
from test_campaign_source_integration import config_and_gateway
from test_narrative_source_input_service import state


OBSERVED = 'Você examina o registro sobre a bancada baixa do Arquivo e consegue recuperar informação útil entre as partes preservadas. O conteúdo revela uma pista relevante para compreender o documento, mas o registro permanece apenas parcialmente restaurado. Mara se inclina sobre a bancada, mantendo os olhos nas páginas incompletas. “Isso já nos dá algo concreto”, ela diz, em voz baixa. “Mas ainda há lacunas demais para considerar o registro inteiro recuperado.” O registro permanece na bancada, intacto em sua posição, enquanto a descoberta é incorporada ao que vocês já sabem.'


def departures(text):
    return [m.group() for _, family, m in _action_signature_matches(text) if family == 'depart']


def test_nominal_parts_are_not_departure():
    assert departures(OBSERVED) == []


@pytest.mark.parametrize('text', [
    'Você parte do Arquivo.',
    'Você partes para a Galeria.',
    'Você examina entre as partes preservadas e parte do Arquivo.',
    'Entre as partes preservadas, você parte do Arquivo.',
    'Você parte entre as partes preservadas.',
])
def test_real_or_ambiguous_departure_is_not_waived(text):
    assert departures(text)


@pytest.mark.asyncio
@pytest.mark.parametrize('unsafe', [False, True])
async def test_exact_r07_commit_and_unauthorized_departure_rollback(tmp_path, monkeypatch, unsafe):
    monkeypatch.setattr(rules_service, 'calculate_resolution', lambda *_a, **_kw: _fixed_resolution(True))
    store = SQLitePersistence(tmp_path / 'parts.sqlite3')
    await create_campaign_source_session(store, 'parts', initial_state=state())
    text = OBSERVED + (' Você parte do Arquivo.' if unsafe else '')
    config, gateway = config_and_gateway(text, ('campaign.content.recovered',), '')
    prepared = await prepare_campaign_source_player_action(
        store=store, session_id='parts', operation_id='parts-1', player_input='Examino o registro',
        config=config, deadline=utc_now()+timedelta(seconds=60), cancellation=CancellationToken())
    assert prepared.capsule.campaign_effect.rule_id == 'R-07'
    delivered = []
    async def deliver(chunk):
        delivered.append(chunk)
    result = await execute_campaign_source_turn(
        store=store, capsule=prepared.capsule, operation_id='parts-1', gateway=gateway,
        deadline=utc_now()+timedelta(seconds=60), cancellation=CancellationToken(), on_chunk=deliver)
    snapshot = await read_campaign_source_snapshot(store, 'parts')
    if unsafe:
        assert result.status == 'failed' and result.error_code == 'campaign_source_policy_failed'
        assert snapshot.current_turn == 0 and not snapshot.sources and not delivered
    else:
        assert result.status == 'completed'
        assert snapshot.current_turn == 1 and snapshot.progression.outcome == 'partial'
        assert delivered
        def forbidden_roll(*_a, **_kw):
            pytest.fail('replay may not reroll')
        monkeypatch.setattr(rules_service, 'calculate_resolution', forbidden_roll)
        restarted = SQLitePersistence(tmp_path / 'parts.sqlite3')
        replay = await execute_campaign_source_turn(
            store=restarted, capsule=prepared.capsule, operation_id='parts-1', gateway=gateway,
            deadline=utc_now()-timedelta(seconds=1), cancellation=CancellationToken(), on_chunk=deliver)
        assert replay.status == 'completed' and replay.envelope == result.envelope
        assert len(gateway.requests) == 1 and len(delivered) == 1
