import { useEffect, useRef, useState } from 'react';
import type { Dispatch, FormEvent } from 'react';
import {
  isSourceTerminal,
  sourceNarrativeReducer,
  sourceOperationLabel,
} from '../sourceNarrativeProtocol';
import type {
  SourceNarrativeAction,
  SourceNarrativeState,
  SourcePlayerAction,
} from '../sourceNarrativeProtocol';

export interface SourceTrialViewProps {
  state: SourceNarrativeState;
  dispatch: Dispatch<SourceNarrativeAction>;
  connected: boolean;
  actionScope?: 'ordinary' | 'dialogue_wait';
  dialogueTarget?: string;
  sourceDescription?: string;
  submissionAllowed?: boolean;
  submissionNotice?: string;
  createOperationId: () => string;
  onSubmit: (action: SourcePlayerAction) => void | Promise<void>;
  onQuery: (operationId: string) => void | Promise<void>;
}

type DialogueMode = 'talk' | 'wait';
type DialogueComposition = { ok: true; value: string } | { ok: false; message: string };

/** Compose only the existing declared-action envelope; never interpret the speech.
 * Validation happens before creating an operation identity. Literal speech is
 * unchanged, including accents, spacing and embedded quote marks.
 */
function composeDialogueInput(mode: DialogueMode, target: string | undefined, speech: string): DialogueComposition {
  if (mode === 'wait') return { ok: true, value: 'Aguardo.' };
  const validCharacters = (value: string) => !value.includes('\0') && Array.from(value).every(point => {
    const code = point.codePointAt(0)!;
    return code < 0xd800 || code > 0xdfff;
  });
  if (!target || target.trim() !== target || !validCharacters(target)) {
    return { ok: false, message: 'O personagem da conversa não pôde ser confirmado. Sua fala foi conservada.' };
  }
  if (!validCharacters(speech)) {
    return { ok: false, message: 'A fala contém um caractere que não pode ser enviado. Seu texto foi conservado.' };
  }
  // The backend removes combining marks and normalizes whitespace for matching.
  // Check that a meaningful quote remains; do not normalize the transmitted text.
  const matchingSpeech = speech.normalize('NFKD').replace(/\p{M}/gu, '');
  const hasSpeech = Array.from(matchingSpeech).some(point => {
    const code = point.codePointAt(0)!;
    return !/\s/u.test(point) && !(code >= 0x1c && code <= 0x1f) && code !== 0x85;
  });
  if (!hasSpeech) {
    return { ok: false, message: 'Escreva o que você quer dizer ao personagem antes de enviar.' };
  }
  const delimiters = [['"', '"'], ['“', '”'], ['«', '»']] as const;
  const quote = delimiters.find(([open, close]) => !matchingSpeech.includes(open) && !matchingSpeech.includes(close));
  if (!quote) {
    return { ok: false, message: 'Não foi possível enquadrar a fala sem alterar suas aspas. Ajuste as aspas para enviar; seu texto foi conservado.' };
  }
  const value = `Digo a ${target}: ${quote[0]}${speech}${quote[1]}`;
  if (Array.from(value).length > 500) {
    return { ok: false, message: 'Esta fala ultrapassa o limite deste ensaio. Encurte-a para enviar; seu texto foi conservado.' };
  }
  return { ok: true, value };
}

/** Unmounted presentation only. A future binding owns transport and initial/query reads.
 * Keep reducer state above this view during reconnection. No browser persistence or
 * restoration after reload is implemented; no effect below sends a command.
 */
