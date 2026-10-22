"""A1 opt-in: deterministic presentation, version isolation, rollback and replay."""
from copy import deepcopy
from datetime import timedelta
import json
from pathlib import Path

import pytest

from api import rules_service
from api.campaign_expression_capsule import CampaignExpressionCapsule, CampaignExpressionConfig
from api.campaign_expression_execution_service import execute_campaign_expression_turn
from api.campaign_expression_input_service import prepare_campaign_expression_player_action
from api.campaign_expression_storage import (
    create_campaign_expression_session, read_campaign_expression_snapshot,
    read_campaign_expression_status, CampaignExpressionStorageError,
)
from api.campaign_expression_rendering import CampaignExpressionProposal, compose_expression, digest
from api.campaign_source_capsule import CampaignSourceCapsule, CampaignSourceConfig
from api.campaign_source_storage import read_campaign_source_snapshot, CampaignSourceStorageError
from api.llm.contract import CancellationToken, utc_now
from api.llm.testing import FakeLLMAdapter
from api.persistence import SQLitePersistence
from api.rules_service import ResolutionResult
from test_campaign_source_integration import config_and_gateway
from test_campaign_source_trajectory_eval import CASES
from test_narrative_source_input_service import state as eligible_state

ROOT = Path(__file__).resolve().parents[1]


class ExpressionFake(FakeLLMAdapter):
    change = None
    reaction = ''

    async def generate_structured(self, request):
        plan = json.loads(request.messages[1].content)['context']['realization_plan']
        self.structured_payload = {'protocol': 'campaign-source-expression-v2',
                                   'plan_sha256': plan['plan_sha256'],
                                   'slots': [{'slot_id': s['slot_id'], 'text': self.reaction if s['slot_id'] == 'mara.reaction' else ''}
                                             for s in plan['slots']]}
        if self.change:
            self.change(self.structured_payload)
        return await super().generate_structured(request)


def setup():
    old_config, old_gateway = config_and_gateway()
    config = CampaignExpressionConfig(
        **old_config.model_dump(exclude={'profile', 'system_prompt'}),
        system_prompt=(ROOT / 'evals/narrator/prompts/campaign-expression-v2.md').read_text(encoding='utf-8'))
    gateway = ExpressionFake(capability_set=old_gateway.capabilities(old_config.target),
                             structured_payload={})
    return config, gateway


async def prepare(store, config, action='Aguardo', operation='op'):
    result = await prepare_campaign_expression_player_action(
        store=store, session_id='expression', operation_id=operation, player_input=action,
        config=config, deadline=utc_now() + timedelta(seconds=60), cancellation=CancellationToken())
    assert result.capsule is not None, result.error_code
    return result.capsule


async def execute(store, capsule, gateway, chunks, *, operation=None, resume=None):
    async def deliver(text):
        chunks.append(text)
    return await execute_campaign_expression_turn(
        store=store, capsule=capsule, operation_id=operation or capsule.operation_id,
        gateway=gateway, deadline=utc_now() + timedelta(seconds=60),
        cancellation=CancellationToken(), on_chunk=deliver, resumes_operation_id=resume)


def receipt(success):
    return ResolutionResult(successes=3 if success else 0, is_success=success,
                            bestial_failure=False, messy_critical=False, summary='Investigação resolvida.',
                            normal_rolls=[8, 8, 8, 5, 4] if success else [2, 2, 2, 3, 4],
                            hunger_rolls=[], margin=0 if success else -3)


