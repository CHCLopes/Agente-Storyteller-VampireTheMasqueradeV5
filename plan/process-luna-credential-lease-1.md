---
goal: Sessão diária temporária de credencial Luna com execução somente aprovada
date_created: 2026-10-19
last_updated: 2026-10-19
status: 'In progress'
tags: [process, credentials, evaluation]
---

# Introduction

![Status: In progress](https://img.shields.io/badge/status-In%20progress-yellow)

Autorização humana explícita em voz: chave em memória até meia-noite de Fortaleza,
janela supervisora aberta, execução apenas de baterias individualmente aprovadas
dentro dos tetos. Após bloqueio inicial, humano autorizou expressamente a execução
supervisionada. Nenhum arquivo foi alterado pela tentativa bloqueada. Regra vale
durante a semana de 19 a 25/10/2026; sessão diária, nunca renovação automática.

## 1. Requirements & Constraints

- REQ-003 (vigente em 19/10): humano autorizou L30 e todos os testes futuros
  necessários ao escopo aprovado com tetos planejados <= USD 0.15 por lote.
  Supera aprovação individual/quantidade descrita historicamente neste plano;
  registrar hipótese/quantidade/teto/hash/parada antes de cada execução e analisar
  antes da seguinte. Não pedir confirmação repetida. Não autoriza retry silencioso,
  best-of, fallback, admissão narrativa ou mudança de arquitetura/escopo.
  Expiração/segurança de credenciais permanecem inalteradas. Acima do teto exige
  aprovação humana nova. Supervisor não toma decisões de autorização.

- REQ-001: Uma entrada protegida por sessão diária, expiração absoluta na próxima
  meia-noite de Fortaleza, passada explicitamente ao lançador; relógio monotônico
  também limita duração para que retrocesso no relógio não prolongue a sessão.
- SEC-001: Sem chave em arquivo, argumento de comando, log ou ambiente permanente.
  Chave fica na memória privada do supervisor e no ambiente temporário apenas do
  avaliador filho, que já remove a variável ao carregá-la. Preflight nunca recebe chave.
- SEC-002: Sem listener de rede. Requests/status locais contêm apenas número do lote,
  hash de manifesto, PID/estado/expiração; não contêm credencial.
- SEC-003: Somente manifestos HYP-007/Luna low/sintéticos individualmente aprovados,
  com flags paid/live verdadeiras, 17 chamadas/USD 0,15, 768 tokens/20.000 bytes,
  sem retry/fallback/admissão; teto maior ou novo modelo exige revisão separada.
- SEC-004: Hash do manifesto no pedido, 22 hashes congelados, runner fixo por lote,
  paths contidos no worktree; preflight e revalidação antes do envio.
- SEC-005: Consumo único do pedido; lote repetido bloqueado na sessão e por latch
  original. Recusa não produz retry. Nenhum lote é aprovado pela supervisora.
- SEC-006: Expiração/interrupção encerram avaliador em andamento; estado synthetic
  pode ficar incompleto e custo indisponível, jamais registrar zero presumido.
- CON-001: Janela e computador precisam continuar ativos. Não manter serviço,
  agendamento, auto-start, recarga, nova chave ou renovação após meia-noite.
- CON-002: Encerrar sessão não revoga a chave no provedor. Aplicação não grava a
  chave; não se promete zeroização forense da RAM nem controle de swap/dumps do SO.
- REQ-002: Após criação da supervisora, humano autorizou UMA chamada paga com teto
  USD 0,15. Esse teto passa a padrão previamente aprovado por teste, sem ampliar
  quantidade ou autorizar execuções não solicitadas. Probe L26 tem authorized_calls=1
  obrigatório e MAX_CALLS=1; max_calls=17 é apenas o envelope compatível com a
  supervisora antiga, nunca o limite autorizado do probe. Bateria L25 fechada.

## 2. Implementation Steps

### Implementation Phase 1

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-001 | Implementar scripts/luna_credential_supervisor.py e run_luna_credential_supervisor.ps1, sem mudar runtime de jogo ou avaliadores congelados. | [x] | 2026-10-19 |
| TASK-002 | 52 testes keyless aprovados/um aviso preexistente python_multipart: manifesto/teto/drift/expiração/kill/entrada sem eco/reutilização e custo; XML eval-results/luna-supervisor-readiness-2026-10-19.xml. AST do PowerShell válido. Sem inferência real. | [x] | 2026-10-19 |
| TASK-003 | Supervisora externa aberta, PID 3076 ativo, status awaiting_secure_credential; sessão 4beb08ec-4442-46ae-bb9d-c9c70377b216. Deadline 20/10/2026 00:00 Fortaleza (=03:00 UTC), entrada protegida ainda necessária. | [x] | 2026-10-19 |
| TASK-004 | Entrada recebida/idle observado sem ler chave. Humano autorizou UMA chamada; probe separado L26 executou uma tentativa sem resposta/uso (custo indisponível), gate fechado e supervisor voltou idle. L25 inteiro permaneceu fechado; resultado não confirma autenticação no provedor. Relatório evals/narrator/reports/luna-single-call-probe-2026-10-19.md. | [x] | 2026-10-19 |

## 3. Alternatives

- ALT-001: Variável permanente ou arquivo de credencial rejeitados: persistência fora
  da sessão solicitada e incompatível com restrição de segredos.
- ALT-002: Porta HTTP/broker de chave rejeitada: superfície desnecessária.
- ALT-003: Fila de comandos arbitrários rejeitada: pedidos só indicam lote/hash.

## 4. Dependencies

- DEP-001: Console externo com stdin interativo e entrada sem eco; falha fechada
  se indisponível. Sem ferramenta de leitura da chave por parte do agente.
- DEP-002: Autorização contínua REQ-003 cobre testes necessários até USD 0.15;
  cada lote exige registro prospectivo e manifesto íntegro, não novo aceite humano.

## 5. Files

- FILE-001: scripts/luna_credential_supervisor.py — ciclo de vida/gates/dispatch.
- FILE-002: scripts/run_luna_credential_supervisor.ps1 — console, deadline explícito.
- FILE-003: tests/test_luna_credential_supervisor.py — fixtures sintéticas sem rede.
- FILE-004: AGENTS.md e PROMPT_RETOMADA_2026-09-06.md — política semanal/estado.

## 6. Testing

- TEST-001: Recusar gate fechado/teto maior/modelo diferente/hash divergente/latch.
- TEST-002: Chave ausente do preflight/argumentos/ambiente pai/status/arquivos/log.
- TEST-003: Expiração UTC/monotônica bloqueia dispatch; timeout mata e recolhe filho.
- TEST-004: Revogação durante preflight impede live; entrada não oculta é recusada.
- TEST-005: Uma entrada, dois lotes sintéticos aprovados, terceira repetição negada.
- TEST-006: Preparação L25 e relatório de custo continuam funcionando sem inferência.

## 7. Risks & Assumptions

- RISK-001: Processo do usuário com acesso à máquina pode inspecionar RAM ou alterar
  arquivos locais. Esta supervisora não é cofre contra comprometimento do host.
- RISK-002: Suspensão/reinício/fechamento perde disponibilidade; não autoriza salvar
  chave ou retomá-la de outro processo. Ao voltar após deadline, não despachar.
- RISK-003: Validação offline não comprova autorização/saldo do provedor ou custo real.
- ASSUMPTION-001: Gates e pedidos são editados pelo agente somente depois da aprovação
  humana registrada; a supervisora valida arquivos, não interpreta conversa.

## 8. Related Specifications / Further Reading

- [Estado vigente](../PROMPT_RETOMADA_2026-09-06.md)
- [Progresso da campanha e aprovação de lotes](architecture-hybrid-campaign-progression-1.md)

## Operação sem credenciais em comandos

Ativação corrigida em 19/10: janela anterior encerrada pelo humano e PID 3076
ausente; nova janela externa com PID 20604 ativo e sessão
2f8a38f5-f351-4f99-89e2-57e16a141407 aguardando entrada protegida.
Status observado: awaiting_secure_credential; expiração 20/10 00:00 Fortaleza.
TASK-006 permanece aberta até conferir entrada local concluída. Nenhuma chamada
paga iniciada na abertura; nenhum manifesto histórico reativado.

Atualização de auditoria em 19/10: editor/adapter corrigidos, 126 testes
relacionados aprovados e console Windows sintético verificado. A supervisora
antiga em memória foi preservada idle e NÃO deve despachar novas inferências.
Ativar versão corrigida exige reinício coordenado e UMA entrada humana, sem
extrair/reaproveitar chave da memória. Relatório e procedimento:
../docs/security-audit/credential-flow-2026-10-19/README.md.

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-005 | Auditar aplicação receptora; implementar feedback mascarado/contador/edição/limpeza, rejeição de duplicata/controles e diagnóstico seguro do adapter. Corrigir fase inexistente. 126 testes aprovados, console Windows sintético/AST/PDF sete páginas verificados. | [x] | 2026-10-19 |
| TASK-006 | Substituir sessão antiga por supervisor corrigido e conferir entrada local. PID 20604, sessão 2f8a38f5-f351-4f99-89e2-57e16a141407; validação local passed. Chamada L27 separadamente autorizada e concluída (1/1), USD 0.000698 estimado; gate fechado, supervisor idle. | [x] | 2026-10-19 |

1. Abrir a supervisora com deadline absoluto. Não abrir segunda supervisora.
2. Humano insere chave no console; observar somente status idle no diretório
   eval-results/credential-leases da sessão ativa e PID/expiração correspondentes.
3. Após aprovação individual: ativar gate específico e registrar o estado durável;
   criar request-<identificador-unico>.json nessa sessão contendo exatamente lot
   (inteiro) e manifest_sha256 (hash SHA256 do manifesto já ativado). Sem chave.
4. Supervisor consome pedido uma vez, valida, roda preflight sem chave, revalida e
   executa lote. Agente observa records/summary, relata custo e fecha gate do lote.
5. À meia-noite expira; dia seguinte exige nova abertura e entrada protegida.