export function SourceTrialView({ state, dispatch, connected, createOperationId, onSubmit, onQuery,
  actionScope = 'ordinary', dialogueTarget, sourceDescription, submissionAllowed = true, submissionNotice }: SourceTrialViewProps) {
  const logRef = useRef<HTMLDivElement>(null);
  const submittingRef = useRef(false);
  const [localFailure, setLocalFailure] = useState(false);
  const [dialogueMode, setDialogueMode] = useState<DialogueMode>('talk');
  const [dialogueDraft, setDialogueDraft] = useState('');
  const [compositionError, setCompositionError] = useState<string | null>(null);
  const dialogueControls = actionScope === 'dialogue_wait';
  const current = state.operations.find(item => item.operationId === state.currentOperationId);
  const maySubmit = submissionAllowed && connected && state.briefing !== null && state.currentOperationId === null && !state.problem;

  useEffect(() => {
    if (logRef.current) logRef.current.scrollTop = logRef.current.scrollHeight;
  }, [state.operations]);

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!maySubmit || submittingRef.current) return;
    const composed = dialogueControls ? composeDialogueInput(dialogueMode, dialogueTarget, dialogueDraft) : null;
    if (composed && !composed.ok) {
      setCompositionError(composed.message);
      return;
    }
    setCompositionError(null);
    let action: SourcePlayerAction;
    try {
      action = Object.freeze({ operation_id: createOperationId(), player_input: composed?.value ?? state.draft });
    } catch {
      setLocalFailure(true);
      return;
    }
    // Register identity and text before handing off, including ambiguous send failures.
    const submission: SourceNarrativeAction = { type: 'submitted', action };
    if (sourceNarrativeReducer(state, submission).problem) {
      setLocalFailure(true);
      return;
    }
    submittingRef.current = true;
    setLocalFailure(false);
    dispatch(submission);
    try {
      await onSubmit(action);
    } catch {
      dispatch({ type: 'delivery_uncertain', operationId: action.operation_id });
    }
  };

  const query = async (operationId: string) => {
    if (!connected) return;
    try {
      await onQuery(operationId);
    } catch {
      dispatch({ type: 'query_failed' });
    }
  };

  const newAction = () => {
    if (!submissionAllowed || !current || !isSourceTerminal(current) || state.problem) return;
    submittingRef.current = false;
    setLocalFailure(false);
    setCompositionError(null);
    setDialogueMode('talk');
    setDialogueDraft('');
    dispatch({ type: 'new_action' });
  };

  return (
    <section className="game-shell min-h-0 min-w-0 overflow-hidden flex flex-col font-sans" aria-label="Ensaio de cena B">
      <header className="shrink-0 border-b border-zinc-800 dark:border-zinc-800 light:border-v5light-border px-4 py-3 flex items-center justify-between gap-4">
        <h1 className="font-serif text-xl" style={{ color: 'var(--text-primary)' }}>Ensaio de cena</h1>
        <span role="status" aria-label="Conexão" className="text-sm" style={{ color: 'var(--text-secondary)' }}>
          {connected ? 'Conectado' : 'Desconectado'}
        </span>
      </header>
      <div className="min-h-0 min-w-0 flex-1 flex flex-col lg:flex-row overflow-hidden">
        <aside aria-label="Cena e estado da ação" className="order-first lg:order-last max-h-[35%] lg:max-h-none lg:w-[360px] xl:w-[400px] min-h-0 shrink-0 flex flex-col overflow-hidden border-b lg:border-b-0 lg:border-l border-zinc-800 dark:border-zinc-800 light:border-v5light-border p-4 gap-4">
          <section aria-labelledby="source-briefing-heading" tabIndex={0} className="min-h-0 flex-1 overflow-y-auto overscroll-contain">
            <h2 id="source-briefing-heading" className="font-serif text-lg mb-2">Introdução da cena</h2>
            {sourceDescription && <p className="text-sm mb-4">{sourceDescription}</p>}
            <p className="whitespace-pre-wrap break-words text-sm" style={{ color: 'var(--text-secondary)' }}>
              {state.briefing ?? 'Aguardando a introdução da cena.'}
            </p>
            <p className="mt-4 text-xs" style={{ color: 'var(--text-secondary)' }}>
              A introdução descreve o preparo deste ensaio. Este painel não apresenta uma ficha atualizada do personagem.
            </p>
            <section id="source-action-guidance" aria-labelledby="source-action-guidance-heading" className="mt-4 text-sm space-y-2">
              <h3 id="source-action-guidance-heading" className="font-medium">{dialogueControls ? 'Como participar' : 'Como escrever sua ação'}</h3>
              {dialogueControls ? <>
                <p>Escolha Conversar com {dialogueTarget ?? 'o personagem'} e escreva apenas o que deseja dizer. Por exemplo: “{dialogueTarget ?? 'Olá'}, me fale sobre este lugar”. Você não precisa escrever um comando.</p>
                <p>Para esperar a reação da cena, escolha Aguardar e confirme a espera. Alternar entre as opções conserva sua fala enquanto você não envia.</p>
                <p>Conversa e espera não rolam dados. Investigação está fora deste recorte, mesmo que citada no preparo geral da cena.</p>
                <p>Envie uma fala ou confirme uma espera por vez. Sua fala será preservada no registro enviado. Uma indisponibilidade encerra novos envios; consulte o estado se a sessão ainda estiver ativa, sem reenviar.</p>
              </> : <>
                <p>Use uma ação por envio, nestes formatos:</p>
                <ul className="list-disc pl-4 space-y-2" style={{ color: 'var(--text-secondary)' }}>
                  <li>Aguardar: <code>Aguardo.</code></li>
                  <li>Conversar: <code>Falo com NOME.</code> ou <code>Pergunto a NOME: "sua pergunta".</code> Troque NOME pelo nome de um personagem presente na introdução.</li>
                  <li>Investigar o local: <code>Investigo o ambiente.</code></li>
                </ul>
                <p>Aguardar e conversar não rolam dados. Investigar faz um teste do personagem.</p>
                <p>Envie apenas uma ação por vez. Textos que não forem reconhecidos ficam sem execução; seu texto é conservado. Mesmo nestes formatos, o teste depende das condições da cena e do personagem.</p>
              </>}
            </section>
          </section>
          <section aria-labelledby="source-operation-heading" className="shrink-0">
            <h2 id="source-operation-heading" className="font-serif text-lg mb-2">Sua ação</h2>
            <p role="status" aria-label="Estado da ação" className="text-sm">
              {current ? sourceOperationLabel(current) : 'Nenhuma ação em andamento.'}
            </p>
          </section>
        </aside>
        <div className="min-h-0 min-w-0 flex-1 flex flex-col overflow-hidden">
          <div ref={logRef} id="narrative-log" role="log" tabIndex={0} aria-label="Histórico da cena"
            className="min-h-0 min-w-0 flex-1 overflow-y-auto overscroll-contain p-4 md:p-6 space-y-5 select-text">
            {!state.operations.length && <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>Leia a introdução e escolha sua ação.</p>}
            {state.operations.map(operation => (
              <article key={operation.operationId} data-operation-id={operation.operationId} className="space-y-3">
                {operation.playerInput !== null && <p className="whitespace-pre-wrap break-words font-sans text-sm bg-zinc-950/40 dark:bg-zinc-950/40 light:bg-v5light-card border border-zinc-800 dark:border-zinc-800 light:border-v5light-border p-3 rounded text-right ml-auto max-w-xl">{operation.playerInput}</p>}
                {operation.lastEvent?.event === 'narrative_complete' && (
                  <>
                    <p className="font-serif text-lg leading-relaxed border-l-2 border-v5-crimson dark:border-v5-crimson light:border-v5light-earth pl-4 py-1 text-left break-words">{operation.lastEvent.n}</p>
                    <p className="font-sans text-sm whitespace-pre-wrap break-words" aria-label="Pergunta do narrador">{operation.lastEvent.q}</p>
                  </>
                )}
                <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>{sourceOperationLabel(operation)}</p>
                <button type="button" disabled={!connected} onClick={() => void query(operation.operationId)}
                  className="text-sm underline disabled:opacity-40 disabled:cursor-not-allowed">Consultar estado da ação</button>
              </article>
            ))}
          </div>
          <div id="action-panel-container" className="shrink-0 border-t border-zinc-800 dark:border-zinc-800 light:border-v5light-border p-4 space-y-3">
            {state.problem && <p role="alert">Uma atualização não pôde ser confirmada. Sua ação e a narrativa foram conservadas. Novos envios estão bloqueados.</p>}
            {state.queryFailed && <p role="alert">Não foi possível consultar o estado. Sua ação e o texto confirmado foram conservados.</p>}
            {localFailure && <p role="alert">Não foi possível preparar o envio. Confira a ação, sem espaços no início ou no fim; seu texto foi conservado.</p>}
            {compositionError && <p id="source-dialogue-error" role="alert">{compositionError}</p>}
            {submissionNotice && <p id="source-submission-notice" role="status" aria-label="Disponibilidade de envio" className="text-sm">{submissionNotice}</p>}
            <form onSubmit={event => void submit(event)} className="space-y-2">
              {dialogueControls && <fieldset disabled={!maySubmit} className="flex flex-wrap gap-x-4 gap-y-1 text-sm">
                <legend className="sr-only">Escolha como participar</legend>
                <label className="flex items-center gap-2"><input type="radio" name="source-dialogue-mode" value="talk"
                  checked={dialogueMode === 'talk'} onChange={() => { if (maySubmit) { setDialogueMode('talk'); setCompositionError(null); } }} />Conversar com {dialogueTarget ?? 'o personagem'}</label>
                <label className="flex items-center gap-2"><input type="radio" name="source-dialogue-mode" value="wait"
                  checked={dialogueMode === 'wait'} onChange={() => { if (maySubmit) { setDialogueMode('wait'); setCompositionError(null); } }} />Aguardar</label>
              </fieldset>}
              <div className="flex gap-2">
                <textarea value={dialogueControls ? dialogueDraft : state.draft} onChange={event => {
                  setCompositionError(null);
                  if (dialogueControls) setDialogueDraft(event.target.value);
                  else dispatch({ type: 'edit_draft', text: event.target.value });
                }}
                  disabled={!maySubmit || (dialogueControls && dialogueMode === 'wait')} maxLength={dialogueControls ? undefined : 1000} rows={2}
                  aria-label={dialogueControls ? `Sua fala para ${dialogueTarget ?? 'o personagem'}` : 'Ação para esta cena'}
                  aria-describedby={['source-action-guidance', submissionNotice && 'source-submission-notice', compositionError && 'source-dialogue-error'].filter(Boolean).join(' ')}
                  aria-invalid={compositionError ? true : undefined}
                  placeholder={dialogueControls ? 'Escreva o que você quer dizer.' : 'Descreva sua ação nesta cena.'}
                  className="flex-1 min-w-0 min-h-[44px] max-h-[120px] resize-none bg-zinc-950/40 dark:bg-zinc-950/40 light:bg-v5light-card border border-zinc-800 dark:border-zinc-800 light:border-v5light-border rounded p-2 text-sm" />
                <button type="submit" disabled={!maySubmit || (!dialogueControls && !state.draft)} className="rounded px-4 bg-v5-crimson dark:bg-v5-crimson light:bg-v5light-earth text-white disabled:opacity-40 disabled:cursor-not-allowed">
                  {dialogueControls ? dialogueMode === 'wait' ? 'Confirmar espera' : 'Enviar fala' : 'Enviar ação'}
                </button>
              </div>
            </form>
            {current && isSourceTerminal(current) && <button type="button" disabled={!submissionAllowed || !!state.problem} onClick={newAction}
              className="text-sm underline disabled:opacity-40">Escrever uma nova ação</button>}
            <p className="text-xs" style={{ color: 'var(--text-secondary)' }}>
              Uma consulta não reenvia a ação. Ao recarregar esta página, a cópia local do texto da ação e sua identificação são perdidas.
            </p>
          </div>
        </div>
      </div>
    </section>
  );
}