@pytest.mark.asyncio
@pytest.mark.parametrize('case_id,actions,rules,outcome', CASES, ids=[row[0] for row in CASES])
async def test_eight_paths_exact_presentation_and_restart(case_id, actions, rules, outcome, tmp_path, monkeypatch):
    rolls = []
    def roll(*args, **kwargs):
        rolls.append(1)
        return receipt(case_id == 'CAMP-EVAL-06')
    monkeypatch.setattr(rules_service, 'calculate_resolution', roll)
    db = tmp_path / 'expression.sqlite3'
    store = SQLitePersistence(db)
    await create_campaign_expression_session(store, 'expression', initial_state=eligible_state())
    config, gateway = setup()
    chunks = []
    for number, (action, rule) in enumerate(zip(actions, rules), 1):
        store = SQLitePersistence(db)
        capsule = await prepare(store, config, action, f'op-{number}')
        assert capsule.campaign_effect.rule_id == rule
        assert (await read_campaign_expression_snapshot(store, 'expression')).current_turn == number - 1
        result = await execute(store, capsule, gateway, chunks)
        assert result.status == 'completed', (rule, result.error_code)
        projection = result.envelope.projection
        assert all(s.origin == 'application' and s.invocation_id is None for s in projection.segments)
        assert projection.semantic_truth_assessed is False
        for s in projection.segments:
            assert projection.text[s.start:s.end] == s.text
        with pytest.raises(ValueError):
            CampaignSourceCapsule.model_validate(capsule.model_dump(mode='json'))
    final = await read_campaign_expression_snapshot(SQLitePersistence(db), 'expression')
    assert final.progression.outcome == outcome
    assert final.progression.record_location == ('dry_surface' if rules[-1] in {'R-05', 'R-06'} else 'bench')
    assert len(rolls) == sum('Examino' in x for x in actions)
    count = len(gateway.requests)
    # Replay must use retained renderer version, never the latest compiler.
    import api.campaign_expression_capsule as capsule_module
    monkeypatch.setattr(capsule_module, 'build_realization_plan', lambda *a: pytest.fail('new plan on replay'))
    replay = await execute(SQLitePersistence(db), capsule, gateway, chunks)
    assert replay.envelope == result.envelope and len(gateway.requests) == count
    assert len(chunks) == len(actions)
    with pytest.raises(CampaignSourceStorageError):
        await read_campaign_source_snapshot(store, 'expression')


@pytest.mark.asyncio
@pytest.mark.parametrize('mutation', ['plan', 'missing', 'duplicate', 'order', 'extra', 'markup', 'control', 'length', 'agency'])
async def test_rejection_has_no_delivery_or_effect(mutation, tmp_path):
    store = SQLitePersistence(tmp_path / 'rejected.sqlite3')
    await create_campaign_expression_session(store, 'expression', initial_state=eligible_state())
    config, gateway = setup()
    capsule = await prepare(store, config)
    def change(value):
        if mutation == 'plan': value['plan_sha256'] = '0' * 64
        if mutation == 'missing': value['slots'].pop()
        if mutation == 'duplicate': value['slots'][1] = value['slots'][0]
        if mutation == 'order': value['slots'].reverse()
        if mutation == 'extra': value['state_after'] = 'preserved'
        if mutation == 'markup': value['slots'][0]['text'] = 'Mara: Faça isso.'
        if mutation == 'control': value['slots'][0]['text'] = 'Olá\u202e'
        if mutation == 'length': value['slots'][0]['text'] = 'a' * 241
        if mutation == 'agency': value['slots'][0]['text'] = 'Você abre a porta.'
    gateway.change = change
    chunks = []
    result = await execute(store, capsule, gateway, chunks)
    assert result.status == 'failed'
    assert chunks == []
    current = await read_campaign_expression_snapshot(store, 'expression')
    assert current.current_turn == 0 and current.progression.record == 'threatened'
    calls = len(gateway.requests)
    same = await execute(store, capsule, gateway, chunks)
    assert same.status == 'failed' and len(gateway.requests) == calls


