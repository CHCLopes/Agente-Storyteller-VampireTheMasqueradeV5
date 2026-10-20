"""L13: an atmospheric Archive clause is not a player closing action."""
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

OBSERVED = 'Você aguarda em silêncio, e o Arquivo parece se fechar ao redor da bancada baixa. A infiltração aumenta, avançando o bastante para tornar o risco imediato. Mara volta o olhar para a ameaça, mantendo-se alerta. “Não espere mais sinais”, ela diz, em tom baixo e firme. “O perigo já está aqui.” O registro permanece seco sobre a bancada baixa no Arquivo, sem mudar de posição. A tensão da sala deixa de ser apenas uma possibilidade distante; agora exige atenção cuidadosa, enquanto Mara observa o ambiente e aguarda sua decisão.'
QUESTION = 'Que ação você toma diante do risco imediato no Arquivo?'

def check(text):
    return validate_source_proposal({'n':text,'q':QUESTION},facts=(),
        current_scene=SceneState(location='Arquivo',npcs_present=('Mara',)),
        player_input='Aguardo',npc_aliases=('Mara',))

def test_exact_atmosphere_is_not_player_closing():
    assert check(OBSERVED).narrative==OBSERVED

@pytest.mark.parametrize('replacement',[
    'você parece fechar a porta ao redor da bancada baixa.',
    'o Arquivo parece se fechar ao redor da bancada baixa. Você fecha a porta.',
    'o Arquivo parece se fechar ao redor da bancada baixa, você abre a porta.',
    'o Arquivo parece se fechar ao redor da bancada baixa e você decide ajudar.',
    'o Arquivo parece se fechar ao redor da bancada baixa. Você parte do Arquivo.',
])
def test_actual_player_actions_are_not_hidden_by_atmosphere(replacement):
    with pytest.raises(SceneProposalError,match='scene_player_agency_violation'):
        check(OBSERVED.replace('o Arquivo parece se fechar ao redor da bancada baixa.',replacement))

@pytest.mark.asyncio
@pytest.mark.parametrize('unsafe',[False,True])
async def test_warning_commit_restart_replay_or_atomic_rejection(tmp_path,monkeypatch,unsafe):
    def forbidden_roll(*_a,**_kw):pytest.fail('wait and replay may not roll')
    monkeypatch.setattr(rules_service,'calculate_resolution',forbidden_roll)
    db=tmp_path/'atmosphere.sqlite3'
    store=SQLitePersistence(db)
    await create_campaign_source_session(store,'atmosphere',initial_state=state())
    config,gateway=config_and_gateway(OBSERVED+(' Você fecha a porta.' if unsafe else ''),('campaign.warning.visible',),QUESTION)
    p=await prepare_campaign_source_player_action(store=store,session_id='atmosphere',operation_id='atmosphere-1',
        player_input='Aguardo',config=config,deadline=utc_now()+timedelta(seconds=60),cancellation=CancellationToken())
    assert p.capsule.campaign_effect.rule_id=='R-03'
    chunks=[]
    async def deliver(text):chunks.append(text)
    result=await execute_campaign_source_turn(store=store,capsule=p.capsule,operation_id='atmosphere-1',gateway=gateway,
        deadline=utc_now()+timedelta(seconds=60),cancellation=CancellationToken(),on_chunk=deliver)
    restarted=SQLitePersistence(db)
    snapshot=await read_campaign_source_snapshot(restarted,'atmosphere')
    assert snapshot.progression.outcome is None
    if unsafe:
        assert result.status=='failed' and result.error_code=='campaign_source_policy_failed'
        assert snapshot.current_turn==0 and snapshot.progression.record=='threatened' and not snapshot.sources and not chunks
    else:
        assert result.status=='completed' and snapshot.current_turn==1 and snapshot.progression.record=='warned'
        replay=await execute_campaign_source_turn(store=restarted,capsule=p.capsule,operation_id='atmosphere-1',gateway=gateway,
            deadline=utc_now()-timedelta(seconds=1),cancellation=CancellationToken(),on_chunk=deliver)
        assert replay.envelope==result.envelope and len(chunks)==1
    assert len(gateway.requests)==1
