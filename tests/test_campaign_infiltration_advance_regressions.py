"""L41: the explicit infiltration subject does not move the player."""
from datetime import timedelta
import pytest
from test_scene_drops_advance_regressions import TEXT as OBSERVED_L78
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
from scripts.run_campaign_source_offline_trial import _initial_state

OBSERVED = 'Você aguarda no Arquivo enquanto a infiltração avança pelas bordas da sala. A bancada baixa continua seca, e o registro permanece intacto sobre ela, sem mudar de lugar. Mara se aproxima apenas o bastante para acompanhar a umidade crescente e fala em tom baixo: “O risco ficou imediato. O registro ainda está seco, mas não por muito tempo.” O ambiente, antes calmo, assume uma vigilância tensa; cada sinal da infiltração parece exigir atenção renovada.'
QUESTION = 'O que você faz diante do risco crescente ao registro?'
OBSERVED_L58 = 'Você aguarda no Arquivo enquanto a infiltração aumenta junto à bancada baixa. O registro continua seco sobre a bancada, mas Mara percebe o risco imediato e volta-se para você, mantendo a atenção na umidade que avança. “A água está chegando mais perto. O registro ainda está seco, mas não por muito tempo”, ela diz, em tom baixo e vigilante. O ambiente permanece tenso, sem que o registro mude de lugar.'
OBSERVED_L57 = 'Você aguarda no Arquivo enquanto a infiltração avança pelas proximidades da bancada baixa. O registro continua seco, ainda ameaçado, sem mudar de lugar. Mara acompanha a umidade que se espalha e volta o rosto para você, a atenção subitamente tensa. “O risco aumentou”, ela diz, apontando para o registro. “Precisamos agir antes que a água alcance as páginas.”'
OBSERVED_L47 = 'Você aguarda enquanto a infiltração se espalha pela parede do Arquivo, avançando o bastante para tornar o risco imediato. Na bancada baixa, o registro continua seco, embora a ameaça ao redor tenha aumentado. Mara acompanha a umidade com o olhar e se aproxima sem tocar no documento. “Ainda está seco”, ela diz, em voz baixa. “Mas não por muito tempo se isso continuar.” A postura dela se torna vigilante, atenta às frestas e ao registro sobre a bancada.'

OBSERVED_L69 = 'Você aguarda enquanto a infiltração se espalha pelo Arquivo. Gotas surgem na borda da bancada baixa, cada vez mais próximas do registro, mas suas páginas continuam secas por enquanto. Mara acompanha o avanço da água e volta-se para você, tensa, sem tocar no objeto. “O risco aumentou. O registro ainda está seco, mas não ficará assim por muito tempo”, ela diz, indicando a bancada. O ar úmido se concentra ao redor do móvel, e a urgência se torna evidente sem que o registro mude de lugar.'

def check(text):
    return validate_source_proposal({'n':text,'q':QUESTION}, facts=(),
        current_scene=SceneState(location='Arquivo',npcs_present=('Mara',)),
        player_input='Aguardo',npc_aliases=('Mara',))

@pytest.mark.parametrize('text',[OBSERVED,OBSERVED_L57,OBSERVED_L58,OBSERVED_L69])
def test_explicit_infiltration_advances_not_player(text):
    assert check(text).narrative == text

@pytest.mark.parametrize('complement',['em direção ao registro','pelo chão do Arquivo'])
def test_same_explicit_actor_does_not_depend_on_its_spatial_complement(complement):
    text=OBSERVED_L57.replace('pelas proximidades da bancada baixa',complement)
    assert check(text).narrative == text


@pytest.mark.parametrize('conjunction',['enquanto','mas','e'])
@pytest.mark.parametrize('actor',['a infiltração','a água'])
def test_explicit_environmental_actor_does_not_depend_on_conjunction(conjunction,actor):
    text=OBSERVED_L57.replace('enquanto a infiltração avança',conjunction+' '+actor+' avança')
    assert check(text).narrative==text
    with pytest.raises(SceneProposalError,match='scene_player_agency_violation'):
        check(text+' Você avança para a Galeria.')

def test_infiltration_owns_its_bounded_advancing_gerund():
    assert check(OBSERVED_L47).narrative == OBSERVED_L47