@pytest.mark.asyncio
async def test_free_speech_has_segment_origin_and_unicode_offsets(tmp_path):
    store = SQLitePersistence(tmp_path / 'speech.sqlite3')
    await create_campaign_expression_session(store, 'expression', initial_state=eligible_state())
    config, gateway = setup()
    gateway.reaction = 'Ainda da\u0301 tempo.'
    capsule = await prepare(store, config)
    result = await execute(store, capsule, gateway, [])
    assert result.status == 'completed', result.error_code
    segment = next(s for s in result.envelope.projection.segments if s.segment_id == 'mara.reaction')
    assert segment.origin == 'llm' and segment.speaker == 'mara'
    assert segment.invocation_id == result.narrative.invocation_id
    assert segment.text == 'Ainda dá tempo.'
    assert result.envelope.projection.segments[-1].origin == 'application'
    assert result.envelope.projection.segments[-1].invocation_id is None
    assert segment.effect_refs == ()
    assert result.envelope.expression.slots[1].text == 'Ainda dá tempo.'


@pytest.mark.asyncio
async def test_plan_tampering_even_with_rehashed_capsule_rejected(tmp_path):
    store = SQLitePersistence(tmp_path / 'tamper.sqlite3')
    await create_campaign_expression_session(store, 'expression', initial_state=eligible_state())
    config, gateway = setup()
    capsule = await prepare(store, config)
    for field, value in [('actor', 'player'), ('text', 'Você abre a porta.'), ('polarity', 'negative'),
                         ('referent', 'founder_identity'), ('effect_refs', ['forged.effect']),
                         ('fact_refs', ['forged.fact'])]:
        raw = capsule.model_dump(mode='json')
        raw['realization_plan']['critical'][0][field] = value
        plan = raw['realization_plan']
        plan['plan_sha256'] = digest({k: v for k, v in plan.items() if k != 'plan_sha256'})
        raw['fingerprint_sha256'] = digest({k: v for k, v in raw.items() if k != 'fingerprint_sha256'})
        with pytest.raises(ValueError):
            CampaignExpressionCapsule.model_validate(raw)


@pytest.mark.asyncio
async def test_second_failed_inspection_is_lost_without_second_roll_on_resume(tmp_path, monkeypatch):
    rolls = []
    def roll(*args, **kwargs):
        rolls.append(1)
        return receipt(False)
    monkeypatch.setattr(rules_service, 'calculate_resolution', roll)
    store = SQLitePersistence(tmp_path / 'failed.sqlite3')
    await create_campaign_expression_session(store, 'expression', initial_state=eligible_state())
    config, gateway = setup()
    first = await prepare(store, config, 'Examino o registro', 'first')
    assert (await execute(store, first, gateway, [])).status == 'completed'
    second = await prepare(store, config, 'Examino o registro', 'second')
    gateway.change = lambda p: p.update(plan_sha256='0' * 64)
    assert (await execute(store, second, gateway, [])).status == 'failed'
    gateway.change = None
    result = await execute(store, second, gateway, [], operation='resume-second', resume='second')
    assert result.status == 'completed', result.error_code
    assert (await read_campaign_expression_snapshot(store, 'expression')).progression.outcome == 'lost'
    assert len(rolls) == 2


def test_profile_versions_are_not_interchangeable():
    config, _ = setup()
    with pytest.raises(ValueError):
        CampaignSourceConfig.model_validate(config.model_dump(mode='json'))


@pytest.mark.asyncio
@pytest.mark.parametrize('stage', ['before', 'after_generation', 'after_delivery'])
async def test_cancellation_leaves_preparation_and_canonical_state_unchanged(stage, tmp_path):
    store = SQLitePersistence(tmp_path / 'cancel.sqlite3')
    await create_campaign_expression_session(store, 'expression', initial_state=eligible_state())
    config, gateway = setup()
    capsule = await prepare(store, config)
    token = CancellationToken()
    chunks = []
    if stage == 'before':
        token.cancel('test')
    if stage == 'after_generation':
        original = gateway.generate_structured
        async def cancelled_after_response(request):
            response = await original(request)
            token.cancel('test')
            return response
        gateway.generate_structured = cancelled_after_response
    async def deliver(text):
        chunks.append(text)
        if stage == 'after_delivery':
            token.cancel('test')
    result = await execute_campaign_expression_turn(
        store=store, capsule=capsule, operation_id='op', gateway=gateway,
        deadline=utc_now() + timedelta(seconds=60), cancellation=token, on_chunk=deliver)
    assert result.status == 'cancelled'
    assert len(gateway.requests) == (0 if stage == 'before' else 1)
    assert len(chunks) == (1 if stage == 'after_delivery' else 0)
    assert (await read_campaign_expression_snapshot(store, 'expression')).current_turn == 0
    assert await store.list_events('expression') == []
    assert (await read_campaign_expression_status(store, 'expression', 'op')).resume_from_operation_id == 'op'


