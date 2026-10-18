# Pausa e retomada do Narrador — auditoria técnica de fechamento

## Resultado

O checkpoint está fechado com `DEC-001-B`, `DEC-002-B` e `DEC-003-B`. A tentativa
original permanece terminal, a retomada é uma nova operação referenciada, o
rascunho local continua editável com submissão e rolagem bloqueadas, e não existe
probe sintético. Após esta auditoria, o usuário respondeu “Prossiga” em
2026-09-22; essa aceitação fechou `TASK-032`, `TASK-033` e `TASK-034` e promoveu o
plano a `Completed`, sem promover Narrador, custo, fallback ou `CAP-001`.

O trabalho ocorreu no worktree
`C:\Users\skate\.codex\worktrees\b008\AgenteStoryteller`, branch
`codex/planejamento-agente-storyteller-v5`, preservando o checkout original e as
alterações acumuladas. `state/PROJECT_STATE.md` não existe. Nenhum `.env`, segredo
ou credencial foi lido, exibido ou persistido.

## Observado antes das correções

- O núcleo da cápsula, o CAS de retomada e a UI já existiam, mas o gate não era
  aplicado uniformemente a todos os dispatches nem imediatamente antes do RNG.
- H4 ainda podia degradar certas falhas de capacidade/configuração em lore
  estático e permitir continuidade indevida.
- A projeção pública não carregava revisão esperada, relógio do servidor e
  atribuição segura de origem/escopo.
- A integridade do payload persistido não era revalidada na leitura e uma lease
  `direct_resume_trial` abandonada por restart não tinha recuperação própria.
- O plano declarava implementação verificada, mas toda a tabela de tarefas e o
  antigo gate humano permaneciam sem reconciliação.

## Corrigido

- Gate local persistido antes de texto, structured output e streaming, com
  atualização por sucesso/falha e bloqueios hierárquicos por escopo opaco.
- Segunda consulta imediatamente antes do RNG regular e do reroll de Força de
  Vontade; frenzy consulta o mesmo gate antes de rolar.
- H4 propaga falha de capacidade/configuração e bloqueio do gate; não converte
  essas falhas em `static_lore` bem-sucedido.
- Falhas H6 transitórias ou de configuração preservam uma cápsula segura sem
  commit; retomadas restauram o `TurnPipelineResult` congelado e chamam somente H6.
- Operação retomada conserva `resumes_operation_id` e `capsule_id` no histórico,
  inclusive após nova falha; repetição idempotente não chama o provedor outra vez.
- Leitura verifica o hash da cápsula. Startup recupera cápsula e gate deixados em
  `direct_resume_trial` para estado seguro, sem disparo remoto.
- Projeção pública ganhou `expected_state_revision`, `server_now`,
  `rate_limit_origin`, `gate_scope` e `evidence_scope`, sem `scope_key`, contexto
  congelado, prompt, header ou segredo.
- Countdown do cliente deriva de `retry_not_before - server_now`, sem confiar no
  relógio local. A UI descreve gateway/upstream/unknown sem inventar cota ou reset.
- Dez claims concorrentes por conexões SQLite distintas resultam em exatamente
  um vencedor; o restante falha fechado por revisão/CAS.

## Matriz de evidência observável

| Requisito auditado | Evidência | Resultado |
|---|---|---|
| Gate antes de H0/H1/H4/H6 | `AvailabilityGatedGateway` e teste parametrizado de texto/structured/stream | Aprovado |
| Segunda verificação antes de RNG | `prepare_turn_pipeline(before_rng=...)`, frenzy e `test_pipeline_rechecks_gate_immediately_before_rng` | Aprovado |
| Nenhum resultado parcial por H0/H1/H4/H6/fallback após bloqueio | H4 falha fechada; pipeline não cria fato/rolagem quando bloqueado; H6 pausa antes do commit | Aprovado |
| Retomada sem novo RNG | restauração do pipeline congelado; E2E contabiliza uma única preparação | Aprovado |
| Vínculo com operação original | `resumes_operation_id`, `source_operation_id`, `capsule_id` e replay do terminal | Aprovado |
| Persistência e reconstrução | reopen SQLite, hash, snapshot congelado e recuperação de lease | Aprovado |
| Restart e reconexão | startup recovery, reidratação WebSocket e replay idempotente | Aprovado |
| Bloqueio de novas ações/rolagens | backend recusa ação com cápsula ativa; `ActionPanel` desabilita submissão/atalhos | Aprovado |
| Rascunho preservado/editável | teste de `ActionPanel` mantém texto e bloqueia envio | Aprovado |
| Cliques/solicitações concorrentes | CAS, dez conexões concorrentes e replay da operação repetida | Aprovado |
| Compatibilidade v1 | suítes WebSocket/cliente existentes e build do cliente | Aprovado |
| Matriz P0/plano/manifestos | origens gateway/upstream/unknown, ramo A `N/A`, target fixo e nenhum candidato/default/CAP-001 promovido | Aprovado |

