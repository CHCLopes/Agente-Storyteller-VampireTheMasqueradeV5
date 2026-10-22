"""Offline characterization; authored labels never grant runtime authority."""
import json
import pytest
from api.experiments.intent_interpretation_offline import Envelope, assess, parse_proposal
from scripts.evaluate_intent_interpretation_offline import CORPUS, envelope, evaluate, reference
CASES=json.loads(CORPUS.read_text(encoding='utf-8'))['cases']
BY_ID={c['id']:c for c in CASES}

@pytest.mark.parametrize('case',CASES,ids=[c['id'] for c in CASES])
def test_reference_boundaries(case):
    raw=reference(case);e=envelope(case);p=parse_proposal(raw,e)
    assert p.envelope_sha256==e.fingerprint
    result=assess(raw,e)
    if case['id'] in {'P07','P08','N02','N03'}:
        assert result.status=='eligible_existing_intent' and result.intent.value==case['expected_intent']
    elif case['category']=='paraphrase':
        assert result.status=='needs_independent_review' and result.intent is None
    else:assert result.status=='no_action' and result.intent is None

@pytest.mark.parametrize('case_id,intent',[('N01','rescue'),('N03','rescue'),('N04','rescue'),('M01','rescue'),('I02','rescue'),('A01','rescue'),('P07','inspect')])
def test_literal_evidence_is_not_semantic_proof(case_id,intent):
    case=BY_ID[case_id];raw=reference(case,intent=intent);e=envelope(case)
    assert parse_proposal(raw,e).kind=='known_intent'
    assert assess(raw,e).status=='needs_independent_review' and assess(raw,e).intent is None

@pytest.mark.parametrize('field,value',[('session_id','other'),('operation_id','other'),('state_sha256','1'*64),('player_input','Aguardo')])
def test_binding(field,value):
    case=BY_ID['P07'];e=envelope(case)
    other=Envelope.model_validate(dict(e.model_dump(),**{field:value}))
    with pytest.raises(ValueError):parse_proposal(reference(case),other)

@pytest.mark.parametrize('mutation',['extra','intent','kind','text','bool','overlap','range','empty','many','version'])
def test_invalid_proposals(mutation):
    case=BY_ID['P07'];v=json.loads(reference(case));span=v['evidence'][0]
    if mutation=='extra':v['narrative']='Resgate concluído.'
    if mutation=='intent':v['intent']='new_rule'
    if mutation=='kind':v['kind']='unsupported'
    if mutation=='text':span['text']='Aguardo'
    if mutation=='bool':span['start']=False
    if mutation=='overlap':v['evidence']=[span,span]
    if mutation=='range':span['end']=500
    if mutation=='empty':v['evidence']=[]
    if mutation=='many':v['evidence']=[span]*5
    if mutation=='version':v['version']='future.v2'
    with pytest.raises(ValueError):parse_proposal(json.dumps(v),envelope(case))

@pytest.mark.parametrize('raw',['[]','{}','null','```json\n{}\n```','{} trailing','x'*4097])
def test_json_limits(raw):
    with pytest.raises(ValueError):parse_proposal(raw,envelope(BY_ID['P07']))

def test_duplicates():
    c=BY_ID['P07'];raw=reference(c)
    for duplicate in [raw[:-1]+',"kind":"unsupported"}',raw.replace('"start": 0','"start": 0, "start": 0')]:
        with pytest.raises(ValueError,match='duplicate_key'):parse_proposal(duplicate,envelope(c))

def test_observation_not_model_score():
    r=evaluate(CASES);c=r['counts']
    assert c['categories']==dict(paraphrase=8,ambiguity=4,negation_actor=4,new_method=4,canon_injection=4)
    assert c['baseline_false_blocked']==['P01','P02','P03','P04','P05','P06']
    assert c['baseline_false_accepts']==[]
    assert (c['guard_eligible'],c['guard_pending_review'],c['guard_no_action'])==(4,6,14)
    assert r['format_only_variant']['attempted_cases']==1
    assert r['format_only_variant']['first_failure']['case_id']=='N01'
    assert not r['model_accuracy_measured'] and r['provider_calls']==0

def test_repeatable_without_network_or_rng(monkeypatch):
    def forbidden(*a,**kw):raise AssertionError('No inference/mechanics')
    monkeypatch.setattr('socket.create_connection',forbidden)
    monkeypatch.setattr('api.rules_service.calculate_resolution',forbidden)
    assert evaluate(CASES)==evaluate(CASES)
