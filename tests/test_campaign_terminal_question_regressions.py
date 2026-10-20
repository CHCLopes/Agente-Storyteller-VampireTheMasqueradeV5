"""L16: terminal partial rescue must not invite a new player action."""
from datetime import timedelta
import pytest
from api.campaign_progression_service import build_campaign_narrator_packet
from api.campaign_source_profile import CampaignSourceProfileError,validate_campaign_source_proposal
from api.campaign_source_execution_service import execute_campaign_source_turn
from api.campaign_source_storage import read_campaign_source_snapshot
from api.llm.contract import CancellationToken,utc_now
from api.persistence import SQLitePersistence
from test_campaign_partial_wording_regressions import prepare
from test_campaign_source_integration import config_and_gateway

OBSERVED = 'Você retira o registro da bancada baixa e o leva com cuidado até a superfície seca na Galeria. O registro permanece parcialmente danificado: a infiltração apagou ou comprometeu parte do conteúdo, mas o que ainda é legível foi salvo. Mara acompanha o transporte sem tocar no documento, mantendo a atenção voltada para a umidade que ficou no Arquivo. Ao ver o registro fora do alcance da água, ela baixa um pouco os ombros, embora a tensão não desapareça. “Certo. O que resistiu está seguro agora. Precisamos trabalhar apenas com essa parte preservada.” O registro permanece na superfície seca da Galeria.'
QUESTION = 'Como você examina o conteúdo legível do registro preservado?'

@pytest.mark.asyncio
@pytest.mark.parametrize('question',[QUESTION,'O que você faz agora?',''])
async def test_terminal_q_contract_is_already_enforced(tmp_path,monkeypatch,question):
    _,_,c,_=await prepare(tmp_path,monkeypatch)
    packet=build_campaign_narrator_packet(c.campaign_request,c.campaign_effect)
    assert packet.state_after.outcome=='partial'
    payload={'n':OBSERVED,'q':question,'realized_effects':['campaign.record.partial']}
    if question:
        with pytest.raises(CampaignSourceProfileError,match='campaign_source_effect_mismatch'):
            validate_campaign_source_proposal(payload,packet=packet,facts=c.draft.facts,snapshot=c.snapshot)
    else:
        # Offline counterfactual only; never rewrite/reclassify the live record.
        assert validate_campaign_source_proposal(payload,packet=packet,facts=c.draft.facts,snapshot=c.snapshot).narrative==OBSERVED

@pytest.mark.asyncio
@pytest.mark.parametrize('question',[QUESTION,''])
async def test_exact_terminal_rejection_or_offline_counterfactual_commit(tmp_path,monkeypatch,question):
    store,db,c,_=await prepare(tmp_path,monkeypatch)
    _,gateway=config_and_gateway(OBSERVED,('campaign.record.partial',),question)
    chunks=[]
    async def deliver(text):chunks.append(text)
    r=await execute_campaign_source_turn(store=store,capsule=c,operation_id='p4',gateway=gateway,
        deadline=utc_now()+timedelta(seconds=60),cancellation=CancellationToken(),on_chunk=deliver)
    restarted=SQLitePersistence(db)
    snapshot=await read_campaign_source_snapshot(restarted,'partial')
    if question:
        assert r.status=='failed' and r.error_code=='campaign_source_policy_failed'
        assert snapshot.current_turn==3 and snapshot.progression.record=='wet'
        assert snapshot.progression.outcome is None and not chunks
    else:
        assert r.status=='completed' and snapshot.current_turn==4 and snapshot.progression.outcome=='partial'
        replay=await execute_campaign_source_turn(store=restarted,capsule=c,operation_id='p4',gateway=gateway,
            deadline=utc_now()-timedelta(seconds=1),cancellation=CancellationToken(),on_chunk=deliver)
        assert replay.envelope==r.envelope and len(chunks)==1
    assert len(gateway.requests)==1