## Verificação executada

- Backend focado final: **163 aprovados**, um aviso preexistente de depreciação
  Starlette, em 13,93 s.
- Frontend completo: **249 aprovados** em 13 arquivos.
- Lint apenas dos arquivos frontend afetados: aprovado.
- Build TypeScript/Vite: aprovado.
- `git diff --check`: sem erro de whitespace; somente avisos de conversão LF/CRLF
  em arquivos preexistentes do worktree.
- Suíte backend canônica ampla: **8.408 aprovados, 333 ignorados, 285 falhas e 61
  erros** em 1h27m41s. As falhas/erros se concentram nos experimentos históricos
  congelados de narrator record/derivation/evidence/medium/quotes/target, com erro
  observável `Final actor schema differs` e fingerprints derivados. Esse conflito
  já estava registrado na fonte de verdade e não pertence ao incremento de
  pausa/retomada; seus arquivos não foram atualizados por arrasto.

O lint frontend completo continua encontrando problemas preexistentes fora do
recorte em `useCharacterState.ts` e `useInitializationLog.ts`; os arquivos
afetados por pausa/retomada passam isoladamente.

## Limites preservados

- O gate do piloto local assume um único operador/conta configurada por runtime e
  persiste o enforcement por sessão. Coordenação multi-conta ou global entre
  campanhas não foi admitida e exigiria migração/decisão própria.
- Ausência de evidência local significa ausência de bloqueio observado; um registro
  explícito `unknown` ou `stale` falha fechado. Isso evita um probe implícito e
  preserva `DEC-003-B`.
- A auditoria é local via tentativas, cápsulas e gates persistidos; não existe
  telemetria externa nem exportador de métricas.
- Nenhum provedor, modelo, custo, retry pago, fallback ou `CAP-001` foi aprovado.
- A suíte ampla histórica permanece vermelha pelos fingerprints congelados acima;
  regravar essas evidências seria uma frente separada e não foi feito.

## Procedimento humano reproduzível — aceito em 2026-09-22

1. No worktree, com `STORYTELLER_DISABLE_DOTENV=1`, executar somente
   `tests/test_websocket_transactional.py::test_pause_reconnect_resume_and_duplicate_replay_commit_once`.
   Confirmar que passa e que o caso prova: pausa sem commit, reconexão, ação nova
   bloqueada, primeira retomada falha conservando a cápsula, segunda conclui,
   duplicata reproduz o resultado, três chamadas H6 no total e uma única preparação/RNG.
2. Em `client`, executar os testes de `NarrationPauseCard`, `ActionPanel` e
   `narrativeProtocol`. Confirmar a experiência: efeitos ainda não aplicados,
   próximo passo claro, countdown do servidor, rascunho editável, envio/atalhos
   bloqueados e nenhum controle de probe.
3. Julgar a redação, clareza, foco, teclado e conforto do cartão. Registrar
   separadamente qualquer reprovação com cenário e texto/controle afetado.
4. O usuário registrou a aceitação com “Prossiga” em 2026-09-22. O plano foi
   promovido a `Completed`; qualquer reprovação futura deve reabrir o cenário
   afetado com evidência específica, sem reclassificar silenciosamente este aceite.

## Próximo item do MVP

Após a aceitação humana, o próximo item é escolher e admitir o Narrador do MVP.
Os manifestos existentes continuam sendo snapshots de avaliação: nenhum candidato
está qualificado, nenhum default foi escolhido e `CAP-001` permanece bloqueada.
Essa decisão deve comparar qualidade e produto com os artefatos atuais; ela não
autoriza automaticamente campanha híbrida, provedor pago ou fallback.
