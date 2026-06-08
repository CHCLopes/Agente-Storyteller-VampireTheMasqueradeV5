import React from 'react';
import { User, HelpCircle, Info } from 'lucide-react';

interface BottomNavProps {
  onToggleSheet: () => void;
  onOpenHelp: () => void;
  onOpenAbout: () => void;
}

export const BottomNav: React.FC<BottomNavProps> = ({
  onToggleSheet,
  onOpenHelp,
  onOpenAbout
}) => {
  return (
    <nav 
      className="lg:hidden fixed bottom-0 left-0 w-full h-14 bg-v5-card/95 dark:bg-v5-card/95 light:bg-v5light-card/98 border-t border-zinc-800/80 dark:border-zinc-800/80 light:border-v5light-border/80 backdrop-blur z-30 flex items-center justify-around"
      role="navigation"
      aria-label="Navegação móvel secundária"
    >
      {/* Botão Sobre */}
      <button
        id="btn-nav-about"
        onClick={onOpenAbout}
        className="flex flex-col items-center gap-1 p-2 text-secondary hover:text-primary transition-colors cursor-pointer"
        style={{ color: 'var(--text-secondary)' }}
      >
        <Info className="w-4.5 h-4.5" />
        <span className="text-[9px] font-bold tracking-wider uppercase">Sobre</span>
      </button>

      {/* Botão Ficha (HUD) */}
      <button
        id="btn-nav-sheet"
        onClick={onToggleSheet}
        className="flex flex-col items-center gap-1 p-2 text-secondary hover:text-primary transition-colors cursor-pointer"
        style={{ color: 'var(--text-secondary)' }}
      >
        <User className="w-4.5 h-4.5 text-v5-crimson dark:text-v5-crimson light:text-v5light-earth" />
        <span className="text-[9px] font-bold tracking-wider uppercase text-v5-crimson dark:text-v5-crimson light:text-v5light-earth">Ficha</span>
      </button>

      {/* Botão Ajuda */}
      <button
        id="btn-nav-help"
        onClick={onOpenHelp}
        className="flex flex-col items-center gap-1 p-2 text-secondary hover:text-primary transition-colors cursor-pointer"
        style={{ color: 'var(--text-secondary)' }}
      >
        <HelpCircle className="w-4.5 h-4.5" />
        <span className="text-[9px] font-bold tracking-wider uppercase">Ajuda</span>
      </button>
    </nav>
  );
};
export default BottomNav;
