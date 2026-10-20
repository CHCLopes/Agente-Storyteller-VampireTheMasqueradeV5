"""HYP-007-L7: adding an article does not change who owns the next action."""
import re
from datetime import timedelta

import pytest

from api.scene_director_service import SceneProposalError, _validate_player_prompt
from api.campaign_source_profile import validate_campaign_source_proposal
from api.campaign_progression_service import build_campaign_narrator_packet
from test_campaign_source_capsule import capsule
from test_campaign_source_integration import config_and_gateway
from test_narrative_source_input_service import state
from api import rules_service
from api.campaign_source_execution_service import execute_campaign_source_turn
from api.campaign_source_input_service import prepare_campaign_source_player_action
from api.campaign_source_storage import create_campaign_source_session, read_campaign_source_snapshot
from api.llm.contract import CancellationToken, utc_now
from api.persistence import SQLitePersistence


OBSERVED = {
    'n': 'Enquanto você aguarda, a infiltração aumenta nas proximidades do Arquivo, tornando o risco imediato. Mara permanece junto à bancada baixa e observa a situação com atenção redobrada. “Não espere mais sinais”, ela diz, mantendo a voz baixa. “O perigo já está aqui.” O registro continua seco, intacto sobre a bancada baixa no Arquivo, mas agora está marcado como advertido. A tensão da sala se torna vigilante, sem que nenhuma descoberta adicional se revele.',
    'q': 'Qual é a sua próxima ação diante do risco imediato?',
    'realized_effects': ['campaign.warning.visible'],
}


def test_exact_l7_response_passes_offline_without_rewriting():
    retained = capsule()
    packet = build_campaign_narrator_packet(retained.campaign_request, retained.campaign_effect)
    assert validate_campaign_source_proposal(OBSERVED, packet=packet,
        facts=retained.draft.facts, snapshot=retained.snapshot).model_dump(by_alias=True)['q'] == OBSERVED['q']


@pytest.mark.parametrize('question', [
    OBSERVED['q'],
    'Qual é sua próxima ação diante do risco imediato?',
    'Qual será a sua próxima atitude?',
    'Qual é o seu próximo passo?',
    'Qual será o seu próximo movimento agora?',
    'Qual é a sua decisão diante de Mara?',
    'Qual é a sua próxima ação diante da infiltração?',
    'Que ação você pretende realizar agora?',
    'Como você quer proceder com o registro molhado?',
])
def test_article_preserves_open_player_choice(question):
    _validate_player_prompt(question, player_aliases=('Neófito',), npc_aliases=('Mara',))


@pytest.mark.parametrize('question', [
    'Mova o registro; qual é a sua próxima ação?',
    'Você abre a porta. Qual é a sua próxima ação?',
    'Mara pergunta: qual é a sua próxima ação?',
    'Qual é a sua próxima ação, Mara?',
    'Qual é a sua decisão, Mara, diante do risco?',
    'Qual é a próxima ação de Mara?',
    'Qual é a sua próxima ação enquanto Mara decide?',
    'Qual é a sua próxima ação? O que Mara decide?',
    'Qual é a sua próxima ação',
    'Você sabe a sua próxima ação?',
    'Qual é a sua próxima ação: abrir a porta?',
    'Abra a porta; que ação você pretende realizar agora?',
    'Você abre a porta. Que ação você pretende realizar agora?',
    'Que ação Mara pretende realizar agora?',
    'Que ação você pretende realizar agora, Mara?',
    'Que ação você pretende realizar agora: abrir ou fugir?',
    'Que ação você pretende realizar agora? O que Mara decide?',
    'Como Mara quer proceder com o registro molhado?',
    'Como você quer proceder com o registro molhado, Mara?',
    'Você abre a porta. Como você quer proceder com o registro molhado?',
    'Como você quer proceder com o registro molhado: abrir ou fugir?',
])
def test_article_does_not_authorize_nonplayer_choice_or_other_invalid_prompt(question):
    with pytest.raises(SceneProposalError):
        _validate_player_prompt(question, player_aliases=('Neófito',), npc_aliases=('Mara',))


def test_existing_15_word_boundary_is_counted_explicitly_and_never_relaxed():
    at_limit = 'Qual é a sua próxima ação diante da infiltração que aumenta lentamente no Arquivo antigo?'
    beyond_limit = at_limit[:-1] + ' abandonado?'
    pattern = r"[^\W_]+(?:[-’'][^\W_]+)*"
    assert len(re.findall(pattern, at_limit, flags=re.UNICODE)) == 15
    assert len(re.findall(pattern, beyond_limit, flags=re.UNICODE)) == 16
    _validate_player_prompt(at_limit, player_aliases=('Neófito',), npc_aliases=('Mara',))
    with pytest.raises(SceneProposalError) as caught:
        _validate_player_prompt(beyond_limit, player_aliases=('Neófito',), npc_aliases=('Mara',))
    assert caught.value.code == 'scene_player_prompt_too_long'
    assert caught.value.evidence['word_count'] == 16


@pytest.mark.asyncio
@pytest.mark.parametrize('wrong_actor', [False, True])
@pytest.mark.parametrize('question',[OBSERVED['q'],'Que ação você pretende realizar agora?'])
async def test_exact_question_commit_restart_replay_and_wrong_actor_rollback(tmp_path, monkeypatch, wrong_actor, question):
    def forbidden_roll(*_args, **_kwargs):
        pytest.fail('wait/replay may not roll')
    monkeypatch.setattr(rules_service, 'calculate_resolution', forbidden_roll)
    db = tmp_path / 'question.sqlite3'
    store = SQLitePersistence(db)
    await create_campaign_source_session(store, 'question', initial_state=state())
    q = 'Qual é a próxima ação de Mara?' if wrong_actor else question
    config, gateway = config_and_gateway(OBSERVED['n'], tuple(OBSERVED['realized_effects']), q)
    prepared = await prepare_campaign_source_player_action(
        store=store, session_id='question', operation_id='question-1', player_input='Aguardo',
        config=config, deadline=utc_now()+timedelta(seconds=30), cancellation=CancellationToken())
    chunks = []
    async def deliver(text):
        chunks.append(text)
    result = await execute_campaign_source_turn(
        store=store, capsule=prepared.capsule, operation_id='question-1', gateway=gateway,
        deadline=utc_now()+timedelta(seconds=30), cancellation=CancellationToken(), on_chunk=deliver)
    restarted = SQLitePersistence(db)
    snapshot = await read_campaign_source_snapshot(restarted, 'question')
    if wrong_actor:
        assert result.status == 'failed' and result.error_code == 'campaign_source_policy_failed'
        assert snapshot.current_turn == 0 and snapshot.progression.record == 'threatened'
        assert not snapshot.sources and not chunks
    else:
        assert result.status == 'completed'
        assert snapshot.current_turn == 1 and snapshot.progression.record == 'warned'
        replay = await execute_campaign_source_turn(
            store=restarted, capsule=prepared.capsule, operation_id='question-1', gateway=gateway,
            deadline=utc_now()-timedelta(seconds=1), cancellation=CancellationToken(), on_chunk=deliver)
        assert replay.status == 'completed' and replay.envelope == result.envelope
        assert len(chunks) == 1
    assert len(gateway.requests) == 1
