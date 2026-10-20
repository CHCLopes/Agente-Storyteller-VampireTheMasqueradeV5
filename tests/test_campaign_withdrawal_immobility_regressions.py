"""L51: withdrawal cannot impose player immobility."""
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

OBSERVED='Você desiste da tentativa no Arquivo. A aventura se encerra sem que você se desloque, e o registro permanece ameaçado sobre a bancada baixa. Mara recebe sua decisão sem insistir; por um instante, observa o registro e então baixa os olhos, aceitando o fim. “Entendo”, ela diz, em voz baixa. “Vamos deixá-lo aqui.” O ambiente volta à calma, sem que nada mais seja feito ao registro ou à situação.'
SAFE=OBSERVED.replace(' sem que você se desloque', '')


@pytest.mark.asyncio
@pytest.mark.parametrize('text,accepted',[(OBSERVED,False),(SAFE,True),(SAFE+' Você abre a porta.',False)])
async def test_withdrawal_requires_npc_and_preserves_agency(tmp_path,monkeypatch,text,accepted):
    def forbidden(*a,**k):pytest.fail('withdrawal/replay must not roll')
    monkeypatch.setattr(rules_service,'calculate_resolution',forbidden)
    db=tmp_path/'withdrawal.sqlite3';store=SQLitePersistence(db)
    await create_campaign_source_session(store,'withdrawal',initial_state=_initial_state())
    config,gateway=config_and_gateway(text,('campaign.withdrawn',),'')
    prepared=await prepare_campaign_source_player_action(store=store,session_id='withdrawal',operation_id='withdraw',player_input='Desisto',config=config,deadline=utc_now()+timedelta(seconds=60),cancellation=CancellationToken())
    c=prepared.capsule;chunks=[]
    async def deliver(text):chunks.append(text)
    result=await execute_campaign_source_turn(store=store,capsule=c,operation_id='withdraw',gateway=gateway,deadline=utc_now()+timedelta(seconds=60),cancellation=CancellationToken(),on_chunk=deliver)
    restarted=SQLitePersistence(db);snapshot=await read_campaign_source_snapshot(restarted,'withdrawal')
    if not accepted:
        assert result.status=='failed' and result.error_code=='campaign_source_policy_failed'
        assert snapshot.current_turn==0 and not chunks and snapshot.progression.outcome is None
    else:
        assert result.status=='completed' and snapshot.current_turn==1
        assert snapshot.progression.outcome=='abandoned' and snapshot.progression.record_location=='bench'
        replay=await execute_campaign_source_turn(store=restarted,capsule=c,operation_id='withdraw',gateway=gateway,deadline=utc_now()-timedelta(seconds=1),cancellation=CancellationToken(),on_chunk=deliver)
        assert replay.envelope==result.envelope and len(chunks)==1
    assert len(gateway.requests)==1
