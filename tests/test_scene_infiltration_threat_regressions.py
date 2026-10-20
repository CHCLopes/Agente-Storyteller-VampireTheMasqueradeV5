"""L30: explicit infiltration threat is not a player's combat action."""
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

OBSERVED='Mara se volta para você, mantendo a voz contida enquanto a infiltração ameaça a bancada baixa. “O registro está molhado, e parte do conteúdo corre risco”, ela explica. Com um gesto discreto, indica a direção da Galeria: “Há uma superfície seca lá.” O registro permanece sobre a bancada baixa no Arquivo, sem deslocamento; a atmosfera continua tensa.'
OBSERVED_L31='Mara volta-se para você, mantendo o tom contido apesar da tensão no Arquivo. “O registro está molhado, e parte do conteúdo continua em risco sobre a bancada baixa. A superfície seca fica na Galeria; é lá que poderemos protegê-lo da infiltração.” O registro permanece sobre a bancada baixa, sem mudar de posição, enquanto a ameaça ao redor se intensifica.'


OBSERVED_L67='Mara aponta para as folhas úmidas na bancada baixa. “Precisamos tirar o registro daqui antes que a infiltração danifique mais páginas. A superfície seca fica na Galeria; lá poderemos apoiar o objeto longe da água e tentar recuperar o conteúdo que ainda resistir.” O registro continua molhado sobre a bancada baixa do Arquivo, com parte das páginas encharcada. Ela observa o caminho da água e depois a passagem para a Galeria, sem tocar no objeto.'

def check(text):
    return validate_source_proposal({'n':text,'q':'O que você faz agora?'},facts=(),
        current_scene=SceneState(location='Arquivo',npcs_present=('Mara',)),
        player_input='O que precisamos fazer?',npc_aliases=('Mara',))


@pytest.mark.parametrize('text',[OBSERVED,OBSERVED_L31])
def test_exact_environmental_subject_is_not_player_combat(text):
    assert check(text).narrative == text


@pytest.mark.parametrize('text',[
    OBSERVED+' Você ameaça Mara.',
    OBSERVED+' Você abre a porta.',
    OBSERVED.replace('a infiltração ameaça','você ameaça'),
    OBSERVED.replace('a infiltração ameaça','Mara ameaça'),
    OBSERVED.replace('ameaça a bancada baixa.','ameaça a bancada baixa e você parte para a Galeria.'),
])
def test_player_other_actor_and_later_actions_not_waived(text):
    with pytest.raises(SceneProposalError,match='scene_player_agency_violation'):
        check(text)


@pytest.mark.asyncio
@pytest.mark.parametrize('unsafe',[False,True])
@pytest.mark.parametrize('observed',[OBSERVED,OBSERVED_L31,OBSERVED_L67])
async def test_help_commit_or_atomic_rejection_and_replay(tmp_path,monkeypatch,unsafe,observed):
    def forbidden(*a,**k):pytest.fail('wait/help/replay must not roll')
    monkeypatch.setattr(rules_service,'calculate_resolution',forbidden)
    db=tmp_path/'threat.sqlite3';store=SQLitePersistence(db)
    await create_campaign_source_session(store,'threat',initial_state=_initial_state())
    for number,(player_input,rule,effects) in enumerate([
        ('Aguardo','R-03',('campaign.warning.visible',)),
        ('Espero','R-03B',('campaign.record.wet',)),
        ('O que precisamos fazer?','R-01',('mara.replies.to_task','campaign.knows.safe_surface')),
    ],1):
        text=PROSE[rule] if number<3 else observed+(' Você ameaça Mara.' if unsafe else '')
        q='Como você quer proceder com o registro molhado?' if number==3 and observed==OBSERVED_L67 else 'O que você faz agora?'
        config,gateway=config_and_gateway(text,effects,q)
        op=f'threat-{number}'
        prepared=await prepare_campaign_source_player_action(store=store,session_id='threat',operation_id=op,player_input=player_input,config=config,deadline=utc_now()+timedelta(seconds=60),cancellation=CancellationToken())
        chunks=[]
        async def deliver(text):chunks.append(text)
        c=prepared.capsule
        result=await execute_campaign_source_turn(store=store,capsule=c,operation_id=op,gateway=gateway,deadline=utc_now()+timedelta(seconds=60),cancellation=CancellationToken(),on_chunk=deliver)
        if number<3:assert result.status=='completed'
    restarted=SQLitePersistence(db)
    snapshot=await read_campaign_source_snapshot(restarted,'threat')
    if unsafe:
        assert result.status=='failed' and snapshot.current_turn==2 and not chunks
        assert snapshot.progression.record=='wet'
    else:
        assert result.status=='completed' and snapshot.current_turn==3
        assert snapshot.progression.record_location=='bench' and snapshot.progression.outcome is None
        replay=await execute_campaign_source_turn(store=restarted,capsule=c,operation_id=op,gateway=gateway,deadline=utc_now()-timedelta(seconds=1),cancellation=CancellationToken(),on_chunk=deliver)
        assert replay.envelope==result.envelope and len(chunks)==1
    assert len(gateway.requests)==1


@pytest.mark.parametrize('suffix',[
    ' Você toma o registro.',
    ' Você abre a porta.',
    ' Você mantém o tom contido e toma o registro.',
    ' Você toma o tom contido de Mara.',
])
def test_nominal_tone_does_not_hide_later_taking(suffix):
    with pytest.raises(SceneProposalError,match='scene_player_agency_violation'):
        check(OBSERVED_L31+suffix)
