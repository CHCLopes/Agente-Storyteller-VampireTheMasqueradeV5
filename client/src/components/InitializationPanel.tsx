import { useEffect, useRef } from "react";
import { useInitializationLog } from "../hooks/useInitializationLog";
import type { LogEntry } from "../hooks/useInitializationLog";

interface InitializationPanelProps {
  onInitializationComplete: (success: boolean) => void;
}

export function InitializationPanel({ onInitializationComplete }: InitializationPanelProps) {
  const { logs, isInitializing, error, retry } = useInitializationLog(onInitializationComplete);
  const logsEndRef = useRef<HTMLDivElement>(null);

  // Scroll automático para o fim ao receber novos logs
  useEffect(() => {
    logsEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [logs]);

  const getStatusIcon = (status: LogEntry["status"]) => {
    switch (status) {
      case "success":
        return <span className="text-emerald-500 font-bold mr-2 select-none">[✓]</span>;
      case "error":
        return <span className="text-rose-500 font-bold mr-2 select-none">[✗]</span>;
      case "warning":
        return <span className="text-amber-500 font-bold mr-2 select-none">[⚠]</span>;
      case "pending":
      default:
        return (
          <span className="text-zinc-500 font-bold mr-2 animate-pulse select-none">
            [...]
          </span>
        );
    }
  };

  const getStatusColor = (status: LogEntry["status"]) => {
    switch (status) {
      case "success":
        return "text-emerald-400 dark:text-emerald-500";
      case "error":
        return "text-rose-400 dark:text-rose-500";
      case "warning":
        return "text-amber-400 dark:text-amber-500";
      case "pending":
      default:
        return "text-zinc-400 dark:text-zinc-500";
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-zinc-950 text-zinc-100 font-sans p-4 relative overflow-hidden selection:bg-rose-900/50 selection:text-rose-100">
      {/* Background radial gradient to give premium vampire atmosphere */}
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,rgba(159,18,57,0.08)_0%,transparent_70%)] pointer-events-none" />

      <div className="w-full max-w-2xl bg-zinc-900/80 backdrop-blur-md border border-zinc-800/80 rounded-lg shadow-2xl p-6 md:p-8 flex flex-col gap-6 relative z-10 animate-fade-in">
        
        {/* Header Area */}
        <div className="flex flex-col gap-2 border-b border-zinc-800 pb-4">
          <div className="flex items-center justify-between">
            <h1 className="text-xl md:text-2xl font-bold tracking-wider text-rose-500 uppercase font-mono">
              ════════ Inicializando Sistema ════════
            </h1>
            {isInitializing && (
              <div className="w-5 h-5 border-2 border-rose-500 border-t-transparent rounded-full animate-spin" />
            )}
          </div>
          <p className="text-xs text-zinc-500 font-mono">
            MÓDULO NARRATIVO V5 // NAVEGADOR E DEPENDÊNCIAS
          </p>
        </div>

        {/* Logs Container */}
        <div className="h-72 overflow-y-auto bg-zinc-950/90 border border-zinc-800/50 rounded p-4 font-mono text-xs md:text-sm flex flex-col gap-2.5 scrollbar-thin scrollbar-thumb-zinc-800 scrollbar-track-transparent">
          {logs.length === 0 ? (
            <div className="text-zinc-500 animate-pulse flex items-center gap-2">
              <span className="animate-ping inline-flex h-2 w-2 rounded-full bg-zinc-600 opacity-75" />
              Aguardando conexão com o servidor...
            </div>
          ) : (
            logs.map((log) => (
              <div
                key={log.id}
                className={`flex items-start animate-fade-in py-0.5 leading-relaxed ${getStatusColor(
                  log.status
                )}`}
              >
                {getStatusIcon(log.status)}
                <span className="flex-1 whitespace-pre-wrap">{log.message}</span>
              </div>
            ))
          )}
          <div ref={logsEndRef} />
        </div>

        {/* Error State Banner & Action Buttons */}
        {error && (
          <div className="bg-rose-950/30 border border-rose-900/50 rounded-lg p-4 flex flex-col gap-3 animate-fade-in">
            <p className="text-rose-400 text-sm font-mono font-medium leading-relaxed">
              [FALHA NA DIAGNOSE] {error}
            </p>
            <div className="flex items-center gap-3">
              <button
                onClick={retry}
                className="px-4 py-2 bg-rose-700 hover:bg-rose-600 active:bg-rose-800 text-white font-semibold font-mono text-xs rounded transition-all duration-200 border border-rose-600/50 cursor-pointer shadow-[0_0_10px_rgba(190,18,60,0.2)]"
              >
                Tentar Novamente
              </button>
              <button
                onClick={() => window.location.reload()}
                className="px-4 py-2 bg-zinc-800 hover:bg-zinc-700 active:bg-zinc-900 text-zinc-300 font-semibold font-mono text-xs rounded transition-all duration-200 border border-zinc-700 cursor-pointer"
              >
                Recarregar Página
              </button>
            </div>
          </div>
        )}

        {/* Footer info */}
        <div className="flex items-center justify-between text-[10px] text-zinc-600 font-mono border-t border-zinc-800/50 pt-4">
          <span>AGENTE STORYTELLER V5</span>
          <span>ESTADO: {isInitializing ? "INICIANDO" : error ? "FALHA" : "PRONTO"}</span>
        </div>
      </div>
    </div>
  );
}
