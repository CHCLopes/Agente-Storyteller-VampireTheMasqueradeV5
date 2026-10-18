import { useState, useCallback, useReducer } from 'react';
import { useDarkMode } from './hooks/useDarkMode';
import { useCharacterState } from './hooks/useCharacterState';
import { useWebSocket } from './hooks/useWebSocket';
import { Header } from './components/Header';
import { HUDCharacterSheet } from './components/HUDCharacterSheet';
import { NarrativeLog } from './components/NarrativeLog';
import { ActionPanel } from './components/ActionPanel';
import { NarrationPauseCard } from './components/NarrationPauseCard';
import { BottomNav } from './components/BottomNav';
import { AboutModal, HelpModal } from './components/GameModals';
import { X } from 'lucide-react';
import { InitializationPanel } from './components/InitializationPanel';
import {
  createInitialNarrativeState,
  narrativeProtocolReducer,
  sendConnectedAction,
} from './narrativeProtocol';


export default function App() {
  const { isDark, toggle: toggleTheme } = useDarkMode();
  const { sheet, relationships, updateSheetFromEvent } = useCharacterState();

  const [initializationComplete, setInitializationComplete] = useState(false);
  const [isPanelFadingOut, setIsPanelFadingOut] = useState(false);

  const handleInitializationComplete = useCallback((success: boolean) => {
    if (success) {
      setIsPanelFadingOut(true);
      setTimeout(() => {
        setInitializationComplete(true);
        setIsPanelFadingOut(false);
      }, 500);
    }
  }, []);

  // Estados dos Modais
  const [isHelpOpen, setIsHelpOpen] = useState(false);
  const [isAboutOpen, setIsAboutOpen] = useState(false);
  const [isSheetMobileOpen, setIsSheetMobileOpen] = useState(false);

  // Estados do Chat e Stream
  const [narrativeState, dispatchNarrative] = useReducer(
    narrativeProtocolReducer,
    undefined,
    () => createInitialNarrativeState(new Date().toISOString())
  );
  const { messages, currentStreamText, isLoading, narrationPause } = narrativeState;

  // Mapeia o sessionId a partir do URL (mesmo padrão do app.js legado)
  const sessionPath = window.location.pathname.split('/').pop();
  const sessionId = (sessionPath && sessionPath.length > 2) ? sessionPath : 'local_player';

  // Handler de mensagens do WebSocket
  const handleWebSocketMessage = useCallback((payload: unknown) => {
    if (typeof payload !== 'object' || payload === null || Array.isArray(payload)) return;
    const data = payload as Record<string, unknown>;

    // Se o evento for de sincronização estruturada de estado
    if (data.action === 'state_update' || data.event === 'state_update') {
      updateSheetFromEvent(data);
      if (Array.isArray(data.narrative_history)) {
        dispatchNarrative({
          type: 'hydrate_history',
          history: data.narrative_history,
          fallbackTimestamp: new Date().toISOString()
        });
      }
    } 
    // Trata mensagens de chat normais
    else if (data.action === 'chat_response') {
      dispatchNarrative({
        type: 'append_message',
        message: {
          id: `msg-${Date.now()}-${Math.random()}`,
          type: 'narrator',
          content: typeof data.message === 'string' ? data.message : '',
          timestamp: new Date().toISOString()
        },
        isLoading: false
      });
    } 
    // Trata chunks do LLM em tempo real
    else if (data.action === 'stream_start') {
      dispatchNarrative({ type: 'stream_start' });
    } else if (data.action === 'stream_chunk') {
      dispatchNarrative({ type: 'stream_chunk', chunk: data.chunk });
    } else if (data.action === 'stream_end') {
      dispatchNarrative({
        type: 'stream_end',
        operationId: data.operation_id,
        status: data.status,
        narrative: data.narrative,
        resolutionReceipt: data.resolution_receipt,
        fallbackId: `msg-${Date.now()}-${Math.random()}`,
        fallbackTimestamp: new Date().toISOString()
      });
    } else if (data.action === 'narration_paused') {
      dispatchNarrative({ type: 'narration_paused', payload: data });
    } else if (data.action === 'narration_abandoned' && data.status === 'abandoned') {
      dispatchNarrative({ type: 'clear_narration_pause' });
    }
    // Uma solicitação de esclarecimento é uma resposta terminal, não um erro.
    else if (data.action === 'clarification') {
      dispatchNarrative({
        type: 'clarification',
        message: data.message,
        operationId: data.operation_id,
        terminal: data.terminal,
        fallbackTimestamp: new Date().toISOString()
      });
    }
    // Trata erros de mecânicas ou backend
    else if (data.action === 'error') {
      dispatchNarrative({
        type: 'append_message',
        message: {
          id: typeof data.operation_id === 'string' && data.operation_id.trim()
            ? `error:${data.operation_id}`
            : `msg-${Date.now()}-${Math.random()}`,
          type: 'error',
          content: `[Erro do Sistema] ${typeof data.message === 'string' ? data.message : 'Erro desconhecido.'}`,
          timestamp: new Date().toISOString()
        },
        isLoading: false
      });
    }
  }, [updateSheetFromEvent]);

  // Hook do WebSocket
  const { isConnected, send, sendAction } = useWebSocket({
    sessionId,
    onMessage: handleWebSocketMessage
  });

  const sendNarrationCommand = (command: 'resume_narration' | 'abandon_narration') => {
    if (!narrationPause) return;
    const id = globalThis.crypto?.randomUUID?.() ?? `${Date.now()}-${Math.random()}`;
    const accepted = send({
      command,
      capsule_id: narrationPause.capsuleId,
      operation_id: `op-${id}`,
      expected_state_revision: narrationPause.expectedStateRevision,
    });
    if (accepted && command === 'resume_narration') {
      dispatchNarrative({ type: 'set_loading', isLoading: true });
    }
  };

  // Handler para enviar ações do jogador
  const handleSendAction = (action: string): boolean => {
    const submittedAction = sendConnectedAction(action, sendAction);
    if (!submittedAction) return false;

    // Adiciona a ação do jogador localmente no log
    dispatchNarrative({
      type: 'append_message',
      message: {
        id: `msg-${Date.now()}-${Math.random()}`,
        type: 'player',
        content: submittedAction,
        timestamp: new Date().toISOString()
      }
    });

    dispatchNarrative({ type: 'set_loading', isLoading: true });
    return true;
  };

  // Handler para exibir o modal de consultas de relacionamento
  const handleConsultRelation = (title: string, desc: string) => {
    dispatchNarrative({
      type: 'append_message',
      message: {
        id: `msg-${Date.now()}-${Math.random()}`,
        type: 'system',
        content: `[Consulta] Relacionamento com ${title}: ${desc}`,
        timestamp: new Date().toISOString()
      }
    });
  };

  if (!initializationComplete) {
    return (
      <div className={isPanelFadingOut ? 'animate-fade-out pointer-events-none' : ''}>
        <InitializationPanel onInitializationComplete={handleInitializationComplete} />
      </div>
    );
  }

  return (
    <div className="game-shell font-sans overflow-hidden flex flex-col relative select-none animate-fade-in">
      {/* Noise Overlay */}
      <div className="noise-overlay fixed inset-0 pointer-events-none z-50 opacity-100" aria-hidden="true" />

      {/* Header */}
      <Header
        isConnected={isConnected}
        isDark={isDark}
        onToggleTheme={toggleTheme}
        onOpenHelp={() => setIsHelpOpen(true)}
        onOpenAbout={() => setIsAboutOpen(true)}
        sessionId={sessionId}
      />

      {/* Layout Principal */}
      <div className="min-h-0 min-w-0 flex-1 flex pt-14 pb-14 lg:pb-0 overflow-hidden">
        {/* Lado Esquerdo / Centro: Chat Narrativo (2/3 de largura em desktop) */}
        <div className="min-h-0 min-w-0 flex-1 flex flex-col overflow-hidden border-r border-zinc-900/50 dark:border-zinc-900/50 light:border-v5light-border/40">
          <NarrativeLog messages={messages} currentStreamText={currentStreamText} />
          {narrationPause && (
            <NarrationPauseCard
              pause={narrationPause}
              connected={isConnected}
              busy={isLoading}
              onResume={() => sendNarrationCommand('resume_narration')}
              onAbandon={() => {
                if (window.confirm('Descartar esta ação? A resolução preservada não será aplicada.')) {
                  sendNarrationCommand('abandon_narration');
                }
              }}
            />
          )}
          <ActionPanel
            sheet={sheet}
            relationships={relationships}
            onSendAction={handleSendAction}
            onConsultRelation={handleConsultRelation}
            disabled={isLoading || !isConnected}
            submissionBlocked={narrationPause !== null}
          />
        </div>

        {/* Lado Direito: HUD Ficha do Personagem (1/3 de largura em desktop) */}
        <aside className="hidden lg:block w-[360px] xl:w-[400px] min-h-0 shrink-0 overflow-y-auto overscroll-contain p-6 bg-v5-card/30 dark:bg-v5-card/30 light:bg-v5light-card/40">
          <HUDCharacterSheet sheet={sheet} />
        </aside>
      </div>

      {/* HUD Ficha Mobile Overlay (Slide-up) */}
      <div 
        id="hud-container"
        className={`lg:hidden fixed bottom-14 left-0 w-full h-[70vh] bg-v5-card dark:bg-v5-card light:bg-v5light-card border-t border-zinc-800 dark:border-zinc-800 light:border-v5light-border rounded-t-xl z-40 p-5 overflow-y-auto shadow-2xl transition-transform duration-300 ${
          isSheetMobileOpen ? 'translate-y-0' : 'translate-y-[calc(100%+3.5rem)] pointer-events-none'
        }`}
      >
        <div className="flex justify-between items-center mb-4 border-b border-zinc-800 dark:border-zinc-800 light:border-v5light-border pb-2">
          <span className="text-[10px] font-bold tracking-widest text-secondary block uppercase" style={{ color: 'var(--text-secondary)' }}>
            Ficha de Personagem
          </span>
          <button 
            id="btnCloseSheet"
            onClick={() => setIsSheetMobileOpen(false)}
            className="p-1 rounded hover:bg-zinc-800 dark:hover:bg-zinc-800 light:hover:bg-v5light-border/40 transition-colors"
            aria-label="Fechar ficha"
          >
            <X className="w-4 h-4 text-primary" style={{ color: 'var(--text-primary)' }} />
          </button>
        </div>
        <HUDCharacterSheet sheet={sheet} />
      </div>

      {/* Mobile Overlay Background */}
      {isSheetMobileOpen && (
        <div 
          id="sheet-overlay"
          onClick={() => setIsSheetMobileOpen(false)}
          className="lg:hidden fixed inset-0 bg-black/60 z-30 transition-opacity"
        />
      )}

      {/* Bottom Nav (Mobile Only) */}
      <BottomNav
        onToggleSheet={() => setIsSheetMobileOpen(prev => !prev)}
        onOpenHelp={() => setIsHelpOpen(true)}
        onOpenAbout={() => setIsAboutOpen(true)}
      />

      {/* Modais do Jogo */}
      <AboutModal isOpen={isAboutOpen} onClose={() => setIsAboutOpen(false)} />
      <HelpModal isOpen={isHelpOpen} onClose={() => setIsHelpOpen(false)} />
    </div>
  );
}
