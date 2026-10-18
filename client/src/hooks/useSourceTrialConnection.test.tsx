import { act, cleanup, renderHook } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { readFileSync } from 'node:fs';
import { URL as NodeURL } from 'node:url';
import {
  SOURCE_COMMAND_PROTOCOL,
  sourceTrialEndpointFromPageUrl,
  useSourceTrialConnection,
  validateSourceTrialEndpoint,
} from './useSourceTrialConnection';
import type { SourceSocketFactory } from './useSourceTrialConnection';
import { SOURCE_PUBLIC_PROTOCOL as protocol } from '../sourceNarrativeProtocol';

const endpoint = 'ws://127.0.0.1:8766/ws/source-local/source-fixture.00000000-0000-4000-8000-000000000001';
const briefing = { protocol, event: 'briefing', origin: 'authored_trial_setup', text: 'Galeria. Mara está presente. Objetivo: conhecer o lugar.' };
const complete = { protocol, event: 'narrative_complete', operation_id: 'first',
  n: 'Mara aponta o índice na parede. A passagem continua aberta e a luz recai sobre a mesa.',
  q: 'O que você faz agora?' };
const action = { operation_id: 'first', player_input: 'Aguardo.' };

class FakeSocket implements ReturnType<SourceSocketFactory> {
  readyState: WebSocket['readyState'] = 0;
  onopen: WebSocket['onopen'] = null;
  onmessage: WebSocket['onmessage'] = null;
  onclose: WebSocket['onclose'] = null;
  onerror: WebSocket['onerror'] = null;
  sent: string[] = [];
  closes: number[] = [];
  throwOnSend = false;
  sendCalls = 0;
  send(data: Parameters<WebSocket['send']>[0]) {
    if (typeof data !== 'string') throw new Error('expected text command');
    this.sendCalls += 1;
    if (this.throwOnSend) throw new Error('PRIVATE socket details');
    this.sent.push(data);
  }
  close(code = 1000) { this.closes.push(code); this.readyState = 3; }
  open() {
    this.readyState = 1;
    this.onopen?.call(this as unknown as WebSocket, new Event('open'));
  }
  message(data: unknown) {
    this.onmessage?.call(this as unknown as WebSocket,
      new MessageEvent('message', { data: typeof data === 'string' ? data : JSON.stringify(data) }));
  }
  closed(code = 1006) {
    this.readyState = 3;
    this.onclose?.call(this as unknown as WebSocket, new CloseEvent('close', { code }));
  }
  error() { this.onerror?.call(this as unknown as WebSocket, new Event('error')); }
  commands() { return this.sent.map(value => JSON.parse(value)); }
}

function setup() {
  const sockets: FakeSocket[] = [];
  const factory = vi.fn(() => {
    const socket = new FakeSocket(); sockets.push(socket); return socket;
  });
  const hook = renderHook(() => useSourceTrialConnection(endpoint, factory));
  const connect = () => {
    act(() => hook.result.current.connect());
    const socket = sockets[sockets.length - 1];
    act(() => socket.open());
    return socket;
  };
  const ready = () => { const socket = connect(); act(() => socket.message(briefing)); return socket; };
  const submit = (value = action) => act(() => {
    hook.result.current.dispatch({ type: 'submitted', action: value });
    hook.result.current.onSubmit(value);
  });
  return { ...hook, sockets, factory, connect, ready, submit };
}

afterEach(() => { cleanup(); vi.restoreAllMocks(); });

