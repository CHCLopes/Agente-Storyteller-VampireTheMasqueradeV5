"""L56: explicit examination and coordinated recovery substantiate success."""
from datetime import timedelta
import pytest
from api import rules_service
from api.scene_director_service import SceneProposalError, validate_mechanical_narrative
from api.campaign_source_execution_service import execute_campaign_source_turn
from api.campaign_source_input_service import prepare_campaign_source_player_action
from api.campaign_source_storage import create_campaign_source_session, read_campaign_source_snapshot
from api.llm.contract import CancellationToken, utc_now
from api.persistence import SQLitePersistence
from scripts.preflight_hybrid_campaign_luna_l56 import _fixed_resolution
from scripts.run_campaign_source_offline_trial import _initial_state
from test_campaign_source_integration import config_and_gateway

OBSERVED='Você examina o registro na bancada baixa do Arquivo e recupera informações úteis entre as páginas danificadas. O conteúdo não volta a formar o registro inteiro; parte permanece incompleta, mas o que foi possível extrair agora integra sua compreensão do caso. O registro continua na bancada, em estado parcial. Mara acompanha o exame com atenção e então baixa um pouco a voz: “Há algo aqui. Não é tudo, mas já basta para separar as pistas do ruído.” Ela observa as páginas com cuidado, sem tocar nelas.'

OBSERVED_L72 = 'Na bancada baixa do Arquivo, você examina o registro com cuidado. Entre as páginas danificadas, alguns trechos se deixam reconstruir: informação útil emerge, embora o registro não volte a ficar inteiro. Mara se inclina apenas o bastante para acompanhar a descoberta, mantendo os olhos nas folhas. “Temos algo”, ela diz, apontando para as linhas que ainda podem ser lidas. “O restante continua comprometido.” O registro permanece na bancada, agora parcial, com parte de seu conteúdo recuperada.'

OBSERVED_L73 = 'Você examina o registro sobre a bancada baixa do Arquivo e recupera parte da informação contida nas páginas. O conteúdo não se recompõe por inteiro; trechos permanecem incompletos, enquanto o registro continua na bancada, em estado parcial. Mara se inclina apenas o bastante para acompanhar sua leitura e fala em voz baixa: “Há algo aqui, mas não tudo. O que restou pode ser consultado, embora as lacunas permaneçam.”'

@pytest.mark.parametrize('observed',[OBSERVED,OBSERVED_L72,OBSERVED_L73,
    'Você examina o registro sobre a bancada baixa no Arquivo e consegue recuperar informação útil das partes ainda legíveis. O conteúdo não é restaurado por inteiro; páginas danificadas continuam incompletas. Mara acompanha o resultado e diz: “Conseguimos extrair algo importante, mas o registro ainda está parcial.”'])
def test_coordinated_recovery_honors_success(observed):
    validate_mechanical_narrative(observed,outcome='success',player_input='Examino o registro')

@pytest.mark.parametrize('text',[
    'Você examina o registro na bancada baixa do Arquivo e recupera informações úteis?',
    'Se você examina o registro na bancada baixa do Arquivo e recupera informações úteis, Mara observa.',
    'Mara deseja que você examina o registro na bancada baixa do Arquivo e recupera informações úteis.',
    'Você examina o registro na bancada baixa do Arquivo e não recupera informações úteis.',
    'Mara examina o registro na bancada baixa do Arquivo e recupera informações úteis.',
    'Mara diz: “Você examina o registro na bancada baixa do Arquivo e recupera informações úteis.”',
])
def test_non_player_or_unasserted_recovery_does_not_honor_success(text):
    with pytest.raises(SceneProposalError,match='scene_success_not_honored'):
        validate_mechanical_narrative(text,outcome='success')


NOMINAL='O registro permanece na bancada, agora parcial, com parte de seu conteúdo recuperada.'

@pytest.mark.parametrize('text',[
    NOMINAL[:-1]+'?',
    'Se '+NOMINAL[0].lower()+NOMINAL[1:],
    'Mara deseja que '+NOMINAL[0].lower()+NOMINAL[1:],
    NOMINAL.replace('permanece','não permanece'),
    'Mara diz: “'+NOMINAL+'”',
])
def test_unasserted_or_negated_nominal_state_is_not_success(text):
    with pytest.raises(SceneProposalError,match='scene_success_not_honored'):
        validate_mechanical_narrative(text,outcome='success')


