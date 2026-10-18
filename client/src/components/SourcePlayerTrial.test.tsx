import { act, cleanup, fireEvent, render, renderHook, screen, within } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { readFileSync } from 'node:fs';
import { URL as NodeURL } from 'node:url';
import { SourcePlayerTrial } from './SourcePlayerTrial';
import { sourcePlayerTrialEndpointFromPageUrl, sourceTrialEndpointFromPageUrl, useSourceTrialConnection } from '../hooks/useSourceTrialConnection';
import type { SourceSocketFactory } from '../hooks/useSourceTrialConnection';
import { SOURCE_PUBLIC_PROTOCOL as protocol } from '../sourceNarrativeProtocol';

const session = 'source-groq-trial.00000000-0000-4000-8000-000000000001';
const endpoint = 'ws://127.0.0.1:8018/ws/source-local/' + session;
const page = 'http://127.0.0.1:5178/source-player-trial.html?backendPort=8018&session=' + session;
const briefing = { protocol, event: 'briefing', origin: 'authored_trial_setup', text: 'Local: Galeria. Elenco presente: Mara. Objetivo: conhecer o lugar.' };
const complete = (id = 'op-1') => ({ protocol, event: 'narrative_complete', operation_id: id,
  n: 'Mara aponta o índice na parede. A passagem continua aberta e a luz recai sobre a mesa.', q: 'O que você faz agora?' });
const unavailable = (id = 'op-1') => ({ protocol, event: 'unavailable', operation_id: id, phase: 'preparation', code: 'unavailable' });

class FakeSocket implements ReturnType<SourceSocketFactory> {
  readyState: WebSocket['readyState'] = 0;
  onopen: WebSocket['onopen'] = null;
  onmessage: WebSocket['onmessage'] = null;
  onclose: WebSocket['onclose'] = null;
  onerror: WebSocket['onerror'] = null;
  sent: string[] = [];
  closes: number[] = [];
  send(data: Parameters<WebSocket['send']>[0]) {
    if (typeof data !== 'string') throw new Error('Expected text command');
    this.sent.push(data);
  }
  close(code = 1000) { this.closes.push(code); this.readyState = 3; }
  open() { this.readyState = 1; this.onopen?.call(this as unknown as WebSocket, new Event('open')); }
  message(data: unknown) {
    this.onmessage?.call(this as unknown as WebSocket, new MessageEvent('message', { data: JSON.stringify(data) }));
  }
  closed(code = 1006) { this.readyState = 3; this.onclose?.call(this as unknown as WebSocket, new CloseEvent('close', { code })); }
  commands() { return this.sent.map(item => JSON.parse(item)); }
}

beforeEach(() => {
  vi.useFakeTimers();
  vi.stubGlobal('fetch', vi.fn(() => { throw new Error('Unexpected network'); }));
  vi.stubGlobal('WebSocket', vi.fn(() => { throw new Error('Unexpected native socket'); }));
});
afterEach(() => { cleanup(); vi.useRealTimers(); vi.restoreAllMocks(); vi.unstubAllGlobals(); });

function sockets() {
  const created: FakeSocket[] = [];
  const factory = vi.fn(() => { const socket = new FakeSocket(); created.push(socket); return socket; });
  return { created, factory };
}
function setup(provider: 'groq' | 'luna' = 'groq') {
  const transport = sockets();
  let nextId = 0;
  const createId = vi.fn(() => 'op-' + ++nextId);
  const result = render(<SourcePlayerTrial endpoint={endpoint} createSocket={transport.factory} createOperationId={createId} provider={provider} />);
  const connect = () => {
    fireEvent.click(screen.getByRole('button', { name: 'Conectar ao ensaio' }));
    const socket = transport.created[transport.created.length - 1];
    act(() => socket.open());
    return socket;
  };
  const ready = () => { const socket = connect(); act(() => socket.message(briefing)); return socket; };
  return { ...transport, ...result, createId, connect, ready };
}
function wait(ms = 60_000) { act(() => vi.advanceTimersByTime(ms)); }
function submit(text?: string) {
  if (text === undefined) {
    fireEvent.click(screen.getByRole('radio', { name: 'Aguardar' }));
    fireEvent.click(screen.getByRole('button', { name: 'Confirmar espera' }));
  } else {
    fireEvent.click(screen.getByRole('radio', { name: 'Conversar com Mara' }));
    fireEvent.change(input(), { target: { value: text } });
    fireEvent.click(screen.getByRole('button', { name: 'Enviar fala' }));
  }
}
function input() { return screen.getByRole('textbox', { name: 'Sua fala para Mara' }); }
function newAction() { return screen.getByRole('button', { name: 'Escrever uma nova ação' }); }