@pytest.mark.asyncio
async def test_repeated_question_and_rescue_request_preserve_player_agency(tmp_path):
    store = SQLitePersistence(tmp_path / 'dialogue.sqlite3')
    await create_campaign_expression_session(store, 'expression', initial_state=eligible_state())
    config, gateway = setup()
    for i, text in enumerate(('Qual é a tarefa?', 'Qual é a tarefa?', 'Mara, leve o registro')):
        cap = await prepare(store, config, text, f'dialogue-{i}')
        result = await execute(store, cap, gateway, [])
        assert result.status == 'completed', result.error_code
        assert cap.campaign_effect.rule_id == 'R-01'
        assert (await read_campaign_expression_snapshot(store, 'expression')).progression.record_location == 'bench'
    assert 'Posso orientar' in result.narrative.text


@pytest.mark.asyncio
async def test_existing_v1_session_cannot_be_upgraded(tmp_path):
    from api.campaign_source_storage import create_campaign_source_session
    store = SQLitePersistence(tmp_path / 'isolation.sqlite3')
    before = await create_campaign_source_session(store, 'expression', initial_state=eligible_state())
    with pytest.raises(CampaignExpressionStorageError):
        await create_campaign_expression_session(store, 'expression', initial_state=eligible_state())
    with pytest.raises(CampaignExpressionStorageError):
        await read_campaign_expression_snapshot(store, 'expression')
    assert await read_campaign_source_snapshot(store, 'expression') == before


@pytest.mark.asyncio
async def test_source_history_retains_mixed_attribution_without_canonical_promotion(tmp_path):
    store = SQLitePersistence(tmp_path / 'history.sqlite3')
    await create_campaign_expression_session(store, 'expression', initial_state=eligible_state())
    config, gateway = setup()
    gateway.reaction = 'Ainda dá tempo.'
    first = await prepare(store, config, 'Qual é a tarefa?', 'first')
    result = await execute(store, first, gateway, [])
    assert result.status == 'completed'
    second = await prepare(store, config, 'Qual é a tarefa?', 'second')
    gateway.reaction = ''
    assert (await execute(store, second, gateway, [])).status == 'completed'
    history = json.loads(gateway.requests[-1].messages[1].content)['context']['attributed_sources']
    assert len(history) == 1 and history[0]['canonical_authority'] == 'prepared_events_only'
    free = [s for s in history[0]['segments'] if s['origin'] == 'llm']
    assert len(free) == 1 and history[0]['text'][free[0]['start']:free[0]['end']] == 'Ainda dá tempo.'
    assert all('Ainda dá tempo.' not in e['payload']['summary'] for e in await store.list_events('expression'))


@pytest.mark.asyncio
async def test_cross_operation_and_revision_plans_cannot_bind(tmp_path):
    store = SQLitePersistence(tmp_path / 'binding.sqlite3')
    await create_campaign_expression_session(store, 'expression', initial_state=eligible_state())
    config, _ = setup()
    cap = await prepare(store, config)
    for key,value in [('operation_id','other'),('base_revision',1),('preparation_sha256','0'*64)]:
        raw=cap.model_dump(mode='json'); plan=raw['realization_plan'];plan[key]=value
        plan['plan_sha256']=digest({k:v for k,v in plan.items() if k!='plan_sha256'})
        raw['fingerprint_sha256']=digest({k:v for k,v in raw.items() if k!='fingerprint_sha256'})
        with pytest.raises(ValueError): CampaignExpressionCapsule.model_validate(raw)
