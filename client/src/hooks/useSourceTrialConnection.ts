import { useCallback, useEffect, useRef, useState } from 'react';
import {
  SOURCE_PUBLIC_PROTOCOL,
  createSourceNarrativeState,
  decodeSourcePublicEvent,
  isSourceTerminal,
  sourceNarrativeReducer,
} from '../sourceNarrativeProtocol';
import type { SourceNarrativeAction, SourcePlayerAction } from '../sourceNarrativeProtocol';

export const SOURCE_COMMAND_PROTOCOL = 'narrative-source-command-v1' as const;
type SourceSocket = Pick<WebSocket, 'readyState' | 'send' | 'close' | 'onopen' | 'onmessage' | 'onclose' | 'onerror'>;
export type SourceSocketFactory = (endpoint: string) => SourceSocket;
type Link = { socket: SourceSocket; generation: number; phase: 'briefing' | 'initial' | 'stream' };
const nativeSocket: SourceSocketFactory = endpoint => new WebSocket(endpoint);
const pythonWhitespaceClass = '[\\t\\n\\v\\f\\r\\u001c-\\u0020\\u0085\\u00a0\\u1680\\u2000-\\u200a\\u2028\\u2029\\u202f\\u205f\\u3000]';
const pythonWhitespace = new RegExp('^' + pythonWhitespaceClass + '|' + pythonWhitespaceClass + '$', 'u');

function identity(value: string): boolean {
  const points = Array.from(value);
  return points.length >= 1 && points.length <= 240 && !pythonWhitespace.test(value)
    && points.every(point => { const code = point.codePointAt(0)!; return code < 0xd800 || code > 0xdfff; });
}

function port(value: string): boolean {
  return /^[1-9][0-9]{0,4}$/.test(value) && Number(value) <= 65535;
}

