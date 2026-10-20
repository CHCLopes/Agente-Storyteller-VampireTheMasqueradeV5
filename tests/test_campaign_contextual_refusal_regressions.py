"""L60: bounded anaphoric refusal binds to the prepared founder question."""
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
from scripts.run_campaign_source_offline_trial import _initial_state
from test_campaign_source_integration import config_and_gateway

OBSERVED='Mara ergue os olhos, mas não cede. “Não vou divulgar essa identidade.” Na bancada baixa do Arquivo, o registro continua ameaçado, ao alcance da atenção da cena. Ela volta o olhar para as páginas, reservada, sem acrescentar explicações.'
NATURAL=OBSERVED.replace('ao alcance da atenção da cena', 'perto das marcas de umidade')

@pytest.mark.asyncio
@pytest.mark.parametrize('variant',['observed','natural','wrong_referent','no_refusal','leak','player_action','hypothetical'])
async def test_contextual_refusal_binding_atomicity_restart_replay(tmp_path,monkeypatch,variant):
    def forbidden(*a,**k):pytest.fail('refusal/replay must not roll')
    monkeypatch.setattr(rules_service,'calculate_resolution',forbidden)
    text=OBSERVED if variant=='observed' else NATURAL
    if variant=='wrong_referent':text=text.replace('essa identidade','essa superfície')
    if variant=='no_refusal':text=text.replace('Não vou divulgar','Vou divulgar')
    if variant=='leak':text+=' A fundadora é Helena.'
    if variant=='player_action':text+=' Você abre a porta.'
    if variant=='hypothetical':text=text.replace('Mara ergue os olhos, mas não cede.', 'Se Mara dissesse:')
    accepted=variant in {'observed','natural'}
    db=tmp_path/'refusal.sqlite3';store=SQLitePersistence(db)
    await create_campaign_source_session(store,'refusal',initial_state=_initial_state())
    config,gateway=config_and_gateway(text,('mara.refuses.founder_identity',),'O que você faz agora?')
    prepared=await prepare_campaign_source_player_action(store=store,session_id='refusal',operation_id='refuse',
        player_input='Quem é a fundadora?',config=config,deadline=utc_now()+timedelta(seconds=60),cancellation=CancellationToken())
    c=prepared.capsule;packet=build_campaign_narrator_packet(c.campaign_request,c.campaign_effect)
    assert not _realizes_rule(OBSERVED,packet.model_copy(update={'player_input':'Qual é a tarefa?'}))
    chunks=[]
    async def deliver(text):chunks.append(text)
    result=await execute_campaign_source_turn(store=store,capsule=c,operation_id='refuse',gateway=gateway,
        deadline=utc_now()+timedelta(seconds=60),cancellation=CancellationToken(),on_chunk=deliver)
    restarted=SQLitePersistence(db);snapshot=await read_campaign_source_snapshot(restarted,'refusal')
    assert snapshot.progression.record=='threatened' and snapshot.progression.outcome is None
    if accepted:
        assert result.status=='completed' and snapshot.current_turn==1
        replay=await execute_campaign_source_turn(store=restarted,capsule=c,operation_id='refuse',gateway=gateway,
            deadline=utc_now()-timedelta(seconds=1),cancellation=CancellationToken(),on_chunk=deliver)
        assert replay.envelope==result.envelope and len(chunks)==1
    else:
        assert result.status=='failed' and snapshot.current_turn==0 and not chunks
    assert len(gateway.requests)==1
