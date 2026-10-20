"""L50: salvaging what remains legible realizes a partial rescue."""
from datetime import timedelta
import pytest
from api import rules_service
from api.campaign_source_execution_service import execute_campaign_source_turn
from api.campaign_source_input_service import prepare_campaign_source_player_action
from api.campaign_source_storage import create_campaign_source_session, read_campaign_source_snapshot
from api.campaign_source_offline_corpus import PROSE
from api.llm.contract import CancellationToken, utc_now
from api.persistence import SQLitePersistence
from scripts.run_campaign_source_offline_trial import _initial_state
from test_campaign_source_integration import config_and_gateway

OBSERVED='Você retira o registro da bancada baixa no Arquivo e o leva até a superfície seca na Galeria. O registro fica fora da infiltração. O que ainda é legível é salvo, mas as páginas já molhadas continuam danificadas, e o conteúdo perdido não é recuperado. Mara acompanha o resultado com atenção tensa e diz: “Está fora da água. Salvamos o que ainda podia ser lido, mas o dano anterior permanece.”'

@pytest.mark.asyncio
@pytest.mark.parametrize('variant',['observed','negation','question','hypothesis','player_action'])
async def test_partial_salvage_preserves_damage_and_atomicity(tmp_path,monkeypatch,variant):
    def forbidden(*a,**k):pytest.fail('waiting/rescue/replay must not roll')
    monkeypatch.setattr(rules_service,'calculate_resolution',forbidden)
    db=tmp_path/'salvage.sqlite3';store=SQLitePersistence(db)
    await create_campaign_source_session(store,'salvage',initial_state=_initial_state())
    text=OBSERVED
    if variant=='negation':text=text.replace('é legível é salvo','é legível não é salvo')
    if variant=='question':text=text.replace('é salvo, mas','é salvo? Mas')
    if variant=='hypothesis':text=text.replace('O que ainda é legível é salvo','Se o que ainda é legível é salvo')
    if variant=='player_action':text+=' Você abre a porta.'
    for turn,(player_input,rule,effects) in enumerate([
        ('Aguardo','R-03',('campaign.warning.visible',)),
        ('Espero','R-03B',('campaign.record.wet',)),
        ('Retiro o registro','R-06',('campaign.record.partial',)),
    ],1):
        config,gateway=config_and_gateway(PROSE[rule] if turn<3 else text,effects,'' if turn==3 else 'O que você faz agora?')
        op=f'salvage-{turn}'
        prepared=await prepare_campaign_source_player_action(store=store,session_id='salvage',operation_id=op,
            player_input=player_input,config=config,deadline=utc_now()+timedelta(seconds=60),cancellation=CancellationToken())
        chunks=[]
        async def deliver(text):chunks.append(text)
        result=await execute_campaign_source_turn(store=store,capsule=prepared.capsule,operation_id=op,
            gateway=gateway,deadline=utc_now()+timedelta(seconds=60),cancellation=CancellationToken(),on_chunk=deliver)
        if turn<3:assert result.status=='completed'
    restarted=SQLitePersistence(db);snapshot=await read_campaign_source_snapshot(restarted,'salvage')
    if variant=='observed':
        assert result.status=='completed' and snapshot.current_turn==3
        assert snapshot.progression.outcome=='partial' and snapshot.progression.record_location=='dry_surface'
        replay=await execute_campaign_source_turn(store=restarted,capsule=prepared.capsule,operation_id=op,
            gateway=gateway,deadline=utc_now()-timedelta(seconds=1),cancellation=CancellationToken(),on_chunk=deliver)
        assert replay.envelope==result.envelope and len(chunks)==1
    else:
        assert result.status=='failed' and snapshot.current_turn==2 and not chunks
        assert snapshot.progression.record=='wet' and snapshot.progression.outcome is None
    assert len(gateway.requests)==1
