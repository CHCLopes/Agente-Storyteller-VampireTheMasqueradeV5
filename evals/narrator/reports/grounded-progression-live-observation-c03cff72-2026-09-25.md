# Observação viva — HYP-001 / lote c03cff72

**Observação fechada em:** 2026-09-25

**Execução:** 2026-09-22

**Status:** lote íntegro; nenhum candidato elegível; resultado aceito pelo usuário

## Resultado

O lote único autorizado `LIVE-HYP-001-L1` executou os 16 slots congelados e foi
verificado causalmente duas vezes. Não houve falha, skip, retry, reparo, fallback,
troca de alvo ou repetição. A revisão semântica independente foi vinculada às
narrativas originais por comparação byte a byte e submetida ao verificador
prospectivo congelado.

| Candidato exato | Casos aprovados | Casos reprovados | Elegível |
|---|---:|---:|---|
| `qwen/qwen3.8-27b`, reasoning `none` | 2/8 | 6/8 | não |
| `openai/gpt-oss-120b`, reasoning `low` | 5/8 | 3/8 | não |

Pela regra prospectiva, um alvo precisa aprovar 8/8. O resultado formal é:
**nenhum candidato elegível, nenhum narrador admitido e nenhum default criado**.
Não repetir o lote nem relaxar os gates para produzir vencedor.

## Integridade e consumo observado

| Evidência | Valor |
|---|---|
| Batch ID | `c03cff72-817f-4881-a864-8a5848011c0a` |
| Janela UTC | `2026-09-22T23:23:58.430349Z` a `2026-09-22T23:38:59.676217Z` |
| Preflight SHA-256 | `d2c647a04435413e2395b858fe436e82bad44f415744076d68ffa2ec584dd348` |
| `summary.json` SHA-256 | `d6c49b33ea03edc16f5c4322ce3eaf4101bab090664cab3d49fefada28af331e` |
| `records.jsonl` SHA-256 | `3466fe2c77d4e079e59e4df928dc3b294e3414fd8f6c7440a80d8d5ff491c578` |
| Chamadas | 16 concluídas; 0 falhas; 0 skips |
| Qwen usage reportado | 7.525 input; 998 output tokens |
| GPT-OSS usage reportado | 8.521 input; 1.419 output tokens |
| Retry / reparo / fallback | 0 / não / não |
| Verificador de artefatos | `verified: true`, exit 0 |
| Credencial | entrada mascarada; valor não observado; removida do ambiente ao final |

O `summary.json` original conserva `semantic_review_status: not_performed` porque
é artefato imutável da execução. A revisão posterior está nas fichas e resultados
versionados citados abaixo; o resumo original não foi reclassificado.

## Revisão caso a caso

| Caso | Qwen | GPT-OSS |
|---|---|---|
| `wait-without-authorized-progression` | reprova: a água avança sem transição e o texto termina cortado | reprova: a água escorre e se aproxima sem transição |
| `wait-with-authorized-event` | reprova: ultrapassa a borda autorizada e trata o papel como já encharcado | aprova |
| `known-object-state` | reprova: inventa estado interno e termina cortado | reprova: atribui ao jogador aproximação não declarada |
| `unknown-object-state` | reprova: inventa fios/etiquetas/fiação e termina cortado com troca de idioma | aprova |
| `favorable-mechanical-result` | aprova | aprova |
| `unfavorable-mechanical-result` | reprova: 29 palavras, abaixo do mínimo 30 | aprova |
| `npc-protected-secret` | reprova: não identifica o índice, não realiza a transição e termina cortado | aprova |
| `ambiguous-action-preserves-choice` | aprova | reprova: inventa tipos de instrumentos e vibração ambiental |

Nenhuma resposta revelou o segredo protegido. Identidade de alvo, proveniência,
schema e vínculo de cápsula passaram nos 16 registros.

## Artefatos de revisão

| Artefato | SHA-256 |
|---|---|
| `evals/narrator/reviews/grounded-progression-live-c03cff72-qwen-codex.json` | `18160a021df7c60c408f57cd86b37c0815a753fbb26a9a40981ef07a1dae90f3` |
| `evals/narrator/reviews/grounded-progression-live-c03cff72-gpt-oss-codex.json` | `9eece69ac74ec050e615a86120c22fa3c82ef1a17fad4b8822e28e870c20f806` |
| `grounded-progression-live-c03cff72-qwen-verification.json` | `45deb4a23e38adb48cb9e673a133d861d788d79c75dcf6da349477a878654ec4` |
| `grounded-progression-live-c03cff72-gpt-oss-verification.json` | `fe0e87c5dd601f92a1aad9835dff3b153a6a96d528eefba26350db705278aac6` |

As 16 narrativas nas fichas foram comparadas byte a byte com o `records.jsonl`:
zero divergência. O verificador retornou exit 1 para ambos porque
`qualified_in_protocol` é falso; isso é o resultado esperado, não erro de
integridade.

## Correção local e verificação final

O launcher versionado foi corrigido para que ausência de credencial produza exit
3 em vez de o `Write-Error` interromper prematuramente com exit 1. Nenhuma chamada
foi repetida. Evidência final:

- 32 testes focados aprovados: 18 contrato, 12 runner, 2 launcher;
- parse PowerShell: 0 erros;
- execução em processo filho sem a variável dedicada: exit 3 antes da rede;
- `scripts/run_grounded_progression_live.ps1` SHA-256:
  `9a7dc3104d8d85b29e611ed8650c7f379e53689c5a82d8fcd3a9966dfceaacfa`;
- `tests/test_grounded_progression_live_launcher.py` SHA-256:
  `32777a07a71ca7415792d4e1f3cc137779813f90f12c2fa78aebdc78de901e62`.

A matriz relacionada de 421 testes permanece como a regressão ampla mais recente.
Ela não foi repetida porque a única mudança de código posterior foi o tratamento
local do exit do launcher, coberto pelos testes focados e pela contraprova real.

## Aceitação humana

Em 2026-09-25, o usuário respondeu:
`Aceito HYP-001-L1: nenhum candidato elegível; nenhum narrador admitido.`
O aceite fecha HYP-001 sem promover qualquer candidato.

Aceitar este resultado não aprova HYP-002, novo alvo, custo, provedor, default ou
campanha híbrida. Como nenhum narrador foi admitido, a próxima tentativa exige
uma hipótese prospectiva distinta e nova autorização humana.
