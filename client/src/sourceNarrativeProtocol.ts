/** Inactive B presentation state. It grants no execution, retry or storage authority. */
export const SOURCE_PUBLIC_PROTOCOL = 'narrative-source-public-event-v1' as const;

type BaseEvent = { readonly protocol: typeof SOURCE_PUBLIC_PROTOCOL };
type OperationEvent = BaseEvent & { readonly operation_id: string };
type Terminal = 'failed' | 'timeout' | 'cancelled';
type PreparationStage = 'preflight' | 'classification' | 'resolution' | 'production' | 'finalization';
type NarrativeStage = 'preflight' | 'generation' | 'policy' | 'admission' | 'delivery' | 'commit';

export type SourceBriefingEvent = BaseEvent & {
  readonly event: 'briefing'; readonly origin: 'authored_trial_setup'; readonly text: string;
};
export type SourcePublicOperationEvent =
  | (OperationEvent & { readonly event: 'preparation'; readonly status: 'pending' | 'ready' })
  | (OperationEvent & { readonly event: 'preparation_rejected'; readonly status: Terminal;
      readonly code: 'out_of_scope' | 'clarification_required' | 'preparation_failed' | 'cancelled' | 'timeout';
      readonly stage: PreparationStage | null })
  | (OperationEvent & { readonly event: 'narrative_pending'; readonly status: 'retained_unstarted' | 'pending' })
  | (OperationEvent & { readonly event: 'narrative_complete'; readonly n: string; readonly q: string })
  | (OperationEvent & { readonly event: 'narrative_rejected'; readonly status: Terminal;
      readonly code: 'narrative_rejected' | 'narrative_failed' | 'cancelled' | 'timeout';
      readonly stage: NarrativeStage | null })
  | (OperationEvent & { readonly event: 'unavailable'; readonly phase: 'preparation' | 'narrative';
      readonly code: 'unavailable' });
export type SourcePublicEvent = SourceBriefingEvent | SourcePublicOperationEvent;
export interface SourcePlayerAction {
  readonly operation_id: string;
  readonly player_input: string;
}

// Match Python's str.strip()/split() and code-point lengths, including U+0085.
const whitespace = '[\\t\\n\\v\\f\\r\\u001c-\\u0020\\u0085\\u00a0\\u1680\\u2000-\\u200a\\u2028\\u2029\\u202f\\u205f\\u3000]';
const strip = (value: string) => value.replace(new RegExp(`^${whitespace}+|${whitespace}+$`, 'gu'), '');
const normalized = (value: string) => strip(value).replace(new RegExp(`${whitespace}+`, 'gu'), ' ');

function text(value: unknown, min: number, max = Infinity): value is string {
  if (typeof value !== 'string') return false;
  const points = Array.from(value);
  return points.length >= min && points.length <= max && points.every(point => {
    const code = point.codePointAt(0)!;
    return code < 0xd800 || code > 0xdfff;
  });
}

function literal(value: unknown, max: number): value is string {
  return text(value, 1, max) && value === strip(value);
}

function record(value: unknown): Record<string, unknown> | null {
  if (typeof value !== 'object' || value === null || Array.isArray(value)) return null;
  const prototype = Object.getPrototypeOf(value);
  if (prototype !== Object.prototype && prototype !== null) return null;
  if (Object.getOwnPropertySymbols(value).length) return null;
  const descriptors = Object.getOwnPropertyDescriptors(value);
  if (Object.values(descriptors).some(item => !item.enumerable || !('value' in item))) return null;
  return value as Record<string, unknown>;
}

function shape(value: Record<string, unknown>, required: readonly string[], optional: readonly string[] = []): boolean {
  return required.every(key => Object.hasOwn(value, key))
    && Object.keys(value).every(key => required.includes(key) || optional.includes(key));
}

const isOneOf = <T extends string>(value: unknown, choices: readonly T[]): value is T =>
  typeof value === 'string' && choices.includes(value as T);

