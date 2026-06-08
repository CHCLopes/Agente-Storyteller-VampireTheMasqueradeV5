import React from 'react';
import { Sun, Moon, HelpCircle, Info } from 'lucide-react';

interface HeaderProps {
  isConnected: boolean;
  isDark: boolean;
  onToggleTheme: () => void;
  onOpenHelp: () => void;
  onOpenAbout: () => void;
  sessionId: string;
}

export const Header: React.FC<HeaderProps> = ({
  isConnected,
  isDark,
  onToggleTheme,
  onOpenHelp,
  onOpenAbout,
  sessionId
}) => {
  return (
    <header 
      className="fixed top-0 left-0 w-full h-14 bg-v5-card/90 dark:bg-v5-card/90 light:bg-v5light-card/95 border-b border-zinc-800/80 dark:border-zinc-800/80 light:border-v5light-border/80 backdrop-blur z-30 flex items-center justify-between px-4"
      role="banner"
    >
      {/* Lado Esquerdo: Título */}
      <div className="flex items-center gap-3">
        <h1 className="font-gothic text-2xl tracking-wider text-v5-crimson dark:text-v5-crimson light:text-v5light-earth m-0">
          COTERIE ONLINE
        </h1>
        <div className="hidden sm:block text-[10px] px-2 py-0.5 border rounded border-zinc-700 dark:border-zinc-700 light:border-v5light-border font-mono opacity-80 uppercase">
          Sessão: {sessionId}
        </div>
      </div>

      {/* Lado Direito: Controles & Acessibilidade */}
      <div className="flex items-center gap-4">
        {/* Status de Conexão */}
        <div className="flex items-center gap-2" aria-live="polite">
          <div 
            id="conn-indicator"
            className={`w-2.5 h-2.5 rounded-full transition-all duration-300 ${
              isConnected 
                ? 'bg-emerald-600 animate-pulse shadow-[0_0_8px_#10b981]' 
                : 'bg-red-700 shadow-[0_0_8px_#b91c1c]'
            }`}
          />
          <span 
            id="conn-text"
            className="text-[10px] font-bold tracking-widest font-mono opacity-70 hidden xs:inline"
          >
            {isConnected ? 'CONECTADO' : 'DESCONECTADO'}
          </span>
        </div>

        {/* Separador */}
        <div className="h-4 w-[1px] bg-zinc-800 dark:bg-zinc-800 light:bg-v5light-border" />

        {/* Botão Sobre */}
        <button
          onClick={onOpenAbout}
          className="p-1.5 rounded hover:bg-zinc-800/50 dark:hover:bg-zinc-800/50 light:hover:bg-v5light-border/40 transition-colors opacity-80 hover:opacity-100"
          title="Sobre o Agente Storyteller"
          aria-label="Sobre o Agente Storyteller"
        >
          <Info className="w-4 h-4 text-primary" style={{ color: 'var(--text-primary)' }} />
        </button>

        {/* Botão Ajuda / Manual */}
        <button
          onClick={onOpenHelp}
          className="p-1.5 rounded hover:bg-zinc-800/50 dark:hover:bg-zinc-800/50 light:hover:bg-v5light-border/40 transition-colors opacity-80 hover:opacity-100"
          title="Manual de Instruções"
          aria-label="Manual de Instruções"
        >
          <HelpCircle className="w-4 h-4 text-primary" style={{ color: 'var(--text-primary)' }} />
        </button>

        {/* Alternador de Tema (Dark/Light Mode) */}
        <button
          onClick={onToggleTheme}
          className="p-1.5 rounded hover:bg-zinc-800/50 dark:hover:bg-zinc-800/50 light:hover:bg-v5light-border/40 transition-colors opacity-80 hover:opacity-100"
          title={isDark ? "Ativar Modo Claro" : "Ativar Modo Escuro"}
          aria-label={isDark ? "Ativar Modo Claro" : "Ativar Modo Escuro"}
        >
          {isDark ? (
            <Sun className="w-4 h-4 text-amber-500" />
          ) : (
            <Moon className="w-4 h-4 text-indigo-950" />
          )}
        </button>
      </div>
    </header>
  );
};
export default Header;