describe('isolated loopback fixture configuration', () => {
  it('builds one encoded WS endpoint from exactly two launcher parameters', () => {
    expect(sourceTrialEndpointFromPageUrl('http://127.0.0.1:5178/source-trial.html?backendPort=8766&session='
      + encodeURIComponent(endpoint.split('/').pop()!))).toBe(endpoint);
    expect(sourceTrialEndpointFromPageUrl('http://127.0.0.1:5178/source-trial.html?session='
      + encodeURIComponent('🦇'.repeat(240)) + '&backendPort=8766')).toContain(encodeURIComponent('🦇'.repeat(240)));
  });
  it.each([
    'http://localhost:5178/source-trial.html?backendPort=8766&session=s',
    'http://127.1:5178/source-trial.html?backendPort=8766&session=s',
    'http://127.0.0.1.evil:5178/source-trial.html?backendPort=8766&session=s',
    'http://user:pass@127.0.0.1:5178/source-trial.html?backendPort=8766&session=s',
    'https://127.0.0.1:5178/source-trial.html?backendPort=8766&session=s',
    'http://127.0.0.1:5178/source-trial.html?backendPort=8766&session=s#extra',
    'http://127.0.0.1:5178/source-trial.html?backendPort=8766&session=s&session=t',
    'http://127.0.0.1:5178/source-trial.html?backendPort=8766&backendPort=9&session=s',
    'http://127.0.0.1:5178/source-trial.html?backendPort=8766&session=s&target=real',
    'http://127.0.0.1:5178/source-trial.html?backendPort=8766',
    'http://127.0.0.1:5178/source-trial.html?backendPort=0&session=s',
    'http://127.0.0.1:5178/source-trial.html?backendPort=65536&session=s',
    'http://127.0.0.1:5178/source-trial.html?backendPort=08766&session=s',
    'http://127.0.0.1:5178/source-trial.html?backendPort=8766&session=%20s',
    'http://127.0.0.1:5178/source-trial.html?backendPort=8766&session=..',
    'http://127.0.0.1:5178/source-trial.html?backendPort=8766&session=' + 'a'.repeat(241),
  ])('rejects ambiguous or nonlocal page URL %#', url => {
    expect(() => sourceTrialEndpointFromPageUrl(url)).toThrow('source_trial_configuration_invalid');
  });
  it.each(['\u001c','\u0085','\u2007','\u3000'])('rejects Python whitespace at either session boundary %#', boundary => {
    for (const session of [boundary + 's', 's' + boundary]) {
      expect(() => sourceTrialEndpointFromPageUrl('http://127.0.0.1:5178/source-trial.html?backendPort=8766&session='
        + encodeURIComponent(session))).toThrow('source_trial_configuration_invalid');
    }
  });
  it.each([
    endpoint.replace('127.0.0.1', 'localhost'), endpoint.replace('ws:', 'wss:'),
    endpoint.replace('127.0.0.1', '127.1'), endpoint + '?key=PRIVATE',
    endpoint + '#tail', endpoint.replace('127.0.0.1', 'user@127.0.0.1'),
    'ws://127.0.0.1:8766/ws/source-local/..', 'ws://127.0.0.1:8766/ws/session/s',
  ])('rejects noncanonical endpoint %#', url => expect(() => validateSourceTrialEndpoint(url)).toThrow());
});

