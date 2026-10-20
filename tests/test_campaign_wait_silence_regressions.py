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

OBSERVED = 'Você permanece em silêncio, mas a infiltração finalmente alcança a bancada baixa. A água atinge o registro, molhando parte de seu conteúdo e colocando-o em risco. O registro permanece sobre a bancada baixa no Arquivo; sua posição não muda. Mara acompanha o avanço da água, tensa, e se volta para você: “Agora o aviso se tornou imediato. Precisamos agir antes que o restante seja comprometido.” Nenhuma informação nova se revela, mas a urgência substitui a espera cautelosa.'
QUESTION = 'O que você faz diante da água que alcança o registro?'

@pytest.mark.parametrize('player_input',['Espero','Aguardo'])
def test_wait_does_not_authorize_silence(player_input):
    with pytest.raises(SceneProposalError,match='scene_player_agency_violation'):
        _check(OBSERVED,player_input)

@pytest.mark.parametrize('phrase',['Você espera','Você aguarda'])
def test_actual_wait_preserves_existing_equivalence(phrase):
    _check(OBSERVED.replace('Você permanece em silêncio',phrase),'Espero')

@pytest.mark.asyncio
@pytest.mark.parametrize('unsafe',[False,True])
async def test_wetting_atomicity_restart_replay(tmp_path,monkeypatch,unsafe):
    def forbidden_roll(*_a,**_kw):pytest.fail('wait/replay may not roll')
    monkeypatch.setattr(rules_service,'calculate_resolution',forbidden_roll)
    db=tmp_path/'silence.sqlite3'
    store=SQLitePersistence(db)
    await create_campaign_source_session(store,'silence',initial_state=state())
    for turn in (1,2):
        text=PROSE['R-03'] if turn==1 else OBSERVED if unsafe else OBSERVED.replace('Você permanece em silêncio','Você espera')
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
