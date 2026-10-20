"""L21: explicit evident threat can realize the initial dry-record warning."""
from datetime import timedelta
import pytest
from api import rules_service
from api.campaign_progression_service import build_campaign_narrator_packet
from api.campaign_source_profile import _realizes_rule
from api.campaign_source_execution_service import execute_campaign_source_turn
from api.campaign_source_input_service import prepare_campaign_source_player_action
from api.campaign_source_storage import create_campaign_source_session, read_campaign_source_snapshot
from api.llm.contract import CancellationToken, utc_now
from api.persistence import SQLitePersistence
from test_campaign_source_integration import config_and_gateway
from test_narrative_source_input_service import state

OBSERVED = 'O tempo passa no Arquivo, e a infiltração se espalha pelas frestas próximas à bancada baixa. O registro permanece seco, mas a ameaça agora é evidente. Mara acompanha a umidade avançando pela parede e finalmente quebra o silêncio: “Está piorando. Se chegar até aqui, o registro pode não continuar protegido.” A postura dela se torna vigilante, enquanto o registro permanece na bancada baixa no Arquivo.'
QUESTION = 'O que você faz diante do risco imediato?'

async def prepare(tmp_path):
    db=tmp_path/'warning.sqlite3'
    store=SQLitePersistence(db)
    await create_campaign_source_session(store,'warning',initial_state=state())
    config,gateway=config_and_gateway(OBSERVED,('campaign.warning.visible',),QUESTION)
    p=await prepare_campaign_source_player_action(store=store,session_id='warning',operation_id='warning-1',
        player_input='Aguardo',config=config,deadline=utc_now()+timedelta(seconds=60),cancellation=CancellationToken())
    assert p.capsule.campaign_effect.rule_id=='R-03'
    return store,db,p.capsule,config,gateway

@pytest.mark.asyncio
@pytest.mark.parametrize('text,accepted',[
    (OBSERVED,True),
    (OBSERVED.replace('a ameaça agora é evidente','a ameaça agora não é evidente'),False),
    (OBSERVED.replace('a ameaça agora é evidente','não há ameaça'),False),
    (OBSERVED.replace('O registro permanece seco','O registro foi molhado'),False),
    (OBSERVED.replace('Mara acompanha','Mara não avisa e acompanha'),False),
    (OBSERVED.replace('Mara','Alguém'),False),
])
async def test_warning_equivalence_preserves_contradictions(tmp_path,text,accepted):
    _,_,capsule,_,_=await prepare(tmp_path)
    packet=build_campaign_narrator_packet(capsule.campaign_request,capsule.campaign_effect)
    assert _realizes_rule(text,packet) is accepted

@pytest.mark.asyncio
@pytest.mark.parametrize('unsafe',[False,True])
async def test_warning_commit_or_atomic_rejection_and_replay(tmp_path,monkeypatch,unsafe):
    def forbidden_roll(*_a,**_kw):pytest.fail('wait/replay may not roll')
    monkeypatch.setattr(rules_service,'calculate_resolution',forbidden_roll)
    store,db,capsule,config,_=await prepare(tmp_path)
    _,gateway=config_and_gateway(OBSERVED+(' Você abre a porta.' if unsafe else ''),('campaign.warning.visible',),QUESTION)
    chunks=[]
    async def deliver(text):chunks.append(text)
    result=await execute_campaign_source_turn(store=store,capsule=capsule,operation_id='warning-1',gateway=gateway,
        deadline=utc_now()+timedelta(seconds=60),cancellation=CancellationToken(),on_chunk=deliver)
    restarted=SQLitePersistence(db)
    snapshot=await read_campaign_source_snapshot(restarted,'warning')
    if unsafe:
        assert result.status=='failed' and result.error_code=='campaign_source_policy_failed'
        assert snapshot.current_turn==0 and snapshot.progression.record=='threatened' and not snapshot.sources and not chunks
    else:
        assert result.status=='completed' and snapshot.current_turn==1 and snapshot.progression.record=='warned'
        replay=await execute_campaign_source_turn(store=restarted,capsule=capsule,operation_id='warning-1',gateway=gateway,
            deadline=utc_now()-timedelta(seconds=1),cancellation=CancellationToken(),on_chunk=deliver)
        assert replay.envelope==result.envelope and len(chunks)==1
    assert len(gateway.requests)==1
