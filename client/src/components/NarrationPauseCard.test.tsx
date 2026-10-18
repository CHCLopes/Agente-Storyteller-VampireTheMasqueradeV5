import { act, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { NarrationPauseCard } from './NarrationPauseCard';

const pause = {
  capsuleId: 'capsule-1', sourceOperationId: 'op-1', expectedStateRevision: 0,
  actionSummary: 'Examino a porta.', resolutionSummary: '3 sucessos',
  category: 'timeout', safeMessage: 'O Narrador não respondeu.',
  retryable: true,
  allowedActions: ['resume', 'abandon'] as const,
};

afterEach(() => vi.useRealTimers());

describe('NarrationPauseCard', () => {
  it('explica preservação, estado não aplicado e oferece ações explícitas', () => {
    const onResume = vi.fn(); const onAbandon = vi.fn();
    render(<NarrationPauseCard pause={pause} connected busy={false}
      onResume={onResume} onAbandon={onAbandon} />);
    expect(screen.getByText(/dados não serão lançados novamente/i)).toBeInTheDocument();
    expect(screen.getByText(/efeitos ainda não foram aplicados/i)).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Retomar narração' }));
    fireEvent.click(screen.getByRole('button', { name: 'Descartar ação' }));
    expect(onResume).toHaveBeenCalledOnce();
    expect(onAbandon).toHaveBeenCalledOnce();
  });

  it('deriva a espera do relógio do servidor mesmo com relógio local divergente', () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date('2030-01-01T00:00:00Z'));
    const onResume = vi.fn();
    render(<NarrationPauseCard pause={{
      ...pause,
      retryNotBefore: '2026-09-21T12:00:30Z',
      serverNow: '2026-09-21T12:00:00Z',
      rateLimitOrigin: 'unknown',
    }} connected busy={false} onResume={onResume} onAbandon={vi.fn()} />);
    expect(screen.getByText(/cerca de 30 s/i)).toBeInTheDocument();
    expect(screen.getByText(/origem do limite não foi confirmada/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Retomar narração' })).toBeDisabled();
    act(() => vi.advanceTimersByTime(30_000));
    expect(screen.getByRole('button', { name: 'Retomar narração' })).toBeEnabled();
  });
});
