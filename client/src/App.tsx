import { useState, useCallback } from 'react';
import { useDarkMode } from './hooks/useDarkMode';
import { useCharacterState } from './hooks/useCharacterState';
import { useWebSocket } from './hooks/useWebSocket';
import { Header } from './components/Header';
import { HUDCharacterSheet } from './components/HUDCharacterSheet';
import { NarrativeLog } from './components/NarrativeLog';
import { ActionPanel } from './components/ActionPanel';
import { BottomNav } from './components/BottomNav';
import { AboutModal, HelpModal } from './components/GameModals';
import type { NarrativeMessage } from './types/narrative';
import { X } from 'lucide-react';

export default function App() {
  const { isDark, toggle: toggleTheme } = useDarkMode();
  const { sheet, updateSheetFromEvent } = useCharacterState();

  // Estados dos Modais
  const [isHelpOpen, setIsHelpOpen] = useState(false);
  const [isAboutOpen, setIsAboutOpen] = useState(false);
  const [isSheetMobileOpen, setIsSheetMobileOpen] = useState(false);

  // Estados do Chat e Stream
  const [messages, setMessages] = useState<NarrativeMessage[]>([
    {
      id: 'init-sys',
      type: 'system',
      content: '[Sistema] Sistema Pronto. Boa Caçada! 🦇',
      timestamp: new Date().toISOString()
    }
  ]);
  const [currentStreamText, setCurrentStreamText] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  // Mapeia o sessionId a partir do URL (mesmo padrão do app.js legado)
  const sessionPath = window.location.pathname.split('/').pop();
  const sessionId = (sessionPath && sessionPath.length > 2) ? sessionPath : 'local_player';

  // Handler de mensagens do WebSocket
  const handleWebSocketMessage = useCallback((data: any) => {
    if (!data) return;

    // Se o evento for de sincronização estruturada de estado
    if (data.action === 'state_update' || data.event === 'state_update') {
      updateSheetFromEvent(data);
    } 
    // Trata mensagens de chat normais
    else if (data.action === 'chat_response') {
      setMessages(prev => [
        ...prev,
        {
          id: `msg-${Date.now()}-${Math.random()}`,
          type: 'narrator',
          content: data.message,
          timestamp: new Date().toISOString()
        }
      ]);
      setIsLoading(false);
    } 
    // Trata chunks do LLM em tempo real
    else if (data.action === 'stream_start') {
      setCurrentStreamText('');
      setIsLoading(true);
    } else if (data.action === 'stream_chunk') {
      if (data.chunk) {
        setCurrentStreamText(prev => prev + data.chunk);
      }
    } else if (data.action === 'stream_end') {
      setCurrentStreamText(prev => {
        if (prev.trim()) {
          setMessages(msgs => [
            ...msgs,
            {
              id: `msg-${Date.now()}-${Math.random()}`,
              type: 'narrator',
              content: prev,
              timestamp: new Date().toISOString()
            }
          ]);
        }
        return '';
      });
      setIsLoading(false);
    } 
    // Trata erros de mecânicas ou backend
    else if (data.action === 'error') {
      setMessages(prev => [
        ...prev,
        {
          id: `msg-${Date.now()}-${Math.random()}`,
          type: 'error',
          content: `[Erro do Sistema] ${data.message}`,
          timestamp: new Date().toISOString()
        }
      ]);
      setIsLoading(false);
    }
  }, [updateSheetFromEvent]);

  // Hook do WebSocket
  const { isConnected, send } = useWebSocket({
    sessionId,
    onMessage: handleWebSocketMessage
  });

  // Handler para enviar ações do jogador
  const handleSendAction = (action: string) => {
    if (!action.trim()) return;

    // Adiciona a ação do jogador localmente no log
    setMessages(prev => [
      ...prev,
      {
        id: `msg-${Date.now()}-${Math.random()}`,
        type: 'player',
        content: action,
        timestamp: new Date().toISOString()
      }
    ]);

    // Envia para o backend pelo canal WebSocket
    setIsLoading(true);
    send(action);
  };

  // Handler para exibir o modal de consultas de relacionamento
  const handleConsultRelation = (title: string, desc: string) => {
    setMessages(prev => [
      ...prev,
      {
        id: `msg-${Date.now()}-${Math.random()}`,
        type: 'system',
        content: `[Consulta] Relacionamento com ${title}: ${desc}`,
        timestamp: new Date().toISOString()
      }
    ]);
  };

  return (
    <div className="min-h-screen font-sans overflow-hidden flex flex-col relative select-none">
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
      <div className="flex-1 flex pt-14 pb-14 lg:pb-0 overflow-hidden">
        {/* Lado Esquerdo / Centro: Chat Narrativo (2/3 de largura em desktop) */}
        <div className="flex-1 flex flex-col h-full overflow-hidden border-r border-zinc-900/50 dark:border-zinc-900/50 light:border-v5light-border/40">
          <NarrativeLog messages={messages} currentStreamText={currentStreamText} />
          <ActionPanel
            sheet={sheet}
            onSendAction={handleSendAction}
            onConsultRelation={handleConsultRelation}
            disabled={isLoading}
          />
        </div>

        {/* Lado Direito: HUD Ficha do Personagem (1/3 de largura em desktop) */}
        <aside className="hidden lg:block w-[360px] xl:w-[400px] h-full overflow-y-auto p-6 bg-v5-card/30 dark:bg-v5-card/30 light:bg-v5light-card/40">
          <HUDCharacterSheet sheet={sheet} />
        </aside>
      </div>

      {/* HUD Ficha Mobile Overlay (Slide-up) */}
      <div 
        id="hud-container"
        className={`lg:hidden fixed bottom-14 left-0 w-full h-[70vh] bg-v5-card dark:bg-v5-card light:bg-v5light-card border-t border-zinc-800 dark:border-zinc-800 light:border-v5light-border rounded-t-xl z-40 p-5 overflow-y-auto shadow-2xl transition-transform duration-300 ${
          isSheetMobileOpen ? 'translate-y-0' : 'translate-y-full'
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
