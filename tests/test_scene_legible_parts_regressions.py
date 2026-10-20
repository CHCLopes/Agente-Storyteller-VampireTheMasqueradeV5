"""L28: nominal legible parts are not the player's departure."""
import pytest
from datetime import timedelta
from api import rules_service
from api.campaign_source_execution_service import execute_campaign_source_turn
from api.campaign_source_input_service import prepare_campaign_source_player_action
from api.campaign_source_storage import create_campaign_source_session, read_campaign_source_snapshot
from api.llm.contract import CancellationToken, utc_now
from api.persistence import SQLitePersistence
from scripts.preflight_hybrid_campaign_luna_l28 import _fixed_resolution
from scripts.run_campaign_source_offline_trial import _initial_state
from test_campaign_source_integration import config_and_gateway
from api.narrative_source_profile import validate_source_proposal
from api.scene_director_service import SceneProposalError, _action_signature_matches, validate_mechanical_narrative
from api.scene_service import SceneState

OBSERVED = 'Ao examinar o registro sobre a bancada baixa no Arquivo, você recupera informação útil de suas partes ainda legíveis. O conteúdo encontrado esclarece aspectos relevantes do registro, mas permanece incompleto: o registro não é restaurado por inteiro e continua parcial. Mara acompanha a leitura com atenção, sem interferir, enquanto os trechos recuperados se tornam conhecidos para você. O registro permanece na bancada baixa no Arquivo.'
OBSERVED_L29 = 'Ao examinar o registro na bancada baixa do Arquivo, você recupera informação útil entre as partes ainda legíveis. O conteúdo esclarece um trecho importante, mas não recompõe o registro inteiro. O registro permanece parcial e continua sobre a bancada, enquanto Mara acompanha a investigação sem interferir.'
OBSERVED_L33 = 'Você examina o registro sobre a bancada baixa no Arquivo, seguindo marcas e trechos ainda legíveis. A investigação recupera informação útil, suficiente para revelar parte do conteúdo, mas o registro continua incompleto; o material danificado não é restaurado. O registro permanece na bancada baixa, e sua condição agora é parcial. Mara observa as páginas ao seu lado e fala em tom contido: “Há algo aqui. Não é o registro inteiro, mas já basta para separar o que ainda pode ser lido do que se perdeu.”'
OBSERVED_L38 = 'Ao examinar o registro sobre a bancada baixa do Arquivo, você recupera informações úteis entre as partes ainda legíveis. Os trechos preservados ajudam a recompor o conteúdo, mas lacunas permanecem e o registro não é restaurado por inteiro. Mara acompanha a análise de perto, inclinando-se sobre as páginas sem tocá-las. “Isso já nos dá algo concreto para trabalhar”, ela diz, com cautela. O registro permanece parcial sobre a bancada baixa, enquanto a descoberta é incorporada ao que você sabe.'


def check(text):
    return validate_source_proposal({'n':text,'q':'O que você faz agora?'}, facts=(),
        current_scene=SceneState(location='Arquivo',npcs_present=('Mara',)),
        player_input='Examino o registro',npc_aliases=('Mara',))


@pytest.mark.parametrize('text',[OBSERVED,OBSERVED_L29])
def test_nominal_parts_not_departure(text):
    assert not any(family=='depart' for _,family,_ in _action_signature_matches(text))


@pytest.mark.parametrize('text',[OBSERVED,OBSERVED_L29,OBSERVED_L33,OBSERVED_L38])
def test_exact_r07_prose_has_no_new_player_action(text):
    assert check(text).narrative == text


@pytest.mark.parametrize('suffix', [' Você parte para a Galeria.',
                                   ' Você partes ainda legíveis e abre a porta.',
                                   ' Você abre a porta.',
                                   ' Você parte.',
                                   ' Você recupera suas partes e sai do Arquivo.'])
def test_later_actions_are_still_rejected(suffix):
    with pytest.raises(SceneProposalError):
        check(OBSERVED+suffix)


def test_bare_parts_is_not_silently_ignored():
    assert any(family=='depart' for _,family,_ in _action_signature_matches('Você partes para a Galeria.'))


