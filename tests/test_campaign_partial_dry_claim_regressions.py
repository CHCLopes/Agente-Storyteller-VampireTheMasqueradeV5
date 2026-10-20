"""L75 qualitative audit: dry surface does not imply pages dried."""
from datetime import timedelta
import pytest
from api import rules_service
from api.campaign_source_offline_corpus import PROSE
from api.campaign_source_execution_service import execute_campaign_source_turn
from api.campaign_source_input_service import prepare_campaign_source_player_action
from api.campaign_source_storage import create_campaign_source_session,read_campaign_source_snapshot
from api.llm.contract import CancellationToken,utc_now
from api.persistence import SQLitePersistence
from scripts.run_campaign_source_offline_trial import _initial_state
from test_campaign_source_integration import config_and_gateway

OBSERVED='Você retira o registro da bancada baixa no Arquivo e o leva até uma superfície seca na Galeria. As páginas molhadas deixam manchas de tinta espalhada; o dano permanece, mas o que ainda estava legível é preservado. Mara acompanha o registro com o olhar e se aproxima, falando baixo: “Está seco agora. O que restou legível foi salvo, embora muita coisa tenha se perdido nas manchas.” O registro fica sobre a superfície seca da Galeria, parcialmente preservado.'

@pytest.mark.asyncio
@pytest.mark.parametrize('variant',['observed','named_dry','safe','negated','extra','l80_raw','l80_safe','l82_raw','l82_safe'])
async def test_partial_rescue_preserves_wet_damage_and_atomicity(tmp_path,monkeypatch,variant):
    def forbidden(*a,**kw):pytest.fail('rescue/replay must not roll')
    monkeypatch.setattr(rules_service,'calculate_resolution',forbidden)
    text=OBSERVED.replace('Está seco agora.','Está fora da água.')
    if variant=='observed':text=OBSERVED
    if variant=='named_dry':text+=' O registro está seco agora.'
    if variant=='negated':text=OBSERVED.replace('Está seco agora.','Não está seco agora.')
    if variant=='extra':text+=' Você abre a porta.'
    if variant.startswith('l80'):
        text='Você retira o registro da bancada baixa do Arquivo e o leva até uma superfície seca na Galeria. As páginas ainda molhadas exibem manchas irregulares, e apenas o que permaneceu legível é salvo; o dano da água continua visível. Mara se inclina para observar o volume e diz: “Está seco por fora, mas as páginas danificadas não voltaram ao que eram. O que ainda se consegue ler foi preservado.”'
        if variant=='l80_safe':text=text.replace('Está seco por fora','Está fora da água')
    if variant.startswith('l82'):
        text='Você retira o registro da bancada baixa no Arquivo e o coloca na superfície seca da Galeria. O que ainda é legível foi salvo, mas as páginas já molhadas continuam danificadas. Mara acompanha o resultado com urgência contida e diz: “Está salvo o que ainda podia ser lido. O dano anterior não foi desfeito; precisamos tratar essas páginas com cuidado.”'
        if variant=='l82_safe':text=text.replace('; precisamos tratar essas páginas com cuidado','')
    accepted=variant in {'safe','negated','l80_safe','l82_safe'}
    db=tmp_path/'dry.sqlite3';store=SQLitePersistence(db)
    await create_campaign_source_session(store,'dry',initial_state=_initial_state())
    for number,(action,rule,effects) in enumerate([
        ('Aguardo','R-03',('campaign.warning.visible',)),
        ('Espero','R-03B',('campaign.record.wet',)),
        ('Retiro o registro','R-06',('campaign.record.partial',)),
    ],1):
        config,gateway=config_and_gateway(PROSE[rule] if number<3 else text,effects,'' if number==3 else 'O que você faz agora?')
        op=f'dry-{number}'
        prepared=await prepare_campaign_source_player_action(store=store,session_id='dry',operation_id=op,player_input=action,
            config=config,deadline=utc_now()+timedelta(seconds=60),cancellation=CancellationToken())
        chunks=[]
        async def deliver(value):chunks.append(value)
        c=prepared.capsule
        result=await execute_campaign_source_turn(store=store,capsule=c,operation_id=op,gateway=gateway,
            deadline=utc_now()+timedelta(seconds=60),cancellation=CancellationToken(),on_chunk=deliver)
        if number<3:assert result.status=='completed'
    restarted=SQLitePersistence(db);snapshot=await read_campaign_source_snapshot(restarted,'dry')
    if accepted:
        assert result.status=='completed' and snapshot.current_turn==3
        assert snapshot.progression.outcome=='partial' and snapshot.progression.record_location=='dry_surface'
        replay=await execute_campaign_source_turn(store=restarted,capsule=c,operation_id=op,gateway=gateway,
            deadline=utc_now()-timedelta(seconds=1),cancellation=CancellationToken(),on_chunk=deliver)
        assert replay.envelope==result.envelope and len(chunks)==1
    else:
        assert result.status=='failed' and snapshot.current_turn==2 and not chunks
        assert snapshot.progression.record=='wet' and snapshot.progression.outcome is None
    assert len(gateway.requests)==1
