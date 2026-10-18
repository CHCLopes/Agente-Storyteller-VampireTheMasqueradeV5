import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import './index.css';
import { SourceTrialView } from './components/SourceTrialView';
import { sourceTrialEndpointFromPageUrl, useSourceTrialConnection } from './hooks/useSourceTrialConnection';

export function TechnicalPreview({ endpoint }: { endpoint: string }) {
  const controller = useSourceTrialConnection(endpoint);
  return <main className="source-trial-preview">
    <header className="shrink-0 p-3 border-b border-zinc-700 space-y-2">
      <p>Prévia técnica local com respostas fixas. Esta página verifica a interface e a conexão; não representa um jogo aprovado.</p>
      <div className="flex gap-4">
        <button type="button" className="underline disabled:opacity-40" onClick={controller.connect}
          disabled={controller.connected || controller.connecting}>{controller.connecting ? 'Conectando…' : 'Conectar à prévia'}</button>
        <button type="button" className="underline disabled:opacity-40" onClick={controller.disconnect}
          disabled={!controller.connected && !controller.connecting}>Desconectar</button>
      </div>
      {controller.connectionFailed && <p role="alert">Não foi possível manter a conexão da prévia. Os dados desta página foram conservados.</p>}
    </header>
    <div className="source-trial-content">
      <SourceTrialView state={controller.state} dispatch={controller.dispatch} connected={controller.connected}
        createOperationId={() => crypto.randomUUID()} onSubmit={controller.onSubmit} onQuery={controller.onQuery} />
    </div>
  </main>;
}

let endpoint: string | null = null;
try { endpoint = sourceTrialEndpointFromPageUrl(window.location.href); } catch { /* Closed configuration error. */ }
createRoot(document.getElementById('root')!).render(<StrictMode>
  {endpoint ? <TechnicalPreview endpoint={endpoint} /> : <main className="p-6">
    <h1>Prévia técnica indisponível</h1>
    <p>Abra o endereço informado pelo lançador local da prévia. Nenhuma conexão foi iniciada.</p>
  </main>}
</StrictMode>);