describe('interactive presentation gate', () => {
  it('Luna is ready without a timer but blocks double submit until completion', () => {
    const trial = setup('luna'), socket = trial.ready();
    expect(input()).toBeEnabled();
    submit();
    submit();
    expect(socket.commands()).toHaveLength(1);
    expect(input()).toBeDisabled();
    act(() => socket.message(complete()));
    expect(newAction()).toBeEnabled();
    fireEvent.click(newAction());
    submit('Como posso ajudar?');
    expect(socket.commands().map(item => item.operation_id)).toEqual(['op-1', 'op-2']);
  });

  it('Luna reconnect queries pending action without a new submission or cooldown', () => {
    const trial = setup('luna'), first = trial.ready();
    submit();
    act(() => first.closed());
    const second = trial.ready();
    expect(second.commands().map(item => item.command)).toEqual(['query']);
    expect(input()).toBeDisabled();
    act(() => second.message(complete()));
    expect(newAction()).toBeEnabled();
    expect(trial.createId).toHaveBeenCalledTimes(1);
  });

  it('Luna remains closed after unavailable even without a cooldown', () => {
    const trial = setup('luna'), socket = trial.ready();
    submit();
    act(() => socket.message(unavailable()));
    expect(input()).toBeDisabled();
    wait(120_000);
    expect(input()).toBeDisabled();
    expect(socket.commands()).toHaveLength(1);
  });
  it('mounts inert and exposes the real source and only declared-action guidance', () => {
    const trial = setup();
    expect(trial.factory).not.toHaveBeenCalled();
    expect(trial.createId).not.toHaveBeenCalled();
    expect(screen.getByText('Ensaio experimental · Qwen via Groq')).toBeInTheDocument();
    const intro = screen.getByRole('region', { name: 'Introdução da cena' });
    expect(intro).toHaveTextContent('A introdução é autorada');
    expect(intro).toHaveTextContent('até quatro chamadas');
    expect(within(intro).queryByText('Investigo o ambiente.')).not.toBeInTheDocument();
    expect(intro).toHaveTextContent('Investigação está fora deste recorte');
    expect(input()).toHaveAccessibleDescription(/Intervalo|Desconectado/);
    expect(fetch).not.toHaveBeenCalled();
    expect(WebSocket).not.toHaveBeenCalled();
  });

  it('waits sixty seconds after validated briefing, not open or submit, while reporting connected truthfully', () => {
    const trial = setup(), socket = trial.connect();
    wait();
    expect(input()).toBeDisabled();
    act(() => socket.message(briefing));
    expect(screen.getByRole('status', { name: 'Conexão' })).toHaveTextContent('Conectado');
    wait(59_999);
    expect(input()).toBeDisabled();
    expect(trial.createId).not.toHaveBeenCalled();
    wait(1);
    expect(input()).toBeEnabled();
    expect(socket.sent).toEqual([]);
    submit();
    expect(trial.createId).toHaveBeenCalledTimes(1);
    expect(socket.commands()).toEqual([{ protocol: 'narrative-source-command-v1', command: 'submit', operation_id: 'op-1', player_input: 'Aguardo.' }]);
    wait(120_000);
    expect(input()).toBeDisabled();
    expect(socket.commands()).toHaveLength(1);
  });

  it('starts a new interval only on a new terminal and does not reset it for a query duplicate', () => {
    const trial = setup(), socket = trial.ready(); wait(); submit();
    act(() => socket.message(complete()));
    expect(newAction()).toBeDisabled();
    wait(30_000);
    fireEvent.click(screen.getByRole('button', { name: 'Consultar estado da ação' }));
    act(() => socket.message(complete()));
    wait(29_999); expect(newAction()).toBeDisabled();
    wait(1); expect(newAction()).toBeEnabled();
    expect(trial.createId).toHaveBeenCalledTimes(1);
    fireEvent.click(newAction()); submit('O que há aqui?');
    expect(socket.commands().map(item => [item.command, item.operation_id])).toEqual([
      ['submit', 'op-1'], ['query', 'op-1'], ['submit', 'op-2'],
    ]);
  });

  it('recovers an uncertain transport via a query without closing admission or replaying a submit', () => {
    const trial = setup(), first = trial.ready(); wait(); submit();
    act(() => first.closed());
    expect(screen.queryByText(/Novos envios foram encerrados/)).not.toBeInTheDocument();
    const second = trial.ready();
    expect(second.commands().map(item => item.command)).toEqual(['query']);
    wait(10_000);
    act(() => second.message(complete()));
    wait(59_999); expect(newAction()).toBeDisabled();
    wait(1); expect(newAction()).toBeEnabled();
    expect(first.commands()).toHaveLength(1);
    expect(second.commands()).toHaveLength(1);
    expect(trial.createId).toHaveBeenCalledTimes(1);
  });

  it('resets local readiness on an explicit reconnection even when no terminal changed', () => {
    const trial = setup(); trial.ready(); wait(); expect(input()).toBeEnabled();
    fireEvent.click(screen.getByRole('button', { name: 'Desconectar' }));
    trial.ready(); expect(input()).toBeDisabled();
    wait(59_999); expect(input()).toBeDisabled(); wait(1); expect(input()).toBeEnabled();
    expect(trial.createId).not.toHaveBeenCalled();
  });

  it('keeps unavailable uncertain and closes admission across timers, query duplicates and reconnect', () => {
    const trial = setup(), first = trial.ready(); wait(); submit();
    act(() => first.message(unavailable()));
    expect(screen.getByRole('status', { name: 'Estado da ação' })).toHaveTextContent('Não foi possível confirmar');
    expect(screen.getByRole('status', { name: 'Disponibilidade de envio' })).toHaveTextContent('Novos envios foram encerrados');
    wait(180_000);
    expect(input()).toBeDisabled();
    expect(screen.queryByRole('button', { name: 'Escrever uma nova ação' })).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Consultar estado da ação' }));
    act(() => first.message(unavailable()));
    act(() => first.closed(1000));
    const second = trial.ready();
    act(() => second.message(complete()));
    wait(120_000);
    expect(newAction()).toBeDisabled();
    expect(input()).toHaveValue('');
    expect(second.commands().map(item => item.command)).toEqual(['query']);
    expect(trial.createId).toHaveBeenCalledTimes(1);
  });

  it.each([1000, 1012])('retains four terminal results before server close %s without claiming four approved responses', closeCode => {
    const trial = setup(), socket = trial.ready();
    for (let i = 1; i <= 4; i += 1) {
      wait();
      if (i > 1) fireEvent.click(newAction());
      submit();
      act(() => socket.message(i === 2
        ? { protocol, event: 'narrative_rejected', operation_id: 'op-2', status: 'failed', code: 'narrative_rejected' }
        : complete('op-' + i)));
    }
    act(() => socket.closed(closeCode)); wait(120_000);
    expect(screen.getAllByLabelText('Pergunta do narrador')).toHaveLength(3);
    expect(newAction()).toBeDisabled();
    expect(input()).toBeDisabled();
    expect(socket.commands()).toHaveLength(4);
    expect(trial.createId).toHaveBeenCalledTimes(4);
    if (closeCode === 1000) expect(screen.queryByRole('alert')).not.toBeInTheDocument();
    else expect(screen.getByRole('alert')).toHaveTextContent('Se a sessão ainda estiver ativa');
  });

  it('does not reconnect or allocate identity when its interval timer expires after unmount', () => {
    const trial = setup(), socket = trial.ready(); trial.unmount(); wait(120_000);
    expect(socket.closes).toEqual([1000]);
    expect(trial.factory).toHaveBeenCalledTimes(1);
    expect(trial.createId).not.toHaveBeenCalled();
    expect(socket.sent).toEqual([]);
  });
});