@pytest.mark.parametrize('text',[
    'Você parte entre as partes ainda legíveis.',
    'Entre as partes ainda legíveis, você parte para a Galeria.',
    'Você examina entre as partes ainda legíveis. Você abre a porta.',
    'Você partes ainda legíveis.',
])
def test_l29_nominal_frame_does_not_hide_actions(text):
    with pytest.raises(SceneProposalError):
        check('O registro permanece sobre a bancada baixa no Arquivo. '+text)


@pytest.mark.parametrize('text',['Você recupera informação útil do registro.','Você recupera informações úteis do registro.'])
def test_recovered_useful_information_is_a_positive_result_not_allowed_on_failure(text):
    validate_mechanical_narrative(text,outcome='success')
    with pytest.raises(SceneProposalError,match='scene_failure_granted_goal'):
        validate_mechanical_narrative('A tentativa falha. '+text,outcome='failure')


@pytest.mark.parametrize('text',[
    'Você não recupera informação útil do registro.',
    'Você tenta recuperar informação útil do registro.',
    'Você recupera informação útil do registro?',
    'Mara diz: “Você recupera informação útil do registro.”',
    'Se você recupera informação útil do registro, Mara ajuda.',
    'Talvez você recupera informação útil do registro.',
    'Mara recupera informação útil do registro.',
    'Você não recupera informações úteis do registro.',
    'Se você recupera informações úteis do registro, Mara ajuda.',
])
def test_negative_attempt_question_or_dialogue_is_not_result(text):
    with pytest.raises(SceneProposalError,match='scene_success_not_honored'):
        validate_mechanical_narrative(text,outcome='success')


@pytest.mark.asyncio
@pytest.mark.parametrize('unsafe',[False,True])
@pytest.mark.parametrize('text',[OBSERVED,OBSERVED_L29,OBSERVED_L33,OBSERVED_L38])
async def test_r07_commit_or_atomic_rejection_and_replay(tmp_path,monkeypatch,unsafe,text):
    rolls=[]
    def roll(*args,**kwargs):
        rolls.append(True)
        return _fixed_resolution(True)
    monkeypatch.setattr(rules_service,'calculate_resolution',roll)
    db=tmp_path/'r07.sqlite3';store=SQLitePersistence(db)
    await create_campaign_source_session(store,'r07',initial_state=_initial_state())
    config,gateway=config_and_gateway(text+(' Você abre a porta.' if unsafe else ''),('campaign.content.recovered',),'')
    prepared=await prepare_campaign_source_player_action(store=store,session_id='r07',operation_id='inspect',player_input='Examino o registro',config=config,deadline=utc_now()+timedelta(seconds=60),cancellation=CancellationToken())
    chunks=[]
    async def deliver(text):chunks.append(text)
    c=prepared.capsule
    result=await execute_campaign_source_turn(store=store,capsule=c,operation_id='inspect',gateway=gateway,deadline=utc_now()+timedelta(seconds=60),cancellation=CancellationToken(),on_chunk=deliver)
    restarted=SQLitePersistence(db)
    snapshot=await read_campaign_source_snapshot(restarted,'r07')
    assert len(rolls)==1 and len(gateway.requests)==1
    if unsafe:
        assert result.status=='failed' and result.error_code=='campaign_source_policy_failed'
        assert snapshot.current_turn==0 and snapshot.progression.outcome is None and not chunks
    else:
        assert result.status=='completed' and snapshot.current_turn==1
        assert snapshot.progression.outcome=='partial' and snapshot.progression.record_location=='bench'
        replay=await execute_campaign_source_turn(store=restarted,capsule=c,operation_id='inspect',gateway=gateway,deadline=utc_now()-timedelta(seconds=1),cancellation=CancellationToken(),on_chunk=deliver)
        assert replay.envelope==result.envelope and len(chunks)==1
        assert len(rolls)==1 and len(gateway.requests)==1


@pytest.mark.parametrize('text',[
    OBSERVED_L33+' Você segue Mara.',
    OBSERVED_L33+' Você parte para a Galeria.',
    OBSERVED_L33.replace('seguindo marcas e trechos ainda legíveis','seguindo Mara até a Galeria'),
    OBSERVED_L33.replace('seguindo marcas e trechos ainda legíveis.','seguindo marcas e trechos ainda legíveis. Você abre a porta.'),
])
def test_reading_frame_never_waives_physical_following(text):
    with pytest.raises(SceneProposalError,match='scene_player_agency_violation'):
        check(text)