@pytest.mark.parametrize('text', [
    OBSERVED_L47.replace('a infiltração se espalha pela parede do Arquivo', 'você segue pela parede do Arquivo'),
    OBSERVED_L47.replace('a infiltração se espalha pela parede do Arquivo', 'Mara segue pela parede do Arquivo'),
    OBSERVED_L47+' Você avança para a Galeria.',
    OBSERVED_L47+' Você abre a porta.',
    OBSERVED_L47.replace('o risco imediato.', 'o risco imediato e você abre a porta.'),
    OBSERVED_L57.replace('a infiltração avança','você avança'),
    OBSERVED_L57.replace('bancada baixa.', 'bancada baixa e você avança para a Galeria.',1),
    OBSERVED_L57+' Você abre a porta.',
    OBSERVED_L58.replace('na umidade que avança','em você que avança'),
    OBSERVED_L58+' Você avança para a Galeria.',
    OBSERVED_L58+' Você abre a porta.',
])
def test_gerund_exception_keeps_player_and_npc_actions_visible(text):
    with pytest.raises(SceneProposalError, match='scene_player_agency_violation'):
        check(text)

@pytest.mark.parametrize('text', [
    OBSERVED.replace('a infiltração avança', 'você avança'),
    OBSERVED.replace('a infiltração avança', 'Mara avança'),
    OBSERVED + ' Você avança para a Galeria.',
    OBSERVED + ' Você abre a porta.',
    OBSERVED.replace('pelas bordas da sala.', 'pelas bordas da sala e você avança para a Galeria.'),
])
def test_real_actions_remain_rejected(text):
    with pytest.raises(SceneProposalError, match='scene_player_agency_violation'):
        check(text)


@pytest.mark.parametrize('text',[
    OBSERVED_L69.replace('Mara acompanha o avanço da água e volta-se para você, tensa, sem tocar no objeto.',
        'Você acompanha o avanço da água, sem tocar no objeto.'),
    OBSERVED_L69.replace('Mara acompanha','Uma pessoa acompanha'),
    OBSERVED_L69.replace('Mara acompanha o avanço da água e volta-se para você, tensa, sem tocar no objeto.',
        '“Mara acompanha o avanço da água e volta-se para você, tensa, sem tocar no objeto.”'),
    OBSERVED_L69.replace('no objeto.','no objeto e você abre a porta.',1),
    OBSERVED_L69+' Você toca no objeto.',
    OBSERVED_L69+' Você abre a porta.',
])
def test_l69_npc_subject_cannot_hide_unknown_actor_or_player_action(text):
    with pytest.raises(SceneProposalError,match='scene_player_agency_violation'):
        check(text)

@pytest.mark.asyncio
@pytest.mark.parametrize('unsafe', [False, True])
@pytest.mark.parametrize('observed', [OBSERVED, OBSERVED_L47, OBSERVED_L57, OBSERVED_L58, OBSERVED_L69,
    OBSERVED_L78])
async def test_warning_atomicity_restart_replay_without_rng(tmp_path, monkeypatch, unsafe, observed):
    def forbidden(*a, **kw):
        pytest.fail('warning/replay must not roll')
    monkeypatch.setattr(rules_service, 'calculate_resolution', forbidden)
    db=tmp_path/'infiltration.sqlite3'
    store=SQLitePersistence(db)
    await create_campaign_source_session(store, 'infiltration', initial_state=_initial_state())
    text=observed+(' Você abre a porta.' if unsafe else '')
    config,gateway=config_and_gateway(text, ('campaign.warning.visible',), QUESTION)
    prepared=await prepare_campaign_source_player_action(store=store,session_id='infiltration',
        operation_id='warning',player_input='Aguardo',config=config,
        deadline=utc_now()+timedelta(seconds=60),cancellation=CancellationToken())
    chunks=[]
    async def deliver(text):
        chunks.append(text)
    result=await execute_campaign_source_turn(store=store,capsule=prepared.capsule,
        operation_id='warning',gateway=gateway,deadline=utc_now()+timedelta(seconds=60),
        cancellation=CancellationToken(),on_chunk=deliver)
    restarted=SQLitePersistence(db)
    snapshot=await read_campaign_source_snapshot(restarted,'infiltration')
    if unsafe:
        assert result.status=='failed' and snapshot.current_turn==0 and not chunks
        assert snapshot.progression.record=='threatened'
    else:
        assert result.status=='completed' and snapshot.current_turn==1
        assert snapshot.progression.record=='warned' and snapshot.progression.outcome is None
        replay=await execute_campaign_source_turn(store=restarted,capsule=prepared.capsule,
            operation_id='warning',gateway=gateway,deadline=utc_now()-timedelta(seconds=1),
            cancellation=CancellationToken(),on_chunk=deliver)
        assert replay.envelope==result.envelope and len(chunks)==1
    assert len(gateway.requests)==1
