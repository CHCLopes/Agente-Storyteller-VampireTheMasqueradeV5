"""E acceptance: exact admission, A2 causal parity and durable raw input."""
import sqlite3

from fastapi.testclient import TestClient
import pytest

from api import rules_service
from api.experiments.intent_interpretation_catalog import APPROVED_PARAPHRASES
from api.experiments.intent_paraphrase_boundary import CANONICAL_INPUTS
from scripts.evaluate_intent_paraphrase_admission_offline import CASES
from scripts.preflight_hybrid_campaign_luna_l85 import _fixed_resolution
from scripts.run_expression_selection_browser_trial import create_app

TOKEN = 'synthetic-exact-paraphrase-token'


def client(path, *, exact=True):
    return TestClient(create_app(path, access_token=TOKEN, exact_paraphrases=exact),
                      base_url='http://127.0.0.1:8032', headers={'X-Trial-Token': TOKEN})


def start(c):
    response = c.post('/api/start')
    assert response.status_code == 200
    return response.json()['session_id']


def act(c, sid, op, text):
    return c.post('/api/action', json={'session_id': sid, 'operation_id': op, 'player_input': text})


def forbid(*args, **kwargs):
    raise AssertionError('No additional RNG, preparation or provider dispatch is allowed')


@pytest.mark.parametrize('text,intent', list(APPROVED_PARAPHRASES.items()))
@pytest.mark.parametrize('success', [False, True])
def test_six_phrases_match_canonical_effect_and_retained_replay(tmp_path, monkeypatch, text, intent, success):
    rolls = []

    def fixed(*a, **kw):
        rolls.append(1)
        return _fixed_resolution(success)

    monkeypatch.setattr(rules_service, 'calculate_resolution', fixed)
    monkeypatch.setattr('api.experiments.expression_selection.service.build_request', forbid)
    path = tmp_path / 'exact.db'
    c = client(path)
    baseline = client(tmp_path / 'baseline.db', exact=False)
    sid, base_sid = start(c), start(baseline)
    result = act(c, sid, 'op', text)
    reference = act(baseline, base_sid, 'op', CANONICAL_INPUTS[intent])
    assert result.status_code == reference.status_code == 200
    assert result.json()['provider_calls'] == reference.json()['provider_calls'] == 0
    assert result.json()['history'][0]['input'] == text
    store, base_store = c.app.state.selection_store, baseline.app.state.selection_store
    assert store.session(sid).state == base_store.session(base_sid).state
    prepared = store.preparation(sid, 'op')
    expected = base_store.preparation(base_sid, 'op')
    assert prepared.effect.rule_id == expected.effect.rule_id
    assert prepared.effect.beat.effect_keys == expected.effect.beat.effect_keys
    assert prepared.resolution == expected.resolution
    assert result.json()['history'][0]['text'] == reference.json()['history'][0]['text']
    assert len(rolls) == (2 if intent.value == 'inspect' else 0)
    monkeypatch.setattr(rules_service, 'calculate_resolution', forbid)
    monkeypatch.setattr('api.experiments.expression_selection.store.produce_preparation', forbid)
    reopened = client(path)
    assert reopened.get('/api/session/' + sid).json() == result.json()
    assert act(reopened, sid, 'op', text).json() == result.json()
    assert reopened.post('/api/resume', json={'session_id': sid, 'operation_id': 'op'}).json() == result.json()
    assert len(store.attempts(sid, 'op')) == 1


@pytest.mark.parametrize('text', [case['player_input'] for case in CASES if case['category'] != 'approved'] + [
    ' Fico esperando.', 'Fico esperando. ', 'fico esperando.', 'Como posso ajudar?',
])
def test_controls_do_not_claim_or_advance(tmp_path, monkeypatch, text):
    c = client(tmp_path / 'exact.db')
    sid = start(c)
    before = c.get('/api/session/' + sid).json()
    monkeypatch.setattr(rules_service, 'calculate_resolution', forbid)
    monkeypatch.setattr('api.experiments.expression_selection.store.produce_preparation', forbid)
    assert act(c, sid, 'op', text).status_code == 422
    assert c.get('/api/session/' + sid).json() == before
    with c.app.state.selection_store._connection() as db:
        assert db.execute('SELECT COUNT(*) FROM operations').fetchone()[0] == 0
    with c.app.state.paraphrase_boundary._connection() as db:
        assert db.execute('SELECT COUNT(*) FROM receipts').fetchone()[0] == 0


def test_same_intent_cannot_rebind_operation_and_sessions_are_isolated(tmp_path):
    c = client(tmp_path / 'exact.db')
    sid, other = start(c), start(c)
    first = act(c, sid, 'op', 'Quero saber qual é a tarefa.')
    assert first.status_code == 200
    assert act(c, sid, 'op', 'Mara, o que eu posso fazer para ajudar?').status_code == 409
    assert c.get('/api/session/' + sid).json() == first.json()
    assert act(c, other, 'op', 'Mara, o que eu posso fazer para ajudar?').status_code == 200