describe('B socket controller', () => {
  it('mounts inert and waits for briefing after explicit connect/open', () => {
    const trial = setup();
    expect(trial.factory).not.toHaveBeenCalled();
    const socket = trial.connect();
    expect(trial.result.current.connecting).toBe(true);
    expect(trial.result.current.connected).toBe(false);
    expect(socket.sent).toEqual([]);
    act(() => socket.message(briefing));
    expect(trial.result.current.connected).toBe(true);
    expect(socket.sent).toEqual([]);
    expect(trial.result.current.state.briefing).toBe(briefing.text);
  });

  it('synchronously registers the literal action before send, exactly once per identity', () => {
    const trial = setup(), socket = trial.ready();
    const value = { operation_id: 'emoji', player_input: '🦇'.repeat(500) };
    trial.submit(value);
    expect(trial.result.current.state.currentOperationId).toBe('emoji');
    expect(trial.result.current.state.draft).toBe(value.player_input);
    expect(socket.commands()).toEqual([{ protocol: SOURCE_COMMAND_PROTOCOL, command: 'submit', ...value }]);
    expect(() => trial.result.current.onSubmit(value)).toThrow('source_trial_submission_unavailable');
    expect(socket.sendCalls).toBe(1);
  });

  it('never sends a request that was not retained or whose text changed', () => {
    const trial = setup(), socket = trial.ready();
    expect(() => trial.result.current.onSubmit(action)).toThrow();
    act(() => trial.result.current.dispatch({ type: 'submitted', action }));
    expect(() => trial.result.current.onSubmit({ ...action, player_input: 'Outro texto.' })).toThrow();
    expect(socket.sent).toEqual([]);
    expect(() => trial.result.current.onQuery('unknown')).toThrow();
  });

  it('marks attempted before an ambiguous send error and never retries it', () => {
    const trial = setup(), socket = trial.ready();
    act(() => trial.result.current.dispatch({ type: 'submitted', action }));
    socket.throwOnSend = true;
    act(() => { expect(() => trial.result.current.onSubmit(action)).toThrow('source_trial_submission_unavailable'); });
    socket.throwOnSend = false;
    expect(() => trial.result.current.onSubmit(action)).toThrow();
    expect(socket.sendCalls).toBe(1);
    expect(trial.result.current.state.operations[0].uncertain).toBe(true);
    expect(trial.result.current.state.draft).toBe(action.player_input);
  });

  it('reconnects only by gesture and queries a retained pending action once after briefing', () => {
    const trial = setup(), first = trial.ready();
    trial.submit();
    const staleMessage = first.onmessage!;
    act(() => first.closed());
    expect(trial.factory).toHaveBeenCalledTimes(1);
    expect(trial.result.current.state.operations[0].uncertain).toBe(true);
    const second = trial.connect();
    expect(second.sent).toEqual([]);
    act(() => second.message(briefing));
    expect(second.commands()).toEqual([{ protocol: SOURCE_COMMAND_PROTOCOL, command: 'query', operation_id: 'first' }]);
    act(() => staleMessage.call(first as unknown as WebSocket, new MessageEvent('message', { data: JSON.stringify(complete) })));
    expect(trial.result.current.state.operations[0].lastEvent).toBeNull();
    act(() => second.message({ protocol, event: 'preparation', status: 'ready', operation_id: 'first' }));
    act(() => second.message(complete));
    expect(trial.result.current.state.operations[0].lastEvent).toEqual(complete);
    expect(first.commands().filter(item => item.command === 'submit')).toHaveLength(1);
    expect(second.commands().some(item => item.command === 'submit')).toBe(false);
  });

  it('queries after an ambiguous send and reconnect without any submission replay', () => {
    const trial = setup(), first = trial.ready();
    act(() => trial.result.current.dispatch({ type: 'submitted', action }));
    first.throwOnSend = true;
    act(() => { expect(() => trial.result.current.onSubmit(action)).toThrow(); });
    act(() => first.closed());
    const next = trial.ready();
    expect(first.sendCalls).toBe(1);
    expect(next.commands()).toEqual([{ protocol: SOURCE_COMMAND_PROTOCOL, command: 'query', operation_id: 'first' }]);
    expect(trial.result.current.state.draft).toBe(action.player_input);
    expect(trial.result.current.state.currentOperationId).toBe('first');
    expect(() => trial.result.current.onSubmit(action)).toThrow();
    expect(next.sendCalls).toBe(1);
  });

  it('closes the latest window when preparation is the first operation frame', () => {
    const trial = setup(), socket = trial.ready();
    trial.submit();
    act(() => socket.message({ protocol, event: 'preparation', status: 'pending', operation_id: 'first' }));
    act(() => socket.message({ ...complete, operation_id: 'unknown' }));
    expect(trial.result.current.state.problem).toBe('invalid_event');
    expect(trial.result.current.state.operations).toHaveLength(1);
    expect(trial.result.current.state.operations[0].lastEvent?.event).toBe('preparation');
    expect(socket.closes).toEqual([4001]);
  });

  it('retains current input while initial latest and query result belong to different operations', () => {
    const trial = setup(), first = trial.ready();
    trial.submit(); act(() => first.closed());
    const next = trial.ready();
    act(() => next.message({ ...complete, operation_id: 'older' }));
    expect(trial.result.current.state.currentOperationId).toBe('first');
    expect(trial.result.current.state.draft).toBe(action.player_input);
    act(() => next.message({ protocol, event: 'unavailable', operation_id: 'first', phase: 'preparation', code: 'unavailable' }));
    expect(trial.result.current.state.operations[0].uncertain).toBe(true);
    expect(trial.result.current.state.operations[1].playerInput).toBeNull();
    expect(next.commands()).toEqual([{ protocol: SOURCE_COMMAND_PROTOCOL, command: 'query', operation_id: 'first' }]);
  });

  it('records failed reconnect query without retrying or losing the pending action', () => {
    const trial = setup(), first = trial.ready();
    trial.submit(); act(() => first.closed());
    const next = trial.connect(); next.throwOnSend = true;
    act(() => next.message(briefing));
    expect(next.sendCalls).toBe(1);
    expect(trial.result.current.state.queryFailed).toBe(true);
    expect(trial.result.current.state.draft).toBe(action.player_input);
    next.throwOnSend = false;
    act(() => next.message({ protocol, event: 'preparation', status: 'pending', operation_id: 'first' }));
    expect(trial.result.current.state.queryFailed).toBe(false);
    expect(next.sendCalls).toBe(1);
  });

  it('refuses a changed briefing and preserves the previous session presentation', () => {
    const trial = setup(), first = trial.ready();
    act(() => first.message(complete)); act(() => first.closed());
    const next = trial.connect();
    act(() => next.message({ ...briefing, text: 'Outro lugar, configuração diferente.' }));
    expect(trial.result.current.state.problem).toBe('conflicting_event');
    expect(trial.result.current.state.briefing).toBe(briefing.text);
    expect(trial.result.current.state.operations[0].lastEvent).toEqual(complete);
    expect(next.closes).toEqual([4001]);
    expect(next.sent).toEqual([]);
  });

  it('does not query a terminal current action on a later connection', () => {
    const trial = setup(), first = trial.ready();
    trial.submit(); act(() => first.message(complete)); act(() => first.closed());
    const next = trial.ready();
    expect(next.sent).toEqual([]);
    act(() => next.message(complete));
    expect(trial.result.current.state.operations).toHaveLength(1);
  });

  it('accepts one initial latest without inventing input, then requires known IDs', () => {
    const trial = setup(), socket = trial.ready();
    act(() => socket.message(complete));
    expect(trial.result.current.state.operations[0].playerInput).toBeNull();
    act(() => socket.message({ ...complete, operation_id: 'other' }));
    expect(trial.result.current.state.problem).toBe('invalid_event');
    expect(trial.result.current.state.operations).toHaveLength(1);
    expect(socket.closes).toEqual([4001]);
  });

  it.each(['before_briefing', 'repeated_briefing', 'binary', 'json', 'extra', 'too_large'])('closes invalid frame order/shape: %s', kind => {
    const trial = setup(), socket = trial.connect();
    if (kind !== 'before_briefing') act(() => socket.message(briefing));
    act(() => {
      if (kind === 'before_briefing') socket.message(complete);
      else if (kind === 'repeated_briefing') socket.message(briefing);
      else if (kind === 'binary') socket.onmessage?.call(socket as unknown as WebSocket, new MessageEvent('message', { data: new ArrayBuffer(1) }));
      else if (kind === 'json') socket.message('{broken');
      else if (kind === 'extra') socket.message({ ...complete, can_retry: true });
      else socket.message('x'.repeat(16385));
    });
    expect(trial.result.current.state.problem).toBe('invalid_event');
    expect(trial.result.current.state.operations).toEqual([]);
    expect(socket.sent).toEqual([]);
    expect(socket.closes).toEqual([4001]);
  });

  it('explicit queries carry no player input and confirmed text survives query/transport failure', () => {
    const trial = setup(), socket = trial.ready();
    act(() => socket.message(complete));
    act(() => trial.result.current.onQuery('first'));
    expect(socket.commands()).toEqual([{ protocol: SOURCE_COMMAND_PROTOCOL, command: 'query', operation_id: 'first' }]);
    act(() => socket.error());
    expect(trial.result.current.connected).toBe(false);
    expect(trial.result.current.state.operations[0].lastEvent).toEqual(complete);
  });

  it('allows another identity only after terminal/new-action gesture', () => {
    const trial = setup(), socket = trial.ready();
    trial.submit(); act(() => socket.message(complete));
    act(() => trial.result.current.dispatch({ type: 'new_action' }));
    trial.submit({ operation_id: 'second', player_input: 'Aguardo.' });
    expect(socket.commands().map(item => item.operation_id)).toEqual(['first', 'second']);
    expect(trial.result.current.state.operations[0].lastEvent).toEqual(complete);
  });

  it('detaches and closes on unmount without a replacement socket', () => {
    const trial = setup(), socket = trial.ready();
    trial.unmount();
    expect(socket.closes).toEqual([1000]);
    expect(socket.onmessage).toBeNull();
    expect(trial.factory).toHaveBeenCalledTimes(1);
  });

  it('refuses endpoint changes without moving the retained session to another target', () => {
    const factory = vi.fn(() => new FakeSocket());
    const hook = renderHook(({ url }) => useSourceTrialConnection(url, factory), { initialProps: { url: endpoint } });
    hook.rerender({ url: endpoint.replace(':8766/', ':8767/') });
    act(() => hook.result.current.connect());
    expect(factory).not.toHaveBeenCalled();
    expect(hook.result.current.connectionFailed).toBe(true);
  });
});

it('keeps technical entry, no-env Vite config and default application separate', () => {
  const main = readFileSync(new NodeURL('../sourceTrialMain.tsx', import.meta.url), 'utf8');
  const html = readFileSync(new NodeURL('../../source-trial.html', import.meta.url), 'utf8');
  const config = readFileSync(new NodeURL('../../vite.source-trial.config.ts', import.meta.url), 'utf8');
  const defaultMain = readFileSync(new NodeURL('../main.tsx', import.meta.url), 'utf8');
  expect(main).toContain('Prévia técnica local com respostas fixas');
  expect(main).not.toMatch(/from ['"].*App|import\.meta\.env|localStorage|sessionStorage/);
  expect(html).toContain('/src/sourceTrialMain.tsx');
  expect(html).toContain('.source-trial-preview .game-shell { height: 100%; }');
  expect(config).toContain('envDir: false');
  expect(config).toContain("host: '127.0.0.1'");
  expect(config).toContain('strictPort: true');
  expect(config).not.toMatch(/proxy\s*:|vite\.config/);
  expect(defaultMain).not.toContain('sourceTrialMain');
});
