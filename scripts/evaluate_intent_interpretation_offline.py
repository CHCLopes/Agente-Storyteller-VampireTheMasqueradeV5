"""Evaluate authored proposals offline; never measures real model accuracy."""
from __future__ import annotations
import argparse
from collections import Counter
from dataclasses import asdict
from hashlib import sha256
import json
from pathlib import Path
from api.campaign_progression_catalog import classify_campaign_intent
from api.experiments.intent_interpretation_offline import Envelope, assess, parse_proposal

CORPUS=Path('evals/narrator/spikes/intent-interpretation-2026-10-22/corpus.json')
SOURCES=(str(CORPUS),'api/experiments/intent_interpretation_offline.py',__file__)


def envelope(case):
    return Envelope(session_id='synthetic-intent-study',operation_id=case['id'],state_sha256='0'*64,player_input=case['input'])


def reference(case, *, intent=None):
    e=envelope(case)
    return json.dumps(dict(version=e.version,envelope_sha256=e.fingerprint,
        kind='known_intent' if intent else case['expected_kind'],intent=intent or case['expected_intent'],
        evidence=[dict(start=0,end=len(e.player_input),text=e.player_input)]),ensure_ascii=False)


def evaluate(cases):
    rows=[]
    for case in cases:
        e=envelope(case);raw=reference(case);p=parse_proposal(raw,e);result=assess(raw,e)
        baseline=classify_campaign_intent(case['input'])
        rows.append(dict(**case,baseline_intent=baseline.value if baseline else None,
            proposal_origin='authored_reference_not_model',schema_valid=True,assessment=asdict(result)))
    # Prospective order: first authority counterexample stops this candidate variant.
    adversarial=[('N01','rescue'),('N03','rescue'),('N04','rescue'),('M01','rescue'),('I02','rescue'),('A01','rescue'),('P07','inspect')]
    by_id={c['id']:c for c in cases}
    diagnosis=[]
    for case_id,wrong_intent in adversarial:
        case=by_id[case_id];raw=reference(case,intent=wrong_intent);e=envelope(case)
        parse_proposal(raw,e)
        diagnosis.append(dict(case_id=case_id,wrong_intent=wrong_intent,
            format_and_literal_evidence_accept=True,guard=asdict(assess(raw,e))))
    known=[r for r in rows if r['expected_kind']=='known_intent']
    other=[r for r in rows if r['expected_kind']!='known_intent']
    return dict(protocol='intent-offline-study.v1',synthetic_only=True,provider_calls=0,provider_cost_usd='0',
        model_accuracy_measured=False,reference_rows=rows,
        counts=dict(cases=len(rows),categories=dict(Counter(r['category'] for r in rows)),
            schema_valid_authored_references=len(rows),expected_known=len(known),expected_non_action=len(other),
            baseline_correct_known=sum(r['baseline_intent']==r['expected_intent'] for r in known),
            baseline_false_blocked=[r['id'] for r in known if r['baseline_intent'] is None],
            baseline_false_accepts=[r['id'] for r in other if r['baseline_intent'] is not None],
            guard_eligible=sum(r['assessment']['status']=='eligible_existing_intent' for r in rows),
            guard_pending_review=sum(r['assessment']['status']=='needs_independent_review' for r in rows),
            guard_no_action=sum(r['assessment']['status']=='no_action' for r in rows)),
        format_only_variant=dict(status='rejected_first_authority_failure',attempted_cases=1,first_failure=diagnosis[0]),
        forensic_diagnosis=diagnosis,forensic_is_separate_from_stopped_variant=True,
        gate='No interpretation admitted; independent semantics for novel inputs remains unresolved.')


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    if args.output.exists():raise SystemExit('Preserve prior evidence: output exists')
    args.output.mkdir(parents=True)
    manifest=dict(hypothesis='Binding and literal spans prevent substitution, but do not prove semantics; independent guard preserves authority without extending coverage.',
        cases=24,synthetic_only=True,provider_calls=0,max_cost_usd='0',retry=False,fallback=False,
        stop='Format-only variant stops at first incorrect intent accepted. Separate forensic diagnosis tests the boundary; no candidate promotion.',
        sha256={str(Path(p).as_posix()):sha256(Path(p).read_bytes()).hexdigest() for p in SOURCES})
    (args.output/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    cases=json.loads(CORPUS.read_text(encoding='utf-8'))['cases']
    assert len(cases)==24
    result=evaluate(cases)
    (args.output/'observation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result['counts'],ensure_ascii=False))

if __name__=='__main__':main()
