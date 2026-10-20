"""L22: moisture advancing in a temporal clause is not player movement."""
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
from api.campaign_source_offline_corpus import PROSE

OBSERVED = "Você retira o registro da bancada baixa antes que a umidade avance. O registro passa a repousar sobre a superfície seca da Galeria, enquanto o que ainda é legível fica preservado. O dano causado pela água, porém, não é revertido: parte do conteúdo permanece comprometida. Mara acompanha a retirada em silêncio até confirmar que o registro está fora da umidade. “O que podia ser salvo, foi”, ela diz, mantendo a voz baixa. “Mas o estrago anterior continua marcado no conteúdo.”"

def check(text):
    return validate_source_proposal({'n':text,'q':'O que você faz agora?'}, facts=(),
        current_scene=SceneState(location='Arquivo',npcs_present=('Mara',)),
        player_input='Retiro o registro',npc_aliases=('Mara',))

def test_exact_temporal_moisture_clause_is_not_player_movement():
    assert check(OBSERVED).narrative == OBSERVED

@pytest.mark.parametrize('replacement', [
    'antes que você avance mais.',
    'antes que a umidade avance mais, você avança para a Galeria.',
    'antes que a umidade avance. Você parte do Arquivo.',
    'antes que a umidade avance mais e você abre a porta.',
    'antes que Mara avance mais.',
])
def test_other_actors_or_later_actions_do_not_inherit_the_exception(replacement):
    with pytest.raises(SceneProposalError,match='scene_player_agency_violation'):
        check(OBSERVED.replace('antes que a umidade avance.',replacement))

@pytest.mark.asyncio
@pytest.mark.parametrize('unsafe',[False,True])
async def test_partial_rescue_commits_once_or_rolls_back(tmp_path,monkeypatch,unsafe):
    def forbidden_roll(*_a,**_kw):
        pytest.fail('waiting/help/rescue and replay may not roll')
    monkeypatch.setattr(rules_service,'calculate_resolution',forbidden_roll)
    db=tmp_path/'moisture_short.sqlite3'
    store=SQLitePersistence(db)
    await create_campaign_source_session(store,'moisture',initial_state=state())
    chunks=[]
    async def deliver(text):chunks.append(text)
    for number,(player_input,rule,effects) in enumerate([
        ('Aguardo','R-03',('campaign.warning.visible',)),
        ('Espero','R-03B',('campaign.record.wet',)),
        ('Como posso ajudar?','R-01',('mara.replies.to_task','campaign.knows.safe_surface')),
        ('Retiro o registro','R-06',('campaign.record.partial',)),
    ],1):
        text=PROSE[rule] if number<4 else OBSERVED+(' Você avança para a Galeria.' if unsafe else '')
        config,gateway=config_and_gateway(text,effects,'' if number==4 else 'O que você faz agora?')
        op=f'moisture-{number}'
        p=await prepare_campaign_source_player_action(store=store,session_id='moisture',operation_id=op,
            player_input=player_input,config=config,deadline=utc_now()+timedelta(seconds=60),cancellation=CancellationToken())
        assert p.capsule.campaign_effect.rule_id==rule
        result=await execute_campaign_source_turn(store=store,capsule=p.capsule,operation_id=op,gateway=gateway,
            deadline=utc_now()+timedelta(seconds=60),cancellation=CancellationToken(),on_chunk=deliver)
        if number<4:assert result.status=='completed'
    restarted=SQLitePersistence(db)
    snapshot=await read_campaign_source_snapshot(restarted,'moisture')
    if unsafe:
        assert result.status=='failed' and result.error_code=='campaign_source_policy_failed'
        assert snapshot.current_turn==3 and snapshot.progression.record=='wet'
        assert snapshot.progression.outcome is None and len(chunks)==3
    else:
        assert result.status=='completed' and snapshot.current_turn==4
        assert snapshot.progression.outcome=='partial' and snapshot.progression.record_location=='dry_surface'
        replay=await execute_campaign_source_turn(store=restarted,capsule=p.capsule,operation_id=op,gateway=gateway,
            deadline=utc_now()-timedelta(seconds=1),cancellation=CancellationToken(),on_chunk=deliver)
        assert replay.envelope==result.envelope and len(chunks)==4
    assert len(gateway.requests)==1
