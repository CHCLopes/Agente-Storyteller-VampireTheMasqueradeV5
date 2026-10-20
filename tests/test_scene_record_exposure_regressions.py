"""L12: avoiding record exposure does not make the player wait."""
from datetime import timedelta
import pytest
from api import rules_service
from api.narrative_source_profile import validate_source_proposal
from api.scene_director_service import SceneProposalError
from api.scene_service import SceneState
from api.campaign_source_execution_service import execute_campaign_source_turn
from api.campaign_source_input_service import prepare_campaign_source_player_action
from api.campaign_source_storage import create_campaign_source_session, read_campaign_source_snapshot
from api.llm.contract import CancellationToken, utc_now
from api.persistence import SQLitePersistence
from test_campaign_source_integration import config_and_gateway
from test_narrative_source_input_service import state

OBSERVED = 'Mara mantém os olhos na bancada baixa, onde o registro permanece ameaçado, e fala em tom calmo: “Você pode ajudar evitando que o registro permaneça exposto ao risco atual. A umidade e o contato com a bancada podem piorar sua condição; precisamos trabalhar com cuidado.” Ela aponta para a Galeria, sem tocar no objeto. “A superfície seca fica na Galeria. É o lugar seguro para apoiar o registro quando chegar a hora.” O registro continua na bancada baixa do Arquivo, intacto por enquanto, e Mara aguarda sua iniciativa.'
QUESTION = 'Que ação você toma diante do risco e da superfície seca indicada por Mara?'

def check(text):
    return validate_source_proposal({'n':text,'q':QUESTION},facts=(),
        current_scene=SceneState(location='Arquivo',npcs_present=('Mara',)),
        player_input='Como posso ajudar?',npc_aliases=('Mara',))

def test_exact_exposure_clause_does_not_make_the_player_wait():
    assert check(OBSERVED).narrative==OBSERVED

@pytest.mark.parametrize('replacement',[
    'evitando que você permaneça exposto ao risco atual.',
    'evitando que o registro permaneça exposto ao risco atual. Você espera.',
    'evitando que o registro permaneça exposto ao risco atual, você permanece no Arquivo.',
    'evitando que o registro permaneça exposto ao risco atual. Você abre a porta.',
    'evitando que o registro permaneça exposto ao risco atual e você decide ajudar.',
])
def test_player_wait_and_later_actions_remain_rejected(replacement):
    with pytest.raises(SceneProposalError,match='scene_player_agency_violation'):
        check(OBSERVED.replace('evitando que o registro permaneça exposto ao risco atual.',replacement))

@pytest.mark.asyncio
@pytest.mark.parametrize('unsafe',[False,True])
async def test_r01_commit_restart_replay_or_atomic_rejection(tmp_path,monkeypatch,unsafe):
    def forbidden_roll(*_a,**_kw):pytest.fail('help and replay may not roll')
    monkeypatch.setattr(rules_service,'calculate_resolution',forbidden_roll)
    db=tmp_path/'exposure.sqlite3'
    store=SQLitePersistence(db)
    await create_campaign_source_session(store,'exposure',initial_state=state())
    text=OBSERVED+(' Você espera.' if unsafe else '')
    config,gateway=config_and_gateway(text,('mara.replies.to_task','campaign.knows.safe_surface'),QUESTION)
    p=await prepare_campaign_source_player_action(store=store,session_id='exposure',operation_id='exposure-1',
        player_input='Como posso ajudar?',config=config,deadline=utc_now()+timedelta(seconds=60),cancellation=CancellationToken())
    chunks=[]
    async def deliver(text):chunks.append(text)
    result=await execute_campaign_source_turn(store=store,capsule=p.capsule,operation_id='exposure-1',gateway=gateway,
        deadline=utc_now()+timedelta(seconds=60),cancellation=CancellationToken(),on_chunk=deliver)
    restarted=SQLitePersistence(db)
    snapshot=await read_campaign_source_snapshot(restarted,'exposure')
    assert snapshot.progression.record=='threatened' and snapshot.progression.outcome is None
    if unsafe:
        assert result.status=='failed' and result.error_code=='campaign_source_policy_failed'
        assert snapshot.current_turn==0 and not snapshot.sources and not chunks
    else:
        assert result.status=='completed' and snapshot.current_turn==1
        replay=await execute_campaign_source_turn(store=restarted,capsule=p.capsule,operation_id='exposure-1',gateway=gateway,
            deadline=utc_now()-timedelta(seconds=1),cancellation=CancellationToken(),on_chunk=deliver)
        assert replay.envelope==result.envelope and len(chunks)==1
    assert len(gateway.requests)==1
