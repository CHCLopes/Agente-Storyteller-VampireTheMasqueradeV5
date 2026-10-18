// @vitest-environment node
import { describe, expect, it } from 'vitest';
import {
  createInitialNarrativeState,
  narrativeProtocolReducer,
  sendConnectedAction,
  type NarrativeProtocolAction,
  type NarrativeProtocolState,
} from './narrativeProtocol';

const timestamp = '2026-08-24T12:00:00.000Z';

function apply(
  state: NarrativeProtocolState,
  ...actions: NarrativeProtocolAction[]
): NarrativeProtocolState {
  return actions.reduce(narrativeProtocolReducer, state);
}

function streamedState(): NarrativeProtocolState {
  return apply(
    createInitialNarrativeState(timestamp),
    { type: 'stream_start' },
    { type: 'stream_chunk', chunk: 'A noite ' },
    { type: 'stream_chunk', chunk: 'cai.' },
  );
}

describe('narrativeProtocolReducer', () => {
  it.each(['failed', 'cancelled', 'timeout'])(
    'descarta chunks provisórios quando o terminal é %s',
    status => {
      const result = narrativeProtocolReducer(streamedState(), {
        type: 'stream_end',
        status,
        narrative: null,
        fallbackId: 'fallback-id',
        fallbackTimestamp: timestamp,
      });

      expect(result.currentStreamText).toBe('');
      expect(result.isLoading).toBe(false);
      expect(result.messages).toHaveLength(2);
      expect(result.messages.at(-1)?.type).toBe('error');
      expect(result.messages.some(message => message.content.includes('A noite'))).toBe(false);
    },
  );

  it('promove exatamente uma narrativa no terminal completed repetido', () => {
    const completed: NarrativeProtocolAction = {
      type: 'stream_end',
      status: 'completed',
      narrative: {
        narrative_id: 'narrative-1',
        text: 'A noite cai.',
        created_at: timestamp,
      },
      fallbackId: 'fallback-id',
      fallbackTimestamp: timestamp,
    };

    const first = narrativeProtocolReducer(streamedState(), completed);
    const repeated = narrativeProtocolReducer(first, completed);

    expect(repeated.currentStreamText).toBe('');
    expect(repeated.messages.filter(message => message.id === 'narrative-1')).toEqual([
      expect.objectContaining({ type: 'narrator', content: 'A noite cai.' }),
    ]);
  });

  it('promove recibo mecânico e narrativa uma única vez no completed repetido', () => {
    const completed: NarrativeProtocolAction = {
      type: 'stream_end',
      status: 'completed',
      resolutionReceipt: {
        receipt_id: 'receipt-1',
        display: 'Raciocínio + Investigação: 3 sucessos.',
        narrative_mode: 'resolved_action',
      },
      narrative: {
        narrative_id: 'narrative-1',
        text: 'As marcas recentes revelam uma passagem lateral.',
        created_at: timestamp,
      },
      fallbackId: 'fallback-id',
      fallbackTimestamp: timestamp,
    };

    const first = narrativeProtocolReducer(streamedState(), completed);
    const repeated = narrativeProtocolReducer(first, completed);

    expect(repeated.messages.slice(-2)).toEqual([
      expect.objectContaining({
        id: 'receipt-1',
        type: 'mechanics',
        content: 'Raciocínio + Investigação: 3 sucessos.',
        narrativeMode: 'resolved_action',
      }),
      expect.objectContaining({
        id: 'narrative-1',
        type: 'narrator',
        content: 'As marcas recentes revelam uma passagem lateral.',
      }),
    ]);
    expect(repeated.messages.filter(message => message.id === 'receipt-1')).toHaveLength(1);
    expect(repeated.messages.filter(message => message.id === 'narrative-1')).toHaveLength(1);
  });

  it('encerra loading e promove clarification como orientação idempotente', () => {
    const clarification: NarrativeProtocolAction = {
      type: 'clarification',
      message: 'Informe o pool no formato: Fazer teste de Raciocínio + Investigação.',
      operationId: 'operation-1',
      terminal: true,
      fallbackTimestamp: timestamp,
    };

    const first = narrativeProtocolReducer(streamedState(), clarification);
    const repeated = narrativeProtocolReducer(first, clarification);

    expect(repeated.currentStreamText).toBe('');
    expect(repeated.isLoading).toBe(false);
    expect(repeated.messages.filter(message => message.id === 'guidance:operation-1')).toEqual([
      expect.objectContaining({
        type: 'guidance',
        content: 'Informe o pool no formato: Fazer teste de Raciocínio + Investigação.',
      }),
    ]);
    expect(repeated.messages.some(message => message.content.includes('[Erro do Sistema]'))).toBe(false);
  });

  it('não trata clarification não terminal como resposta concluída', () => {
    const state = streamedState();
    const result = narrativeProtocolReducer(state, {
      type: 'clarification',
      message: 'Ainda processando.',
      operationId: 'operation-1',
      terminal: false,
      fallbackTimestamp: timestamp,
    });

    expect(result).toBe(state);
  });

  it('não duplica narrativa hidratada antes do terminal completed', () => {
    const hydrated = narrativeProtocolReducer(streamedState(), {
      type: 'hydrate_history',
      history: [{ id: 'narrative-1', content: 'A noite cai.', timestamp }],
      fallbackTimestamp: timestamp,
    });
    const completed = narrativeProtocolReducer(hydrated, {
      type: 'stream_end',
      status: 'completed',
      narrative: {
        narrative_id: 'narrative-1',
        text: 'A noite cai.',
        created_at: timestamp,
      },
      fallbackId: 'fallback-id',
      fallbackTimestamp: timestamp,
    });

    expect(completed.messages.filter(message => message.id === 'narrative-1')).toHaveLength(1);
  });

  it('aborta o buffer provisório ao reidratar depois de uma reconexão', () => {
    const reconnected = narrativeProtocolReducer(streamedState(), {
      type: 'hydrate_history',
      history: [],
      fallbackTimestamp: timestamp,
    });

    expect(reconnected.currentStreamText).toBe('');
    expect(reconnected.isLoading).toBe(false);
    expect(reconnected.messages.some(message => message.content.includes('A noite'))).toBe(false);
  });

  it('não promove completed sem narrativa canônica identificada', () => {
    const result = narrativeProtocolReducer(streamedState(), {
      type: 'stream_end',
      status: 'completed',
      narrative: null,
      fallbackId: 'fallback-id',
      fallbackTimestamp: timestamp,
    });

    expect(result.currentStreamText).toBe('');
    expect(result.isLoading).toBe(false);
    expect(result.messages).toHaveLength(1);
  });

  it('reidrata narrative_history de forma idempotente inclusive dentro do mesmo payload', () => {
    const history = [
      { id: 'narrative-1', content: 'Primeiro turno.', timestamp },
      { id: 'narrative-1', content: 'Duplicata.', timestamp },
      { id: 'receipt-1', type: 'mechanics', content: '3 sucessos.', narrative_mode: 'resolved_action' },
      { id: 'guidance-1', type: 'guidance', content: 'Escolha um atributo e uma habilidade.' },
      { id: 'invalid-player', type: 'player', content: 'Não deve ser hidratada.' },
      { id: '', content: 'Invalida.' },
    ];
    const initial = createInitialNarrativeState(timestamp);
    const once = narrativeProtocolReducer(initial, {
      type: 'hydrate_history',
      history,
      fallbackTimestamp: timestamp,
    });
    const twice = narrativeProtocolReducer(once, {
      type: 'hydrate_history',
      history,
      fallbackTimestamp: timestamp,
    });

    expect(twice.messages.map(message => message.id)).toEqual([
      'init-sys',
      'narrative-1',
      'receipt-1',
      'guidance-1',
    ]);
    expect(twice.messages.find(message => message.id === 'narrative-1')?.content).toBe(
      'Primeiro turno.',
    );
    expect(twice.messages.find(message => message.id === 'receipt-1')).toEqual(
      expect.objectContaining({
        type: 'mechanics',
        timestamp,
        narrativeMode: 'resolved_action',
      }),
    );
    expect(twice.messages.find(message => message.id === 'guidance-1')?.type).toBe('guidance');
  });
});

