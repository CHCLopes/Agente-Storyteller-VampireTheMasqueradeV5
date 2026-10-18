import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import type { PlayerSheet, Relationship } from '../types/character';
import { ActionPanel } from './ActionPanel';

const sheet: PlayerSheet = {
  nome: 'Mara',
  clan: 'Nosferatu',
  geracao: '12ª',
  attributes: {},
  skills: {},
  disciplines: {},
};

const relationships: Relationship[] = [
  {
    id: 'relationship-1',
    titulo: 'Aliada — Helena',
    desc: 'Uma informante confiável.',
  },
];

describe('ActionPanel', () => {
  it('mantém o rascunho editável durante pausa mas bloqueia envio e atalhos', () => {
    const onSendAction = vi.fn(() => true);
    render(
      <ActionPanel sheet={sheet} relationships={relationships}
        onSendAction={onSendAction} onConsultRelation={vi.fn()} submissionBlocked />,
    );
    const input = screen.getByRole('textbox', { name: 'Ação do Jogador' });
    expect(input).not.toBeDisabled();
    fireEvent.change(input, { target: { value: 'Planejo a próxima ação' } });
    expect(input).toHaveValue('Planejo a próxima ação');
    expect(screen.getByRole('button', { name: 'Enviar Ação' })).toBeDisabled();
    expect(screen.getByRole('combobox', { name: 'Fazer teste de habilidade' })).toBeDisabled();
    expect(onSendAction).not.toHaveBeenCalled();
  });
  it('orienta que uma rolagem precisa de um pool específico', () => {
    render(
      <ActionPanel
        sheet={sheet}
        relationships={relationships}
        onSendAction={vi.fn(() => true)}
        onConsultRelation={vi.fn()}
      />,
    );

    expect(
      screen.getByRole('textbox', { name: 'Ação do Jogador' }),
    ).toHaveAttribute(
      'placeholder',
      "Descreva sua ação ou use: 'Fazer teste de Raciocínio + Investigação'...",
    );
  });

  it('mantém a ação digitada quando o transporte rejeita o envio', () => {
    const onSendAction = vi.fn(() => false);

    render(
      <ActionPanel
        sheet={sheet}
        relationships={relationships}
        onSendAction={onSendAction}
        onConsultRelation={vi.fn()}
      />,
    );

    const input = screen.getByRole('textbox', { name: 'Ação do Jogador' });
    fireEvent.change(input, { target: { value: '  Examinar a porta  ' } });
    fireEvent.click(screen.getByRole('button', { name: 'Enviar Ação' }));

    expect(onSendAction).toHaveBeenCalledWith('Examinar a porta');
    expect(input).toHaveValue('  Examinar a porta  ');
  });

  it('não confirma nem limpa um relacionamento quando o envio é rejeitado', () => {
    const onSendAction = vi.fn(() => false);
    const onConsultRelation = vi.fn();

    render(
      <ActionPanel
        sheet={sheet}
        relationships={relationships}
        onSendAction={onSendAction}
        onConsultRelation={onConsultRelation}
      />,
    );

    const relationshipSelect = screen.getByRole('combobox', {
      name: 'Consultar relacionamento',
    });
    fireEvent.change(relationshipSelect, { target: { value: 'relationship-1' } });

    expect(onSendAction).toHaveBeenCalledWith('Consultando relacionamento com Helena');
    expect(onConsultRelation).not.toHaveBeenCalled();
    expect(relationshipSelect).toHaveValue('relationship-1');
  });
});
