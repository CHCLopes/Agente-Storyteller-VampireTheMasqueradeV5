# Prontidão técnica viva — HYP-001 / L1

**Data:** 2026-09-22

**Status:** runner verificado offline; credencial protegida disponível; zero chamadas

## Resultado

O runner delimitado de `LIVE-HYP-001-L1` foi implementado e verificado sem
consultar credencial nem abrir rede. Ele congela dois alvos Groq exatos, a ordem
dos 16 slots, `temperature 0.65`, 768 tokens máximos por chamada, intervalo
global mínimo de 60 segundos, zero retry, zero reparo e zero fallback.

O caminho vivo requer simultaneamente `--live`, `--allow-synthetic-only`, um
preflight reconstruído com hash esperado e a credencial no ambiente dedicado do
processo. Ausência da credencial encerra antes de criar diretório de lote ou
realizar request. Não há launcher específico versionado para capturar, copiar ou
descobrir a credencial.

## Evidência de controle

- cancelamento durante a espera de cadência: zero chamadas, uma falha registrada
  e 15 skips causais;
- falha de transporte: uma chamada, nenhum retry e parada global;
- saída estruturada inválida no primeiro elo: apenas o dependente do mesmo
  candidato é pulado; o outro candidato e casos independentes continuam;
- divergência de alvo/proveniência e eco de credencial: parada global;
- cápsulas, fonte anterior, body, invocation, rota, skips e resumo são
  reconstruídos pelo verificador, não apenas aceitos por hash;
- adulteração acompanhada de recálculo dos hashes externos continua rejeitada;
- o teste de execução completa usa apenas adapter falso e comprova 16 despachos
  máximos, sem chamada real.

## Freeze observado

| Artefato | SHA-256 |
|---|---|
| `scripts/evaluate_grounded_progression_live.py` | `8904bde2e58cb0a8d5340a8d5f32a04f2bf9705eaa77c23ec33da31cddef5ebd` |
| `tests/test_grounded_progression_live.py` | `a738358f48ba358f9ea9442ce184ca51703da7b011585c36f0a76e1d33ea8e7e` |
| `scripts/evaluate_grounded_progression_contract.py` | `38d2f3ce74ebd292846176463471b8620b3dffdb08fa6e67cad18ad8db04e81a` |
| `tests/test_grounded_progression_contract.py` | `25962f83da3dbb2e76263f0a69b335a941f2694394637834868cc811a41ecc98` |
| `grounded-progression-live-gate-2026-09-22.json` | `f905e1d570c23979641c442a47511b7ae5ff8c85b96d522a256d2d87f91944dc` |
| `grounded-progression-live-gate-2026-09-22.md` | `5a554c48f05af435ce21f6776c0f08d15e3cd2ff4b55bf0030b963b925a9d436` |

## Verificação executada

- 18 testes do contrato offline e 12 testes do runner: **30 aprovados**;
- matriz relacionada com cena, resolvedor, ator narrador e Groq:
  **421 aprovados**;
- preflight keyless reconstruído após os testes: `provider_calls: 0`,
  `credential_inspected: false`, 16 slots e teto de 12.288 tokens de saída;
- hash canônico dos metadados reconstruídos do preflight:
  `084ebd791527b0428d4eafaf113ed550a0142907cad98e8283bdc8cc1abd33f9`;
- avisos não bloqueantes: depreciação conhecida do Starlette e impossibilidade
  do sandbox gravar `.pytest_cache` no worktree externo.

A suíte backend integral não foi repetida porque o incremento toca apenas o
harness de avaliação, o contrato offline e a composição já coberta do adapter;
a matriz relacionada é maior que a anterior e a suíte ampla histórica possui
falhas congeladas já documentadas.

## Gate restante

A credencial foi disponibilizada por entrada mascarada no ambiente dedicado do
terminal, sem revelar o valor. Não enviar a chave no chat, não gravá-la em `.env`,
arquivo, argumento, relatório ou histórico. O próximo passo técnico é reconstruir
e congelar o preflight, confirmar seu hash e só então iniciar o lote único de até
16 chamadas.

Mesmo um lote tecnicamente íntegro exigirá revisão semântica humana de cada caso;
aprovação de L1 não admite candidato, não promove default e não inicia campanha.
