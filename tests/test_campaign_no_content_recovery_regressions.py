"""L46: failed recovery is distinct from irrecoverable loss of the record."""
from datetime import timedelta
import pytest
from test_scene_attempt_no_content_regressions import TEXT as OBSERVED_L81
from api import rules_service
from api.scene_director_service import SceneProposalError, validate_mechanical_narrative
from api.campaign_source_execution_service import execute_campaign_source_turn
from api.campaign_source_input_service import prepare_campaign_source_player_action
from api.campaign_source_storage import create_campaign_source_session, read_campaign_source_snapshot
from api.llm.contract import CancellationToken, utc_now
from api.persistence import SQLitePersistence
from scripts.preflight_hybrid_campaign_luna_l46 import _fixed_resolution
from scripts.run_campaign_source_offline_trial import _initial_state
from test_campaign_source_integration import config_and_gateway

OBSERVED='Ao examinar o registro na bancada baixa do Arquivo, você não recupera nenhum conteúdo. A umidade se espalha pelas páginas, deixando o registro molhado e comprometendo o que estava escrito. Mara observa a mudança de perto; a tensão toma o ambiente, e sua expressão se fecha. “Não há nada legível aqui agora”, ela diz, sem tirar os olhos do registro. O registro permanece na bancada baixa do Arquivo, molhado, enquanto a investigação chega ao fim sem revelar informação.'
SAFE=OBSERVED.replace('Não há nada legível aqui agora', 'A água molhou o registro. Ainda há trechos a salvar')
OBSERVED_L59='Ao examinar o registro na bancada baixa do Arquivo, você não recupera seu conteúdo. A água alcança as páginas e molha o registro, fazendo a escrita se espalhar sob seus olhos. Mara se inclina, tensa, sem tocar no objeto. “Ainda pode haver algo legível”, ela diz, acompanhando o dano com atenção. O registro permanece na bancada, molhado, e a tentativa deixa de revelar o que você procurava.'
SAFE_L59=OBSERVED_L59.replace('e a tentativa deixa de revelar o que você procurava', 'e a investigação termina sem recuperar conteúdo')
OBSERVED_L53='Ao examinar o registro na bancada baixa do Arquivo, você não recupera seu conteúdo. A água alcança as páginas, e o registro fica molhado, ainda apoiado na bancada. Mara se aproxima, observando as folhas úmidas com tensão contida. “Cuidado. Ainda pode haver algo recuperável, mas não assim.”'
OBSERVED_L52='Sua tentativa de examinar o registro não recupera conteúdo algum. A água alcança a bancada baixa no Arquivo e molha as páginas do registro, borrando o que estava marcado sem tornar tudo irrecuperável. Mara observa o dano de perto, tensa, e fala baixo: “Ainda há algo que pode ser salvo, mas não assim.” O registro permanece molhado sobre a bancada, sem ser deslocado.'
OBSERVED_L48='Ao examinar o registro sobre a bancada baixa do Arquivo, você não consegue recuperar nenhum conteúdo nesta tentativa. A umidade se espalha pelas folhas, deixando o registro molhado, mas ainda há sinais de que parte dele pode ser recuperada. Mara se aproxima, observando as páginas com o cenho franzido. “Cuidado”, ela diz, mantendo a voz baixa. “Ainda não está perdido, mas cada marca d’água torna a leitura mais difícil.” O registro permanece na bancada; nada em sua posição muda, e o ambiente agora carrega uma tensão evidente.'

@pytest.mark.parametrize('text', [OBSERVED, OBSERVED_L48, OBSERVED_L52, OBSERVED_L53])
def test_explicit_player_no_content_honors_failure(text):
    validate_mechanical_narrative(text,outcome='failure',player_input='Examino o registro')

@pytest.mark.parametrize('text',[
    'A água alcança a bancada baixa no Arquivo e molha as páginas do registro.',
    'A água alcança as páginas.',
])
def test_water_reaching_bench_cannot_substantiate_player_success(text):
    with pytest.raises(SceneProposalError,match='scene_success_not_honored'):
        validate_mechanical_narrative(text,outcome='success')

def test_actual_player_reaching_bench_still_grants_goal_in_failure():
    with pytest.raises(SceneProposalError,match='scene_failure_granted_goal'):
        validate_mechanical_narrative(OBSERVED_L52.replace('A água alcança','Você alcança'),
            outcome='failure',player_input='Examino o registro')

def test_quoted_npc_recovery_does_not_substantiate_success():
    with pytest.raises(SceneProposalError,match='scene_success_not_honored'):
        validate_mechanical_narrative('Mara diz: “Você recupera informações úteis.”',outcome='success')

