import { useEffect, useState } from 'react';
import type { NarrationPause } from '../narrativeProtocol';

interface Props {
  pause: NarrationPause;
  connected: boolean;
  busy: boolean;
  onResume: () => void;
  onAbandon: () => void;
}

export function NarrationPauseCard({ pause, connected, busy, onResume, onAbandon }: Props) {
  const reportedWaitMs = (() => {
    if (!pause.retryNotBefore || !pause.serverNow) return 0;
    const retryAt = Date.parse(pause.retryNotBefore);
    const serverAt = Date.parse(pause.serverNow);
    return Number.isFinite(retryAt) && Number.isFinite(serverAt)
      ? Math.max(0, retryAt - serverAt) : 0;
  })();
  const [remainingMs, setRemainingMs] = useState(reportedWaitMs);
  useEffect(() => {
    const resetTimer = window.setTimeout(() => setRemainingMs(reportedWaitMs), 0);
    if (reportedWaitMs <= 0) return () => window.clearTimeout(resetTimer);
    const localDeadline = Date.now() + reportedWaitMs;
    const timer = window.setInterval(() => {
      const next = Math.max(0, localDeadline - Date.now());
      setRemainingMs(next);
      if (next === 0) window.clearInterval(timer);
    }, 250);
    return () => {
      window.clearTimeout(resetTimer);
      window.clearInterval(timer);
    };
  }, [pause.retryNotBefore, pause.serverNow, reportedWaitMs]);
  const waitActive = remainingMs > 0;
  const rateLimitLabel = pause.rateLimitOrigin === 'gateway'
    ? 'Limite informado pelo gateway.'
    : pause.rateLimitOrigin === 'upstream'
      ? 'Limite informado pelo provedor do modelo.'
      : pause.rateLimitOrigin === 'unknown'
        ? 'A origem do limite não foi confirmada.'
        : null;
  return (
    <section className="mx-4 md:mx-6 mb-3 rounded border border-amber-700 bg-amber-950/30 p-4 text-sm"
      aria-live="polite" aria-label="Narração pausada">
      <h2 className="font-bold text-amber-200">Narração pausada</h2>
      <p className="mt-2 text-primary">Sua ação foi preservada. Se houve rolagem, os dados não serão lançados novamente.</p>
      <p className="mt-2 text-secondary"><strong>Ação:</strong> {pause.actionSummary}</p>
      {pause.resolutionSummary && <p className="mt-1 text-secondary"><strong>Resolução preservada:</strong> {pause.resolutionSummary}</p>}
      <p className="mt-2 text-secondary">{pause.safeMessage} Os efeitos ainda não foram aplicados à campanha.</p>
      {rateLimitLabel && <p className="mt-2 text-secondary">{rateLimitLabel}</p>}
      {waitActive && <p className="mt-2 text-amber-200">Disponível em cerca de {Math.ceil(remainingMs / 1000)} s, conforme o relógio do servidor.</p>}
      <div className="mt-3 flex flex-wrap gap-2">
        <button type="button" onClick={onResume}
          disabled={!connected || busy || waitActive || !pause.allowedActions.includes('resume')}
          className="rounded bg-v5-crimson px-3 py-2 text-white disabled:opacity-40">
          Retomar narração
        </button>
        <button type="button" onClick={onAbandon}
          disabled={!connected || busy || !pause.allowedActions.includes('abandon')}
          className="rounded border border-amber-700 px-3 py-2 text-amber-100 disabled:opacity-40">
          Descartar ação
        </button>
      </div>
    </section>
  );
}
