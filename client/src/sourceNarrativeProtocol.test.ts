import { describe, expect, it } from 'vitest';
import {
  SOURCE_PUBLIC_PROTOCOL as protocol,
  createSourceNarrativeState,
  decodeSourcePublicEvent,
  sourceNarrativeReducer as reduce,
  sourceOperationLabel,
} from './sourceNarrativeProtocol';
import type { SourceNarrativeState } from './sourceNarrativeProtocol';

const operation_id = 'op-scene-1';
const player_input = 'Espero a reação de Rui.';
const n = 'Rui aponta o índice na parede. O corredor permanece aberto e o relógio marca o silêncio.';
const q = 'O que você faz agora?';
const complete = { protocol, event: 'narrative_complete', operation_id, n, q };
const briefing = { protocol, event: 'briefing', origin: 'authored_trial_setup', text: 'Local: Arquivo\nElenco presente: Rui\nObjetivo: conhecer o arquivo.' };
const receive = (state: SourceNarrativeState, event: unknown, operationId = operation_id) => reduce(state, { type: 'receive', operationId, event });
const submitted = () => reduce(createSourceNarrativeState(), { type: 'submitted', action: { operation_id, player_input } });

const legitimate = [
  briefing,
  ...['pending', 'ready'].map(status => ({ protocol, event: 'preparation', operation_id, status })),
  ...['retained_unstarted', 'pending'].map(status => ({ protocol, event: 'narrative_pending', operation_id, status })),
  complete,
  ...['out_of_scope', 'clarification_required', 'preparation_failed', 'cancelled', 'timeout'].map(code => ({ protocol, event: 'preparation_rejected', operation_id, code, status: ['cancelled', 'timeout'].includes(code) ? code : 'failed', stage: null })),
  ...['narrative_rejected', 'narrative_failed', 'cancelled', 'timeout'].map(code => ({ protocol, event: 'narrative_rejected', operation_id, code, status: ['cancelled', 'timeout'].includes(code) ? code : 'failed', stage: null })),
  ...['preparation', 'narrative'].map(phase => ({ protocol, event: 'unavailable', operation_id, phase, code: 'unavailable' })),
];

describe('B public wire decoder', () => {
  it.each(legitimate)('accepts the public event %# without changing data', event => {
    const before = JSON.stringify(event);
    expect(decodeSourcePublicEvent(event)).toEqual(event);
    expect(JSON.stringify(event)).toBe(before);
    expect(Object.isFrozen(decodeSourcePublicEvent(event))).toBe(true);
  });

  it.each(['target', 'SYSTEM', 'player_sheet', 'session_id', 'request', 'capsule', 'error_json', 'can_retry', 'hash', 'timestamp'])('rejects extra %s on every event', key => {
    for (const event of legitimate) expect(decodeSourcePublicEvent({ ...event, [key]: 'PRIVATE' })).toBeNull();
  });

  it.each([
    null, [], 'text', 1, true, { ...complete, protocol: undefined }, { ...complete, protocol: 'old' },
    { ...complete, event: 'state_update' }, { ...complete, operation_id: 5 },
    { ...complete, operation_id: '' }, { ...complete, operation_id: ' op' },
    { ...complete, operation_id: 'op\u0085' }, { ...complete, operation_id: 'a'.repeat(241) },
    { ...complete, operation_id: '\ud800' }, { ...complete, n: 'a'.repeat(39) },
    { ...complete, n: 'a'.repeat(1601) }, { ...complete, n: n + ' ' },
    { ...complete, n: n.replace(' ', '\u0085') }, { ...complete, q: 'ab' },
    { ...complete, q: 'a'.repeat(201) }, { ...complete, q: q + '\n' },
    { ...complete, q: 4 }, { ...briefing, origin: 'model' },
    { ...briefing, text: ' \u0085 ' }, { ...briefing, text: '\udfff' },
    { protocol, event: 'preparation', operation_id, status: 'completed' },
    { protocol, event: 'narrative_pending', operation_id, status: 'ready' },
    { protocol, event: 'unavailable', operation_id, phase: 'unknown', code: 'unavailable' },
    { protocol, event: 'unavailable', operation_id, phase: 'narrative', code: 'retry' },
  ])('rejects malformed wire %#', event => expect(decodeSourcePublicEvent(event)).toBeNull());

  it('requires explicit protocol, event and public defaults in emitted wire', () => {
    for (const event of legitimate) {
      for (const field of ['protocol', 'event', ...('origin' in event ? ['origin'] : [])]) {
        const copy: Record<string, unknown> = { ...event };
        delete copy[field];
        expect(decodeSourcePublicEvent(copy)).toBeNull();
      }
    }
  });

  it('validates terminal status/code pairs and phase-specific stages', () => {
    for (const event of legitimate.filter(item => item.event.endsWith('_rejected'))) {
      for (const status of ['failed', 'timeout', 'cancelled']) {
        expect(decodeSourcePublicEvent({ ...event, status }) !== null).toBe('status' in event && status === event.status);
      }
      for (const stage of [false, 1, '', undefined, 'secret', 'retry']) {
        expect(decodeSourcePublicEvent({ ...event, stage })).toBeNull();
      }
      const copy = { ...event } as Record<string, unknown>;
      delete copy.stage;
      expect(decodeSourcePublicEvent(copy)).toEqual({ ...event, stage: null });
    }
    for (const stage of ['preflight', 'classification', 'resolution', 'production', 'finalization']) {
      expect(decodeSourcePublicEvent({ protocol, event: 'preparation_rejected', operation_id, status: 'failed', code: 'preparation_failed', stage })).not.toBeNull();
    }
    for (const stage of ['preflight', 'generation', 'policy', 'admission', 'delivery', 'commit']) {
      expect(decodeSourcePublicEvent({ protocol, event: 'narrative_rejected', operation_id, status: 'failed', code: 'narrative_failed', stage })).not.toBeNull();
    }
    expect(decodeSourcePublicEvent({ protocol, event: 'preparation_rejected', operation_id, status: 'failed', code: 'narrative_failed' })).toBeNull();
    expect(decodeSourcePublicEvent({ protocol, event: 'narrative_rejected', operation_id, status: 'failed', code: 'narrative_failed', stage: 'classification' })).toBeNull();
  });

  it('uses Unicode code points and does not invoke accessors or inherited fields', () => {
    expect(decodeSourcePublicEvent({ ...complete, operation_id: '🦇'.repeat(240), n: '🦇'.repeat(40) })).not.toBeNull();
    const forged = Object.defineProperty({}, 'protocol', { enumerable: true, get() { throw new Error('PRIVATE'); } });
    expect(decodeSourcePublicEvent(forged)).toBeNull();
    expect(decodeSourcePublicEvent(Object.create(complete))).toBeNull();
  });
});

