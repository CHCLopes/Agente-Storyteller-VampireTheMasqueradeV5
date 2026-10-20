# HYP-007-L5 — prontidão técnica, sem autorização de gasto

Data: 18/10/2026. Worktree: `b008/AgenteStoryteller`.
Branch: `codex/planejamento-agente-storyteller-v5`.
Base Git: `2e84c55f6f93ec2c7e6b00f3622054ef99c61ece`.
Estado: preparação verificada; paid/live false; nenhum narrador admitido.

Atualização posterior à preparação, em 18/10: o usuário declarou "Novo lote
pago autorizado. Continue" e aprovou os limites propostos abaixo. Somente os
flags paid/live do manifesto de 18/10 foram ativados; hashes, prompt, parâmetros
e critérios preservados. O SHA do manifesto com flags false abaixo identifica
a preparação anterior, não o arquivo após autorização. O próximo passo é a
entrada protegida da chave no PowerShell externo L5, seguida de execução única,
relatório de custo/gates e fechamento live. Nenhum resultado live é afirmado
por esta atualização. Os parágrafos abaixo registram a preparação pré-aprovação.

## Aceite e limites

O usuário declarou: "O resultado de L4 foi aceito. Continue". O resultado
delimitado HYP-007-L4 foi duas chamadas reais, um turno completo e parada de
política R-05. Custo histórico estimado: USD 0,0014972; cobrança não conferida.
Esse aceite não transforma o lote em campanha completa, não admite narrador e
não autoriza novo gasto. L4 fica fechado e não será repetido.

A reprodução local atribuiu a frase de objeto "Ele permanece intacto" a espera
ambígua. O prompt v3 prospectivo já preparado pede sujeito explícito para o
estado físico. Nesta etapa ele não foi alterado; detector, política, RNG,
persistência e critérios de aceitação também não foram alterados. A eficácia
narrativa da instrução continua hipótese a verificar em L5.

## Preparação renovada

- Novo manifesto: [gate L5 de 18/10](hybrid-campaign-luna-l5-live-gate-2026-10-18.json).
- Runner e lançador L5 apontam somente para esse manifesto. Congelamento de
  22 arquivos, incluindo `api/local_request_security.py`, com a segurança local
  pós-auditoria. Manifestos L4/L5 de 03/10 preservados byte a byte.
- O gate recusa hashes divergentes ou ausência de arquivos, prompt divergente,
  retry/fallback habilitados, admissão automática e dados não sintéticos.
- Target preservado: `gpt-5.6-luna`, esforço `low`, até 17 chamadas, até 768
  tokens de saída e 20.000 bytes de corpo por requisição. Prazo existente: 60 s.
  Nenhuma troca de modelo, retry, fallback ou novo default.
- Gate paid/live fechado antes de acesso à credencial/adaptador, trava atômica
  contra lote concorrente/repetido e rechecagem antes de cada envio.
- SHA-256 do prompt v3:
  `250f2fa0fd043a74c953b2ceb22ed8ada947e60d113820118d60ab8f61755362`.
- SHA-256 do manifesto prospectivo com flags false:
  `bd9e07b289e78f98bb9a7c21fbd8059eae2a947aaa9c4d5ed6fc2852efa2c57d`.

## Evidência executada

| Verificação | Resultado observado | Limite |
|---|---|---|
| Testes focados L5 | 15 aprovados | Adaptadores falsos; não mede qualidade Luna |
| Seleção relacionada | 78 aprovados, 1 aviso de depreciação preexistente | Inclui os 15; não somar como 93 distintos |
| CLI real `--preflight` | 17 turnos sintéticos, 8 casos, zero chamadas ao provedor | Não é execução live nem aceite narrativo |
| Maior corpo do preflight | 13.415 bytes, abaixo de 20.000 | Contexto sintético deste corpus |
| PowerShell | AST do lançador válido, sem executá-lo | Terminal/credencial não abertos nesta etapa |
| Gate/trava | paid/live false; trava live L5 ausente | Autenticação e saldo atuais não consultados |

Os testes verificam negação antes de credencial/adaptador/saída, pré-voo sem
getter de segredo ou dispatch real, rejeição de drift, concorrência/repetição,
e revogação que permite uma chamada falsa e impede a segunda. O percurso falso
completo verifica os 17 turnos sem habilitar o gate real. Testes relacionados
cobrem preflight B, custo Luna, segurança local e ensaio offline.

Comandos executados no worktree, com `STORYTELLER_DISABLE_DOTENV=1`:

```powershell
.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider --tb=short tests/test_hybrid_campaign_luna_l5_preparation.py
.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider --tb=short --junitxml=eval-results/hyp-007-l5-readiness-2026-10-18.xml tests/test_hybrid_campaign_luna_l5_preparation.py tests/test_hybrid_campaign_luna_live.py tests/test_hybrid_campaign_luna_l3_live.py tests/test_preflight_hybrid_campaign_luna.py tests/test_campaign_v2_keyless_preflight.py tests/test_luna_test_cost.py tests/test_security_audit_regressions.py tests/test_campaign_source_offline_trial.py
.venv\Scripts\python.exe -m scripts.evaluate_hybrid_campaign_luna_l5_live --preflight
```

JUnit local gerado: `eval-results/hyp-007-l5-readiness-2026-10-18.xml`.
Diff de código/testes/documentação inspecionado e whitespace do incremento
verificado. Nenhuma leitura de `.env*`, save ou credencial; nenhum launcher live
executado, latch real criado ou inferência real iniciada.

A seleção foi ampliada somente após os focados passarem. Não se repetiu a suíte
integral ou frontend/build: a alteração é de runner/manifesto prospectivo, não
de runtime da aplicação ou UI. A consolidação Git anterior documenta 8.719
aprovados, 333 skips, 286 falhas e 61 erros; suas limitações históricas continuam
em [registro Git](../../../docs/repository-promotion.md). Não há alegação de
suíte integral verde nem correção lateral desses testes congelados.

## Custo e próximo bloqueio

**CUSTO FINAL LUNA DESTA PREPARAÇÃO: USD 0 (nenhuma chamada iniciada).**
Os custos estimados dos adaptadores falsos nos testes não são cobranças reais.

Proposta L5: teto estimado adicional **USD 0,15**, até 17 chamadas, sem
retry/fallback. Ainda não aprovado. Os preços-base usados pelo guard continuam
USD 0,20/1 milhão de tokens de entrada e USD 1,20/1 milhão de saída, conferidos
em 18/10 na [página oficial do modelo](https://developers.openai.com/api/docs/models/gpt-5.6-luna).
A documentação também prevê cache write a 1,25 vez a entrada não cacheada.
O guard usa bytes UTF-8 como proxy conservador de tokens, não faturamento exato;
USD 0,15 não é trava financeira garantida da conta. Autenticação, saldo, limites
de conta, impostos e cobrança efetiva não foram verificados. Revalidar se os
parâmetros, preço ou manifesto mudarem antes da autorização/execução.

Após autorização explícita do lote: ativar somente os dois flags do novo gate,
revalidar hashes/preflight, abrir PowerShell externo para entrada protegida,
executar uma vez e mostrar custo final, gates, trajetórias e limitações. Uma
parada de política/erro interrompe o lote; não há repetição automática ou saldo
transferido. Não solicitar credencial antes da autorização.

TASK-016 fecha apenas esta preparação; TASK-013, CAMP-24, julgamento da
experiência e admissão do narrador permanecem abertos. Mudanças locais ainda
sem commit/push; checkout original e GitHub principal não alterados nesta etapa.
