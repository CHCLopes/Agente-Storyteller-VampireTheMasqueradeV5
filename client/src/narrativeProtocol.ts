import type {
  NarrativeMessage,
  PersistedNarrativeMessageType,
} from './types/narrative';

export interface NarrativeProtocolState {
  messages: NarrativeMessage[];
  currentStreamText: string;
  isLoading: boolean;
  narrationPause: NarrationPause | null;
}

export interface NarrationPause {
  capsuleId: string;
  sourceOperationId: string;
  expectedStateRevision: number;
  actionSummary: string;
  resolutionSummary?: string;
  category: string;
  safeMessage: string;
  retryable: boolean;
  retryNotBefore?: string;
  serverNow?: string;
  rateLimitOrigin?: 'gateway' | 'upstream' | 'unknown';
  gateScope?: 'exact_target' | 'gateway_account' | 'upstream_target' | 'unknown_conservative';
  evidenceScope?: string;
  allowedActions: readonly ('resume' | 'abandon')[];
}

interface AppendMessageAction {
  type: 'append_message';
  message: NarrativeMessage;
  isLoading?: boolean;
}

interface SetLoadingAction {
  type: 'set_loading';
  isLoading: boolean;
}

interface HydrateHistoryAction {
  type: 'hydrate_history';
  history: readonly unknown[];
  fallbackTimestamp: string;
}

interface StreamStartAction {
  type: 'stream_start';
}

interface StreamChunkAction {
  type: 'stream_chunk';
  chunk: unknown;
}

interface StreamEndAction {
  type: 'stream_end';
  operationId?: unknown;
  status: unknown;
  narrative: unknown;
  resolutionReceipt?: unknown;
  fallbackId: string;
  fallbackTimestamp: string;
}

interface ClarificationAction {
  type: 'clarification';
  message: unknown;
  operationId: unknown;
  terminal: unknown;
  fallbackTimestamp: string;
}

interface NarrationPausedAction { type: 'narration_paused'; payload: unknown; }
interface ClearNarrationPauseAction { type: 'clear_narration_pause'; }

export type NarrativeProtocolAction =
  | AppendMessageAction
  | SetLoadingAction
  | HydrateHistoryAction
  | StreamStartAction
  | StreamChunkAction
  | StreamEndAction
  | ClarificationAction
  | NarrationPausedAction
  | ClearNarrationPauseAction;

export function sendConnectedAction(
  action: string,
  send: (message: string) => boolean,
): string | null {
  const normalized = action.trim();
  if (!normalized || !send(normalized)) return null;
  return normalized;
}

interface UnknownRecord {
  [key: string]: unknown;
}

function asRecord(value: unknown): UnknownRecord | null {
  if (typeof value !== 'object' || value === null || Array.isArray(value)) {
    return null;
  }
  return value as UnknownRecord;
}

function nonEmptyString(value: unknown): string | null {
  return typeof value === 'string' && value.trim() ? value : null;
}

function persistedMessageType(value: unknown): PersistedNarrativeMessageType | null {
  if (value === undefined || value === null) return 'narrator';
  if (value === 'narrator' || value === 'mechanics' || value === 'guidance') {
    return value;
  }
  return null;
}

function appendUniqueMessages(
  messages: NarrativeMessage[],
  candidates: readonly NarrativeMessage[],
): NarrativeMessage[] {
  const knownIds = new Set(messages.map(message => message.id));
  const uniqueCandidates: NarrativeMessage[] = [];

  for (const candidate of candidates) {
    if (knownIds.has(candidate.id)) continue;
    knownIds.add(candidate.id);
    uniqueCandidates.push(candidate);
  }

  return uniqueCandidates.length ? [...messages, ...uniqueCandidates] : messages;
}