describe('B presentation reducer', () => {
  it('records a local protocol_error without inventing a wire event or erasing prior data/problems', () => {
    const confirmed = reduce(receive(submitted(), complete), { type: 'query_failed' });
    const priorProblem = receive(confirmed, { ...complete, q: 'Como você reage?' });
    for (const before of [submitted(), confirmed, priorProblem]) {
      const after = reduce(before, { type: 'protocol_error' });
      expect(after.problem).toBe(before.problem ?? 'invalid_event');
      expect({ ...after, problem: before.problem }).toEqual(before);
      expect(after.operations).toBe(before.operations);
      expect(reduce(after, { type: 'protocol_error' })).toBe(after);
    }
    expect(decodeSourcePublicEvent({ protocol, event: 'protocol_error', operation_id })).toBeNull();
  });

  it('keeps the exact authored briefing separate and re-presents it idempotently', () => {
    const state = reduce(createSourceNarrativeState(), { type: 'present_briefing', event: briefing });
    expect(state.briefing).toBe(briefing.text);
    expect(state.operations).toEqual([]);
    expect(reduce(state, { type: 'present_briefing', event: briefing })).toBe(state);
    const conflict = reduce(state, { type: 'present_briefing', event: { ...briefing, text: 'Other' } });
    expect(conflict.problem).toBe('conflicting_event');
    expect(conflict.briefing).toBe(briefing.text);
  });

  it('retains submitted input and identity across every distinct nonterminal phase', () => {
    let state = submitted();
    const labels = [sourceOperationLabel(state.operations[0])];
    for (const event of legitimate.filter(item => item.event === 'preparation' || item.event === 'narrative_pending')) {
      state = receive(state, event);
      labels.push(sourceOperationLabel(state.operations[0]));
      expect(state.draft).toBe(player_input);
      expect(state.currentOperationId).toBe(operation_id);
      expect(state.operations[0].playerInput).toBe(player_input);
      expect(state.operations[0].lastEvent?.event).not.toBe('narrative_complete');
    }
    expect(new Set(labels).size).toBe(5);
    expect(labels[2]).toContain('Ação preparada');
    expect(labels[3]).toContain('a narrativa ainda não começou');
    expect(labels[4]).toContain('O narrador está preparando');
  });

  it.each(legitimate.filter(item => item.event.endsWith('_rejected')))('preserves terminal failure %# and rejects conflicting replacements', event => {
    const before = submitted();
    const state = receive(before, event);
    expect(state.operations[0].playerInput).toBe(player_input);
    expect(state.draft).toBe(player_input);
    expect(receive(state, event)).toBe(state);
    expect(receive(state, complete).problem).toBe('conflicting_event');
    expect(receive(state, complete).operations).toBe(state.operations);
    expect(before.operations[0].lastEvent).toBeNull();
  });

  it('does not regress or duplicate a confirmed terminal; rejects conflicting n and q', () => {
    const state = receive(submitted(), complete);
    expect(receive(state, complete)).toBe(state);
    for (const event of legitimate.filter(item => item.event === 'preparation' || item.event === 'narrative_pending' || item.event === 'unavailable')) {
      expect(receive(state, event)).toBe(state);
    }
    for (const event of [{ ...complete, n: n + ' A luz apaga.' }, { ...complete, q: 'Como você reage?' }]) {
      const conflict = receive(state, event);
      expect(conflict.problem).toBe('conflicting_event');
      expect(conflict.operations).toBe(state.operations);
    }
  });

  it('does not interpret unavailable or ambiguous delivery as execution, failure, or retry permission', () => {
    const state = receive(submitted(), { protocol, event: 'preparation', operation_id, status: 'ready' });
    const unavailable = receive(state, { protocol, event: 'unavailable', operation_id, phase: 'narrative', code: 'unavailable' });
    expect(unavailable.operations[0].lastEvent).toEqual(state.operations[0].lastEvent);
    expect(unavailable.operations[0].uncertain).toBe(true);
    expect(reduce(unavailable, { type: 'new_action' })).toBe(unavailable);
    const uncertain = reduce(state, { type: 'delivery_uncertain', operationId: operation_id });
    expect(uncertain.draft).toBe(player_input);
    expect(sourceOperationLabel(uncertain.operations[0])).toContain('Consulte o estado');
  });

  it('requires operation identity and preserves safe state on invalid input', () => {
    const state = submitted();
    for (const action of [
      { type: 'receive' as const, operationId: 'other', event: complete },
      { type: 'receive' as const, operationId: 'other', event: { ...complete, operation_id: 'other' } },
      { type: 'receive' as const, operationId: operation_id, event: { ...complete, can_retry: true } },
    ]) {
      const rejected = reduce(state, action);
      expect(rejected.problem).not.toBeNull();
      expect(rejected.operations).toBe(state.operations);
      expect(rejected.draft).toBe(player_input);
    }
  });

  it('presents only the latest known text without inventing input, timestamps, turn numbers or old history', () => {
    const state = reduce(createSourceNarrativeState(), { type: 'present_latest', event: complete });
    expect(state.operations).toHaveLength(1);
    expect(state.operations[0].playerInput).toBeNull();
    expect(state.currentOperationId).toBeNull();
    expect(reduce(state, { type: 'present_latest', event: complete })).toBe(state);
    expect(JSON.stringify(state)).not.toMatch(/timestamp|turn_number|player_sheet/);
    expect(reduce(state, { type: 'present_latest', event: legitimate[1] }).problem).toBe('invalid_event');
  });

  it('requires a deliberate new action and a new identity after a terminal', () => {
    const state = receive(submitted(), complete);
    const fresh = reduce(state, { type: 'new_action' });
    expect(fresh.draft).toBe('');
    expect(fresh.operations).toBe(state.operations);
    expect(reduce(fresh, { type: 'submitted', action: { operation_id, player_input } }).problem).toBe('invalid_submission');
    const next = reduce(fresh, { type: 'submitted', action: { operation_id: 'op-new', player_input } });
    expect(next.problem).toBeNull();
    expect(next.operations).toHaveLength(2);
  });

  it.each([
    { protocol, event: 'preparation', operation_id, status: 'ready' },
    { protocol, event: 'narrative_pending', operation_id, status: 'retained_unstarted' },
    { protocol, event: 'narrative_pending', operation_id, status: 'pending' },
  ])('does not regress a completed preparation into failure %#', event => {
    const pending = receive(submitted(), event);
    const result = receive(pending, { protocol, event: 'preparation_rejected', operation_id, status: 'failed', code: 'preparation_failed' });
    expect(result.problem).toBe('conflicting_event');
    expect(result.operations).toBe(pending.operations);
  });

  it('clears a failed-query notice only after a valid matching observation or latest presentation', () => {
    const failed = reduce(submitted(), { type: 'query_failed' });
    expect(receive(failed, { ...complete, can_retry: true }).queryFailed).toBe(true);
    expect(receive(failed, complete, 'other').queryFailed).toBe(true);
    expect(receive(failed, complete).queryFailed).toBe(false);
    const presented = reduce(reduce(createSourceNarrativeState(), { type: 'query_failed' }), { type: 'present_latest', event: complete });
    expect(presented.queryFailed).toBe(false);
    const repeated = reduce(presented, { type: 'query_failed' });
    expect(reduce(repeated, { type: 'present_latest', event: complete }).queryFailed).toBe(false);
  });
});
