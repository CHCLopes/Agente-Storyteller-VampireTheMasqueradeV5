import { useCallback, useEffect, useState } from 'react';
import { useSourceTrialConnection } from '../hooks/useSourceTrialConnection';
import type { SourcePlayerTrialProvider, SourceSocketFactory } from '../hooks/useSourceTrialConnection';
import { isSourceTerminal } from '../sourceNarrativeProtocol';
import { SourceTrialView } from './SourceTrialView';

interface SourcePlayerTrialProps {
  endpoint: string;
  createSocket?: SourceSocketFactory;
  createOperationId?: () => string;
  provider?: SourcePlayerTrialProvider;
}

const randomOperationId = () => crypto.randomUUID();

/** Isolated presentation gate. The server alone owns call count and HTTP pacing. */
export function SourcePlayerTrial({ endpoint, createSocket, createOperationId = randomOperationId,
  provider = 'groq' }: SourcePlayerTrialProps) {
  const [admissionsClosed, setAdmissionsClosed] = useState(false);
  const [readyFor, setReadyFor] = useState<string | null>(null);
  const closeAdmissions = useCallback(() => setAdmissionsClosed(true), []);
  const controller = useSourceTrialConnection(endpoint, createSocket, closeAdmissions);
  // Stable across duplicate terminal/query frames; counts no provider usage.
  const terminalKey = JSON.stringify(controller.state.operations.filter(isSourceTerminal).map(item => item.operationId));
  const submissionAllowed = controller.connected && !admissionsClosed
    && (provider === 'luna' || readyFor === terminalKey);

  useEffect(() => {
    if (!controller.connected || admissionsClosed || provider === 'luna') return;
    const timer = window.setTimeout(() => setReadyFor(terminalKey), 60_000);
    return () => window.clearTimeout(timer);
  }, [controller.connected, admissionsClosed, terminalKey, provider]);

  const connect = () => {
    setReadyFor(null);
    controller.connect();
  };
  const notice = admissionsClosed
    ? 'Novos envios foram encerrados após uma indisponibilidade. Sua ação foi conservada. Se a sessão ainda estiver ativa, consulte o estado sem reenviar.'
    : !controller.connected
      ? 'Desconectado. Enquanto a sessão estiver ativa, conecte para ler a cena ou consultar a ação conservada, sem gerar narrativa.'
      : !submissionAllowed
        ? 'Intervalo de segurança em andamento: até 60 segundos após a conexão ou um novo resultado. Consultar o estado continua disponível.'
        : provider === 'luna'
          ? 'Sem espera artificial. Uma ação por vez; o servidor verifica os limites antes de cada envio.'
          : 'Intervalo local concluído. O servidor ainda verifica os limites antes de aceitar uma nova ação.';
  const providerLabel = provider === 'luna' ? 'Luna via OpenAI' : 'Qwen via Groq';

  return (
    <main className="source-player-trial">
      <header className="shrink-0 border-b border-zinc-800 p-3 text-sm space-y-2">
        <p>Ensaio experimental · {providerLabel}</p>
        <div className="flex gap-4">
          <button type="button" onClick={connect} disabled={controller.connected || controller.connecting}
            className="underline disabled:opacity-40">Conectar ao ensaio</button>
          <button type="button" onClick={controller.disconnect} disabled={!controller.connected && !controller.connecting}
            className="underline disabled:opacity-40">Desconectar</button>
        </div>
        {controller.connectionFailed && <p role="alert">A conexão foi interrompida. Se a sessão ainda estiver ativa, reconecte para consultar o estado, sem reenviar sua ação.</p>}
      </header>
      <div className="source-player-trial-content">
        <SourceTrialView state={controller.state} dispatch={controller.dispatch} connected={controller.connected}
          createOperationId={createOperationId} onSubmit={controller.onSubmit} onQuery={controller.onQuery}
          actionScope="dialogue_wait" dialogueTarget="Mara" submissionAllowed={submissionAllowed} submissionNotice={notice}
          sourceDescription={`A introdução é autorada; as continuações usam ${providerLabel}. Use somente ficção e personagens sintéticos, sem dados pessoais ou de campanhas. Este ensaio permite até quatro chamadas de geração, sem garantir quatro respostas confirmadas. O servidor pode encerrar novos envios antes desse limite. Recarregar a página não reinicia esse limite. O ensaio para automaticamente no limite ou em erro operacional. Consultas e reconexões dependem de a sessão ainda estar ativa. Relançar inicia outra sessão; não retoma nem reenvia esta ação. É uma observação experimental, sem aprovação do jogo ou do narrador.`} />
      </div>
    </main>
  );
}
