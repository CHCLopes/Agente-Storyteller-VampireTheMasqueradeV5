"""Natural refusal satisfies secrecy without exposing control-plane labels."""
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

REFUSAL='Mara sustenta o olhar por um instante. “Não vou divulgar a identidade da fundadora.” A água pinga perto da bancada baixa no Arquivo. O registro continua ameaçado sobre a madeira; Mara volta os olhos para o documento, sem o tocar.'
TASK='Mara aponta para a bancada baixa no Arquivo. “A água ameaça o registro. Há uma superfície seca na Galeria, onde o registro pode ficar a salvo.” O registro permanece na bancada, ainda ameaçado. Mara aguarda a próxima ação sem insistir na pergunta anterior.'
RESCUE='Você retira o registro da bancada baixa no Arquivo e o leva até a superfície seca na Galeria. O registro permanece intacto e protegido da água. Mara solta o ar devagar. “Está salvo.” O resgate se encerra, sem novas tarefas.'


async def prepare(store,operation,player_input,text,effects,question):
    config,gateway=config_and_gateway(text,effects,question)
    prepared=await prepare_campaign_source_player_action(store=store,session_id='natural',operation_id=operation,player_input=player_input,config=config,deadline=utc_now()+timedelta(seconds=60),cancellation=CancellationToken())
    return prepared.capsule,gateway


@pytest.mark.asyncio
async def test_natural_refusal_help_rescue_without_secrecy_recap(tmp_path,monkeypatch):
    def forbidden(*args,**kwargs):pytest.fail('dialogue/rescue/replay must not roll')
    monkeypatch.setattr(rules_service,'calculate_resolution',forbidden)
    db=tmp_path/'natural.sqlite3';store=SQLitePersistence(db)
    await create_campaign_source_session(store,'natural',initial_state=_initial_state())
    chunks=[]
    async def deliver(text):chunks.append(text)
    for number,(player_input,text,effects,q) in enumerate([
        ('Quem é a fundadora?',REFUSAL,('mara.refuses.founder_identity',),'O que você faz agora?'),
        ('Qual é a tarefa?',TASK,('mara.replies.to_task','campaign.knows.safe_surface'),'O que você faz agora?'),
        ('Retiro o registro',RESCUE,('campaign.record.preserved',),''),
    ],1):
        op=f'natural-{number}';c,gateway=await prepare(store,op,player_input,text,effects,q)
        result=await execute_campaign_source_turn(store=store,capsule=c,operation_id=op,gateway=gateway,deadline=utc_now()+timedelta(seconds=60),cancellation=CancellationToken(),on_chunk=deliver)
        assert result.status=='completed' and len(gateway.requests)==1
        assert all(term not in chunks[-1].casefold() for term in (
            'informação permanece protegida', 'identidade da fundadora continua protegida',
        ))
    snapshot=await read_campaign_source_snapshot(SQLitePersistence(db),'natural')
    assert snapshot.current_turn==3 and snapshot.progression.outcome=='preserved'
    assert snapshot.progression.record_location=='dry_surface'
    assert 'fundadora' not in TASK and 'fundadora' not in RESCUE
    replay=await execute_campaign_source_turn(store=SQLitePersistence(db),capsule=c,operation_id=op,gateway=gateway,deadline=utc_now()-timedelta(seconds=1),cancellation=CancellationToken(),on_chunk=deliver)
    assert replay.envelope==result.envelope and len(gateway.requests)==1 and len(chunks)==3


@pytest.mark.asyncio
@pytest.mark.parametrize('suffix',[' A fundadora é Helena.',' Você abre a porta.'])
async def test_natural_language_never_waives_secrecy_or_agency(tmp_path,monkeypatch,suffix):
    def forbidden(*args,**kwargs):pytest.fail('refusal must not roll')
    monkeypatch.setattr(rules_service,'calculate_resolution',forbidden)
    store=SQLitePersistence(tmp_path/'unsafe.sqlite3')
    await create_campaign_source_session(store,'natural',initial_state=_initial_state())
    c,gateway=await prepare(store,'unsafe','Quem é a fundadora?',REFUSAL+suffix,('mara.refuses.founder_identity',),'O que você faz agora?')
    chunks=[]
    async def deliver(text):chunks.append(text)
    result=await execute_campaign_source_turn(store=store,capsule=c,operation_id='unsafe',gateway=gateway,deadline=utc_now()+timedelta(seconds=60),cancellation=CancellationToken(),on_chunk=deliver)
    snapshot=await read_campaign_source_snapshot(store,'natural')
    assert result.status=='failed' and snapshot.current_turn==0 and not chunks
    assert len(gateway.requests)==1 and not snapshot.sources
