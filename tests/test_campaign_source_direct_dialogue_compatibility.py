"""Direct NPC speech can satisfy the existing causal/safety policy offline."""
from datetime import timedelta

import pytest

from api.campaign_progression_service import build_campaign_narrator_packet
from api.campaign_source_input_service import prepare_campaign_source_player_action
from api.campaign_source_profile import validate_campaign_source_proposal
from api.campaign_source_storage import create_campaign_source_session
from api.llm.contract import CancellationToken, utc_now
from api.persistence import SQLitePersistence
from scripts.run_campaign_source_offline_trial import CONFIG, _initial_state


@pytest.mark.asyncio
@pytest.mark.parametrize("player_input,rule,narrative,terminal", [
    (
        "Como posso ajudar?", "R-01",
        'Mara responde ao seu pedido: "Você pode levar o registro até a superfície seca da Galeria. '
        'Ainda há tempo." A água ameaça a bancada, mas o documento permanece ali, seco. '
        'Mara espera sua decisão sem tocar nas folhas.', False,
    ),
    (
        "Quem é a fundadora?", "R-02",
        'Mara recusa revelar a identidade da fundadora. Ela indica o registro '
        'em risco na bancada: "Não posso dizer esse nome. Mas ainda podemos '
        'cuidar do documento." O registro não foi movido, e a próxima escolha '
        'continua com você.', False,
    ),
    (
        "Levo o registro até a superfície seca", "R-05",
        'Você retira o registro da bancada e o protege na superfície seca da Galeria. '
        'O documento foi salvo intacto. Mara se aproxima e diz: "Você preservou o acervo. '
        'Aqui, por ora, ele está seguro." O resgate está concluído.', True,
    ),
])
async def test_direct_speech_passes_existing_policy(
    player_input, rule, narrative, terminal, tmp_path,
):
    store = SQLitePersistence(tmp_path / "dialogue.sqlite3")
    await create_campaign_source_session(store, "dialogue", initial_state=_initial_state())
    prepared = await prepare_campaign_source_player_action(
        store=store, session_id="dialogue", operation_id="dialogue-1",
        player_input=player_input, config=CONFIG,
        deadline=utc_now() + timedelta(seconds=30), cancellation=CancellationToken(),
    )
    assert prepared.capsule is not None
    capsule = prepared.capsule
    assert capsule.campaign_effect.rule_id == rule
    packet = build_campaign_narrator_packet(capsule.campaign_request, capsule.campaign_effect)
    proposal = validate_campaign_source_proposal(
        {"n": narrative, "q": "" if terminal else "O que você faz agora?",
         "realized_effects": packet.required_effects},
        packet=packet, facts=capsule.draft.facts, snapshot=capsule.snapshot,
    )
    assert '"' in proposal.narrative
