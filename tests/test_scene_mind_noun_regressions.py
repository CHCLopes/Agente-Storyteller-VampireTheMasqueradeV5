"""L76: em mente names the mind, not the action mentir."""
import pytest
from api.narrative_source_profile import validate_source_proposal
from api.scene_director_service import SceneProposalError
from api.scene_service import SceneState

OBSERVED='Mara olha para o registro ameaçado sobre a bancada baixa do Arquivo e aponta para a passagem da Galeria. “A água pode alcançar as páginas se ele continuar aqui. A superfície seca da Galeria é o lugar mais seguro para o registro por enquanto. Se você for ajudar, tenha isso em mente.”'

def check(text):
    return validate_source_proposal({'n':text,'q':'O que você faz agora?'}, facts=(),
        current_scene=SceneState(location='Arquivo',npcs_present=('Mara',)),
        player_input='Como posso ajudar?',npc_aliases=('Mara',))

def test_observed_mind_noun():
    assert check(OBSERVED).narrative == OBSERVED

@pytest.mark.parametrize('extra', [' Você mente para Mara.', ' Você mentiu para Mara.',
    ' Você oculta o registro.', ' Você abre a porta.', ' Você mente e mantém isso em mente.'])
def test_real_actions_remain_rejected(extra):
    with pytest.raises(SceneProposalError,match='scene_player_agency_violation'):
        check(OBSERVED+extra)

@pytest.mark.asyncio
@pytest.mark.parametrize('extra', ['', ' Você mente para Mara.'])
async def test_task_commit_restart_replay_or_atomic_rejection(tmp_path,monkeypatch,extra):
    from datetime import timedelta
    from api import rules_service
    from api.campaign_source_execution_service import execute_campaign_source_turn
    from api.campaign_source_input_service import prepare_campaign_source_player_action
    from api.campaign_source_storage import create_campaign_source_session,read_campaign_source_snapshot
    from api.llm.contract import CancellationToken,utc_now
    from api.persistence import SQLitePersistence
    from scripts.run_campaign_source_offline_trial import _initial_state
    from test_campaign_source_integration import config_and_gateway
    def forbidden(*a,**kw):pytest.fail('task/replay must not roll')
    monkeypatch.setattr(rules_service,'calculate_resolution',forbidden)
    db=tmp_path/'mind.sqlite3';store=SQLitePersistence(db)
    await create_campaign_source_session(store,'mind',initial_state=_initial_state())
    config,gateway=config_and_gateway(OBSERVED+extra,
        ('mara.replies.to_task','campaign.knows.safe_surface'),'O que você faz agora?')
    prepared=await prepare_campaign_source_player_action(store=store,session_id='mind',operation_id='task',
        player_input='Como posso ajudar?',config=config,deadline=utc_now()+timedelta(seconds=60),cancellation=CancellationToken())
    chunks=[]
    async def deliver(value):chunks.append(value)
    result=await execute_campaign_source_turn(store=store,capsule=prepared.capsule,operation_id='task',gateway=gateway,
        deadline=utc_now()+timedelta(seconds=60),cancellation=CancellationToken(),on_chunk=deliver)
    restarted=SQLitePersistence(db);snapshot=await read_campaign_source_snapshot(restarted,'mind')
    assert snapshot.progression.record=='threatened' and snapshot.progression.outcome is None
    if extra:
        assert result.status=='failed' and snapshot.current_turn==0 and not chunks
    else:
        assert result.status=='completed' and snapshot.current_turn==1
        replay=await execute_campaign_source_turn(store=restarted,capsule=prepared.capsule,operation_id='task',gateway=gateway,
            deadline=utc_now()-timedelta(seconds=1),cancellation=CancellationToken(),on_chunk=deliver)
        assert replay.envelope==result.envelope and len(chunks)==1
    assert len(gateway.requests)==1
