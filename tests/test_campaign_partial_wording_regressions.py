"""L14: explicitly salvaging still-legible content realizes partial rescue."""
from datetime import timedelta
import pytest
from api import rules_service
from api.campaign_progression_service import build_campaign_narrator_packet
from api.campaign_source_profile import _realizes_rule
from api.campaign_source_execution_service import execute_campaign_source_turn
from api.campaign_source_input_service import prepare_campaign_source_player_action
from api.campaign_source_storage import create_campaign_source_session, read_campaign_source_snapshot
from api.campaign_source_offline_corpus import PROSE
from api.llm.contract import CancellationToken, utc_now
from api.persistence import SQLitePersistence
from test_campaign_source_integration import config_and_gateway
from test_narrative_source_input_service import state

OBSERVED = 'Você retira o registro da bancada baixa no Arquivo e o leva até a superfície seca na Galeria. Ali, o que ainda permanece legível é salvo, enquanto o dano causado pela umidade continua visível e não é revertido. Mara acompanha o deslocamento sem tocar no objeto; ao vê-lo protegido do alcance da infiltração, solta o ar com cautela. “O que restou legível está a salvo”, ela diz, mantendo os olhos atentos às páginas danificadas.'

async def prepare(tmp_path,monkeypatch):
    def forbidden_roll(*_a,**_kw):pytest.fail('waiting/help/rescue/replay may not roll')
    monkeypatch.setattr(rules_service,'calculate_resolution',forbidden_roll)
    db=tmp_path/'partial.sqlite3'
    store=SQLitePersistence(db)
    await create_campaign_source_session(store,'partial',initial_state=state())
    for i,(player_input,rule,effects) in enumerate([
        ('Aguardo','R-03',('campaign.warning.visible',)),
        ('Espero','R-03B',('campaign.record.wet',)),
        ('Como posso ajudar?','R-01',('mara.replies.to_task','campaign.knows.safe_surface')),
    ],1):
        config,gateway=config_and_gateway(PROSE[rule],effects,'O que você faz agora?')
        p=await prepare_campaign_source_player_action(store=store,session_id='partial',operation_id=f'p{i}',
            player_input=player_input,config=config,deadline=utc_now()+timedelta(seconds=60),cancellation=CancellationToken())
        async def deliver(_text):pass
        r=await execute_campaign_source_turn(store=store,capsule=p.capsule,operation_id=f'p{i}',gateway=gateway,
            deadline=utc_now()+timedelta(seconds=60),cancellation=CancellationToken(),on_chunk=deliver)
        assert r.status=='completed'
    config,gateway=config_and_gateway(OBSERVED,('campaign.record.partial',),'')
    p=await prepare_campaign_source_player_action(store=store,session_id='partial',operation_id='p4',player_input='Retiro o registro',
        config=config,deadline=utc_now()+timedelta(seconds=60),cancellation=CancellationToken())
    return store,db,p.capsule,gateway

@pytest.mark.asyncio
@pytest.mark.parametrize('text,accepted',[
    (OBSERVED,True),
    ('O registro é levado à superfície seca. O conteúdo foi salvo.',False),
    ('O registro continua perdido. O que ainda permanece legível é salvo, mas o dano permanece.',False),
    ('Mara levou o registro à superfície seca; o que ainda permanece legível é salvo, com dano.',False),
])
async def test_partial_wording_requires_salvage_and_preserves_counterexamples(tmp_path,monkeypatch,text,accepted):
    _,_,c,_=await prepare(tmp_path,monkeypatch)
    packet=build_campaign_narrator_packet(c.campaign_request,c.campaign_effect)
    assert _realizes_rule(text,packet) is accepted

@pytest.mark.asyncio
@pytest.mark.parametrize('unsafe',[False,True])
async def test_exact_partial_rescue_commit_or_atomic_rejection(tmp_path,monkeypatch,unsafe):
    store,db,c,_=await prepare(tmp_path,monkeypatch)
    _,gateway=config_and_gateway(OBSERVED+(' Você abre a porta.' if unsafe else ''),('campaign.record.partial',),'')
    chunks=[]
    async def deliver(text):chunks.append(text)
    r=await execute_campaign_source_turn(store=store,capsule=c,operation_id='p4',gateway=gateway,
        deadline=utc_now()+timedelta(seconds=60),cancellation=CancellationToken(),on_chunk=deliver)
    restarted=SQLitePersistence(db)
    snapshot=await read_campaign_source_snapshot(restarted,'partial')
    if unsafe:
        assert r.status=='failed' and r.error_code=='campaign_source_policy_failed'
        assert snapshot.current_turn==3 and snapshot.progression.record=='wet' and not chunks
    else:
        assert r.status=='completed' and snapshot.current_turn==4 and snapshot.progression.outcome=='partial'
        assert snapshot.progression.record_location=='dry_surface'
        replay=await execute_campaign_source_turn(store=restarted,capsule=c,operation_id='p4',gateway=gateway,
            deadline=utc_now()-timedelta(seconds=1),cancellation=CancellationToken(),on_chunk=deliver)
        assert replay.envelope==r.envelope and len(chunks)==1
    assert len(gateway.requests)==1
