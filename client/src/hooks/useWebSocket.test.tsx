import { act, cleanup, renderHook } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { useWebSocket } from './useWebSocket';

class MockWebSocket {
  static readonly CONNECTING = 0;
  static readonly OPEN = 1;
  static readonly CLOSING = 2;
  static readonly CLOSED = 3;
  static instances: MockWebSocket[] = [];

  readonly url: string;
  readyState = MockWebSocket.CONNECTING;
  onopen: ((event: Event) => void) | null = null;
  onmessage: ((event: MessageEvent) => void) | null = null;
  onerror: ((event: Event) => void) | null = null;
  onclose: ((event: CloseEvent) => void) | null = null;
  send = vi.fn();
  close = vi.fn(() => {
    this.readyState = MockWebSocket.CLOSED;
  });

  constructor(url: string | URL) {
    this.url = String(url);
    MockWebSocket.instances.push(this);
  }

  open(): void {
    this.readyState = MockWebSocket.OPEN;
    this.onopen?.(new Event('open'));
  }

  serverClose(): void {
    this.readyState = MockWebSocket.CLOSED;
    this.onclose?.(new Event('close') as CloseEvent);
  }

  emitMessage(data: unknown): void {
    this.onmessage?.(new MessageEvent('message', { data: JSON.stringify(data) }));
  }
}

describe('useWebSocket reconnect backoff', () => {
  beforeEach(() => {
    vi.useFakeTimers();
    MockWebSocket.instances = [];
    vi.stubGlobal('WebSocket', MockWebSocket);
    vi.spyOn(console, 'log').mockImplementation(() => undefined);
    vi.spyOn(console, 'warn').mockImplementation(() => undefined);
    vi.spyOn(console, 'error').mockImplementation(() => undefined);
  });

  afterEach(() => {
    cleanup();
    vi.clearAllTimers();
    vi.useRealTimers();
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it('mantém o backoff crescente após conexões que abrem e fecham imediatamente', () => {
    renderHook(() => useWebSocket({ sessionId: 'ephemeral', onMessage: vi.fn() }));

    const first = MockWebSocket.instances[0];
    act(() => {
      first.open();
      first.serverClose();
    });

    act(() => vi.advanceTimersByTime(1_000));
    expect(MockWebSocket.instances).toHaveLength(2);

    const second = MockWebSocket.instances[1];
    act(() => {
      second.open();
      second.serverClose();
    });

    act(() => vi.advanceTimersByTime(1_000));
    expect(MockWebSocket.instances).toHaveLength(2);

    act(() => vi.advanceTimersByTime(1_000));
    expect(MockWebSocket.instances).toHaveLength(3);
  });

  it('reinicia o backoff depois de receber o snapshot canônico', () => {
    const onMessage = vi.fn();
    renderHook(() => useWebSocket({ sessionId: 'snapshot', onMessage }));

    const first = MockWebSocket.instances[0];
    act(() => {
      first.open();
      first.serverClose();
      vi.advanceTimersByTime(1_000);
    });

    const second = MockWebSocket.instances[1];
    const snapshot = { action: 'state_update', snapshot_version: 1 };
    act(() => {
      second.open();
      second.emitMessage(snapshot);
      second.serverClose();
    });

    expect(onMessage).toHaveBeenCalledWith(snapshot);
    act(() => vi.advanceTimersByTime(999));
    expect(MockWebSocket.instances).toHaveLength(2);

    act(() => vi.advanceTimersByTime(1));
    expect(MockWebSocket.instances).toHaveLength(3);
  });

  it('serializa um envelope estável e o reenvia até receber o terminal', () => {
    const { result } = renderHook(() =>
      useWebSocket({ sessionId: 'idempotent', onMessage: vi.fn() }),
    );
    const first = MockWebSocket.instances[0];
    act(() => first.open());

    let accepted = false;
    act(() => {
      accepted = result.current.sendAction('  Eu avanço.  ');
    });
    expect(accepted).toBe(true);
    const firstEnvelope = JSON.parse(first.send.mock.calls[0][0]) as {
      operation_id: string;
      input: string;
    };
    expect(firstEnvelope.operation_id).toMatch(/^op-/);
    expect(firstEnvelope.input).toBe('Eu avanço.');

    act(() => {
      first.serverClose();
      vi.advanceTimersByTime(1_000);
    });
    const second = MockWebSocket.instances[1];
    act(() => second.open());
    expect(JSON.parse(second.send.mock.calls[0][0])).toEqual(firstEnvelope);

    act(() => {
      second.emitMessage({
        action: 'operation_pending',
        operation_id: firstEnvelope.operation_id,
        status: 'pending',
      });
      second.serverClose();
      vi.advanceTimersByTime(2_000);
    });
    const third = MockWebSocket.instances[2];
    act(() => third.open());
    expect(JSON.parse(third.send.mock.calls[0][0])).toEqual(firstEnvelope);

    act(() => {
      third.emitMessage({
        action: 'stream_end',
        operation_id: firstEnvelope.operation_id,
        status: 'completed',
      });
      third.serverClose();
      vi.advanceTimersByTime(4_000);
    });
    const fourth = MockWebSocket.instances[3];
    act(() => fourth.open());
    expect(fourth.send).not.toHaveBeenCalled();
  });
});
