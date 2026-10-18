import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import type { NarrativeMessage } from '../types/narrative';
import { NarrativeLog } from './NarrativeLog';

const timestamp = '2026-08-25T12:00:00.000Z';

describe('NarrativeLog', () => {
  it.each(['narrator', 'player', 'mechanics', 'guidance', 'error'] as const)(
    'escapa HTML não confiável na mensagem %s e no streaming', (type) => {
      const payload = '<img src=x onerror="globalThis.SECURITY_PROBE=true">';
      const { container } = render(<NarrativeLog messages={[
        { id: 'security-probe', type, content: payload, timestamp },
      ]} currentStreamText={'<script>globalThis.SECURITY_PROBE=true</script>'} />);
      expect(container.textContent).toContain(payload);
      expect(container.textContent).toContain('<script>globalThis.SECURITY_PROBE=true</script>');
      expect(container.querySelector('img,script')).toBeNull();
    },
  );

  it('renderiza mecânica e orientação como cartões distintos nos dois temas', () => {
    const messages: NarrativeMessage[] = [
      {
        id: 'receipt-1',
        type: 'mechanics',
        content: 'Raciocínio + Investigação: 3 sucessos.',
        timestamp,
        narrativeMode: 'resolved_action',
      },
      {
        id: 'guidance:operation-1',
        type: 'guidance',
        content: 'Use o formato solicitado.',
        timestamp,
      },
    ];

    render(<NarrativeLog messages={messages} currentStreamText="" />);

    const mechanics = screen.getByRole('article', { name: 'Resultado mecânico' });
    expect(mechanics).toHaveTextContent('Raciocínio + Investigação: 3 sucessos.');
    expect(mechanics).toHaveAttribute('data-narrative-mode', 'resolved_action');
    expect(mechanics).toHaveClass('dark:bg-sky-950/40', 'light:bg-sky-50');

    const guidance = screen.getByRole('article', { name: 'Orientação' });
    expect(guidance).toHaveTextContent('Use o formato solicitado.');
    expect(guidance).not.toHaveTextContent('[Erro do Sistema]');
    expect(guidance).toHaveClass('dark:bg-amber-950/30', 'light:bg-amber-50');
  });

  it('mantém mensagens de sistema e erro legíveis no tema claro', () => {
    const messages: NarrativeMessage[] = [
      {
        id: 'system-1',
        type: 'system',
        content: '[Sistema] Pronto.',
        timestamp,
      },
      {
        id: 'error-1',
        type: 'error',
        content: '[Erro do Sistema] Falha segura.',
        timestamp,
      },
    ];

    render(<NarrativeLog messages={messages} currentStreamText="" />);

    for (const message of screen.getAllByText(/\[(?:Sistema|Erro do Sistema)\]/)) {
      expect(message).toHaveClass(
        'dark:text-red-500',
        'light:text-red-800',
        'light:bg-red-50',
        'light:border-red-700',
      );
    }
  });
});