function appendMessage(messages: NarrativeMessage[], message: NarrativeMessage): NarrativeMessage[] {
  // A terminal fallback may arrive before the backend's specific error.
  // Replace only the same operation's error, preserving its position and ID.
  const previous = messages.find(item => item.id === message.id);
  if (message.type === 'error' && previous?.type === 'error') {
    return previous.content === message.content
      ? messages
      : messages.map(item => item.id === message.id ? message : item);
  }
  return appendUniqueMessages(messages, [message]);
}

function recordUncompletedStream(
  messages: NarrativeMessage[],
  action: StreamEndAction,
): NarrativeMessage[] {
  let content: string;
  switch (action.status) {
    case 'failed':
      content = 'A continuação não foi concluída. Sua ação permanece no registro.';
      break;
    case 'cancelled':
      content = 'A geração da continuação foi interrompida.';
      break;
    case 'timeout':
      content = 'O Narrador não respondeu dentro do prazo.';
      break;
    default:
      content = 'Não foi possível confirmar o resultado desta ação.';
  }
  const operationId = nonEmptyString(action.operationId) ?? action.fallbackId;
  // This is feedback about the terminal status, never rejected/provisional text.
  // An earlier specific error with this ID wins over the generic fallback.
  return appendUniqueMessages(messages, [{
    id: `error:${operationId}`,
    type: 'error',
    content: `[Erro do Sistema] ${content}`,
    timestamp: action.fallbackTimestamp,
  }]);
}

function historyMessage(value: unknown, fallbackTimestamp: string): NarrativeMessage | null {
  const item = asRecord(value);
  if (!item) return null;

  const id = nonEmptyString(item.id);
  const content = nonEmptyString(item.content);
  const type = persistedMessageType(item.type);
  if (!id || !content || !type) return null;

  const narrativeMode = type === 'mechanics'
    ? nonEmptyString(item.narrative_mode) ?? undefined
    : undefined;

  return {
    id,
    type,
    content,
    timestamp: nonEmptyString(item.timestamp) ?? fallbackTimestamp,
    ...(narrativeMode ? { narrativeMode } : {}),
  };
}

function hydrateHistory(
  messages: NarrativeMessage[],
  history: readonly unknown[],
  fallbackTimestamp: string,
): NarrativeMessage[] {
  const recovered: NarrativeMessage[] = [];

  for (const item of history) {
    const message = historyMessage(item, fallbackTimestamp);
    if (message) recovered.push(message);
  }

  return appendUniqueMessages(messages, recovered);
}

function promoteCompletedStream(
  state: NarrativeProtocolState,
  action: StreamEndAction,
): NarrativeMessage[] {
  if (action.status !== 'completed') return state.messages;

  const candidates: NarrativeMessage[] = [];
  const receipt = asRecord(action.resolutionReceipt);
  const receiptId = nonEmptyString(receipt?.receipt_id);
  const receiptDisplay = nonEmptyString(receipt?.display);
  const narrativeMode = nonEmptyString(receipt?.narrative_mode);

  if (receiptId && receiptDisplay && narrativeMode) {
    candidates.push({
      id: receiptId,
      type: 'mechanics',
      content: receiptDisplay,
      timestamp: action.fallbackTimestamp,
      narrativeMode,
    });
  }

  const narrative = asRecord(action.narrative);
  const committedText = nonEmptyString(narrative?.text);
  const committedId = nonEmptyString(narrative?.narrative_id);

  if (committedText && committedId) {
    candidates.push({
      id: committedId,
      type: 'narrator',
      content: committedText,
      timestamp: nonEmptyString(narrative?.created_at) ?? action.fallbackTimestamp,
    });
  }

  return appendUniqueMessages(state.messages, candidates);
}

function promoteClarification(
  messages: NarrativeMessage[],
  action: ClarificationAction,
): NarrativeMessage[] {
  if (action.terminal !== true) return messages;

  const operationId = nonEmptyString(action.operationId);
  const content = nonEmptyString(action.message);
  if (!operationId || !content) return messages;

  return appendUniqueMessages(messages, [
    {
      id: `guidance:${operationId}`,
      type: 'guidance',
      content,
      timestamp: action.fallbackTimestamp,
    },
  ]);
}