function callbackTrial(callback?: (id: string) => void) {
  const transport = sockets();
  const hook = renderHook(() => useSourceTrialConnection(endpoint, transport.factory, callback));
  act(() => hook.result.current.connect());
  const socket = transport.created[0];
  act(() => { socket.open(); socket.message(briefing); });
  const submit = () => act(() => {
    const action = { operation_id: 'op-1', player_input: 'Aguardo.' };
    hook.result.current.dispatch({ type: 'submitted', action }); hook.result.current.onSubmit(action);
  });
  return { ...hook, socket, submit };
}

describe('optional unavailable presentation callback', () => {
  it('notifies after application once for a known operation, including its explicit query response', () => {
    const callback = vi.fn();
    const trial = callbackTrial(callback); trial.submit();
    act(() => trial.result.current.onQuery('op-1'));
    act(() => trial.socket.message(unavailable()));
    expect(trial.result.current.state.operations[0].uncertain).toBe(true);
    expect(callback).toHaveBeenCalledWith('op-1');
    act(() => trial.socket.message(unavailable()));
    expect(callback).toHaveBeenCalledTimes(1);
  });

  it('does not signal a terminal record ignored by the reducer', () => {
    const callback = vi.fn(), trial = callbackTrial(callback); trial.submit();
    act(() => trial.socket.message(complete()));
    act(() => trial.socket.message(unavailable()));
    expect(callback).not.toHaveBeenCalled();
    expect(trial.result.current.state.operations[0].lastEvent).toEqual(complete());
    expect(trial.result.current.connected).toBe(true);
  });

  it.each(['unknown', 'invalid', 'stale'])('does not notify for %s unavailable frames', kind => {
    const callback = vi.fn(), trial = callbackTrial(callback); trial.submit();
    if (kind === 'stale') {
      const handler = trial.socket.onmessage!;
      act(() => trial.result.current.disconnect());
      act(() => handler.call(trial.socket as unknown as WebSocket, new MessageEvent('message', { data: JSON.stringify(unavailable()) })));
    } else act(() => trial.socket.message(kind === 'unknown' ? unavailable('unknown') : { ...unavailable(), retry: true }));
    expect(callback).not.toHaveBeenCalled();
    expect(trial.result.current.state.operations).toHaveLength(1);
  });

  it('contains callback exceptions without corrupting retained state or a valid connection', () => {
    const callback = vi.fn(() => { throw new Error('PRIVATE callback detail'); });
    const trial = callbackTrial(callback); trial.submit();
    act(() => trial.socket.message(unavailable()));
    expect(trial.result.current.state.problem).toBeNull();
    expect(trial.result.current.state.operations[0].uncertain).toBe(true);
    expect(trial.result.current.connected).toBe(true);
    expect(trial.socket.closes).toEqual([]);
  });

  it('preserves the default consumer without a callback and does not turn a socket close into unavailable', () => {
    const trial = callbackTrial(); trial.submit();
    act(() => trial.socket.message(unavailable()));
    expect(trial.result.current.connected).toBe(true);
    const callback = vi.fn(), other = callbackTrial(callback); other.submit();
    act(() => other.socket.closed());
    expect(other.result.current.state.operations[0].uncertain).toBe(true);
    expect(callback).not.toHaveBeenCalled();
  });
});

