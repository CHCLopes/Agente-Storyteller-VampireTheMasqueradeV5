"""L34: explicit no-content recovery honors failure; water arrival is not success."""
from datetime import timedelta
import pytest
from api import rules_service
from api.scene_director_service import SceneProposalError, validate_mechanical_narrative
from api.campaign_source_execution_service import execute_campaign_source_turn
from api.campaign_source_input_service import prepare_campaign_source_player_action
from api.campaign_source_storage import create_campaign_source_session, read_campaign_source_snapshot
from api.llm.contract import CancellationToken, utc_now
from api.persistence import SQLitePersistence
from scripts.preflight_hybrid_campaign_luna_l34 import _fixed_resolution
from scripts.run_campaign_source_offline_trial import _initial_state
from test_campaign_source_integration import config_and_gateway

OBSERVED='Ao examinar o registro na bancada baixa do Arquivo, a investigação não recupera conteúdo algum. A umidade alcança as páginas e o registro fica molhado sobre a bancada, comprometendo o que ainda pudesse ser lido. Nenhuma informação nova se torna conhecida, e a tensão no ambiente aumenta enquanto o conteúdo permanece inacessível.'


def test_exact_failed_recovery_honors_failure():
    validate_mechanical_narrative(OBSERVED,outcome='failure',player_input='Examino o registro')


def test_water_alone_is_not_player_success():
    with pytest.raises(SceneProposalError,match='scene_success_not_honored'):
        validate_mechanical_narrative('A umidade alcança as páginas.',outcome='success')


@pytest.mark.parametrize('text',[
    OBSERVED+' Você encontra uma pista.',
    OBSERVED+' Você recupera informação útil do registro.',
    OBSERVED+' Você alcança as páginas.',
    'A tentativa falha. A umidade alcança as páginas. Você encontra a prova.',
])
def test_environment_does_not_hide_goal_grant(text):
    with pytest.raises(SceneProposalError,match='scene_failure_granted_goal'):
        validate_mechanical_narrative(text,outcome='failure',player_input='Examino o registro')


@pytest.mark.parametrize('text',[
    'A investigação recupera conteúdo algum.',
    'A investigação não recupera conteúdo algum?',
    'Mara diz: “A investigação não recupera conteúdo algum.”',
])
def test_failure_requires_assertive_negative_result(text):
    with pytest.raises(SceneProposalError,match='scene_failure_not_honored'):
        validate_mechanical_narrative(text,outcome='failure')


@pytest.mark.asyncio
@pytest.mark.parametrize('unsafe',[False,True])
async def test_r08_commit_or_reject_atomically_and_replay(tmp_path,monkeypatch,unsafe):
    rolls=[]
    def roll(*a,**kw):rolls.append(True);return _fixed_resolution(False)
    monkeypatch.setattr(rules_service,'calculate_resolution',roll)
    db=tmp_path/'failure.sqlite3';store=SQLitePersistence(db)
    await create_campaign_source_session(store,'failure',initial_state=_initial_state())
    config,gateway=config_and_gateway(OBSERVED+(' Você encontra uma pista.' if unsafe else ''),('campaign.inspect.failed',),'O que você faz agora?')
    prepared=await prepare_campaign_source_player_action(store=store,session_id='failure',operation_id='inspect',player_input='Examino o registro',config=config,deadline=utc_now()+timedelta(seconds=60),cancellation=CancellationToken())
    c=prepared.capsule;chunks=[]
    async def deliver(text):chunks.append(text)
    result=await execute_campaign_source_turn(store=store,capsule=c,operation_id='inspect',gateway=gateway,deadline=utc_now()+timedelta(seconds=60),cancellation=CancellationToken(),on_chunk=deliver)
    restarted=SQLitePersistence(db);snapshot=await read_campaign_source_snapshot(restarted,'failure')
    assert len(rolls)==1 and len(gateway.requests)==1
    if unsafe:
        assert result.status=='failed' and snapshot.current_turn==0 and not chunks
    else:
        assert result.status=='completed' and snapshot.current_turn==1
        assert snapshot.progression.record=='wet' and snapshot.progression.outcome is None
        replay=await execute_campaign_source_turn(store=restarted,capsule=c,operation_id='inspect',gateway=gateway,deadline=utc_now()-timedelta(seconds=1),cancellation=CancellationToken(),on_chunk=deliver)
        assert replay.envelope==result.envelope and len(chunks)==1
        assert len(rolls)==1 and len(gateway.requests)==1
