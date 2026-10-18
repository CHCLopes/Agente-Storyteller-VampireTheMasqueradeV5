# HYP-007-L3 — estado e prompt v2, prontidão

Data: 03/10/2026. Aprovação humana: "Aprovado. Continue", em resposta à
proposta de até 17 chamadas Luna low e teto estimado adicional USD 0,15.
Worktree `b008`, branch `codex/planejamento-agente-storyteller-v5`.

## Configuração e hipótese prospectiva

Avaliar novamente os oito percursos causais de Registro em risco com posição
canônica v2 antes/depois e prompt v2 explicitando a faixa existente de 30–150
palavras. Pergunta: o modelo realiza os efeitos, mantém origem/destino do
registro e responde pertinentemente ao jogador ao longo dos percursos?
Não pressupor que as correções resolvem a fidelidade ou tornam Luna elegível.

- Alvo explícito `gpt-5.6-luna`, esforço `low`, Responses API, `store=false`.
- Até 17 chamadas, 768 tokens de saída por chamada, deadline 60 s, corpo
  máximo 20.000 bytes. Sem cooldown artificial, retry, reparo ou fallback.
- Teto estimado adicional USD 0,15; guard local antes de cada envio e uso
  reportado após cada resposta. Parar na primeira reprovação, uso indisponível,
  orçamento esgotado ou mudança de manifesto. Custo final sempre exibido.
- Somente fixtures sintéticas; recibos mecânicos fixos em 06/07 preservam o
  protocolo de avaliação e evitam repetir RNG até obter um resultado desejado.
- Versões `record-at-risk.v2` / `campaign-progression.v2`; só R-05/R-06 movem
  o documento para `dry_surface`. A movimentação não move o jogador.

As tarifas usadas no estimador foram reconferidas em 03/10 na
[documentação oficial](https://developers.openai.com/api/docs/models/gpt-5.6-luna):
USD 0,20 / milhão de tokens de entrada e USD 1,20 / milhão de saída. O guard
usa bytes UTF-8 como proxy conservador de entrada; não é limite rígido de
cobrança do provedor. O relatório conserva suas limitações sobre cache/taxas.

## Arquivos próprios e integridade

- Runner `scripts/evaluate_hybrid_campaign_luna_l3_live.py`.
- Preflight `scripts/preflight_hybrid_campaign_luna_l3.py`.
- Lançador `scripts/run_hybrid_campaign_luna_l3_live.ps1`.
- Gate `evals/narrator/reports/hybrid-campaign-luna-l3-live-gate-2026-10-03.json`.
- Trava atômica `eval-results/hybrid-campaign-luna-l3-once`.
- Resultados `eval-results/hybrid-campaign-luna-l3-<batch-id>`.

Gate autorizado, com 20 arquivos congelados e prompt SHA-256
`4c3f88d3eff9c33863189173dfba91789fedd4e8b07d842f59d4b86beebc939a`.
As cópias prospectivas preservam os arquivos de execução de L2 e permitem
comparar diretamente o diff do runner, preflight e lançador. Não rehash de L2.
SHA dos registros L2 rechecado e preservado:
`23e741bfa5260363057c4058cff6a97a804b4036c6287afc9182bf40cea30e71`.

## Verificação

**35 testes focados aprovados**, cobrindo L3, runner L2, preflight, prompt v2 e
relatório de custos (seleção em `tests/test_hybrid_campaign_luna_l3_live.py`,
`test_hybrid_campaign_luna_live.py`, `test_preflight_hybrid_campaign_luna.py`,
`test_campaign_v2_keyless_preflight.py`, `test_luna_test_cost.py`).

Preflight CLI L3: 17 turnos autorados simulados, zero chamadas externas, maior
corpo 13.043 bytes. Todas as posições antes/depois conferidas no contexto real
serializado. Parser PowerShell, manifesto final e autorização conferidos.
Diff prospectivo comparado com L2; nenhuma alteração de runtime da campanha,
dependência, DDL, default ou Git commit neste incremento. Suíte integral não
repetida: a mudança é o lançador de um lote delimitado e os contratos de
campanha foram auditados no relatório de posição v2.

## Operação e dependência humana

O lançador executa o preflight antes de pedir chave via `Read-Host -AsSecureString`.
O orçamento já aprovado não é solicitado novamente. A chave passa apenas por
ambiente do processo e é removida ao final; não há transcript, arquivo de chave,
argumento com credencial ou leitura de `.env`. O sinal de prontidão contém
somente lote, PID, horário, hashes e tamanho do corpo em
`eval-results/preflights/hybrid-campaign-luna-l3-ready.json`.

A única intervenção operacional prevista é inserir a chave na janela externa
aberta para esse lançador. Depois da inserção, o lote inicia automaticamente e
escreve registros/summary para observação. Analisar integridade, efeitos,
continuidade, qualidade narrativa e custo antes do próximo checkpoint humano.
Nenhum resultado deste preflight admite narrador ou encerra CAMP-24/TASK-013.

Configuração recomendada para a entrada: **gpt-5.6-sol / low**, operação mecânica.
Análise de fechamento posterior: **Sol high**, por autoridade, persistência,
critérios e reconciliação das evidências. Preparação sem inferência: **USD 0**.

Prontidão operacional observada na janela externa: PID 10424, horário UTC
`2026-10-04T01:22:46.9169239Z` (03/10 no fuso do usuário), fase
`awaiting_secure_credential`, zero chamadas. A primeira janela não produziu
prontidão no ambiente restrito; o lançador foi reaberto com acesso aprovado ao
worktree. Um diagnóstico sem interação passou o preflight e encerrou antes da
chave, exibindo custo USD 0. Nenhuma trava L3 ou diretório de lote existia no
último check. O sinal de prontidão não prova execução: acompanhar os artefatos
de lote após a entrada da chave, sem tentar ler o conteúdo digitado.