describe('isolated interactive page configuration', () => {
  it('accepts only its own canonical page with the two explicit launcher parameters', () => {
    expect(sourcePlayerTrialEndpointFromPageUrl(page)).toBe(endpoint);
    expect(sourcePlayerTrialEndpointFromPageUrl(page.replace('source-groq-trial.', 'source-luna-trial.')))
      .toBe(endpoint.replace('source-groq-trial.', 'source-luna-trial.'));
    expect(() => sourceTrialEndpointFromPageUrl(page)).toThrow('source_trial_configuration_invalid');
    expect(() => sourcePlayerTrialEndpointFromPageUrl(page.replace('source-player-trial.html', 'source-trial.html'))).toThrow();
  });
  it.each([
    page.replace('127.0.0.1', 'localhost'), page.replace('127.0.0.1', '127.1'),
    page.replace('http:', 'https:'), page.replace('127.0.0.1', 'user:PRIVATE@127.0.0.1'),
    page + '#tail', page + '&model=qwen', page + '&apiKey=PRIVATE', page + '&session=other',
    page.replace('backendPort=8018', 'backendPort=08018'), page.replace('backendPort=8018', 'backendPort=65536'),
    page.replace('source-groq-trial.', 'source-fixture.'), page.replace('source-groq-trial.', 'source-player.'),
    page.replace(session, 'source-groq-trial.not-a-uuid'),
    page.replace('session=' + session, 'session=..'), page.replace('session=' + session, 'session=%20s'),
  ])('rejects a divergent or ambiguous interactive URL %#', url => expect(() => sourcePlayerTrialEndpointFromPageUrl(url)).toThrow());
  it('keeps new and historical entries separate and disables dotenv in the new build', () => {
    const main = readFileSync(new NodeURL('../sourcePlayerTrialMain.tsx', import.meta.url), 'utf8');
    const html = readFileSync(new NodeURL('../../source-player-trial.html', import.meta.url), 'utf8');
    const config = readFileSync(new NodeURL('../../vite.source-player-trial.config.ts', import.meta.url), 'utf8');
    const fixture = readFileSync(new NodeURL('../sourceTrialMain.tsx', import.meta.url), 'utf8');
    expect(main).not.toMatch(/from ['"].*App|import\.meta\.env|localStorage|sessionStorage/);
    expect(html).toContain('/src/sourcePlayerTrialMain.tsx');
    expect(config).toContain('envDir: false');
    expect(config).toContain("new URL('./source-player-trial.html'");
    expect(config).not.toMatch(/proxy\s*:|vite\.config/);
    expect(fixture).toContain('Prévia técnica local com respostas fixas');
    expect(fixture).not.toContain('SourcePlayerTrial');
  });
});

it('labels an explicitly admitted Luna session without changing the default Groq presentation', () => {
  const transport = sockets();
  render(<SourcePlayerTrial endpoint={endpoint.replace('source-groq-trial.', 'source-luna-trial.')}
    provider="luna" createSocket={transport.factory} />);
  expect(screen.getByText('Ensaio experimental · Luna via OpenAI')).toBeInTheDocument();
  expect(screen.getByText(/as continuações usam Luna via OpenAI/)).toBeInTheDocument();
});

it('composes the observed natural speech before retaining or sending its operation', () => {
  const trial = setup(), socket = trial.ready(); wait();
  const speech = 'Mara, me fale sobre este lugar';
  fireEvent.change(screen.getByRole('textbox'), { target: { value: speech } });
  fireEvent.click(screen.getByRole('button', { name: /^Enviar/ }));
  expect(socket.commands()).toEqual([{ protocol: 'narrative-source-command-v1', command: 'submit',
    operation_id: 'op-1', player_input: 'Digo a Mara: "Mara, me fale sobre este lugar"' }]);
  expect(trial.createId).toHaveBeenCalledTimes(1);
  expect(screen.getByRole('log')).toHaveTextContent('Digo a Mara: "Mara, me fale sobre este lugar"');
});


describe('declared dialogue controls', () => {
  it.each([
    ['Ela disse "olá".', 'Digo a Mara: “Ela disse "olá".”'],
    ['Ela disse "olá" e “até breve”.', 'Digo a Mara: «Ela disse "olá" e “até breve”.»'],
    ['Ela disse “olá” e «até breve».', 'Digo a Mara: "Ela disse “olá” e «até breve»."'],
    ['Ela disse ＂olá＂.', 'Digo a Mara: “Ela disse ＂olá＂.”'],
    ['  Olá, Mara.\nVocê está bem?  '.replace('\\n', '\n'), 'Digo a Mara: "  Olá, Mara.\nVocê está bem?  "'.replace('\\n', '\n')],
    ['Aguardo.', 'Digo a Mara: "Aguardo."'],
    ['Investigo o ambiente.', 'Digo a Mara: "Investigo o ambiente."'],
  ])('preserves literal speech with compatible quotes %#', (speech, expected) => {
    const trial = setup(), socket = trial.ready(); wait(); submit(speech);
    expect(socket.commands()).toHaveLength(1);
    expect(socket.commands()[0].player_input).toBe(expected);
    expect(input()).toHaveValue(speech);
    expect(trial.createId).toHaveBeenCalledTimes(1);
  });

  it.each([
    '', '   ', '\u0085\u001c'.replace('\\u0085', '\u0085').replace('\\u001c', '\u001c'),
    '\u0301'.replace('\\u0301', '\u0301'),
    'Olá\0Mara'.replace('\\0', '\0'), '\ud800'.replace('\\ud800', '\ud800'),
    'Ela disse "a", “b” e «c».', 'Ela disse ＂a＂, “b” e «c».',
    'a'.repeat(486), '🦇'.repeat(486), 'a'.repeat(501), '🦇'.repeat(501),
  ])('rejects invalid or unrepresentable speech locally before allocating an ID %#', speech => {
    const trial = setup(), socket = trial.ready(); wait(); submit(speech);
    expect(screen.getByRole('alert')).toBeInTheDocument();
    expect(input()).toHaveValue(speech);
    expect(input()).toHaveAttribute('aria-invalid', 'true');
    expect(trial.createId).not.toHaveBeenCalled();
    expect(socket.sent).toEqual([]);
    expect(screen.getByRole('status', { name: 'Estado da ação' })).toHaveTextContent('Nenhuma ação em andamento');
    expect(screen.getByRole('log').querySelector('[data-operation-id]')).toBeNull();
  });

  it.each(['a', '🦇'])('accepts the exact 500-codepoint envelope with %s without truncation', unit => {
    const trial = setup(), socket = trial.ready(); wait();
    const speech = unit.repeat(485);
    submit(speech);
    const sent = socket.commands()[0].player_input;
    expect(Array.from(sent)).toHaveLength(500);
    expect(sent).toBe('Digo a Mara: "' + speech + '"');
    expect(trial.createId).toHaveBeenCalledTimes(1);
  });

  it('switches modes without losing the unsubmitted draft and requires an explicit wait confirmation', () => {
    const trial = setup(), socket = trial.ready(); wait();
    fireEvent.change(input(), { target: { value: 'Ainda quero perguntar sobre a galeria.' } });
    fireEvent.click(screen.getByRole('radio', { name: 'Aguardar' }));
    expect(input()).toBeDisabled();
    expect(input()).toHaveValue('Ainda quero perguntar sobre a galeria.');
    expect(socket.sent).toEqual([]);
    fireEvent.click(screen.getByRole('radio', { name: 'Conversar com Mara' }));
    expect(input()).toHaveValue('Ainda quero perguntar sobre a galeria.');
    expect(input()).toBeEnabled();
    expect(trial.createId).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole('radio', { name: 'Aguardar' }));
    fireEvent.click(screen.getByRole('button', { name: 'Confirmar espera' }));
    fireEvent.click(screen.getByRole('button', { name: 'Confirmar espera' }));
    expect(trial.createId).toHaveBeenCalledTimes(1);
    expect(socket.commands().map(item => item.player_input)).toEqual(['Aguardo.']);
  });

  it('guards both controls during cooldown and keeps a composed unavailable action unchanged on query', () => {
    const trial = setup(), socket = trial.ready();
    expect(screen.getByRole('radio', { name: 'Conversar com Mara' })).toBeDisabled();
    expect(screen.getByRole('radio', { name: 'Aguardar' })).toBeDisabled();
    fireEvent.click(screen.getByRole('radio', { name: 'Aguardar' }));
    wait();
    expect(screen.getByRole('radio', { name: 'Conversar com Mara' })).toBeChecked();
    submit('Mara, me fale sobre este lugar');
    act(() => socket.message(unavailable())); wait(120_000);
    expect(screen.getByRole('radio', { name: 'Conversar com Mara' })).toBeDisabled();
    expect(screen.getByRole('radio', { name: 'Aguardar' })).toBeDisabled();
    fireEvent.click(screen.getByRole('button', { name: 'Consultar estado da ação' }));
    expect(socket.commands().map(item => [item.command, item.operation_id])).toEqual([['submit', 'op-1'], ['query', 'op-1']]);
    expect(input()).toHaveValue('Mara, me fale sobre este lugar');
    expect(trial.createId).toHaveBeenCalledTimes(1);
    expect(screen.queryByRole('button', { name: 'Escrever uma nova ação' })).not.toBeInTheDocument();
  });
});

it('keeps an unsubmitted speech across reconnect and clears it only on explicit new action', () => {
  const trial = setup(), first = trial.ready(); wait();
  const speech = 'Mara, me fale sobre este lugar';
  fireEvent.change(input(), { target: { value: speech } });
  fireEvent.click(screen.getByRole('button', { name: 'Desconectar' }));
  const second = trial.ready();
  expect(input()).toHaveValue(speech);
  expect(input()).toBeDisabled();
  expect(first.sent).toEqual([]);
  expect(second.sent).toEqual([]);
  wait();
  fireEvent.click(screen.getByRole('button', { name: 'Enviar fala' }));
  act(() => second.message(complete()));
  fireEvent.click(screen.getByRole('button', { name: 'Consultar estado da ação' }));
  act(() => second.message(complete()));
  expect(input()).toHaveValue(speech);
  wait();
  fireEvent.click(newAction());
  expect(input()).toHaveValue('');
  expect(screen.getByRole('radio', { name: 'Conversar com Mara' })).toBeChecked();
  expect(screen.getByRole('log')).toHaveTextContent('Digo a Mara: "Mara, me fale sobre este lugar"');
  expect(second.commands().map(item => item.command)).toEqual(['submit', 'query']);
  expect(trial.createId).toHaveBeenCalledTimes(1);
});