describe('sendConnectedAction', () => {
  it('não aceita nem promove ação quando o transporte recusa o envio', () => {
    const sent: string[] = [];
    const result = sendConnectedAction('  Eu avanço.  ', message => {
      sent.push(message);
      return false;
    });

    expect(result).toBeNull();
    expect(sent).toEqual(['Eu avanço.']);
  });

  it('devolve a ação normalizada somente depois do envio aceito', () => {
    const result = sendConnectedAction('  Eu avanço.  ', () => true);

    expect(result).toBe('Eu avanço.');
  });
});

describe('feedback de falhas e sincronização do playtest', () => {
  function failure(status: unknown = 'failed', operationId: unknown = 'operation-1'): Extract<NarrativeProtocolAction, { type: 'stream_end' }> {
    return {
      type: 'stream_end', status, operationId,
      narrative: { narrative_id: 'rejected', text: 'TRECHO REJEITADO' },
      resolutionReceipt: { receipt_id: 'rejected-receipt', display: 'Resultado não confirmado', narrative_mode: 'llm' },
      fallbackId: 'fallback-error', fallbackTimestamp: timestamp,
    };
  }

  it('registra uma falha por operação mesmo quando o terminal é repetido', () => {
    const first = narrativeProtocolReducer(streamedState(), failure());
    const repeated = narrativeProtocolReducer(first, {
      ...failure(), fallbackId: 'another-fallback',
    } as NarrativeProtocolAction);
    expect(repeated.messages.filter(message => message.id === 'error:operation-1')).toHaveLength(1);
    expect(repeated.messages.at(-1)?.type).toBe('error');
    expect(repeated.messages.some(message => /TRECHO REJEITADO|Resultado não confirmado|A noite/.test(message.content))).toBe(false);
  });

  it('preserva o erro específico recebido antes do terminal sem acrescentar outro', () => {
    const error = {
      id: 'error:operation-1', type: 'error' as const,
      content: '[Erro do Sistema] A continuação contrariou a cena.', timestamp,
    };
    const state = apply(streamedState(), { type: 'append_message', message: error, isLoading: false });
    const result = narrativeProtocolReducer(state, failure());
    expect(result.messages.filter(message => message.type === 'error')).toEqual([error]);
    expect(result.currentStreamText).toBe('');
  });

  it('troca apenas o aviso da mesma operação pelo erro específico que chegar depois', () => {
    const error = {
      id: 'error:operation-1', type: 'error' as const,
      content: '[Erro do Sistema] A preparação da ação falhou.', timestamp,
    };
    const result = apply(streamedState(), failure(),
      { type: 'append_message', message: error, isLoading: false },
      { type: 'append_message', message: error, isLoading: false });
    expect(result.messages.filter(message => message.type === 'error')).toEqual([error]);
    expect(result.messages[0].id).toBe('init-sys');
  });

  it('não deixa o erro de uma operação anterior ocultar uma nova falha', () => {
    const result = apply(streamedState(), failure('failed', 'one'),
      { type: 'stream_start' }, failure('timeout', 'two'));
    expect(result.messages.filter(message => message.type === 'error').map(message => message.id))
      .toEqual(['error:one', 'error:two']);
  });

  it('mantém pending em processamento sem promover chunks ou mostrar sucesso', () => {
    const state = streamedState();
    const result = narrativeProtocolReducer(state, failure('pending'));
    expect(result.currentStreamText).toBe(state.currentStreamText);
    expect(result.messages).toEqual(state.messages);
    expect(result.isLoading).toBe(true);
  });

  it.each([undefined, null, true, 'unknown'])('expõe resultado não confirmado para status inválido %s', status => {
    const result = narrativeProtocolReducer(streamedState(), { ...failure(), status });
    expect(result.messages.at(-1)?.type).toBe('error');
    expect(result.messages.at(-1)?.content).toContain('Não foi possível confirmar');
    expect(result.messages.some(message => message.type === 'narrator' || message.type === 'mechanics')).toBe(false);
    expect(result.currentStreamText).toBe('');
    expect(result.isLoading).toBe(false);
  });

  it('usa fallback estável quando o terminal não informa operation_id', () => {
    const action = failure('failed', null);
    const result = apply(streamedState(), action, action);
    expect(result.messages.filter(message => message.type === 'error').map(message => message.id))
      .toEqual(['error:fallback-error']);
  });

  it('preserva dez ações e cinco falhas durante sincronizações repetidas de cinco narrativas', () => {
    let state = createInitialNarrativeState(timestamp);
    const history: { id: string; type: 'narrator'; content: string; timestamp: string }[] = [];
    for (let index = 1; index <= 10; index += 1) {
      state = apply(state, {
        type: 'append_message', message: {
          id: `player-${index}`, type: 'player', content: `Ação ${index}.`, timestamp,
        },
      }, { type: 'stream_start' }, { type: 'stream_chunk', chunk: `Provisório ${index}.` });
      if (index % 2 === 0) {
        const record = { id: `narrative-${index}`, type: 'narrator' as const,
          content: `Continuação ${index}.`, timestamp };
        history.push(record);
        state = apply(state, {
          type: 'stream_end', status: 'completed', narrative: {
            narrative_id: record.id, text: record.content, created_at: timestamp,
          }, fallbackId: `terminal-${index}`, fallbackTimestamp: timestamp,
        });
      } else {
        state = apply(state, failure('failed', `operation-${index}`));
      }
      state = apply(state,
        { type: 'hydrate_history', history, fallbackTimestamp: timestamp },
        { type: 'hydrate_history', history: [], fallbackTimestamp: timestamp });
    }
    expect(state.messages.filter(message => message.type === 'player')).toHaveLength(10);
    expect(state.messages.filter(message => message.type === 'error')).toHaveLength(5);
    expect(state.messages.filter(message => message.type === 'narrator')).toHaveLength(5);
    expect(state.messages.some(message => /Provisório|TRECHO REJEITADO/.test(message.content))).toBe(false);
    expect(state.isLoading).toBe(false);
  });

  it('preserva erro de preparo sem stream e mantém o limite explícito do histórico após reload', () => {
    const preparedError = {
      id: 'error:preparation', type: 'error' as const, content: 'A preparação falhou.', timestamp,
    };
    const history = [{ id: 'narrative-old', content: 'Turno confirmado.', timestamp }];
    const local = apply(createInitialNarrativeState(timestamp), {
      type: 'append_message', message: { id: 'player-1', type: 'player', content: 'Eu observo.', timestamp },
    }, { type: 'append_message', message: preparedError, isLoading: false },
    { type: 'hydrate_history', history, fallbackTimestamp: timestamp });
    expect(local.messages.find(message => message.id === preparedError.id)).toEqual(preparedError);
    expect(local.messages.find(message => message.id === 'player-1')?.content).toBe('Eu observo.');
    const fresh = apply(createInitialNarrativeState(timestamp),
      { type: 'hydrate_history', history, fallbackTimestamp: timestamp });
    // The client cannot recover inputs/failures that the backend did not send.
    expect(fresh.messages.map(message => message.type)).toEqual(['system', 'narrator']);
  });

  it('rehidrata uma pausa sem promover texto provisório e a remove após conclusão', () => {
    const paused = narrativeProtocolReducer(streamedState(), {
      type: 'narration_paused', payload: {
        capsule_id: 'capsule-1', source_operation_id: 'op-source',
        expected_state_revision: 2, action_summary: 'Examino a porta.',
        resolution_summary: '3 sucessos', category: 'timeout',
        safe_message: 'O Narrador não respondeu.', retryable: true,
        retry_not_before: '2026-09-21T12:00:30Z', server_now: '2026-09-21T12:00:00Z',
        rate_limit_origin: 'gateway', gate_scope: 'gateway_account',
        evidence_scope: 'gateway', allowed_actions: ['resume', 'abandon'],
      },
    });
    expect(paused.currentStreamText).toBe('');
    expect(paused.isLoading).toBe(false);
    expect(paused.narrationPause?.capsuleId).toBe('capsule-1');
    expect(paused.narrationPause).toMatchObject({
      retryable: true,
      serverNow: '2026-09-21T12:00:00Z',
      rateLimitOrigin: 'gateway',
      gateScope: 'gateway_account',
      evidenceScope: 'gateway',
    });
    const completed = narrativeProtocolReducer(paused, {
      type: 'stream_end', status: 'completed', operationId: 'op-resume',
      narrative: { narrative_id: 'n-1', text: 'A porta cede.', created_at: timestamp },
      resolutionReceipt: null, fallbackId: 'fallback', fallbackTimestamp: timestamp,
    });
    expect(completed.narrationPause).toBeNull();
  });
});
