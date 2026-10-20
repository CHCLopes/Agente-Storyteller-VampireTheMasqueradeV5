"""L6's real question-limit rejection and a separate closed L7 contract."""
import hashlib
import json

import pytest
from pydantic import SecretStr

from api.campaign_source_profile import CampaignSourceProposal, _PolicyView
from api.scene_director_service import SceneProposalError, validate_scene_continuation
from api.scene_service import SceneState
from scripts import evaluate_hybrid_campaign_luna_l7_live as subject
from scripts import evaluate_hybrid_campaign_luna_l6_live as historical
from test_hybrid_campaign_luna_live import fake_adapter


@pytest.fixture(autouse=True)
def isolated_current_manifest(tmp_path, monkeypatch):
    """Closed L7 records/manifests are never refreshed for later runtime."""
    original = subject.GATE
    gate = json.loads(original.read_text(encoding='utf-8'))
    gate['implementation_sha256'] = {
        name: subject._sha((subject.ROOT / name).read_bytes()) for name in subject.FROZEN_FILES
    }
    path = tmp_path / original.name
    path.write_text(json.dumps(gate), encoding='utf-8')
    monkeypatch.setattr(subject, 'GATE', path)
    return original


def test_executed_l7_rejects_corrected_runtime(isolated_current_manifest, monkeypatch):
    assert hashlib.sha256(isolated_current_manifest.read_bytes()).hexdigest() == 'dc2d96b72df8fba484474b3ba73a5e1cbe0e062324e0222436c274018be2dcd4'
    monkeypatch.setattr(subject, 'GATE', isolated_current_manifest)
    with pytest.raises(ValueError, match='implementation_drifted'):
        subject._gate()


OBSERVED = {
    'n': 'Mara lança um olhar para a bancada baixa, onde o registro ameaçado permanece intacto, e depois indica a passagem para a Galeria. “O risco atual é a umidade; qualquer descuido aqui pode comprometer o registro. Se precisarmos manuseá-lo, a superfície seca fica na Galeria. Por enquanto, não o mova da bancada.” A orientação deixa claro o cuidado necessário sem alterar a posição do objeto.',
    'q': 'Como prefere proceder: manter o registro na bancada e preparar a passagem, ou examinar o risco mais de perto?',
    'realized_effects': ['mara.replies.to_task', 'campaign.knows.safe_surface'],
}


def validate_question(q):
    proposal = CampaignSourceProposal.model_validate({**OBSERVED, 'q': q})
    view = _PolicyView(narrative=proposal.narrative, player_prompt=proposal.player_prompt,
                      outcome='unresolved', location='Arquivo', npcs_present=('Mara',))
    return validate_scene_continuation(view, facts=(), current_scene=SceneState(
        location='Arquivo', npcs_present=('Mara',)), player_input='Como posso ajudar?',
        protected_secrets=(), npc_aliases=('Mara',))


def test_exact_l6_output_is_schema_valid_but_rejected_for_19_question_words():
    CampaignSourceProposal.model_validate(OBSERVED)
    with pytest.raises(SceneProposalError) as caught:
        validate_question(OBSERVED['q'])
    assert caught.value.code == 'scene_player_prompt_too_long'
    assert caught.value.evidence['word_count'] == 19


@pytest.mark.parametrize('q', [
    'O que você faz agora?',
    'O que você faz agora diante do risco da água que aumenta lentamente no Arquivo?',
])
def test_short_open_question_keeps_same_narrative_and_passes_existing_policy(q):
    assert validate_question(q).narrative == OBSERVED['n']


def test_existing_question_limit_remains_15_not_relaxed():
    with pytest.raises(SceneProposalError) as caught:
        validate_question('O que você faz agora diante do risco da água que aumenta lentamente no Arquivo antigo?')
    assert caught.value.code == 'scene_player_prompt_too_long'
    assert caught.value.evidence['word_count'] == 16