@pytest.mark.parametrize('retained_choice', [False, True])
def test_interrupted_inspection_resumes_with_original_receipt(tmp_path, monkeypatch, retained_choice):
    from api.experiments.expression_selection.contract import Choice, Selection
    path = tmp_path / 'exact.db'
    c = client(path)
    sid = start(c)
    boundary, store = c.app.state.paraphrase_boundary, c.app.state.selection_store
    canonical = boundary.admit(sid, 'op', 'Analiso o registro.')
    monkeypatch.setattr(rules_service, 'calculate_resolution', lambda *a, **kw: _fixed_resolution(False))
    prepared = store.prepare(sid, 'op', canonical)
    store.claim(sid, 'op', 'interrupted')
    if retained_choice:
        store.save_selection(sid, 'op', 'interrupted', Selection(
            choice=Choice(utterance='original', atmosphere='none', layout='inline'),
            origin='deterministic', source_attempt_id='interrupted'))
    monkeypatch.setattr(rules_service, 'calculate_resolution', forbid)
    monkeypatch.setattr('api.experiments.expression_selection.store.produce_preparation', forbid)
    reopened = client(path)
    pending = reopened.get('/api/session/' + sid).json()['pending']
    assert pending['input'] == 'Analiso o registro.'
    result = reopened.post('/api/resume', json={'session_id': sid, 'operation_id': 'op'})
    assert result.status_code == 200 and result.json()['turn'] == 1
    assert result.json()['history'][0]['input'] == 'Analiso o registro.'
    assert store.preparation(sid, 'op') == prepared
    assert [row['status'] for row in store.attempts(sid, 'op')] == ['interrupted', 'completed']


@pytest.mark.parametrize('actions,outcome', [
    (['Quero saber qual é a tarefa.', 'Vou retirar o registro da bancada.'], 'preserved'),
    (['Fico esperando.', 'Fico esperando.', 'Vou retirar o registro da bancada.'], 'partial'),
    (['Fico esperando.'] * 3, 'lost'),
    (['Não participarei do resgate.'], 'abandoned'),
])
def test_complete_paths_and_terminal_guard(tmp_path, actions, outcome):
    c = client(tmp_path / 'exact.db')
    sid = start(c)
    for n, text in enumerate(actions):
        result = act(c, sid, str(n), text)
        assert result.status_code == 200
    assert result.json()['outcome'] == outcome
    assert act(c, sid, 'terminal', 'Fico esperando.').status_code == 409
    assert c.get('/api/session/' + sid).json() == result.json()


def test_receipt_survives_claim_gap_and_failed_preparation_does_not_reroll(tmp_path, monkeypatch):
    path = tmp_path / 'exact.db'
    c = client(path)
    sid = start(c)
    c.app.state.paraphrase_boundary.admit(sid, 'op', 'Analiso o registro.')
    reopened = client(path)
    calls = []

    def interrupted(*a, **kw):
        calls.append(1)
        raise ValueError('synthetic-interruption')

    monkeypatch.setattr('api.experiments.expression_selection.store.produce_preparation', interrupted)
    assert act(reopened, sid, 'op', 'Analiso o registro.').status_code == 409
    assert act(reopened, sid, 'op', 'Analiso o registro.').status_code == 409
    assert calls == [1]
    assert reopened.get('/api/session/' + sid).json()['turn'] == 0


def test_missing_or_corrupt_receipt_fails_closed_and_baseline_db_untouched(tmp_path):
    path = tmp_path / 'exact.db'
    c = client(path)
    sid = start(c)
    assert act(c, sid, 'op', 'Fico esperando.').status_code == 200
    receipt_path = c.app.state.paraphrase_boundary.path
    with sqlite3.connect(receipt_path) as db:
        db.execute("UPDATE receipts SET canonical_input='Retiro o registro'")
    assert c.get('/api/session/' + sid).status_code == 409
    with pytest.raises(ValueError, match='receipt_invalid'):
        client(path)
    baseline_path = tmp_path / 'baseline.db'
    baseline = client(baseline_path, exact=False)
    start(baseline)
    before = baseline_path.read_bytes()
    with pytest.raises(ValueError, match='receipts_missing'):
        client(baseline_path)
    assert baseline_path.read_bytes() == before


def test_opt_in_page_and_local_boundary(tmp_path):
    c = client(tmp_path / 'exact.db')
    page = c.get('/')
    assert page.status_code == 200
    assert all(text in page.text for text in APPROVED_PARAPHRASES)
    assert 'selection-a2-exact-session' in page.text
    assert "const text=$('input').value;if(!text.trim())return;" in page.text
    assert 'innerHTML' not in page.text
    assert c.post('/api/start', headers={'X-Trial-Token': ''}).status_code == 403
    assert c.post('/api/start', headers={'Origin': 'https://external.invalid'}).status_code == 403
    assert c.get('/', headers={'Host': 'external.invalid'}).status_code == 403
    assert act(c, 'absent', 'op', 'Fico esperando.').status_code == 404
