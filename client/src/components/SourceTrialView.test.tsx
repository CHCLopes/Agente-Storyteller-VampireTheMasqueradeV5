import { useReducer } from 'react';
import type { Dispatch } from 'react';
import { act, cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import {
  SOURCE_PUBLIC_PROTOCOL as protocol,
  createSourceNarrativeState,
  sourceNarrativeReducer,
} from '../sourceNarrativeProtocol';
import type { SourceNarrativeAction, SourceNarrativeState, SourcePlayerAction } from '../sourceNarrativeProtocol';
import { SourceTrialView } from './SourceTrialView';

const briefing = { protocol, event: 'briefing', origin: 'authored_trial_setup', text: 'Preparação autorada deste ensaio.\nLocal: Arquivo\nElenco presente: Rui\nObjetivo declarado: conhecer o arquivo.' };
const initial = () => sourceNarrativeReducer(createSourceNarrativeState(), { type: 'present_briefing', event: briefing });
const input = 'Espero a reação de Rui.';
const n = 'Rui aponta o índice na parede. O corredor permanece aberto e o relógio marca o silêncio.';
const q = 'O que você faz agora?';
const complete = { protocol, event: 'narrative_complete', operation_id: 'op-1', n, q };

function renderTrial(options: {
  connected?: boolean;
  initialState?: SourceNarrativeState;
  onSubmit?: (action: SourcePlayerAction) => void | Promise<void>;
  onQuery?: (id: string) => void | Promise<void>;
} = {}) {
  const submit = vi.fn(options.onSubmit ?? (() => undefined));
  const query = vi.fn(options.onQuery ?? (() => undefined));
  const createId = vi.fn().mockReturnValueOnce('op-1').mockReturnValueOnce('op-2');
  let observedState = options.initialState ?? initial();
  let applyAction: Dispatch<SourceNarrativeAction> = () => undefined;
  function Harness({ connected }: { connected: boolean }) {
    const [state, dispatch] = useReducer(sourceNarrativeReducer, options.initialState ?? initial());
    observedState = state;
    applyAction = dispatch;
    return <SourceTrialView state={state} dispatch={dispatch} connected={connected}
      createOperationId={createId} onSubmit={submit} onQuery={query} />;
  }
  const result = render(<Harness connected={options.connected ?? true} />);
  return {
    ...result, submit, query, createId,
    state: () => observedState,
    dispatch: (action: SourceNarrativeAction) => act(() => applyAction(action)),
    connection: (connected: boolean) => result.rerender(<Harness connected={connected} />),
  };
}

function send(text = input) {
  fireEvent.change(screen.getByRole('textbox', { name: 'Ação para esta cena' }), { target: { value: text } });
  fireEvent.click(screen.getByRole('button', { name: 'Enviar ação' }));
}

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

describe('inactive SourceTrialView', () => {
  it('mounts without socket, request, submission or fabricated character state', () => {
    const socket = vi.fn(() => { throw new Error('Unexpected socket'); });
    const fetch = vi.fn(() => { throw new Error('Unexpected fetch'); });
    vi.stubGlobal('WebSocket', socket);
    vi.stubGlobal('fetch', fetch);
    const trial = renderTrial();
    expect(socket).not.toHaveBeenCalled();
    expect(fetch).not.toHaveBeenCalled();
    expect(trial.submit).not.toHaveBeenCalled();
    expect(trial.query).not.toHaveBeenCalled();
    expect(trial.createId).not.toHaveBeenCalled();
    expect(screen.getByRole('complementary', { name: 'Cena e estado da ação' })).toHaveTextContent(briefing.text.replace(/\s+/g, ' '));
    expect(screen.queryByText(/Karl Brujah|Fome|Saúde/)).not.toBeInTheDocument();
    expect(screen.queryByRole('combobox')).not.toBeInTheDocument();
    expect(screen.getByText(/Ao recarregar esta página, a cópia local do texto da ação e sua identificação são perdidas/)).toBeInTheDocument();
  });

  it('keeps briefing focus separate from action status and the history box', () => {
    const trial = renderTrial();
    const shell = screen.getByRole('region', { name: 'Ensaio de cena B' });
    const log = screen.getByRole('log', { name: 'Histórico da cena' });
    const panel = screen.getByRole('complementary', { name: 'Cena e estado da ação' });
    const introduction = screen.getByRole('region', { name: 'Introdução da cena' });
    const actionStatus = screen.getByRole('region', { name: 'Sua ação' });
    expect(shell).toContainElement(log);
    expect(panel).toContainElement(introduction);
    expect(panel).toContainElement(actionStatus);
    expect(introduction).not.toContainElement(actionStatus);
    expect(introduction).toHaveTextContent('Este painel não apresenta uma ficha atualizada do personagem.');
    introduction.focus();
    expect(introduction).toHaveFocus();
    expect(within(actionStatus).getByRole('status', { name: 'Estado da ação' })).toHaveTextContent('Nenhuma ação em andamento.');
    expect(log).not.toContainElement(panel);
    trial.dispatch({ type: 'present_latest', event: complete });
    expect(within(log).getByText(n)).toBeInTheDocument();
    expect(panel).toHaveTextContent('Local: Arquivo');
    // Keyboard focus and DOM separation do not prove pixel clipping in a real browser.
  });

  it('describes the action input with guidance inside the independent introduction', () => {
    const trial = renderTrial();
    const introduction = screen.getByRole('region', { name: 'Introdução da cena' });
    const guidance = screen.getByRole('region', { name: 'Como escrever sua ação' });
    const inputBox = screen.getByRole('textbox', { name: 'Ação para esta cena' });
    expect(introduction).toContainElement(guidance);
    expect(guidance).not.toContainElement(screen.getByRole('status', { name: 'Estado da ação' }));
    expect(inputBox).toHaveAccessibleDescription(/Use uma ação por envio/);
    inputBox.focus();
    expect(inputBox).toHaveFocus();
    expect(trial.submit).not.toHaveBeenCalled();
    expect(trial.query).not.toHaveBeenCalled();
    expect(trial.createId).not.toHaveBeenCalled();
  });

  it('blocks submission while disconnected or before the briefing exists', () => {
    const trial = renderTrial({ connected: false });
    expect(screen.getByRole('button', { name: 'Enviar ação' })).toBeDisabled();
    trial.connection(true);
    expect(trial.submit).not.toHaveBeenCalled();
    cleanup();
    renderTrial({ initialState: createSourceNarrativeState() });
    expect(screen.getByRole('textbox')).toBeDisabled();
    expect(screen.getByText('Aguardando a introdução da cena.')).toBeInTheDocument();
  });

  it('forwards one literal frozen action and keeps the input while pending', () => {
    let frozenAction = false;
    const trial = renderTrial({ onSubmit: action => {
      frozenAction = action.operation_id === 'op-1' && Object.isFrozen(action);
    } });
    send();
    fireEvent.click(screen.getByRole('button', { name: 'Enviar ação' }));
    expect(trial.submit).toHaveBeenCalledTimes(1);
    expect(trial.submit).toHaveBeenCalledWith({ operation_id: 'op-1', player_input: input });
    expect(trial.createId).toHaveBeenCalledTimes(1);
    expect(frozenAction).toBe(true);
    expect(trial.state().operations[0]).toMatchObject({ operationId: 'op-1', playerInput: input });
    expect(screen.getByRole('textbox')).toHaveValue(input);
    expect(screen.getByRole('textbox')).toBeDisabled();
    expect(screen.queryByRole('button', { name: 'Escrever uma nova ação' })).not.toBeInTheDocument();
  });

  it('dispatches the retained action before invoking the transport callback', () => {
    const sequence: string[] = [];
    const dispatch = vi.fn(() => { sequence.push('register'); });
    const submit = vi.fn(() => { sequence.push('submit'); });
    const state = sourceNarrativeReducer(initial(), { type: 'edit_draft', text: input });
    render(<SourceTrialView state={state} dispatch={dispatch} connected createOperationId={() => 'op-1'}
      onSubmit={submit} onQuery={() => undefined} />);
    fireEvent.click(screen.getByRole('button', { name: 'Enviar ação' }));
    expect(sequence).toEqual(['register', 'submit']);
    expect(dispatch).toHaveBeenCalledWith({ type: 'submitted', action: { operation_id: 'op-1', player_input: input } });
  });

  it('keeps input and operation after an ambiguous send failure, and only queries on explicit request', async () => {
    const trial = renderTrial({ onSubmit: () => { throw new Error('PRIVATE provider text'); } });
    send();
    await waitFor(() => expect(trial.state().operations[0].uncertain).toBe(true));
    expect(screen.getByRole('textbox')).toHaveValue(input);
    expect(screen.queryByText(/PRIVATE/)).not.toBeInTheDocument();
    trial.connection(false);
    expect(screen.getByRole('button', { name: 'Consultar estado da ação' })).toBeDisabled();
    trial.connection(true);
    expect(trial.submit).toHaveBeenCalledTimes(1);
    expect(trial.query).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole('button', { name: 'Consultar estado da ação' }));
    expect(trial.query).toHaveBeenCalledExactlyOnceWith('op-1');
    expect(trial.submit).toHaveBeenCalledTimes(1);
    expect(trial.state().currentOperationId).toBe('op-1');
  });

  it('shows preparation, retained unstarted and actual narrative pending separately', () => {
    const trial = renderTrial();
    send();
    for (const [event, status, label] of [
      ['preparation', 'pending', 'Preparando sua ação.'],
      ['preparation', 'ready', 'Ação preparada; aguardando a continuação.'],
      ['narrative_pending', 'retained_unstarted', 'A ação está preparada; a narrativa ainda não começou.'],
      ['narrative_pending', 'pending', 'O narrador está preparando a continuação.'],
    ]) {
      trial.dispatch({ type: 'receive', operationId: 'op-1', event: { protocol, event, operation_id: 'op-1', status } });
      expect(screen.getByRole('status', { name: 'Estado da ação' })).toHaveTextContent(label);
      expect(screen.queryByLabelText('Pergunta do narrador')).not.toBeInTheDocument();
    }
  });

  it.each([
    ['preparation_rejected', 'failed', 'clarification_required'],
    ['preparation_rejected', 'timeout', 'timeout'],
    ['narrative_rejected', 'failed', 'narrative_rejected'],
    ['narrative_rejected', 'cancelled', 'cancelled'],
  ])('conserves the submitted text and ID for %s/%s/%s', (event, status, code) => {
    const trial = renderTrial();
    send();
    trial.dispatch({ type: 'receive', operationId: 'op-1', event: { protocol, event, operation_id: 'op-1', status, code } });
    expect(screen.getByRole('textbox')).toHaveValue(input);
    expect(trial.state().currentOperationId).toBe('op-1');
    expect(screen.getByRole('status', { name: 'Estado da ação' })).toHaveTextContent('Sua ação foi conservada');
    expect(trial.submit).toHaveBeenCalledTimes(1);
    expect(screen.queryByRole('button', { name: /tentar novamente|reenviar/i })).not.toBeInTheDocument();
  });

  it('renders confirmed n and q once, keeps them after invalid/conflicting events and escapes content', () => {
    const trial = renderTrial();
    send();
    const safe = { ...complete, n: n + ' <script>PRIVATE_EXECUTION</script>' };
    trial.dispatch({ type: 'receive', operationId: 'op-1', event: safe });
    trial.dispatch({ type: 'receive', operationId: 'op-1', event: safe });
    expect(screen.getAllByText(safe.n)).toHaveLength(1);
    expect(screen.getByLabelText('Pergunta do narrador')).toHaveTextContent(q);
    expect(document.querySelector('script')).toBeNull();
    trial.dispatch({ type: 'receive', operationId: 'op-1', event: { ...complete, n: n + ' OTHER CONFIRMATION' } });
    expect(screen.queryByText(/OTHER CONFIRMATION/)).not.toBeInTheDocument();
    expect(screen.getByText(safe.n)).toBeInTheDocument();
    expect(screen.getByRole('alert')).toHaveTextContent('Novos envios estão bloqueados');
    expect(screen.getByRole('button', { name: 'Escrever uma nova ação' })).toBeDisabled();
  });

  it('writes a new action only after a separate gesture, retaining the old terminal record', () => {
    const trial = renderTrial();
    send();
    trial.dispatch({ type: 'receive', operationId: 'op-1', event: complete });
    expect(screen.getByRole('textbox')).toHaveValue(input);
    fireEvent.click(screen.getByRole('button', { name: 'Escrever uma nova ação' }));
    expect(screen.getByRole('textbox')).toHaveValue('');
    expect(trial.submit).toHaveBeenCalledTimes(1);
    send('Pergunto a Rui por onde começar.');
    expect(trial.submit).toHaveBeenLastCalledWith({ operation_id: 'op-2', player_input: 'Pergunto a Rui por onde começar.' });
    expect(screen.getByText(n)).toBeInTheDocument();
    expect(trial.state().operations).toHaveLength(2);
  });

  it('keeps malformed local text instead of trimming it or sending a changed action', () => {
    const trial = renderTrial();
    send('  Espero a reação de Rui.  ');
    expect(trial.submit).not.toHaveBeenCalled();
    expect(screen.getByRole('textbox')).toHaveValue('  Espero a reação de Rui.  ');
    expect(screen.getByRole('alert')).toHaveTextContent('seu texto foi conservado');
  });

  it('accepts 500 Unicode code points without a 250-emoji DOM ceiling', () => {
    const trial = renderTrial();
    const text = '🦇'.repeat(500);
    expect(screen.getByRole('textbox')).toHaveAttribute('maxlength', '1000');
    send(text);
    expect(trial.submit).toHaveBeenCalledExactlyOnceWith({ operation_id: 'op-1', player_input: text });
    expect(screen.getByRole('textbox')).toHaveValue(text);
  });

  it('reports a query failure without erasing a confirmed narrative or issuing another action', async () => {
    const trial = renderTrial({ onQuery: () => Promise.reject(new Error('PRIVATE')) });
    trial.dispatch({ type: 'present_latest', event: complete });
    fireEvent.click(screen.getByRole('button', { name: 'Consultar estado da ação' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('Não foi possível consultar o estado');
    expect(screen.getByText(n)).toBeInTheDocument();
    expect(trial.submit).not.toHaveBeenCalled();
    expect(screen.queryByText('PRIVATE')).not.toBeInTheDocument();
    trial.dispatch({ type: 'receive', operationId: 'op-1', event: complete });
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
    expect(screen.getByText(n)).toBeInTheDocument();
  });
});
