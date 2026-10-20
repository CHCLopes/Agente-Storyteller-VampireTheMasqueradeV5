"""L42: affirmative water dampening the record realizes wet, not mere risk."""
from datetime import timedelta
import pytest
from api import rules_service
from api.narrative_source_profile import validate_source_proposal
from api.scene_director_service import SceneProposalError
from api.scene_service import SceneState
from api.campaign_source_execution_service import execute_campaign_source_turn
from api.campaign_source_input_service import prepare_campaign_source_player_action
from api.campaign_source_storage import create_campaign_source_session, read_campaign_source_snapshot
from api.campaign_source_offline_corpus import PROSE
from api.llm.contract import CancellationToken, utc_now
from api.persistence import SQLitePersistence
from test_campaign_source_integration import config_and_gateway
from scripts.run_campaign_source_offline_trial import _initial_state

OBSERVED='Você aguarda. No Arquivo, a água alcança o registro sobre a bancada baixa e umedece suas páginas; parte do conteúdo fica em risco. Mara acompanha o avanço da infiltração e se volta para você, tensa. “A água chegou ao registro”, diz ela. “Ainda há conteúdo ali, mas cada momento pode custar uma parte dele.”'
OBSERVED_L49='Você espera no Arquivo enquanto a água alcança a bancada baixa e toca o registro. A umidade se espalha pelas bordas, ameaçando parte do conteúdo. Mara observa o contato sem tocar no registro e estreita o olhar. “A água chegou ao registro”, ela diz, em voz baixa. “Ainda há algo a fazer, mas o risco aumentou.”'

OBSERVED_L71 = 'Você espera no Arquivo, e a infiltração alcança a bancada baixa. A água molha o registro onde ele estava, encharcando parte de suas páginas e colocando seu conteúdo em risco. Mara acompanha o dano sem tocar no objeto. “A água atingiu o registro”, ela diz, com a voz tensa. “Ainda pode haver algo recuperável, mas precisamos agir com cuidado.”'

def check_contact(text):
    return validate_source_proposal({'n':text,'q':'O que você faz agora?'},facts=(),
        current_scene=SceneState(location='Arquivo',npcs_present=('Mara',)),
        player_input='Espero',npc_aliases=('Mara',))

def test_explicit_water_contact_is_not_player_touch():
    assert check_contact(OBSERVED_L49).narrative == OBSERVED_L49

@pytest.mark.parametrize('text',[
    OBSERVED_L49.replace('a água alcança a bancada baixa e toca', 'você toca'),
    OBSERVED_L49+' Você toca o registro.',
    OBSERVED_L49+' Você abre a porta.',
])
def test_water_contact_never_authorizes_player_actions(text):
    with pytest.raises(SceneProposalError,match='scene_player_agency_violation'):
        check_contact(text)

@pytest.mark.asyncio
@pytest.mark.parametrize('variant', ['observed','negation','hypothesis','wish','contradiction','player_action',
    'contact_only','contact_with_wet','l71_original','l71_named','l71_extra'])
async def test_wet_effect_atomicity_restart_replay(tmp_path,monkeypatch,variant):
    def forbidden(*a,**kw):
        pytest.fail('waiting/replay must not roll')
    monkeypatch.setattr(rules_service,'calculate_resolution',forbidden)
    db=tmp_path/'damp.sqlite3';store=SQLitePersistence(db)
    await create_campaign_source_session(store,'damp',initial_state=_initial_state())
    text=OBSERVED
    if variant=='negation': text=text.replace('e umedece','e não umedece')
    if variant=='hypothesis': text=text.replace('No Arquivo, a água alcança','Se a água alcança')
    if variant=='wish': text=text.replace('No Arquivo, a água alcança','Mara deseja que a água alcança')
    if variant=='contradiction': text+=' O registro permanece seco.'
    if variant=='player_action': text+=' Você abre a porta.'
    if variant=='contact_only': text=OBSERVED_L49
    if variant.startswith('l71_'): text=OBSERVED_L71
    if variant in {'l71_named','l71_extra'}: text=text.replace('onde ele estava','na bancada baixa')
    if variant=='l71_extra': text+=' Você abre a porta.'
    if variant=='contact_with_wet': text=OBSERVED_L49.replace('A umidade se espalha pelas bordas', 'O registro fica molhado; a umidade se espalha pelas bordas')
    for turn,(player_input,rule,effects) in enumerate([
        ('Aguardo','R-03',('campaign.warning.visible',)),
        ('Espero','R-03B',('campaign.record.wet',)),
    ],1):
        config,gateway=config_and_gateway(PROSE[rule] if turn==1 else text,effects)
        op=f'damp-{turn}'
        prepared=await prepare_campaign_source_player_action(store=store,session_id='damp',operation_id=op,
            player_input=player_input,config=config,deadline=utc_now()+timedelta(seconds=60),cancellation=CancellationToken())
        chunks=[]
        async def deliver(text):chunks.append(text)
        result=await execute_campaign_source_turn(store=store,capsule=prepared.capsule,operation_id=op,
            gateway=gateway,deadline=utc_now()+timedelta(seconds=60),cancellation=CancellationToken(),on_chunk=deliver)
        if turn==1: assert result.status=='completed'
    restarted=SQLitePersistence(db);snapshot=await read_campaign_source_snapshot(restarted,'damp')
    if variant in {'observed','contact_with_wet','l71_named'}:
        assert result.status=='completed' and snapshot.current_turn==2
        assert snapshot.progression.record=='wet' and snapshot.progression.record_location=='bench'
        replay=await execute_campaign_source_turn(store=restarted,capsule=prepared.capsule,operation_id=op,
            gateway=gateway,deadline=utc_now()-timedelta(seconds=1),cancellation=CancellationToken(),on_chunk=deliver)
        assert replay.envelope==result.envelope and len(chunks)==1
    else:
        assert result.status=='failed' and snapshot.current_turn==1 and not chunks
        assert snapshot.progression.record=='warned' and snapshot.progression.outcome is None
    assert len(gateway.requests)==1
