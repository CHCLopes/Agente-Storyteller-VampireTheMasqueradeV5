"""L36: water advancing onto the record is not player movement."""
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

OBSERVED='Você aguarda no Arquivo, e a água avança sobre o registro na bancada baixa. O texto se torna irrecuperável; o conteúdo perdido encerra a aventura. Mara acompanha a perda com atenção contida, sem tocar no registro. “A água venceu o registro”, ela diz, enquanto a urgência da ameaça chega ao fim junto com qualquer possibilidade de recuperar o texto. O registro permanece na bancada baixa do Arquivo, molhado e perdido.'
OBSERVED_L54='Você aguarda no Arquivo enquanto a água alcança a bancada baixa e atravessa as páginas do registro. A umidade se espalha pelo papel até tornar o texto irrecuperável. O registro permanece perdido na bancada, sem mudar de lugar. Mara observa as folhas arruinadas, o rosto tenso, e baixa os olhos por um instante. “A água levou o registro”, ela diz, em voz baixa. “Não há mais conteúdo para salvar.” As gotas continuam descendo pelo reboco, enquanto Mara recebe o desfecho sem insistir ou acrescentar qualquer pedido.'


OBSERVED_L62='Você aguarda no Arquivo, mas a água continua sobre a bancada baixa e atravessa o registro. As páginas se encharcam até que o texto se torna irrecuperável; o registro permanece perdido onde estava, na bancada. Mara observa as folhas danificadas e baixa a voz: “Está perdido. A água apagou o conteúdo.” Ela recebe o resultado sem insistir, diante do registro que já não pode ser recuperado.'

OBSERVED_L65 = 'Você aguarda no Arquivo, mas a água continua avançando pela bancada baixa. O registro fica completamente molhado, e o texto se desfaz até se tornar irrecuperável. As páginas permanecem sobre a bancada, encharcadas e sem conteúdo legível. Mara se aproxima sem tocar no objeto e observa o dano consumado. “Está perdido”, diz ela, com a voz baixa. “A água levou o texto.” Ela recebe o resultado em silêncio, sem deslocar o registro nem sugerir outro caminho.'

OBSERVED_L68 = 'Você aguarda, mas a infiltração avança sobre a bancada baixa no Arquivo. A água encharca o registro, espalha a tinta e torna o texto irrecuperável. Mara se volta para o documento, sem tocá-lo; sua expressão pesa enquanto ela diz, em voz baixa: “Está perdido. A água levou o conteúdo.” O registro permanece na bancada, molhado e sem possibilidade de recuperação.'

def check(text):
    return validate_source_proposal({'n':text,'q':'O que você faz agora?'},facts=(),
        current_scene=SceneState(location='Arquivo',npcs_present=('Mara',)),
        player_input='Aguardo',npc_aliases=('Mara',))


@pytest.mark.parametrize('text',[OBSERVED,OBSERVED_L54,OBSERVED_L62,OBSERVED_L65,OBSERVED_L68])
def test_exact_water_actor_not_player_movement(text):
    assert check(text).narrative==text

@pytest.mark.parametrize('text',[
    OBSERVED_L54.replace('a água alcança a bancada baixa e atravessa as páginas do registro','você atravessa a Galeria'),
    OBSERVED_L54+' Você atravessa a Galeria.',
    OBSERVED_L54+' Você abre a porta.',
])
def test_water_crossing_does_not_authorize_player_movement(text):
    with pytest.raises(SceneProposalError,match='scene_player_agency_violation'):
        check(text)


@pytest.mark.parametrize('text',[
    OBSERVED.replace('a água avança','você avança'),
    OBSERVED.replace('a água avança','Mara avança'),
    OBSERVED+' Você avança para a Galeria.',
    OBSERVED+' Você abre a porta.',
    OBSERVED.replace('na bancada baixa.','na bancada baixa e você avança para a Galeria.',1),
])
def test_actual_player_actions_not_waived(text):
    with pytest.raises(SceneProposalError,match='scene_player_agency_violation'):
        check(text)


