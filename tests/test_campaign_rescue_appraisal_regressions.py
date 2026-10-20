"""L45: concrete NPC reaction instead of asserting a new choice."""
from datetime import timedelta
import pytest
from api import rules_service
from api.campaign_source_execution_service import execute_campaign_source_turn
from api.campaign_source_input_service import prepare_campaign_source_player_action
from api.campaign_source_storage import create_campaign_source_session, read_campaign_source_snapshot
from api.llm.contract import CancellationToken, utc_now
from api.persistence import SQLitePersistence
from scripts.run_campaign_source_offline_trial import _initial_state
from test_campaign_source_integration import config_and_gateway

OBSERVED='Você leva o registro da bancada baixa no Arquivo até a superfície seca na Galeria. Ali, o registro fica protegido e intacto, afastado da ameaça. Mara observa o gesto e solta o ar, com a tensão enfim cedendo: “Está salvo. Você fez a escolha certa.” A aventura se encerra nesse ponto, com o registro preservado na superfície seca.'
SAFE=OBSERVED.replace('Você fez a escolha certa.', 'Assim a água não alcança o registro.')

@pytest.mark.asyncio
@pytest.mark.parametrize('text,accepted',[(OBSERVED,False),(SAFE,True),(SAFE+' Você abre a porta.',False)])
async def test_rescue_reaction_preserves_strict_agency_and_replay(tmp_path,monkeypatch,text,accepted):
    def forbidden(*a,**k):pytest.fail('rescue/replay must not roll')
    monkeypatch.setattr(rules_service,'calculate_resolution',forbidden)
    db=tmp_path/'rescue.sqlite3';store=SQLitePersistence(db)
    await create_campaign_source_session(store,'rescue',initial_state=_initial_state())
    config,gateway=config_and_gateway(text,('campaign.record.preserved',),'')
    prepared=await prepare_campaign_source_player_action(store=store,session_id='rescue',operation_id='rescue',
        player_input='Levo o registro até a superfície seca',config=config,
        deadline=utc_now()+timedelta(seconds=60),cancellation=CancellationToken())
    chunks=[]
    async def deliver(text):chunks.append(text)
    result=await execute_campaign_source_turn(store=store,capsule=prepared.capsule,operation_id='rescue',
        gateway=gateway,deadline=utc_now()+timedelta(seconds=60),cancellation=CancellationToken(),on_chunk=deliver)
    restarted=SQLitePersistence(db);snapshot=await read_campaign_source_snapshot(restarted,'rescue')
    if not accepted:
        assert result.status=='failed' and result.error_code=='campaign_source_policy_failed'
        assert snapshot.current_turn==0 and not chunks and snapshot.progression.outcome is None
    else:
        assert result.status=='completed' and snapshot.current_turn==1
        assert snapshot.progression.outcome=='preserved' and snapshot.progression.record_location=='dry_surface'
        replay=await execute_campaign_source_turn(store=restarted,capsule=prepared.capsule,operation_id='rescue',
            gateway=gateway,deadline=utc_now()-timedelta(seconds=1),cancellation=CancellationToken(),on_chunk=deliver)
        assert replay.envelope==result.envelope and len(chunks)==1
    assert len(gateway.requests)==1
