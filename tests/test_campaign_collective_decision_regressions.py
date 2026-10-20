"""L32: NPC speech cannot silently include the player in a decision."""
from datetime import timedelta
import pytest
from api import rules_service
from api.scene_director_service import SceneProposalError
from api.campaign_source_execution_service import execute_campaign_source_turn
from api.campaign_source_input_service import prepare_campaign_source_player_action
from api.campaign_source_storage import create_campaign_source_session, read_campaign_source_snapshot
from api.llm.contract import CancellationToken, utc_now
from api.persistence import SQLitePersistence
from scripts.run_campaign_source_offline_trial import _initial_state
from test_campaign_source_integration import config_and_gateway
from test_scene_pending_decision_regressions import check

OBSERVED='Mara olha para a bancada baixa onde o registro ameaçado permanece e responde com cautela: “Você pode ajudar evitando que o risco aumente enquanto decidimos o próximo passo. A bancada do Arquivo não é uma superfície segura para o registro; se precisarmos apoiá-lo em outro lugar, a superfície seca na Galeria é a opção indicada.”'
SAFE=OBSERVED.replace(' enquanto decidimos o próximo passo','')


def test_observed_collective_choice_stays_rejected():
    with pytest.raises(SceneProposalError,match='scene_player_agency_violation'):
        check(OBSERVED)


def test_offer_without_collective_choice_is_valid():
    assert check(SAFE).narrative==SAFE


@pytest.mark.asyncio
@pytest.mark.parametrize('unsafe',[False,True])
async def test_r01_atomic_rejection_or_commit_and_restart(tmp_path,monkeypatch,unsafe):
    def forbidden(*a,**kw):pytest.fail('help/replay must not roll')
    monkeypatch.setattr(rules_service,'calculate_resolution',forbidden)
    db=tmp_path/'collective.sqlite3';store=SQLitePersistence(db)
    await create_campaign_source_session(store,'collective',initial_state=_initial_state())
    config,gateway=config_and_gateway(OBSERVED if unsafe else SAFE,('mara.replies.to_task','campaign.knows.safe_surface'),'O que você faz agora?')
    prepared=await prepare_campaign_source_player_action(store=store,session_id='collective',operation_id='help',player_input='Como posso ajudar?',config=config,deadline=utc_now()+timedelta(seconds=60),cancellation=CancellationToken())
    c=prepared.capsule;chunks=[]
    async def deliver(text):chunks.append(text)
    result=await execute_campaign_source_turn(store=store,capsule=c,operation_id='help',gateway=gateway,deadline=utc_now()+timedelta(seconds=60),cancellation=CancellationToken(),on_chunk=deliver)
    restarted=SQLitePersistence(db);snapshot=await read_campaign_source_snapshot(restarted,'collective')
    if unsafe:
        assert result.status=='failed' and result.error_code=='campaign_source_policy_failed'
        assert snapshot.current_turn==0 and not snapshot.sources and not chunks
    else:
        assert result.status=='completed' and snapshot.current_turn==1
        replay=await execute_campaign_source_turn(store=restarted,capsule=c,operation_id='help',gateway=gateway,deadline=utc_now()-timedelta(seconds=1),cancellation=CancellationToken(),on_chunk=deliver)
        assert replay.envelope==result.envelope and len(chunks)==1
    assert len(gateway.requests)==1