@pytest.mark.parametrize('text', [
    OBSERVED_L48.replace('o ambiente agora carrega uma tensão evidente', 'você carrega o registro'),
    OBSERVED_L48+' Você carrega o registro.',
    OBSERVED_L48+' Você segura o registro.',
    OBSERVED_L48+' Você recupera informações úteis.',
])
def test_environmental_tension_never_hides_real_goal_or_possession(text):
    with pytest.raises(SceneProposalError, match='scene_failure_granted_goal'):
        validate_mechanical_narrative(text,outcome='failure',player_input='Examino o registro')

@pytest.mark.parametrize('text',[
    'Você recupera nenhum conteúdo.',
    'Você não recupera nenhum conteúdo?',
    'Mara diz: “Você não recupera nenhum conteúdo.”',
    'Se você não recupera nenhum conteúdo, Mara observa.',
    'Se a investigação prosseguir, você não recupera nenhum conteúdo.',
    'Mara deseja que você não recupera nenhum conteúdo.',
    'Sua tentativa de examinar o registro não recupera conteúdo algum?',
    'Se sua tentativa de examinar o registro não recupera conteúdo algum, Mara observa.',
    'Mara diz: “Sua tentativa de examinar o registro não recupera conteúdo algum.”',
    'Sua tentativa de examinar o registro recupera conteúdo algum.',
    'Você não recupera seu conteúdo?',
    'Se você não recupera seu conteúdo, Mara observa.',
    'Mara diz: “Você não recupera seu conteúdo.”',
    'Você recupera seu conteúdo.',
])
def test_non_assertions_cannot_substantiate_failure(text):
    with pytest.raises(SceneProposalError,match='scene_failure_not_honored'):
        validate_mechanical_narrative(text,outcome='failure')

@pytest.mark.parametrize('suffix',[' Você encontra uma pista.',' Você recupera informações úteis.'])
@pytest.mark.parametrize('text',[SAFE, OBSERVED_L52, OBSERVED_L53])
def test_negative_recovery_never_hides_a_later_success(suffix,text):
    with pytest.raises(SceneProposalError,match='scene_failure_granted_goal'):
        validate_mechanical_narrative(text+suffix,outcome='failure',player_input='Examino o registro')

@pytest.mark.asyncio
@pytest.mark.parametrize('text,accepted',[(OBSERVED,False),(SAFE,True),(SAFE+' Você abre a porta.',False),
    (OBSERVED_L48,True),(OBSERVED_L48+' Você carrega o registro.',False),
    (OBSERVED_L48+' Você leva o registro.',False),
    (OBSERVED_L52,True),(OBSERVED_L52+' Você recupera informações úteis.',False),
    (OBSERVED_L53,True),(OBSERVED_L53+' Você recupera informações úteis.',False),
    (OBSERVED_L59,False),(SAFE_L59,True),(SAFE_L59+' Você abre a porta.',False),
    (SAFE_L59+' Você recupera informações úteis.',False),
    (OBSERVED_L81,True),(OBSERVED_L81+' Você abre a porta.',False),
    (OBSERVED_L81+' Você recupera informações úteis.',False)])
async def test_wet_not_lost_atomicity_restart_and_single_rng(tmp_path,monkeypatch,text,accepted):
    rolls=[]
    def roll(*a,**kw):rolls.append(True);return _fixed_resolution(False)
    monkeypatch.setattr(rules_service,'calculate_resolution',roll)
    db=tmp_path/'recovery.sqlite3';store=SQLitePersistence(db)
    await create_campaign_source_session(store,'recovery',initial_state=_initial_state())
    config,gateway=config_and_gateway(text,('campaign.inspect.failed',),'O que você faz agora?')
    prepared=await prepare_campaign_source_player_action(store=store,session_id='recovery',operation_id='inspect',
        player_input='Examino o registro',config=config,deadline=utc_now()+timedelta(seconds=60),cancellation=CancellationToken())
    chunks=[]
    async def deliver(text):chunks.append(text)
    result=await execute_campaign_source_turn(store=store,capsule=prepared.capsule,operation_id='inspect',
        gateway=gateway,deadline=utc_now()+timedelta(seconds=60),cancellation=CancellationToken(),on_chunk=deliver)
    restarted=SQLitePersistence(db);snapshot=await read_campaign_source_snapshot(restarted,'recovery')
    if not accepted:
        assert result.status=='failed' and snapshot.current_turn==0 and not chunks
    else:
        assert result.status=='completed' and snapshot.current_turn==1
        assert snapshot.progression.record=='wet' and snapshot.progression.outcome is None
        replay=await execute_campaign_source_turn(store=restarted,capsule=prepared.capsule,operation_id='inspect',
            gateway=gateway,deadline=utc_now()-timedelta(seconds=1),cancellation=CancellationToken(),on_chunk=deliver)
        assert replay.envelope==result.envelope and len(chunks)==1
    assert len(rolls)==1 and len(gateway.requests)==1
