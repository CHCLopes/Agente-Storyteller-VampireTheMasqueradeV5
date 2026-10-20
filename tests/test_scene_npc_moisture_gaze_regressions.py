"""L18: a proven NPC pronoun owns its coordinated gaze and speech."""
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

OBSERVED = 'Você aguarda no Arquivo, enquanto a infiltração se espalha mais depressa pelas frestas e deixa o ar úmido ao redor da bancada baixa. O registro permanece seco sobre a bancada, mas a ameaça se torna visível na tensão do ambiente. Mara acompanha as marcas de umidade sem tocar no objeto. Ela ergue os olhos para você e fala em voz baixa: “O risco é imediato. Ainda está seco, mas não por muito tempo.” A postura dela muda; a atenção antes tranquila se torna vigilante, concentrada nas bordas da sala e na proteção do registro.'
QUESTION = 'Que ação você toma diante do risco imediato no Arquivo?'

def check(text):
    return validate_source_proposal({'n':text,'q':QUESTION},facts=(),
        current_scene=SceneState(location='Arquivo',npcs_present=('Mara',)),
        player_input='Aguardo',npc_aliases=('Mara',))

def test_exact_npc_moisture_gaze_is_not_player_speech():
    assert check(OBSERVED).narrative==OBSERVED

@pytest.mark.parametrize('replacement',[
    'Você ergue os olhos para Mara e fala em voz baixa:',
    'Ela ergue os olhos para você e você fala em voz baixa:',
    'Ela ergue os olhos para você e obriga você a falar em voz baixa:',
    'Ela ergue os olhos para você e fala em voz baixa: “Você abre a porta.”',
    'Ela ergue os olhos para você e fala em voz baixa: “Você decide ajudar.”',
])
def test_actual_player_actions_are_not_hidden_by_npc_report(replacement):
    with pytest.raises(SceneProposalError,match='scene_player_agency_violation'):
        check(OBSERVED.replace('Ela ergue os olhos para você e fala em voz baixa:',replacement))

@pytest.mark.parametrize('actor',['Alguém','Você'])
def test_unknown_or_player_antecedent_does_not_own_npc_pronoun(actor):
    with pytest.raises(SceneProposalError):
        check(OBSERVED.replace('Mara acompanha as marcas de umidade',actor+' acompanha as marcas de umidade'))
@pytest.mark.asyncio
@pytest.mark.parametrize('unsafe',[False,True])
async def test_warning_commit_restart_replay_or_atomic_rejection(tmp_path,monkeypatch,unsafe):
    def forbidden_roll(*_a,**_kw):pytest.fail('wait and replay may not roll')
    monkeypatch.setattr(rules_service,'calculate_resolution',forbidden_roll)
    db=tmp_path/'npc_moisture_gaze.sqlite3'
    store=SQLitePersistence(db)
    await create_campaign_source_session(store,'npc_moisture_gaze',initial_state=state())
    config,gateway=config_and_gateway(OBSERVED+(' Você fecha a porta.' if unsafe else ''),('campaign.warning.visible',),QUESTION)
    p=await prepare_campaign_source_player_action(store=store,session_id='npc_moisture_gaze',operation_id='npc_moisture_gaze-1',
        player_input='Aguardo',config=config,deadline=utc_now()+timedelta(seconds=60),cancellation=CancellationToken())
    assert p.capsule.campaign_effect.rule_id=='R-03'
    chunks=[]
    async def deliver(text):chunks.append(text)
    result=await execute_campaign_source_turn(store=store,capsule=p.capsule,operation_id='npc_moisture_gaze-1',gateway=gateway,
        deadline=utc_now()+timedelta(seconds=60),cancellation=CancellationToken(),on_chunk=deliver)
    restarted=SQLitePersistence(db)
    snapshot=await read_campaign_source_snapshot(restarted,'npc_moisture_gaze')
    assert snapshot.progression.outcome is None
    if unsafe:
        assert result.status=='failed' and result.error_code=='campaign_source_policy_failed'
        assert snapshot.current_turn==0 and snapshot.progression.record=='threatened' and not snapshot.sources and not chunks
    else:
        assert result.status=='completed' and snapshot.current_turn==1 and snapshot.progression.record=='warned'
        replay=await execute_campaign_source_turn(store=restarted,capsule=p.capsule,operation_id='npc_moisture_gaze-1',gateway=gateway,
            deadline=utc_now()-timedelta(seconds=1),cancellation=CancellationToken(),on_chunk=deliver)
        assert replay.envelope==result.envelope and len(chunks)==1
    assert len(gateway.requests)==1