/** Wire fields are explicit; unlike Python model construction, version is never inferred. */
export function decodeSourcePublicEvent(value: unknown): SourcePublicEvent | null {
  try {
    const item = record(value);
    if (!item || item.protocol !== SOURCE_PUBLIC_PROTOCOL || typeof item.event !== 'string') return null;
    const base = { protocol: SOURCE_PUBLIC_PROTOCOL };
    if (item.event === 'briefing') {
      if (!shape(item, ['protocol', 'event', 'origin', 'text'])
        || item.origin !== 'authored_trial_setup' || !text(item.text, 1) || !strip(item.text)) return null;
      return Object.freeze({ ...base, event: 'briefing', origin: item.origin, text: item.text });
    }
    if (!literal(item.operation_id, 240)) return null;
    const operation = { ...base, operation_id: item.operation_id };
    const fields = ['protocol', 'event', 'operation_id'];
    switch (item.event) {
      case 'preparation':
        if (!shape(item, [...fields, 'status']) || !isOneOf(item.status, ['pending', 'ready'])) return null;
        return Object.freeze({ ...operation, event: item.event, status: item.status });
      case 'narrative_pending':
        if (!shape(item, [...fields, 'status']) || !isOneOf(item.status, ['retained_unstarted', 'pending'])) return null;
        return Object.freeze({ ...operation, event: item.event, status: item.status });
      case 'narrative_complete':
        if (!shape(item, [...fields, 'n', 'q']) || !text(item.n, 40, 1600) || !text(item.q, 3, 200)
          || normalized(item.n) !== item.n || normalized(item.q) !== item.q) return null;
        return Object.freeze({ ...operation, event: item.event, n: item.n, q: item.q });
      case 'preparation_rejected': {
        if (!shape(item, [...fields, 'status', 'code'], ['stage'])
          || !isOneOf(item.code, ['out_of_scope', 'clarification_required', 'preparation_failed', 'cancelled', 'timeout'])) return null;
        const status = item.code === 'cancelled' || item.code === 'timeout' ? item.code : 'failed';
        const stage = Object.hasOwn(item, 'stage') ? item.stage : null;
        if (item.status !== status || (stage !== null && !isOneOf(stage, ['preflight', 'classification', 'resolution', 'production', 'finalization']))) return null;
        return Object.freeze({ ...operation, event: item.event, status, code: item.code, stage });
      }
      case 'narrative_rejected': {
        if (!shape(item, [...fields, 'status', 'code'], ['stage'])
          || !isOneOf(item.code, ['narrative_rejected', 'narrative_failed', 'cancelled', 'timeout'])) return null;
        const status = item.code === 'cancelled' || item.code === 'timeout' ? item.code : 'failed';
        const stage = Object.hasOwn(item, 'stage') ? item.stage : null;
        if (item.status !== status || (stage !== null && !isOneOf(stage, ['preflight', 'generation', 'policy', 'admission', 'delivery', 'commit']))) return null;
        return Object.freeze({ ...operation, event: item.event, status, code: item.code, stage });
      }
      case 'unavailable':
        if (!shape(item, [...fields, 'phase', 'code']) || item.code !== 'unavailable'
          || !isOneOf(item.phase, ['preparation', 'narrative'])) return null;
        return Object.freeze({ ...operation, event: item.event, phase: item.phase, code: item.code });
      default:
        return null;
    }
  } catch {
    return null;
  }
}

export interface SourceOperationRecord {
  readonly operationId: string;
  /** null only for a confirmed narrative presented without a local submitted action. */
  readonly playerInput: string | null;
  readonly lastEvent: Exclude<SourcePublicOperationEvent, { event: 'unavailable' }> | null;
  readonly uncertain: boolean;
}
export interface SourceNarrativeState {
  readonly briefing: string | null;
  readonly draft: string;
  readonly operations: readonly SourceOperationRecord[];
  readonly currentOperationId: string | null;
  readonly problem: 'invalid_event' | 'identity_mismatch' | 'conflicting_event' | 'invalid_submission' | null;
  readonly queryFailed: boolean;
}
export type SourceNarrativeAction =
  | { type: 'edit_draft'; text: string }
  | { type: 'submitted'; action: SourcePlayerAction }
  | { type: 'present_briefing'; event: unknown }
  | { type: 'present_latest'; event: unknown }
  | { type: 'receive'; operationId: string; event: unknown }
  | { type: 'delivery_uncertain'; operationId: string }
  | { type: 'query_failed' }
  | { type: 'protocol_error' }
  | { type: 'new_action' };

export function createSourceNarrativeState(): SourceNarrativeState {
  return { briefing: null, draft: '', operations: [], currentOperationId: null, problem: null, queryFailed: false };
}

export function isSourceTerminal(operation: SourceOperationRecord): boolean {
  return operation.lastEvent?.event === 'narrative_complete'
    || operation.lastEvent?.event === 'preparation_rejected'
    || operation.lastEvent?.event === 'narrative_rejected';
}

function rank(event: SourceOperationRecord['lastEvent']): number {
  if (!event) return 0;
  if (event.event === 'preparation') return event.status === 'pending' ? 1 : 2;
  if (event.event === 'narrative_pending') return event.status === 'retained_unstarted' ? 3 : 4;
  return 5;
}

function updateOperation(state: SourceNarrativeState, id: string, update: (operation: SourceOperationRecord) => SourceOperationRecord): SourceNarrativeState {
  return { ...state, operations: state.operations.map(operation => operation.operationId === id ? update(operation) : operation) };
}

