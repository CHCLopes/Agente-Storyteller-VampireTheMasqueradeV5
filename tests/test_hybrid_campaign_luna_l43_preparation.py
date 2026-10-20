"""L43 resumes the full schedule without modifying historical gates."""
import json
import pytest
from pydantic import SecretStr
from scripts import evaluate_hybrid_campaign_luna_l43_live as subject
from test_hybrid_campaign_luna_live import fake_adapter


@pytest.fixture
def gate(tmp_path, monkeypatch):
    value = json.loads(subject.GATE.read_text(encoding='utf-8'))
    value.update(paid_ceiling_authorized=False, live_inference_authorized=False)
    # Historical live manifest stays immutable after the proven local fix.
    value['implementation_sha256'] = {name: subject._sha((subject.ROOT/name).read_bytes()) for name in subject.FROZEN_FILES}
    path = tmp_path / 'gate.json'
    path.write_text(json.dumps(value), encoding='utf-8')
    monkeypatch.setattr(subject, 'GATE', path)
    return subject._gate()


@pytest.mark.parametrize('name', ['evaluate_hybrid_campaign_luna_l25_live.py',
                                  'preflight_hybrid_campaign_luna_l25.py',
                                  'run_hybrid_campaign_luna_l25_live.ps1'])
def test_identity_only(name):
    expected = (subject.ROOT/'scripts'/name).read_text(encoding='utf-8')
    expected = expected.replace('l25','l43').replace('L25','L43').replace('2026-10-18','2026-10-20').replace('source-v6','source-v9')
    assert (subject.ROOT/'scripts'/name.replace('l25','l43')).read_text(encoding='utf-8').splitlines() == expected.splitlines()


def test_current_manifest_limits_and_historical_gates(gate):
    assert gate['max_calls'] == subject.MAX_CALLS == 17
    assert gate['max_estimated_usd'] == '0.15'
    assert gate['retry'] is gate['fallback'] is gate['admission_automatic'] is False
    assert len(gate['implementation_sha256']) == 22
    for lot, day in ((25,'18'),(26,'19'),(27,'19')):
        path = subject.ROOT/f'evals/narrator/reports/hybrid-campaign-luna-l{lot}-live-gate-2026-10-{day}.json'
        old = json.loads(path.read_text(encoding='utf-8'))
        assert old['live_inference_authorized'] is old['paid_ceiling_authorized'] is False


def test_preflight_has_no_dispatch(gate, monkeypatch, capsys):
    def forbidden(*args, **kwargs):
        pytest.fail('offline rehearsal cannot access credential or dispatch')
    monkeypatch.setattr(SecretStr, 'get_secret_value', forbidden)
    monkeypatch.setattr(subject.CampaignLunaAdapter, 'generate_structured', forbidden)
    assert subject.main(['--preflight']) == 0
    result = json.loads(capsys.readouterr().out.splitlines()[0])
    assert result['calls_planned'] == 17 and result['provider_calls'] == 0


@pytest.mark.asyncio
async def test_fake_full_schedule(gate, monkeypatch, tmp_path):
    monkeypatch.setattr(subject, '_gate', lambda: dict(gate, paid_ceiling_authorized=True, live_inference_authorized=True))
    result = await subject.run_batch(directory=tmp_path/'fake', key=SecretStr('synthetic-only'), adapter_factory=fake_adapter)
    assert result['status'] == 'completed' and result['completed_turns'] == 17


@pytest.mark.asyncio
async def test_closed_gate_precedes_dispatch(gate, tmp_path, monkeypatch):
    latch = tmp_path/'once'
    monkeypatch.setattr(subject, 'LOT_LOCK', latch)
    with pytest.raises(ValueError, match='authorization_missing'):
        await subject.run_batch(directory=tmp_path/'blocked', key=SecretStr('synthetic-only'))
    assert not latch.exists()


def test_prompt_v9_changes_only_the_registered_style_block():
    old=(subject.ROOT/'evals/narrator/prompts/hybrid-campaign-source-v8.md').read_text(encoding='utf-8')
    new=subject.PROMPT.read_text(encoding='utf-8')
    start=new.index('A proteção de segredos e o estado da campanha')
    end=new.index('Preserve danos, descobertas, destinos escolhidos e a ordem causal.', start)
    assert ' '.join((new[:start]+new[end:]).split()) == ' '.join(old.split())
    normalized=' '.join(new.split()).casefold()
    assert 'não invente juramento, proibição, esquecimento, desconhecimento' in normalized
    assert 'não repita o segredo ou sua recusa em ajuda ou conclusão' in normalized
    assert 'não cria ramos de diálogo, novas intenções ou passagem de tempo' in normalized
