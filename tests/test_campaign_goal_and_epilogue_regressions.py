"""L82 audit: narrator cannot replace rescue with inspection or repeat a move."""
from datetime import timedelta
import pytest
from api import rules_service
from api.campaign_source_execution_service import execute_campaign_source_turn
from api.campaign_source_input_service import prepare_campaign_source_player_action
from api.campaign_source_storage import create_campaign_source_session,read_campaign_source_snapshot
from api.llm.contract import CancellationToken,utc_now
from api.persistence import SQLitePersistence
from scripts.run_campaign_source_offline_trial import _initial_state
from test_campaign_source_integration import config_and_gateway

HELP='Mara aponta para o registro ameaçado sobre a bancada baixa no Arquivo. “A tarefa é examinar o documento e descobrir o que ele registra antes que o risco cause mais dano. A superfície seca fica na Galeria; ela pode proteger o registro da água, mas será preciso agir com cuidado.” O registro continua na bancada, sem ser movido, enquanto Mara acompanha a situação com atenção serena.'
END='Você retira o registro da bancada baixa no Arquivo e o leva até a superfície seca na Galeria. O documento é protegido intacto, longe da água e do risco que o ameaçava. Mara acompanha o deslocamento e solta o ar, aliviada. “Está salvo. Coloque-o com cuidado sobre a superfície seca; assim, suas páginas permanecem protegidas.” Ela observa o registro agora preservado, sem tocá-lo nem movê-lo novamente.'

@pytest.mark.asyncio
@pytest.mark.parametrize('case',['help','end'])
@pytest.mark.parametrize('variant',['raw','safe','extra'])
async def test_goal_and_epilogue_atomicity_restart_replay(tmp_path,monkeypatch,case,variant):
    def forbidden(*a,**kw):pytest.fail('dialogue/rescue/replay must not roll')
    monkeypatch.setattr(rules_service,'calculate_resolution',forbidden)
    text=HELP if case=='help' else END
    if variant!='raw':
        text=text.replace('A tarefa é examinar o documento e descobrir o que ele registra antes que o risco cause mais dano.',
            'A tarefa é preservar o documento antes que a água danifique suas páginas.')
        text=text.replace('Coloque-o com cuidado sobre a superfície seca; assim, suas páginas permanecem protegidas.',
            'Suas páginas permanecem protegidas sobre a superfície seca.')
    if variant=='extra':text+=' Você abre a porta.'
    db=tmp_path/'goal.sqlite3';store=SQLitePersistence(db)
    await create_campaign_source_session(store,'goal',initial_state=_initial_state())
    effects=('mara.replies.to_task','campaign.knows.safe_surface') if case=='help' else ('campaign.record.preserved',)
    config,gateway=config_and_gateway(text,effects,'O que você faz agora?' if case=='help' else '')
    prepared=await prepare_campaign_source_player_action(store=store,session_id='goal',operation_id='op',
        player_input='Qual é a tarefa?' if case=='help' else 'Retiro o registro',config=config,
        deadline=utc_now()+timedelta(seconds=60),cancellation=CancellationToken())
    chunks=[]
    async def deliver(value):chunks.append(value)
    result=await execute_campaign_source_turn(store=store,capsule=prepared.capsule,operation_id='op',gateway=gateway,
        deadline=utc_now()+timedelta(seconds=60),cancellation=CancellationToken(),on_chunk=deliver)
    restarted=SQLitePersistence(db);snapshot=await read_campaign_source_snapshot(restarted,'goal')
    if variant=='safe':
        assert result.status=='completed' and snapshot.current_turn==1
        assert snapshot.progression.outcome==(None if case=='help' else 'preserved')
        replay=await execute_campaign_source_turn(store=restarted,capsule=prepared.capsule,operation_id='op',gateway=gateway,
            deadline=utc_now()-timedelta(seconds=1),cancellation=CancellationToken(),on_chunk=deliver)
        assert replay.envelope==result.envelope and len(chunks)==1
    else:
        assert result.status=='failed' and snapshot.current_turn==0 and not chunks
        assert snapshot.progression.record=='threatened' and snapshot.progression.outcome is None
    assert len(gateway.requests)==1
