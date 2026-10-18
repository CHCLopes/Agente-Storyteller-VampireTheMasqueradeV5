import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import './index.css';
import { SourcePlayerTrial } from './components/SourcePlayerTrial';
import { sourcePlayerTrialConfigurationFromPageUrl } from './hooks/useSourceTrialConnection';

let configuration: ReturnType<typeof sourcePlayerTrialConfigurationFromPageUrl> | null = null;
try { configuration = sourcePlayerTrialConfigurationFromPageUrl(window.location.href); } catch { /* No raw configuration in UI. */ }
createRoot(document.getElementById('root')!).render(
  <StrictMode>
    {configuration ? <SourcePlayerTrial endpoint={configuration.endpoint} provider={configuration.provider} />
      : <main className="p-6"><h1>Ensaio indisponível</h1><p>Abra o endereço fornecido pelo lançador deste ensaio local.</p></main>}
  </StrictMode>,
);
