import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import PipTracker from './PipTracker';

describe('PipTracker Component', () => {
  it('should render correct number of hunger pips and check active state', () => {
    render(<PipTracker type="hunger" value={3} />);
    const container = screen.getByLabelText('Tracker de Fome');
    expect(container).toBeInTheDocument();
    
    const activePips = screen.getAllByLabelText('Fome ativa');
    const emptyPips = screen.getAllByLabelText('Fome vazia');
    
    expect(activePips).toHaveLength(3);
    expect(emptyPips).toHaveLength(2);
  });

  it('should render health tracker with superficial and aggravated damages', () => {
    const healthTracker = {
      size: 7,
      superficial: 2,
      aggravated: 1
    };
    render(<PipTracker type="health" tracker={healthTracker} />);
    
    const container = screen.getByLabelText('Tracker de Vida');
    expect(container).toBeInTheDocument();

    const aggravatedPips = screen.getAllByLabelText('Dano agravado');
    const superficialPips = screen.getAllByLabelText('Dano superficial');
    const intactPips = screen.getAllByLabelText('Intacto');

    expect(aggravatedPips).toHaveLength(1);
    expect(superficialPips).toHaveLength(2);
    expect(intactPips).toHaveLength(4);
  });
});