def test_nominal_recovered_content_cannot_be_granted_on_failure():
    with pytest.raises(SceneProposalError,match='scene_failure_granted_goal'):
        validate_mechanical_narrative('A tentativa falha. '+NOMINAL,outcome='failure')


PARTIAL=OBSERVED_L73.split('.')[0]+'.'

@pytest.mark.parametrize('text',[
    PARTIAL[:-1]+'?',
    'Se '+PARTIAL[0].lower()+PARTIAL[1:],
    'Mara deseja que '+PARTIAL[0].lower()+PARTIAL[1:],
    PARTIAL.replace('recupera','não recupera'),
    PARTIAL.replace('Você examina','Mara examina'),
    'Mara diz: “'+PARTIAL+'”',
])
def test_partial_recovery_requires_actual_player_subject(text):
    with pytest.raises(SceneProposalError,match='scene_success_not_honored'):
        validate_mechanical_narrative(text,outcome='success')


def test_partial_recovery_cannot_be_granted_on_failure():
    with pytest.raises(SceneProposalError,match='scene_failure_granted_goal'):
        validate_mechanical_narrative('A tentativa falha. '+PARTIAL,outcome='failure')


@pytest.mark.parametrize('extra',[' Você parte do Arquivo.',' Você abre a porta.',
    ' Você recupera parte da informação e parte do Arquivo.'])
def test_partial_information_noun_never_authorizes_departure(extra):
    from api.narrative_source_profile import validate_source_proposal
    from api.scene_service import SceneState
    with pytest.raises(SceneProposalError,match='scene_player_agency_violation'):
        validate_source_proposal({'n':OBSERVED_L73+extra,'q':'O que você faz agora?'},facts=(),
            current_scene=SceneState(location='Arquivo',npcs_present=('Mara',)),
            player_input='Examino o registro',npc_aliases=('Mara',))

@pytest.mark.asyncio
@pytest.mark.parametrize('unsafe',[False,True])
@pytest.mark.parametrize('observed',[OBSERVED,OBSERVED_L72,OBSERVED_L73])
async def test_success_commit_restart_replay_with_single_roll(tmp_path,monkeypatch,unsafe,observed):
    rolls=[]
    def roll(*a,**kw):rolls.append(True);return _fixed_resolution(True)
    monkeypatch.setattr(rules_service,'calculate_resolution',roll)
    db=tmp_path/'coordinated.sqlite3';store=SQLitePersistence(db)
    await create_campaign_source_session(store,'coordinated',initial_state=_initial_state())
    config,gateway=config_and_gateway(observed+(' Você abre a porta.' if unsafe else ''),('campaign.content.recovered',),'')
    prepared=await prepare_campaign_source_player_action(store=store,session_id='coordinated',operation_id='inspect',
        player_input='Examino o registro',config=config,deadline=utc_now()+timedelta(seconds=60),cancellation=CancellationToken())
    chunks=[]
    async def deliver(text):chunks.append(text)
    result=await execute_campaign_source_turn(store=store,capsule=prepared.capsule,operation_id='inspect',
        gateway=gateway,deadline=utc_now()+timedelta(seconds=60),cancellation=CancellationToken(),on_chunk=deliver)
    restarted=SQLitePersistence(db);snapshot=await read_campaign_source_snapshot(restarted,'coordinated')
    if unsafe:
        assert result.status=='failed' and snapshot.current_turn==0 and not chunks
    else:
        assert result.status=='completed' and snapshot.current_turn==1
        assert snapshot.progression.outcome=='partial' and snapshot.progression.record_location=='bench'
        replay=await execute_campaign_source_turn(store=restarted,capsule=prepared.capsule,operation_id='inspect',
            gateway=gateway,deadline=utc_now()-timedelta(seconds=1),cancellation=CancellationToken(),on_chunk=deliver)
        assert replay.envelope==result.envelope and len(chunks)==1
    assert len(rolls)==1 and len(gateway.requests)==1
