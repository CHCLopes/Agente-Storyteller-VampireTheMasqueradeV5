# HYP-005 L3-B — prontidão técnica

Data: 2026-09-27  
Estado: preparado offline; execução permitida somente em nova janela diária gratuita

## Decisão incorporada

O aceite humano fechou HYP-005 L2-B sem candidato elegível e autorizou L3-B com
uma única mudança: cada slot pode repetir exatamente a mesma requisição uma vez,
somente quando a primeira tentativa retorna `provider_unavailable` com código
`openrouter_provider_overloaded` e `retryable: true`.

Todos os demais gates de L2-B permanecem: três slugs explícitos `:free`, 24
slots sintéticos, 2048 tokens por resposta, custo reportado exatamente zero,
JSON Schema estrito, sem reparo, fallback, router dinâmico, troca de alvo,
agregação ou best-of. O teto teórico é 48 chamadas e 98.304 tokens de saída.

## Implementação e contraprovas

- O runner L3 é aditivo e não altera os runners congelados L1/L2.
- O retry reutiliza o mesmo objeto de requisição: invocation ID, deadline, corpo
  e alvo permanecem idênticos.
- `Retry-After` só é aceito entre 0 e 60 segundos; na ausência do campo, o delay
  congelado é 15 segundos. Valor inválido ou acima de 60 encerra sem retry.
- Outros códigos, categorias ou `retryable != true` nunca repetem a chamada.
- A segunda falha encerra o lote; não existe terceira tentativa.
- Cancelamento durante o pacing é persistido fail-closed e conta zero chamadas.
- O verificador reconstrói tentativas, identidade, causalidade de retry, skips e
  sumário; adulterações não podem ser legitimadas apenas recalculando o sumário.
- Ausência de credencial encerra antes da criação do diretório do lote.
- O launcher usa dois prompts mascarados, não consulta `.env` e remove a variável
  de processo em `finally`.

## Evidência técnica

- 14 testes próprios: aprovados.
- Regressão combinada L1/L2/L3, revisores, runner-base e isolamento de rede:
  43 testes aprovados.
- Parser PowerShell do launcher: zero erro.
- Preflight keyless: exit 0, `provider_calls: 0`, `credential_inspected: false`.
- SHA-256 do preflight observado: `20d612cd88d7de6f29773cf37fdc30c78bc0cab58532ec7bae9e1556f508807b`.
- Runner: `730d6f57edacfaa0efa83f34d750f0ad453f599f07d4a09e362e0a6b29d3dbff`.
- Launcher: `dd89e23f87139a8fa8aeb616e187542e64c8ec56347cf06ff761130177eb3b95`.
- Testes L3: `4ecc56f7ba2496efc438d6e5b44b3b8e26ba19b1b6d37fd11500b841efa659a2`.
- Gate: `81ba33bf24bd124f8ecb290ecf421cf2651a99f15f42b3fffffc9fae066131d7`.

Os avisos de cache do pytest decorrem da permissão do diretório `.pytest_cache`
no worktree e não afetaram a execução nem os resultados.

## Próximo checkpoint

Não executar em 2026-09-27 por arrasto. Na primeira nova janela diária gratuita,
confirmar que os três slugs continuam gratuitos no catálogo e iniciar uma única
vez `scripts/run_openrouter_free_narrators_l3_live.ps1` em terminal observável.
A revisão semântica e a decisão de admissão só ocorrerão após verificação íntegra
dos artefatos. Nenhum narrador ou default está admitido neste estado.