function observeOperation(state: SourceNarrativeState, event: SourcePublicOperationEvent): SourceNarrativeState {
  const operation = state.operations.find(item => item.operationId === event.operation_id);
  if (!operation) return { ...state, problem: 'identity_mismatch' };
  const observed = state.queryFailed ? { ...state, queryFailed: false } : state;
  if (event.event === 'unavailable') {
    return isSourceTerminal(operation) ? observed : updateOperation(observed, event.operation_id, item => ({ ...item, uncertain: true }));
  }
  if (isSourceTerminal(operation)) {
    if (rank(event) < 5 || JSON.stringify(operation.lastEvent) === JSON.stringify(event)) return observed;
    return { ...state, problem: 'conflicting_event' };
  }
  if (event.event === 'preparation_rejected' && rank(operation.lastEvent) >= 2) {
    return { ...state, problem: 'conflicting_event' };
  }
  if (rank(event) < rank(operation.lastEvent)) return observed;
  return updateOperation(observed, event.operation_id, item => ({ ...item, lastEvent: event, uncertain: false }));
}

/** No clock, socket, browser storage, action generation or replay occurs in this reducer. */
export function sourceNarrativeReducer(state: SourceNarrativeState, action: SourceNarrativeAction): SourceNarrativeState {
  switch (action.type) {
    case 'edit_draft':
      return state.currentOperationId === null && text(action.text, 0, 500)
        ? { ...state, draft: action.text } : state;
    case 'submitted': {
      const item = record(action.action);
      if (state.problem || state.currentOperationId !== null || !item
        || !shape(item, ['operation_id', 'player_input']) || !literal(item.operation_id, 240)
        || !literal(item.player_input, 500) || !strip(item.player_input)
        || state.operations.some(operation => operation.operationId === item.operation_id)) {
        return { ...state, problem: 'invalid_submission' };
      }
      return { ...state, draft: item.player_input, currentOperationId: item.operation_id,
        operations: [...state.operations, { operationId: item.operation_id, playerInput: item.player_input, lastEvent: null, uncertain: false }] };
    }
    case 'present_briefing': {
      const event = decodeSourcePublicEvent(action.event);
      if (event?.event !== 'briefing') return { ...state, problem: 'invalid_event' };
      if (state.briefing !== null && state.briefing !== event.text) return { ...state, problem: 'conflicting_event' };
      return state.briefing === event.text ? state : { ...state, briefing: event.text };
    }
    case 'present_latest': {
      const event = decodeSourcePublicEvent(action.event);
      if (event?.event !== 'narrative_complete') return { ...state, problem: 'invalid_event' };
      if (state.operations.some(item => item.operationId === event.operation_id)) return observeOperation(state, event);
      // This is one presented confirmed text, not fabricated history, input or chronology.
      return { ...state, queryFailed: false, operations: [...state.operations, { operationId: event.operation_id, playerInput: null, lastEvent: event, uncertain: false }] };
    }
    case 'receive': {
      const event = decodeSourcePublicEvent(action.event);
      if (!event || event.event === 'briefing') return { ...state, problem: 'invalid_event' };
      if (event.operation_id !== action.operationId) return { ...state, problem: 'identity_mismatch' };
      return observeOperation(state, event);
    }
    case 'delivery_uncertain':
      return updateOperation(state, action.operationId, item => isSourceTerminal(item) ? item : { ...item, uncertain: true });
    case 'query_failed':
      return { ...state, queryFailed: true };
    case 'protocol_error':
      return state.problem ? state : { ...state, problem: 'invalid_event' };
    case 'new_action': {
      const current = state.operations.find(item => item.operationId === state.currentOperationId);
      return current && isSourceTerminal(current) && !state.problem
        ? { ...state, currentOperationId: null, draft: '', queryFailed: false } : state;
    }
  }
}

export function sourceOperationLabel(operation: SourceOperationRecord): string {
  if (operation.uncertain) return 'Não foi possível confirmar o estado desta ação. Consulte o estado; sua ação foi conservada.';
  const event = operation.lastEvent;
  if (!event) return 'Ação enviada; aguardando confirmação.';
  if (event.event === 'preparation') return event.status === 'pending'
    ? 'Preparando sua ação.' : 'Ação preparada; aguardando a continuação.';
  if (event.event === 'narrative_pending') return event.status === 'pending'
    ? 'O narrador está preparando a continuação.' : 'A ação está preparada; a narrativa ainda não começou.';
  if (event.event === 'narrative_complete') return 'Continuação confirmada.';
  if (event.code === 'cancelled') return 'O processamento foi interrompido. Sua ação foi conservada.';
  if (event.code === 'timeout') return 'O prazo de resposta terminou. Sua ação foi conservada.';
  if (event.code === 'out_of_scope') return 'Essa ação não está disponível neste ensaio. Sua ação foi conservada.';
  if (event.code === 'clarification_required') return 'A ação precisa de esclarecimento. Sua ação foi conservada.';
  return event.event === 'preparation_rejected'
    ? 'Não foi possível preparar a ação. Sua ação foi conservada.'
    : 'A continuação não foi confirmada. Sua ação foi conservada.';
}
