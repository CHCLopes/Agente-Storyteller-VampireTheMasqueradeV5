import { useEffect, useRef } from 'react';
import type { NarrativeMessage } from '../types/narrative';

interface NarrativeLogProps {
  messages: NarrativeMessage[];
  currentStreamText: string;
}

export const NarrativeLog: React.FC<NarrativeLogProps> = ({ messages, currentStreamText }) => {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (containerRef.current) {
      containerRef.current.scrollTop = containerRef.current.scrollHeight;
    }
  }, [messages, currentStreamText]);

  return (
    <div 
      ref={containerRef}
      id="narrative-log"
      className="min-h-0 min-w-0 flex-1 overflow-y-auto overscroll-contain p-4 md:p-6 space-y-4 select-text"
      role="log"
      tabIndex={0}
      aria-label="Registro de narrativa do RPG"
    >
      {messages.map((msg) => {
        if (msg.type === 'narrator') {
          return (
            <div 
              key={msg.id}
              className="font-serif text-lg leading-relaxed border-l-2 border-v5-crimson dark:border-v5-crimson light:border-v5light-earth pl-4 py-1 text-left text-primary animate-fade-in"
              style={{ color: 'var(--text-primary)' }}
            >
              {msg.content}
            </div>
          );
        } else if (msg.type === 'player') {
          return (
            <div 
              key={msg.id}
              className="font-sans text-sm bg-zinc-950/40 dark:bg-zinc-950/40 light:bg-v5light-card border border-zinc-900 dark:border-zinc-900 light:border-v5light-border p-3 rounded text-right ml-auto max-w-xl animate-fade-in"
              style={{ color: 'var(--text-primary)' }}
            >
              {msg.content}
            </div>
          );
        } else if (msg.type === 'mechanics') {
          return (
            <article
              key={msg.id}
              aria-label="Resultado mecânico"
              data-message-type="mechanics"
              data-narrative-mode={msg.narrativeMode}
              className="font-sans text-sm bg-sky-950/40 dark:bg-sky-950/40 light:bg-sky-50 border border-sky-700/70 dark:border-sky-700/70 light:border-sky-700 rounded p-3 text-left text-sky-100 dark:text-sky-100 light:text-sky-950 animate-fade-in"
            >
              <span className="block text-[10px] font-bold tracking-widest uppercase opacity-80 mb-1">
                Resultado mecânico
              </span>
              <span className="whitespace-pre-wrap">{msg.content}</span>
            </article>
          );
        } else if (msg.type === 'guidance') {
          return (
            <article
              key={msg.id}
              aria-label="Orientação"
              data-message-type="guidance"
              className="font-sans text-sm bg-amber-950/30 dark:bg-amber-950/30 light:bg-amber-50 border border-amber-700/70 dark:border-amber-700/70 light:border-amber-700 rounded p-3 text-left text-amber-100 dark:text-amber-100 light:text-amber-950 animate-fade-in"
            >
              <span className="block text-[10px] font-bold tracking-widest uppercase opacity-80 mb-1">
                Orientação
              </span>
              <span className="whitespace-pre-wrap">{msg.content}</span>
            </article>
          );
        } else if (msg.type === 'error' || msg.type === 'system') {
          return (
            <div 
              key={msg.id}
              className="font-mono text-xs text-red-500 dark:text-red-500 light:text-red-800 bg-red-950/10 dark:bg-red-950/10 light:bg-red-50 border border-red-900/40 dark:border-red-900/40 light:border-red-700 p-3 rounded text-left animate-fade-in"
            >
              {msg.content}
            </div>
          );
        } else {
          return (
            <div 
              key={msg.id}
              className="font-sans text-sm text-secondary bg-zinc-950/20 p-2 rounded text-left opacity-80 animate-fade-in"
              style={{ color: 'var(--text-secondary)' }}
            >
              {msg.content}
            </div>
          );
        }
      })}

      {/* Bloco de Stream ativo */}
      {currentStreamText && (
        <div 
          className="font-serif text-lg leading-relaxed border-l-2 border-v5-crimson dark:border-v5-crimson light:border-v5light-earth pl-4 py-1 text-left text-primary transition-opacity duration-300"
          style={{ color: 'var(--text-primary)' }}
        >
          {currentStreamText}
          <span className="inline-block w-2 h-4 ml-1 bg-v5-crimson dark:bg-v5-crimson light:bg-v5light-earth animate-pulse-subtle" />
        </div>
      )}
    </div>
  );
};
export default NarrativeLog;
