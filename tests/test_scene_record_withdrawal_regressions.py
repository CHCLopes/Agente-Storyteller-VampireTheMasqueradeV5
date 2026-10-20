"""L17: moving the record away from infiltration is not player withdrawal."""
from datetime import timedelta
import pytest
from api import rules_service
from api.narrative_source_profile import validate_source_proposal
from api.scene_director_service import SceneProposalError, _action_signature_matches
from api.scene_service import SceneState
from api.campaign_source_execution_service import execute_campaign_source_turn
from api.campaign_source_input_service import prepare_campaign_source_player_action
from api.campaign_source_storage import create_campaign_source_session, read_campaign_source_snapshot
from api.llm.contract import CancellationToken, utc_now
from api.persistence import SQLitePersistence
from test_campaign_source_integration import config_and_gateway
from test_narrative_source_input_service import state
from api.campaign_source_offline_corpus import PROSE

OBSERVED = 'Você retira o registro da bancada baixa no Arquivo e o coloca na superfície seca da Galeria, afastando-o da infiltração. O que ainda é legível é salvo, mas a umidade já comprometeu parte do conteúdo, e esse dano não é revertido. Mara acompanha a transferência com atenção tensa e só relaxa quando o registro fica sobre a superfície seca. “Pelo menos o que restou legível está a salvo”, ela diz, mantendo os olhos nas páginas danificadas. O registro permanece parcialmente comprometido, agora fora da água, e o resgate é encerrado com conteúdo incompleto.'

OBSERVED_L64 = 'Você retira o registro molhado da bancada baixa, afastando-o da água que se espalha pelo Arquivo, e o leva até a superfície seca na Galeria. Parte das páginas ensopadas permanece danificada, mas o que ainda é legível fica salvo. Mara acompanha o deslocamento e examina o registro sobre a superfície seca, sem desfazer o dano anterior. “Está fora da água”, diz, com alívio contido. “O que resistiu ainda pode ser lido; algumas páginas, porém, não voltam ao estado de antes.”'

def check(text):
    return validate_source_proposal({'n':text,'q':'O que você faz agora?'}, facts=(),
        current_scene=SceneState(location='Arquivo',npcs_present=('Mara',)),
        player_input='Retiro o registro',npc_aliases=('Mara',))

@pytest.mark.parametrize('observed',[OBSERVED,OBSERVED_L64])
def test_exact_temporal_record_withdrawal_clause_is_not_player_movement(observed):
    assert check(observed).narrative == observed

def test_clitic_without_local_record_antecedent_is_not_waived():
    assert any(family == 'withdraw' for _,family,_ in _action_signature_matches(
        'Você aguarda, afastando-o da infiltração.'))
    assert any(family == 'withdraw' for _,family,_ in _action_signature_matches(
        'Você retira o registro. Afastando-o da infiltração.'))


@pytest.mark.parametrize('text',[
    OBSERVED_L64.replace('afastando-o','afastando-se'),
    OBSERVED_L64.replace('retira o registro molhado da bancada baixa','aguarda'),
    OBSERVED_L64.replace('afastando-o','afastando você'),
    OBSERVED_L64.replace('pelo Arquivo,','pelo Arquivo e você abre a porta,',1),
])
def test_l64_clitic_does_not_allow_other_antecedents_or_actions(text):
    with pytest.raises(SceneProposalError,match='scene_player_agency_violation'):
        check(text)

@pytest.mark.parametrize('replacement', [
    'afastando-se da infiltração.',
    'afastando-o da infiltração, você avança para a Galeria.',
    'afastando-o da infiltração. Você parte do Arquivo.',
    'afastando-o da infiltração e você abre a porta.',
    'afastando você da infiltração.',
])
def test_other_actors_or_later_actions_do_not_inherit_the_exception(replacement):
    with pytest.raises(SceneProposalError,match='scene_player_agency_violation'):
        check(OBSERVED.replace('afastando-o da infiltração.',replacement))

@pytest.mark.asyncio
@pytest.mark.parametrize('unsafe',[False,True])
@pytest.mark.parametrize('observed',[OBSERVED,OBSERVED_L64])
async def test_partial_rescue_commits_once_or_rolls_back(tmp_path,monkeypatch,unsafe,observed):
    def forbidden_roll(*_a,**_kw):
        pytest.fail('waiting/help/rescue and replay may not roll')
    monkeypatch.setattr(rules_service,'calculate_resolution',forbidden_roll)
    db=tmp_path/'record_withdrawal.sqlite3'
    store=SQLitePersistence(db)
    await create_campaign_source_session(store,'record_withdrawal',initial_state=state())
    chunks=[]
    async def deliver(text):chunks.append(text)
    for number,(player_input,rule,effects) in enumerate([
        ('Aguardo','R-03',('campaign.warning.visible',)),
        ('Espero','R-03B',('campaign.record.wet',)),
        ('Como posso ajudar?','R-01',('mara.replies.to_task','campaign.knows.safe_surface')),
        ('Retiro o registro','R-06',('campaign.record.partial',)),
    ],1):
        text=PROSE[rule] if number<4 else observed+(' Você avança para a Galeria.' if unsafe else '')
        config,gateway=config_and_gateway(text,effects,'' if number==4 else 'O que você faz agora?')
        op=f'record_withdrawal-{number}'
        p=await prepare_campaign_source_player_action(store=store,session_id='record_withdrawal',operation_id=op,
            player_input=player_input,config=config,deadline=utc_now()+timedelta(seconds=60),cancellation=CancellationToken())
        assert p.capsule.campaign_effect.rule_id==rule
        result=await execute_campaign_source_turn(store=store,capsule=p.capsule,operation_id=op,gateway=gateway,
            deadline=utc_now()+timedelta(seconds=60),cancellation=CancellationToken(),on_chunk=deliver)
        if number<4:assert result.status=='completed'
    restarted=SQLitePersistence(db)
    snapshot=await read_campaign_source_snapshot(restarted,'record_withdrawal')
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
