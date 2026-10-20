"""L20: explicit infiltration movement is not a player approach."""
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

OBSERVED = 'Enquanto você aguarda, a infiltração se espalha pelas paredes do Arquivo, aproximando-se da bancada baixa. Mara permanece atenta, o olhar fixo nas marcas úmidas que avançam pelo entorno. Ela fala em tom baixo: “O risco é imediato. Se continuar aumentando, a margem para agir desaparece.” O registro continua seco, intacto sobre a bancada baixa, embora o ambiente ao redor se torne mais ameaçador. Mara não se afasta nem toca no objeto; apenas acompanha a progressão da infiltração, pronta para reagir ao menor sinal de mudança.'
QUESTION = 'O que você faz diante do risco imediato?'

def check(text):
    return validate_source_proposal({'n':text,'q':QUESTION},facts=(),
        current_scene=SceneState(location='Arquivo',npcs_present=('Mara',)),
        player_input='Aguardo',npc_aliases=('Mara',))

def test_exact_infiltration_approach_is_not_player_movement():
    assert check(OBSERVED).narrative == OBSERVED

@pytest.mark.parametrize('replacement',[
    'você se espalha pelas paredes do Arquivo, aproximando-se da bancada baixa.',
    'Mara se espalha pelas paredes do Arquivo, aproximando-se da bancada baixa.',
    'a infiltração se espalha pelas paredes do Arquivo, você aproximando-se da bancada baixa.',
    'a infiltração se espalha pelas paredes do Arquivo, aproximando-se da bancada baixa, você abre a porta.',
    'a infiltração se espalha pelas paredes do Arquivo, aproximando-se da bancada baixa e você avança.',
    'a infiltração se espalha pelas paredes do Arquivo, aproximando-se da bancada baixa. Você parte do Arquivo.',
])
def test_other_actors_and_following_actions_remain_rejected(replacement):
    with pytest.raises(SceneProposalError,match='scene_player_agency_violation'):
        check(OBSERVED.replace('a infiltração se espalha pelas paredes do Arquivo, aproximando-se da bancada baixa.',replacement))

@pytest.mark.asyncio
@pytest.mark.parametrize('unsafe',[False,True])
async def test_warning_atomicity_restart_and_replay(tmp_path,monkeypatch,unsafe):
    def forbidden_roll(*_a,**_kw):pytest.fail('wait/replay may not roll')
    monkeypatch.setattr(rules_service,'calculate_resolution',forbidden_roll)
    db=tmp_path/'infiltration.sqlite3'
    store=SQLitePersistence(db)
    await create_campaign_source_session(store,'infiltration',initial_state=state())
    config,gateway=config_and_gateway(OBSERVED+(' Você fecha a porta.' if unsafe else ''),('campaign.warning.visible',),QUESTION)
    p=await prepare_campaign_source_player_action(store=store,session_id='infiltration',operation_id='infiltration-1',
        player_input='Aguardo',config=config,deadline=utc_now()+timedelta(seconds=60),cancellation=CancellationToken())
    assert p.capsule.campaign_effect.rule_id=='R-03'
    chunks=[]
    async def deliver(text):chunks.append(text)
    result=await execute_campaign_source_turn(store=store,capsule=p.capsule,operation_id='infiltration-1',gateway=gateway,
        deadline=utc_now()+timedelta(seconds=60),cancellation=CancellationToken(),on_chunk=deliver)
    restarted=SQLitePersistence(db)
    snapshot=await read_campaign_source_snapshot(restarted,'infiltration')
    if unsafe:
        assert result.status=='failed' and result.error_code=='campaign_source_policy_failed'
        assert snapshot.current_turn==0 and snapshot.progression.record=='threatened' and not chunks and not snapshot.sources
    else:
        assert result.status=='completed' and snapshot.current_turn==1 and snapshot.progression.record=='warned'
        replay=await execute_campaign_source_turn(store=restarted,capsule=p.capsule,operation_id='infiltration-1',gateway=gateway,
            deadline=utc_now()-timedelta(seconds=1),cancellation=CancellationToken(),on_chunk=deliver)
        assert replay.envelope==result.envelope and len(chunks)==1
    assert len(gateway.requests)==1
