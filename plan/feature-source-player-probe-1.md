---
goal: Observar diálogo seguido de espera pela entrada real do produtor B com setup autorado
version: 1
date_created: 2026-09-11
last_updated: 2026-09-11
owner: Agente Storyteller
status: 'Completed'
tags: [narrative-source, synthetic, probe, groq]
---

# Introduction

![Status: Completed](https://img.shields.io/badge/status-Completed-brightgreen)

Hipótese registrada antes de chamada: em cena com interlocutora presente, uma
pergunta explícita com objetivo pode provocar resposta e reação posterior mais
concretas que a espera dos lotes históricos. Esta observação não é A/B causal,
não muda SYSTEM nem repete/importa qualquer lote encerrado.

## 1. Requirements & Constraints

- **REQ-001**: Campanha sintética nova, local Galeria, NPC Mara, objetivo declarado
  conhecer melhor este lugar por meio da conversa. Introdução autorada persistida
  pelo setup, sem fonte inicial. Ficha sintética Wits3/Investigation2/Fome0,
  rastreadores saudáveis, relações vazias; nenhuma campanha real usada. Configuração
  servidor inclui npc_aliases=("Mara",), porque elenco de cena não preenche
  automaticamente os aliases usados pela proteção de agência.
- **REQ-002**: Duas ações autoradas como fixtures de jogador:
  `Pergunto a Mara: "Quero conhecer melhor este lugar por meio da conversa. O que você pode me contar?"`
  e `Espero a reação de Mara.`. Passam por prepare_source_player_action; não usar
  declaração pré-classificada ou recibo fabricado no harness. São ações sintéticas
  do experimento, nunca submissão em nome do usuário real.
- **REQ-003**: Qwen/Groq exato do manifesto groq_candidates_2026-09-05.json,
  candidate qwen-3.8-27b-groq-free-synthetic-nonthink, reasoning none,
  structured native, SYSTEM narrative-source-progress-v1 preservado. Sem fallback.
- **REQ-004**: Máximo duas chamadas normais, 768 tokens/call, 1536 totais,
  temperature0.65, 60s iniciais, intervalo mínimo60s, deadline60s/call.
  Primeira falha interrompe cadeia. Sem diagnóstico, retry, reparo ou baseline.
- **REQ-005**: Registrar manifesto, hashes de código/schema/SYSTEM/caso,
  requests efetivos ligados às cápsulas, observação provider, JSONL/summary e
  banco sintético selado. Verificar P/K/H e replay sem nova produção/chamada.
- **REQ-006**: Avaliação narrativa separada: resposta da interlocutora compatível
  com pergunta; avanço/reação perceptível na espera; continuidade da fonte;
  agência preservada; incertezas não endurecidas nem causas afirmadas sem suporte.
  Schema/HTTP não bastam. A revisão pode continuar inconclusiva ou falhar.
- **CON-001**: Sem acesso a .env/save/chaves em arquivos. Credencial somente via
  ambiente do processo já seguro ou Read-Host -AsSecureString no launcher.
  Nunca recuperar segredo de outra janela. Filtrar eco de chave antes de artefatos.
- **CON-002**: Preparação offline, revisão e freeze precedem credencial/rede.
  Não ativar UI/default, alterar gates, aprovar CAP-001 ou decidir CAMP/DEC.

## 2. Implementation Steps

### Implementation Phase 1

- GOAL-001: Preparar harness revisável usando componentes já verificados.

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-001 | Criar scripts/evaluate_source_player.py com preflight puro e execução limitada setup→produtor→cápsula→executor, reutilizando observador Groq/captura seguros existentes sem editar experimentos antigos. | Sim | 2026-09-11 |
| TASK-002 | Criar scripts/run_groq_source_player_probe.ps1 com PreflightOnly, identidade/hash/limites verificados e credencial protegida; congelar preflight antes de chamar. Nenhuma janela nova automática. | Sim | 2026-09-11 |
| TASK-003 | Criar tests/test_source_player_probe.py com HTTP MockTransport, casos de dois turnos, falha e limite, adulteração de manifesto/artefatos, binding P/K/H, zero eco de chave e preflight sem rede/credencial. Revisão independente antes testes finais. | Sim | 2026-09-11 |

### Implementation Phase 2

- GOAL-002: Executar uma observação nova e fechar evidência sem reclassificar história.

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-004 | Executar preflight congelado e uma observação bounded com chave disponível no processo autorizado; se ausente, deixar comando concreto para o PowerShell seguro e solicitar somente essa intervenção. | Sim | 2026-09-11 |
| TASK-005 | Verificar summary/JSONL/banco e cronologia, revisar narrativa independentemente, registrar limitações e decidir próximo passo pelo resultado; não repetir lote para elevar taxa. | Sim | 2026-09-11 |

## 3. Alternatives

- **ALT-001**: Mais uma paráfrase de SYSTEM não diagnostica o efeito da interação.
- **ALT-002**: Recibos autorados bypassam o produtor; usar ações reais da fixture.
- **ALT-003**: Acrescentar investigação live agora excederia a hipótese de diálogo
  e espera; sucesso/falha já possuem contraprovas de composição offline.

## 4. Dependencies

- **DEP-001**: feature-narrative-source-setup-1.md verificado antes da observação.
- **DEP-002**: Credencial acessível somente ao processo executor. Sua presença em
  outra janela não garante herança por esta sessão; não exibir valor para verificar.

## 5. Files

- **FILE-001**: scripts/evaluate_source_player.py e launcher correspondente.
- **FILE-002**: tests/test_source_player_probe.py.
- **FILE-003**: Relatórios novos em evals/narrator/reports, README/retomada.
- **FILE-004**: Artefatos novos sob eval-results/source-player-<batch UUID>.

## 6. Testing

- **TEST-001**: Preflight não chama gateway nem lê credencial; identifica contexto/template.
- **TEST-002**: Segundo USER carrega somente fontes legítimas completas; briefing não é fonte.
- **TEST-003**: P/K/H e replay permanecem consistentes, sem segunda produção ou chamada.
- **TEST-004**: Falha interrompe segundo turno, teto e pacing aplicam-se ao HTTP real.
- **TEST-005**: Artefatos não aceitam hashes, identidades ou histórias adulterados.

## 7. Risks & Assumptions

- **RISK-001**: Pequeno ensaio não demonstra campanha longa ou generalização.
- **RISK-002**: O modelo pode improvisar conteúdo adequado e ainda não sustentar
  continuidade; revisar atribuição e consequência, sem exigir repetição estéril.
- **ASSUMPTION-001**: Mudança de cena/elenco/ação impede conclusão causal entre lotes.

## 8. Related Specifications / Further Reading

- [Setup](feature-narrative-source-setup-1.md)
- [Produtor](feature-narrative-source-input-producer-1.md)
- [Transporte futuro](feature-narrative-source-transport-1.md)
- [Último diagnóstico](../evals/narrator/reports/source-context-observation-cc09080a-2026-09-10.md)

Preparação concluída em11/09/2026:43 testes do executor e7 cenários do launcher
aprovados, revisão independente encerrada, preflight real exit0 sem chave/live.
[Prova e comando pronto](../evals/narrator/reports/source-player-preparation-2026-09-11.md).
TASK-004/005 concluídas: lote83921947 encerrado finished/0, duas chamadas,
dois commits/replays; auditoria offline aprovada. Revisão narrativa independente:
continuidade/agência preservadas, reação mínima presente, progresso substantivo
insuficiente. Gates técnicos não aprovam experiência. Resultado separado em
[relatório do ensaio](../evals/narrator/reports/source-player-observation-83921947-2026-09-11.md).
Próximo: projeções públicas puras/inativas, sem repetir lote ou ativar transporte.