@pytest.mark.parametrize('text',[
    OBSERVED_L62.replace('a água continua','você continua'),
    OBSERVED_L62.replace('a água continua','Mara continua'),
    OBSERVED_L62+' Você atravessa a Galeria.',
    OBSERVED_L62.replace('atravessa o registro.','atravessa o registro e você abre a porta.'),
])
def test_l62_actor_binding_cannot_hide_player_action(text):
    with pytest.raises(SceneProposalError,match='scene_player_agency_violation'):
        check(text)


@pytest.mark.parametrize('text',[
    OBSERVED_L65.replace('a água continua','você continua'),
    OBSERVED_L65.replace('a água continua','Mara continua'),
    OBSERVED_L65+' Você avança para a Galeria.',
    OBSERVED_L65.replace('pela bancada baixa.','pela bancada baixa e você abre a porta.',1),
])
def test_l65_environmental_gerund_never_authorizes_player_motion(text):
    with pytest.raises(SceneProposalError,match='scene_player_agency_violation'):
        check(text)


@pytest.mark.asyncio
@pytest.mark.parametrize('unsafe',[False,True])
@pytest.mark.parametrize('observed',[OBSERVED,OBSERVED_L54,OBSERVED_L62,OBSERVED_L65,OBSERVED_L68,
    'Você aguarda no Arquivo, e a água continua sobre a bancada baixa até atravessar completamente o registro. As páginas se desfazem sob a umidade, e o texto se torna irrecuperável. Mara observa o volume perdido, com as mãos afastadas do papel encharcado. “Está perdido. A água apagou o conteúdo do registro”, ela diz, enquanto o gotejamento prossegue pelas frestas.'])
async def test_r04_atomicity_restart_replay_without_rng(tmp_path,monkeypatch,unsafe,observed):
    def forbidden(*a,**kw):pytest.fail('waiting/replay must not roll')
    monkeypatch.setattr(rules_service,'calculate_resolution',forbidden)
    db=tmp_path/'water.sqlite3';store=SQLitePersistence(db)
    await create_campaign_source_session(store,'water',initial_state=_initial_state())
    for number,(player_input,rule,effects) in enumerate([
        ('Aguardo','R-03',('campaign.warning.visible',)),
        ('Espero','R-03B',('campaign.record.wet',)),
        ('Aguardo','R-04',('campaign.record.lost',)),
    ],1):
        text=PROSE[rule] if number<3 else observed+(' Você avança para a Galeria.' if unsafe else '')
        config,gateway=config_and_gateway(text,effects,'' if number==3 else 'O que você faz agora?')
        op=f'water-{number}'
        prepared=await prepare_campaign_source_player_action(store=store,session_id='water',operation_id=op,player_input=player_input,config=config,deadline=utc_now()+timedelta(seconds=60),cancellation=CancellationToken())
        c=prepared.capsule;chunks=[]
        async def deliver(text):chunks.append(text)
        result=await execute_campaign_source_turn(store=store,capsule=c,operation_id=op,gateway=gateway,deadline=utc_now()+timedelta(seconds=60),cancellation=CancellationToken(),on_chunk=deliver)
        if number<3:assert result.status=='completed'
    restarted=SQLitePersistence(db);snapshot=await read_campaign_source_snapshot(restarted,'water')
    if unsafe:
        assert result.status=='failed' and snapshot.current_turn==2 and not chunks
        assert snapshot.progression.record=='wet' and snapshot.progression.outcome is None
    else:
        assert result.status=='completed' and snapshot.current_turn==3
        assert snapshot.progression.outcome=='lost' and snapshot.progression.record_location=='bench'
        replay=await execute_campaign_source_turn(store=restarted,capsule=c,operation_id=op,gateway=gateway,deadline=utc_now()-timedelta(seconds=1),cancellation=CancellationToken(),on_chunk=deliver)
        assert replay.envelope==result.envelope and len(chunks)==1
    assert len(gateway.requests)==1