function parseNarrationPause(value: unknown): NarrationPause | null {
  const item = asRecord(value);
  if (!item) return null;
  const capsuleId = nonEmptyString(item.capsule_id);
  const sourceOperationId = nonEmptyString(item.source_operation_id);
  const actionSummary = nonEmptyString(item.action_summary);
  const category = nonEmptyString(item.category);
  const safeMessage = nonEmptyString(item.safe_message);
  const revision = item.expected_state_revision;
  if (!capsuleId || !sourceOperationId || !actionSummary || !category || !safeMessage
      || typeof revision !== 'number' || !Number.isInteger(revision) || revision < 0) return null;
  const allowed = Array.isArray(item.allowed_actions)
    ? item.allowed_actions.filter((v): v is 'resume' | 'abandon' => v === 'resume' || v === 'abandon')
    : [];
  return {
    capsuleId, sourceOperationId, expectedStateRevision: revision, actionSummary,
    category, safeMessage, retryable: item.retryable === true,
    resolutionSummary: nonEmptyString(item.resolution_summary) ?? undefined,
    retryNotBefore: nonEmptyString(item.retry_not_before) ?? undefined,
    serverNow: nonEmptyString(item.server_now) ?? undefined,
    rateLimitOrigin: (
      item.rate_limit_origin === 'gateway' || item.rate_limit_origin === 'upstream'
        || item.rate_limit_origin === 'unknown'
        ? item.rate_limit_origin : undefined
    ),
    gateScope: (
      item.gate_scope === 'exact_target' || item.gate_scope === 'gateway_account'
        || item.gate_scope === 'upstream_target' || item.gate_scope === 'unknown_conservative'
        ? item.gate_scope : undefined
    ),
    evidenceScope: nonEmptyString(item.evidence_scope) ?? undefined,
    allowedActions: allowed,
  };
}

export function createInitialNarrativeState(timestamp: string): NarrativeProtocolState {
  return {
    messages: [
      {
        id: 'init-sys',
        type: 'system',
        content: '[Sistema] Sistema Pronto. Boa Caçada! 🦇',
        timestamp,
      },
    ],
    currentStreamText: '',
    isLoading: false,
    narrationPause: null,
  };
}

export function narrativeProtocolReducer(
  state: NarrativeProtocolState,
  action: NarrativeProtocolAction,
): NarrativeProtocolState {
  switch (action.type) {
    case 'append_message':
      return {
        ...state,
        messages: appendMessage(state.messages, action.message),
        isLoading: action.isLoading ?? state.isLoading,
      };
    case 'set_loading':
      return { ...state, isLoading: action.isLoading };
    case 'hydrate_history':
      return {
        ...state,
        messages: hydrateHistory(state.messages, action.history, action.fallbackTimestamp),
        currentStreamText: '',
        isLoading: false,
      };
    case 'stream_start':
      return { ...state, currentStreamText: '', isLoading: true };
    case 'stream_chunk':
      return typeof action.chunk === 'string' && action.chunk
        ? { ...state, currentStreamText: state.currentStreamText + action.chunk }
        : state;
    case 'stream_end':
      if (action.status === 'pending') return { ...state, isLoading: true };
      return {
        ...state,
        messages: action.status === 'completed'
          ? promoteCompletedStream(state, action)
          : recordUncompletedStream(state.messages, action),
        currentStreamText: '',
        isLoading: false,
        narrationPause: action.status === 'completed' ? null : state.narrationPause,
      };
    case 'clarification':
      if (action.terminal !== true) return state;
      return {
        ...state,
        messages: promoteClarification(state.messages, action),
        currentStreamText: '',
        isLoading: false,
      };
    case 'narration_paused': {
      const pause = parseNarrationPause(action.payload);
      return pause ? { ...state, currentStreamText: '', isLoading: false, narrationPause: pause } : state;
    }
    case 'clear_narration_pause':
      return { ...state, narrationPause: null, currentStreamText: '', isLoading: false };
  }
}