/** Fixed loopback transport configuration, never authentication or session authority. */
export function validateSourceTrialEndpoint(endpoint: string): string {
  const match = /^ws:\/\/127\.0\.0\.1:([1-9][0-9]{0,4})\/ws\/source-local\/([^?#]+)$/u.exec(endpoint);
  if (!match || !port(match[1])) throw new Error('source_trial_configuration_invalid');
  try {
    const session = decodeURIComponent(match[2]);
    const url = new URL(endpoint);
    if (!identity(session) || encodeURIComponent(session) !== match[2]
      || url.pathname !== '/ws/source-local/' + match[2]
      || url.host !== '127.0.0.1:' + match[1] || url.username || url.password || url.search || url.hash) throw new Error();
    return endpoint;
  } catch {
    throw new Error('source_trial_configuration_invalid');
  }
}

/** Only launcher-authored backendPort/session parameters; no environment or remote config. */
function endpointFromPageUrl(pageUrl: string, page: 'source-trial.html' | 'source-player-trial.html'): string {
  try {
    const match = /^http:\/\/127\.0\.0\.1:([1-9][0-9]{0,4})\/(source-trial\.html|source-player-trial\.html)(?:\?|$)/u.exec(pageUrl);
    if (!match || !port(match[1]) || match[2] !== page) throw new Error();
    const url = new URL(pageUrl);
    const entries: Array<[string, string]> = [];
    url.searchParams.forEach((value, key) => entries.push([key, value]));
    if (url.username || url.password || url.hash || url.pathname !== '/' + page
      || url.host !== '127.0.0.1:' + match[1] || entries.length !== 2
      || entries.filter(([key]) => key === 'backendPort').length !== 1
      || entries.filter(([key]) => key === 'session').length !== 1) throw new Error();
    const backendPort = url.searchParams.get('backendPort')!;
    const session = url.searchParams.get('session')!;
    if (!port(backendPort) || !identity(session)) throw new Error();
    return validateSourceTrialEndpoint('ws://127.0.0.1:' + backendPort + '/ws/source-local/' + encodeURIComponent(session));
  } catch {
    throw new Error('source_trial_configuration_invalid');
  }
}

export function sourceTrialEndpointFromPageUrl(pageUrl: string): string {
  return endpointFromPageUrl(pageUrl, 'source-trial.html');
}

export function sourcePlayerTrialEndpointFromPageUrl(pageUrl: string): string {
  return sourcePlayerTrialConfigurationFromPageUrl(pageUrl).endpoint;
}

export type SourcePlayerTrialProvider = 'groq' | 'luna';

export function sourcePlayerTrialConfigurationFromPageUrl(pageUrl: string): {
  endpoint: string; provider: SourcePlayerTrialProvider;
} {
  const endpoint = endpointFromPageUrl(pageUrl, 'source-player-trial.html');
  // Prevent an edited fixture URL from acquiring the real-provider presentation.
  // This name is configuration only; server admission remains authoritative.
  const session = new URL(pageUrl).searchParams.get('session')!;
  const match = /^source-(groq|luna)-trial\.[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/u.exec(session);
  if (!match) {
    throw new Error('source_trial_configuration_invalid');
  }
  return { endpoint, provider: match[1] as SourcePlayerTrialProvider };
}

/** Inactive until connect() is explicitly called. Keep this hook above the view.
 * State and attempted IDs survive socket replacement, not page reload/unmount.
 * No timer, browser storage, automatic submit, diagnostics or target selection.
 */
export function useSourceTrialConnection(endpoint: string, createSocket: SourceSocketFactory = nativeSocket,
  onUnavailable?: (operationId: string) => void) {
  const [state, setState] = useState(createSourceNarrativeState);
  const stateRef = useRef(state);
  const [connection, setConnection] = useState<'disconnected' | 'connecting' | 'connected'>('disconnected');
  const [connectionFailed, setConnectionFailed] = useState(false);
  const initialEndpoint = useRef(endpoint);
  const linkRef = useRef<Link | null>(null);
  const generation = useRef(0);
  const attempted = useRef(new Set<string>());
  const reportedUnavailable = useRef(new Set<string>());
  const mounted = useRef(true);

  // View dispatches submitted before invoking onSubmit in the same event. This
  // synchronous reference makes that retained request visible before React paints.
  const dispatch = useCallback((action: SourceNarrativeAction) => {
    if (!mounted.current) return;
    const next = sourceNarrativeReducer(stateRef.current, action);
    stateRef.current = next;
    setState(next);
  }, []);

  const retire = useCallback((link: Link, failed = false, code = 1000) => {
    if (linkRef.current !== link) return;
    linkRef.current = null;
    generation.current += 1;
    link.socket.onopen = link.socket.onmessage = link.socket.onclose = link.socket.onerror = null;
    if (mounted.current) {
      setConnection('disconnected');
      setConnectionFailed(failed);
      const current = stateRef.current.operations.find(item => item.operationId === stateRef.current.currentOperationId);
      if (current && !isSourceTerminal(current)) dispatch({ type: 'delivery_uncertain', operationId: current.operationId });
    }
    try { link.socket.close(code); } catch { /* No raw transport error enters presentation. */ }
  }, [dispatch]);

  const onQuery = useCallback((operationId: string) => {
    const link = linkRef.current;
    if (!link || link.phase === 'briefing' || link.socket.readyState !== 1
      || !stateRef.current.operations.some(item => item.operationId === operationId)) {
      throw new Error('source_trial_query_unavailable');
    }
    link.socket.send(JSON.stringify({ protocol: SOURCE_COMMAND_PROTOCOL, command: 'query', operation_id: operationId }));
  }, []);

  const onSubmit = useCallback((action: SourcePlayerAction) => {
    const link = linkRef.current;
    const retained = stateRef.current.operations.find(item => item.operationId === action.operation_id);
    if (!link || link.phase === 'briefing' || link.socket.readyState !== 1 || stateRef.current.problem
      || stateRef.current.currentOperationId !== action.operation_id || !retained
      || retained.playerInput !== action.player_input || retained.lastEvent !== null || attempted.current.has(action.operation_id)) {
      throw new Error('source_trial_submission_unavailable');
    }
    attempted.current.add(action.operation_id);
    try {
      link.socket.send(JSON.stringify({ protocol: SOURCE_COMMAND_PROTOCOL, command: 'submit',
        operation_id: action.operation_id, player_input: action.player_input }));
    } catch {
      dispatch({ type: 'delivery_uncertain', operationId: action.operation_id });
      throw new Error('source_trial_submission_unavailable');
    }
  }, [dispatch]);

  const connect = useCallback(() => {
    if (!mounted.current || linkRef.current) return;
    let socket: SourceSocket;
    try {
      if (endpoint !== initialEndpoint.current) throw new Error();
      socket = createSocket(validateSourceTrialEndpoint(endpoint));
    } catch {
      setConnectionFailed(true);
      return;
    }
    const link: Link = { socket, generation: ++generation.current, phase: 'briefing' };
    linkRef.current = link;
    setConnection('connecting');
    setConnectionFailed(false);
    const current = () => mounted.current && linkRef.current === link && generation.current === link.generation;
    const invalid = () => {
      dispatch({ type: 'protocol_error' });
      // Browsers permit application close codes 3000..4999, not server code1008.
      retire(link, true, 4001);
    };
    socket.onopen = () => { /* Wait for the new connection's briefing before enabling input. */ };
    socket.onmessage = message => {
      if (!current()) return;
      if (typeof message.data !== 'string' || new TextEncoder().encode(message.data).length > 16384) { invalid(); return; }
      let raw: unknown;
      try { raw = JSON.parse(message.data); } catch { invalid(); return; }
      const event = decodeSourcePublicEvent(raw);
      if (!event || event.protocol !== SOURCE_PUBLIC_PROTOCOL) { invalid(); return; }
      if (link.phase === 'briefing') {
        if (event.event !== 'briefing') { invalid(); return; }
        const previous = stateRef.current.briefing;
        dispatch({ type: 'present_briefing', event });
        if (previous !== null && previous !== event.text) { retire(link, true, 4001); return; }
        link.phase = 'initial';
        setConnection('connected');
        const pending = stateRef.current.operations.find(item => item.operationId === stateRef.current.currentOperationId);
        if (pending && !isSourceTerminal(pending)) {
          try { onQuery(pending.operationId); } catch { dispatch({ type: 'query_failed' }); }
        }
        return;
      }
      if (event.event === 'briefing') { invalid(); return; }
      const initial = link.phase === 'initial';
      link.phase = 'stream';
      if (initial && event.event === 'narrative_complete') {
        dispatch({ type: 'present_latest', event });
      } else {
        if (!stateRef.current.operations.some(item => item.operationId === event.operation_id)) { invalid(); return; }
        dispatch({ type: 'receive', operationId: event.operation_id, event });
      }
      if (stateRef.current.problem) { retire(link, true, 4001); return; }
      // Presentation only, after validation and reducer admission. An unavailable
      // ignored for a terminal record is not a new admission failure. Duplicated
      // query/replay frames notify at most once per retained identity.
      const applied = stateRef.current.operations.find(item => item.operationId === event.operation_id);
      if (event.event === 'unavailable' && applied?.uncertain && !isSourceTerminal(applied)
        && !reportedUnavailable.current.has(event.operation_id)) {
        reportedUnavailable.current.add(event.operation_id);
        try { onUnavailable?.(event.operation_id); } catch { /* A view callback cannot invalidate a valid frame. */ }
      }
    };
    socket.onerror = () => { if (current()) retire(link, true); };
    socket.onclose = message => { if (current()) retire(link, message.code !== 1000); };
  }, [createSocket, dispatch, endpoint, onQuery, onUnavailable, retire]);

  const disconnect = useCallback(() => {
    if (linkRef.current) retire(linkRef.current);
  }, [retire]);

  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
      if (linkRef.current) retire(linkRef.current);
    };
  }, [retire]);

  return { state, dispatch, connected: connection === 'connected', connecting: connection === 'connecting',
    connectionFailed, connect, disconnect, onSubmit, onQuery };
}
