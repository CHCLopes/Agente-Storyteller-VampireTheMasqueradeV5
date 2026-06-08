import React from 'react';

interface TrackerDetail {
  superficial: number;
  aggravated: number;
  size: number;
}

interface PipTrackerProps {
  type: 'hunger' | 'health' | 'willpower';
  value?: number; // Para Fome
  tracker?: TrackerDetail; // Para Vida e Vontade
}

export const PipTracker: React.FC<PipTrackerProps> = ({ type, value = 0, tracker }) => {
  if (type === 'hunger') {
    return (
      <div className="flex gap-2 items-center" aria-label="Tracker de Fome">
        {Array.from({ length: 5 }).map((_, i) => {
          const isActive = i < value;
          return (
            <div
              key={i}
              className="w-[18px] h-[18px] rounded-full border-2 transition-all duration-300"
              style={{
                borderColor: 'var(--hunger-color)',
                backgroundColor: isActive ? 'var(--hunger-color)' : 'transparent',
                boxShadow: isActive ? '0 0 8px var(--hunger-color)' : 'none',
              }}
              aria-label={isActive ? 'Fome ativa' : 'Fome vazia'}
            />
          );
        })}
      </div>
    );
  }

  const { size = 7, superficial = 0, aggravated = 0 } = tracker || { size: 7, superficial: 0, aggravated: 0 };

  return (
    <div className="flex gap-2 flex-wrap items-center" aria-label={`Tracker de ${type === 'health' ? 'Vida' : 'Vontade'}`}>
      {Array.from({ length: size }).map((_, i) => {
        const isAggravated = i < aggravated;
        const isSuperficial = i < (aggravated + superficial);
        
        let backgroundStyle = 'transparent';
        if (isAggravated) {
          // Dano Agravado: "X" (2 gradients)
          backgroundStyle = 'linear-gradient(135deg, transparent 45%, var(--damage-color) 45%, var(--damage-color) 55%, transparent 55%), linear-gradient(45deg, transparent 45%, var(--damage-color) 45%, var(--damage-color) 55%, transparent 55%)';
        } else if (isSuperficial) {
          // Dano Superficial: "/" (diagonal)
          backgroundStyle = 'linear-gradient(135deg, transparent 45%, var(--damage-color) 45%, var(--damage-color) 55%, transparent 55%)';
        }

        return (
          <div
            key={i}
            className="w-[18px] h-[18px] rounded border-2 transition-all duration-300 relative overflow-hidden"
            style={{
              borderColor: 'var(--border)',
              background: backgroundStyle,
            }}
            aria-label={
              isAggravated 
                ? 'Dano agravado' 
                : isSuperficial 
                ? 'Dano superficial' 
                : 'Intacto'
            }
          />
        );
      })}
    </div>
  );
};
export default PipTracker;
