---
goal: Integrar e verificar o transporte B local inativo sem reutilizar inicialização ou reenvio v1
version: 1
date_created: 2026-09-11
last_updated: 2026-09-12
status: 'Completed'
---

# Transporte local B: implementação inativa

Incremento técnico de TASK-001/003/004/005 do plano de transporte. A autorização
contínua cobre esta preparação reversível e suas verificações. Aceitação do recorte
para uso do jogador não é um bloqueio para construir o artefato verificável.

## Contrato e limites

- Uma factory ASGI separada, sem instância global ou launcher ativo, reserva
  `/ws/source-local/{session_id}` para B. A configuração do servidor habilita o
  recorte; o seletor verifica sessão/Host/Origin antes do accept. O lifespan não
  importa main/state_service ou executa recuperação/migração/seed v1.
- O handler recebe WebSocket aceito e seleção interna, gateway explícito e prazo
  de ação do servidor. Nenhuma conta, proxy, acesso direto remoto ou modelo default.
- O comando JSON tem versão `narrative-source-command-v1`: `submit` contém somente
  `operation_id` e `player_input`; `query` contém somente `operation_id`. O cliente
  não fornece sessão, alvo, recibo, estado, deadline ou permissão de execução.
  Identidades e texto preservam os limites já definidos no contrato de entrada.
- Conectar reapresenta briefing e último turno confirmado. Consultar não produz,
  migra, recupera ou renova prazo de geração. Unknown não vira pending nem retry.
- Submit explícito usa prepare_source_player_action e só P completo pode seguir
  ao coordenador retido. Um deadline absoluto e um token cobrem P/H. O coordenador
  existente continua arbitrando pending/terminal/replay; sem novo mecanismo de retry.
- O callback de texto do executor é anterior ao commit: nunca publicá-lo no socket.
  A publicação de n/q vem do leitor agregado do estado realmente confirmado.
- Cancelamento/desconexão sinalizam a operação uma vez e aguardam settlement das
  transações protegidas. Um commit que já ocorreu permanece consultável. Reenvio
  automático do hook v1 não é reutilizado.
- O leitor agregado opera numa transação SQLite mode=ro e usa os restauradores
  existentes. Retorna manifesto, último confirmado e operação pedida com P/H/texto
  internos coerentes. No recorte do produtor, K/H/turn sem P é inconsistência;
  leitores anteriores mantêm sua compatibilidade. Não retorna ficha/estado completo.
- A view B e seu reducer/decoder são independentes de App/hook v1. Briefing e estado
  ficam visíveis; n/q confirmados rolam na caixa. Entrada/ID são preservados em falha
  e consulta, sem fabricar ficha, timestamps ou história não fornecida. Reconexão na
  mesma montagem não implica persistência após reload; essa ligação será verificada.

## Passos

| Tarefa | Estado |
|---|---|
| Seletor de vínculo servidor antes da consulta B | Concluído: 73 testes próprios |
| Leitor agregado somente leitura, contrato e contraprovas | Concluído: 89 casos distintos aprovados |
| Factory ASGI separada e ordem real pré-accept com handler injetado | Concluído: 29 testes aprovados, incluindo correção do close após desconexão |
| Handler com submit/query, publicação após commit e cancelamento | Concluído: 37 testes aprovados; mais 129 regressões anteriores |
| Decoder/reducer/view próprios, sem montagem no App | Concluído: protocolo/view/hook/entrada próprios e orientação REQ-006 verificados |
| Composição técnica sintética, reconexão/consulta e inspeção visual | Concluído: duas fixtures novas, recusa/continuação, consultas, reconexão, recorte estreito/desktop e desligamento auditados |
| Evidências, revisão e retomada consolidadas | Concluído: relatório e checkpoint com 101 cópias verificadas em 12/09 |

## Verificação

Provar snapshot único, identidades deslocadas, ausência/corrupção sem criação,
P pendente/terminal antes de K, K retido/H em curso/terminal e replay antigo após
mais de dois turnos. Provar ausência de RNG/H6 em query/reconnect e de texto antes
do commit; desconexão antes/durante/depois do commit; cancelamentos repetidos sem
repetir settlement. ASGI não importa bootstrap legado; frontend não reenvia no
reconnect nem converte evento atrasado em regressão ou narrativa duplicada.

As provas usarão SQLite sintético e gateway controlado, sem inferência externa ou
credencial. Um teste de navegador do componente composto não ativa um narrador real.
Nenhum desses resultados altera o lote comparativo 61b83a2f, escolhe narrador ou
aprova experiência de campanha completa/CAP-001. Ativação para participação do usuário
continua distinta da preparação interna, conforme transporte CON-001 e entrada DEP-005.

Backend inativo encerrado e revisado: [evidência](../evals/narrator/reports/narrative-source-local-backend-2026-09-11.md). Composição técnica concluída na retomada registrada abaixo.

## Pausa solicitada em11/09/2026

Backend e hook foram verificados, mas a composição real está incompleta. Um turno
sintético foi confirmado; o encerramento revelou websocket.close duplicado na
factoryASGI. Delta visual para manter estado visível em janela estreita aplicado
e ainda sem checagens finais. Nenhum novo teste após a pausa. Próximo passo:
reproduzir/corrigir encerramento ASGI; depois verificar delta visual e composição
nova. [Registro e evidências](../evals/narrator/reports/source-local-pause-2026-09-11.md).
As contagens anteriores permanecem históricas; não equivalem a aprovação final.


## Retomada e fechamento técnico em 12/09/2026

O usuário retomou a execução. O erro ASGI da pausa foi reproduzido e corrigido;
29 testes passaram, com contraprovas de propagação de erros e cancelamento.
A primeira fixture d249b3fc confirmou dois turnos e consultas/reload/reconexão
sem mutação, mas permaneceu failed no encerramento. Essa evidência foi preservada.

O lançador passou a tratar os sinais sem reaplicação após shutdown e recusar
stopped diante de pendência, interrupção forçada ou falha do lifespan. Foram
aprovados 33 casos distintos em etapas, incluindo duas reproduções vermelhas.

A fixture final d8abaa85 recusou uma ação fora da gramática sem K/H/turno e
confirmou o diálogo seguinte. Consultas/reconexão/desligamento preservaram o
banco. O lifecycle final é stopped; o exit 1 da sessão PowerShell interrompida
não mede separadamente o código Python. Vite exit 0 e listeners ausentes.

Rolagem, estado fixo e orientação REQ-006 foram verificados em janela estreita
e desktop, com testes focais, lint e TypeScript. Nenhuma montagem no App legado,
inferência externa ou decisão de produto. [Relatório final](../evals/narrator/reports/source-local-resume-2026-09-12.md).
Checkpoint: eval-results/checkpoints/source-local-resume-20260912/manifest.json.
O próximo diagnóstico de extensão é preparação separada, sem reabrir lotes antigos.