def test_v4_only_makes_existing_question_contract_explicit():
    previous = (subject.ROOT / 'evals/narrator/prompts/hybrid-campaign-source-v3.md').read_text(encoding='utf-8')
    old = 'Em `q`, convide a próxima ação somente se o objetivo ainda estiver aberto; em'
    new = ('Em `q`, escreva uma única pergunta aberta sobre a próxima ação do jogador,\n'
           'com no máximo 15 palavras, terminada em "?". Não restrinja a resposta a um menu\n'
           'de alternativas. Convide a próxima ação somente se o objetivo ainda estiver\n'
           'aberto; em')
    assert subject.PROMPT.read_text(encoding='utf-8') == previous.replace(old, new)
    gate = subject._gate()
    assert gate['lot_id'] == 'HYP-007-L7' and len(gate['implementation_sha256']) == 22
    assert gate['paid_ceiling_authorized'] is gate['live_inference_authorized'] is False
    assert gate['retry'] is gate['fallback'] is gate['admission_automatic'] is False
    assert gate['max_calls'] == 17 and gate['max_estimated_usd'] == '0.15'
    assert historical.GATE != subject.GATE and historical.LOT_LOCK != subject.LOT_LOCK
    assert hashlib.sha256(historical.GATE.read_bytes()).hexdigest() == 'b0e582b28d46cb015f8e11aa7a6e0f37b26458168704a139963297fce1eb1c49'


@pytest.mark.parametrize('field', ['retry', 'fallback', 'synthetic_only', 'admission_automatic'])
def test_l7_refuses_protocol_drift(field, tmp_path, monkeypatch):
    gate = subject._gate()
    gate[field] = not gate[field]
    path = tmp_path / 'mutated.json'
    path.write_text(json.dumps(gate), encoding='utf-8')
    monkeypatch.setattr(subject, 'GATE', path)
    with pytest.raises(ValueError, match='gate_drifted'):
        subject._gate()


def test_l7_preflight_cannot_read_credential_or_dispatch(monkeypatch, capsys):
    def forbidden(*_args, **_kwargs):
        pytest.fail('keyless preflight may not read credential or dispatch')
    monkeypatch.setattr(SecretStr, 'get_secret_value', forbidden)
    monkeypatch.setattr(subject.CampaignLunaAdapter, 'generate_structured', forbidden)
    assert subject.main(['--preflight']) == 0
    lines = capsys.readouterr().out.splitlines()
    result = json.loads(lines[0])
    assert result['lot_id'] == 'HYP-007-L7'
    assert result['provider_calls'] == 0 and result['calls_planned'] == 17
    assert result['max_request_bytes_observed'] <= 20000
    assert 'CUSTO FINAL LUNA: USD 0 (nenhuma chamada iniciada).' in lines


@pytest.mark.asyncio
async def test_l7_closed_gate_blocks_before_adapter_credential_latch_and_output(tmp_path, monkeypatch):
    def forbidden(*_args, **_kwargs):
        pytest.fail('closed gate must precede credential and adapter')
    monkeypatch.setattr(SecretStr, 'get_secret_value', forbidden)
    monkeypatch.setattr(subject.CampaignLunaAdapter, '__init__', forbidden)
    monkeypatch.setattr(subject, 'LOT_LOCK', tmp_path / 'once')
    with pytest.raises(ValueError, match='authorization_missing'):
        await subject.run_batch(directory=tmp_path / 'blocked', key=SecretStr('synthetic-only'))
    assert not subject.LOT_LOCK.exists() and not (tmp_path / 'blocked').exists()


@pytest.mark.asyncio
async def test_l7_fake_full_schedule_does_not_enable_real_gate(tmp_path, monkeypatch):
    gate = subject._gate()
    monkeypatch.setattr(subject, '_gate', lambda: {
        **gate, 'paid_ceiling_authorized': True, 'live_inference_authorized': True,
    })
    result = await subject.run_batch(directory=tmp_path / 'fake', key=SecretStr('synthetic-only'),
                                     adapter_factory=fake_adapter)
    assert result['status'] == 'completed' and result['completed_turns'] == 17
    assert json.loads(subject.GATE.read_text(encoding='utf-8'))['live_inference_authorized'] is False


@pytest.mark.asyncio
async def test_l7_latch_prevents_repeated_or_concurrent_batch(tmp_path, monkeypatch):
    gate = subject._gate()
    monkeypatch.setattr(subject, '_gate', lambda: {
        **gate, 'paid_ceiling_authorized': True, 'live_inference_authorized': True,
    })
    latch = tmp_path / 'once'
    latch.mkdir()
    monkeypatch.setattr(subject, 'LOT_LOCK', latch)
    with pytest.raises(FileExistsError):
        await subject.run_batch(directory=tmp_path / 'repeated', key=SecretStr('synthetic-only'))
    assert not (tmp_path / 'repeated').exists()
