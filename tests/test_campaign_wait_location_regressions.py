"""L23: waiting is not permission to impose silence."""
from datetime import timedelta
import pytest
from api import rules_service
from api.scene_director_service import SceneProposalError
from api.campaign_source_execution_service import execute_campaign_source_turn
from api.campaign_source_input_service import prepare_campaign_source_player_action
from api.campaign_source_storage import create_campaign_source_session, read_campaign_source_snapshot
from api.campaign_source_offline_corpus import PROSE
from api.llm.contract import CancellationToken, utc_now
from api.persistence import SQLitePersistence
from test_campaign_source_integration import config_and_gateway
from test_narrative_source_input_service import state
from test_scene_focus_wait_regressions import _check

OBSERVED = "Você aguarda no Arquivo enquanto a água alcança o registro sobre a bancada baixa. O registro fica molhado, e parte do conteúdo entra em risco. A pressão na sala se torna tensa. Mara volta o rosto para a infiltração e diz, em tom baixo: “Não podemos contar com muito tempo; isso já está perto demais.”"
QUESTION = 'O que você faz diante da água que alcança o registro?'

@pytest.mark.parametrize('text,player_input,location,accepted',[
    (OBSERVED,'Espero','Arquivo',True),
    (OBSERVED,'Aguardo','Arquivo',True),
    (OBSERVED.replace('no Arquivo','na Galeria'),'Espero','Arquivo',False),
    (OBSERVED,'Espero a resposta de Mara','Arquivo',False),
    (OBSERVED+' Você abre a porta.','Espero','Arquivo',False),
    (OBSERVED.replace('Você aguarda no Arquivo','Você permanece em silêncio'),'Espero','Arquivo',False),
])
def test_wait_location_is_grounded_not_a_new_target(text,player_input,location,accepted):
    from api.narrative_source_profile import validate_source_proposal
    from api.scene_service import SceneState
    def check():
        return validate_source_proposal({'n':text,'q':QUESTION},facts=(),
            current_scene=SceneState(location=location,npcs_present=('Mara',)),
            player_input=player_input,npc_aliases=('Mara',))
    if accepted:assert check().narrative==text
    else:
        with pytest.raises(SceneProposalError):check()

@pytest.mark.asyncio
@pytest.mark.parametrize('unsafe',[False,True])
async def test_wetting_atomicity_restart_replay(tmp_path,monkeypatch,unsafe):
    def forbidden_roll(*_a,**_kw):pytest.fail('wait/replay may not roll')
    monkeypatch.setattr(rules_service,'calculate_resolution',forbidden_roll)
    db=tmp_path/'wait_location.sqlite3'
    store=SQLitePersistence(db)
    await create_campaign_source_session(store,'silence',initial_state=state())
    for turn in (1,2):
        text=PROSE['R-03'] if turn==1 else OBSERVED+(' Você abre a porta.' if unsafe else '')
        config,gateway=config_and_gateway(text,('campaign.warning.visible',) if turn==1 else ('campaign.record.wet',),QUESTION)
        p=await prepare_campaign_source_player_action(store=store,session_id='silence',operation_id=f'wait-{turn}',
            player_input='Aguardo' if turn==1 else 'Espero',config=config,deadline=utc_now()+timedelta(seconds=60),cancellation=CancellationToken())
        chunks=[]
        async def deliver(text):chunks.append(text)
        result=await execute_campaign_source_turn(store=store,capsule=p.capsule,operation_id=f'wait-{turn}',gateway=gateway,
            deadline=utc_now()+timedelta(seconds=60),cancellation=CancellationToken(),on_chunk=deliver)
        if turn==1:assert result.status=='completed'
    restarted=SQLitePersistence(db)
    snapshot=await read_campaign_source_snapshot(restarted,'silence')
    if unsafe:
        assert result.status=='failed' and result.error_code=='campaign_source_policy_failed'
        assert snapshot.current_turn==1 and snapshot.progression.record=='warned' and len(snapshot.sources)==1 and not chunks
    else:
        assert result.status=='completed' and snapshot.current_turn==2 and snapshot.progression.record=='wet'
        replay=await execute_campaign_source_turn(store=restarted,capsule=p.capsule,operation_id='wait-2',gateway=gateway,
            deadline=utc_now()-timedelta(seconds=1),cancellation=CancellationToken(),on_chunk=deliver)
        assert replay.envelope==result.envelope and len(chunks)==1
    assert len(gateway.requests)==1
