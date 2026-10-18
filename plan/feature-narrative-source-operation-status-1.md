---
goal: Consultar estado e causa segura de operação B retida sem nova execução
version: 1
date_created: 2026-09-10
last_updated: 2026-09-11
status: 'Completed'
---

# Consulta interna de operação B retida

Retomado em 11/09/2026 por solicitação do usuário, após o preflight do worktree.
Implementação local concluída e verificada. O lote source-context anterior continua encerrado;
este incremento não necessita observação externa nem credencial.

Incremento reversível da integração da direção B já autorizada. O coordenador
preserva o recibo e impede reenvio de pending/terminal; sua reexecução terminal
mantém o código genérico anterior. A nova consulta pareia tentativa/cápsula/turno
e devolve o diagnóstico seguro da causa original, preservando o comportamento
de execução. Antes deste incremento, essa consulta composta não existia.

## Contrato antes do código

`SQLitePersistence.read_source_operation_status(session_id, operation_id)` retorna
`SourceOperationSnapshot | None`. Novo modelo puro em api/narrative_source_status.py.
Protocolo próprio: narrative-source-operation-status-v1. Campos: protocol,
session_id, operation_id, capsule_sha256, base_turn, base_state_revision,
current_turn, current_state_revision, status, committed_turn_id e failure.

Estados observados: retained_unstarted, pending, completed, failed, timeout,
cancelled. O estado retained_unstarted não promete que a base ainda é atual.
Não expor can_retry/can_execute/ready nem autorizar takeover/reenvio.
committed_turn_id somente em completed validado. failure somente em terminal
de falha, com código literal de allowlist fechada e estágio fechado ou ausente;
diagnóstico desconhecido/fora da allowlist fica indisponível. Não retornar
error_json bruto, narrativa, pergunta, prompt, ficha, relações ou evidência livre.

Uma única transação de leitura sobre banco existente: validar schema atual sem
inicialização/migração, origem/história B, controle da cápsula, identidade estática
da tentativa H6 e pareamento do turno comprometido. Conexão SQLite mode=ro,
fechada explicitamente; não criar diretório/banco ou chamar initialize.
Sem cápsula e sem tentativa/turno correspondente: None em campanha B válida.
Registro órfão, controles divergentes, estado/identidade/hash incompatíveis:
erro fechado. Banco ausente, schema antigo ou cena/origem incompatível: recusa.

Reutilizar validadores existentes na mesma conexão. A reconstrução pura da
identidade de tentativa a partir da cápsula seguirá o formato atual e será
comparada com a tentativa efetivamente reservada nos testes. Preservar executor,
coordenador e a identidade dos commits; nenhuma refatoração adicional.

## Tarefas e propriedade

| Tarefa | Entrega | Concluída |
|---|---|---|
| TASK-001 | Modelo puro, diagnóstico fechado e identidade esperada; tests/test_narrative_source_status.py. | Sim |
| TASK-002 | Método transacional em api/persistence.py; tests/test_narrative_source_status_persistence.py. | Sim |
| TASK-003 | Revisão independente, regressões pertinentes e preservação das funções anteriores. | Sim |
| TASK-004 | Relatório de evidência, README e próximo passo na retomada. | Sim |

## Contraprovas necessárias

- Ausente, retida sem H6, pending, completed e cada terminal, inclusive após reinício.
- Código original seguro disponível; conteúdo livre/código desconhecido não sai.
- Cápsula/tentativa/turno órfãos ou adulterados recusados, inclusive hash/metadata.
- Base antiga mostra revisões distintas sem falsa prontidão.
- Consulta intercalada com commit conserva fotografia única transacional.
- Consulta não reserva, chama gateway, rola dados, emite chunk ou altera estado.
- Banco ausente/antigo não é criado/migrado; modelo rejeita tipos/combinações inválidos.
- Regressões focadas de retenção, coordenação, contexto e persistência mantêm comportamento.

Testes offline com conftest de isolamento ativo. Rodadas por superfície congelada;
repetir somente controles afetados por mudança/falha ou risco demonstrado.

## Limites

Nenhuma rota pública/UI/default/save real, nova observação/credencial, mudança
de admissão narrativa, política de retry, produtor antes do RNG ou DDL. A consulta
é informação interna observada, sem prova de qualidade narrativa ou CAP-001.
O diagnóstico cc09080a está encerrado; seu sucesso técnico não foi promovido a
qualidade integral e seus artefatos/executáveis históricos permanecem intactos.

Fechamento em 11/09/2026: 673 casos distintos verificados em rodadas focadas,
98 novos; revisão independente encerrada, 93 funções anteriores preservadas.
[Evidência e limites](../evals/narrator/reports/narrative-source-operation-status-2026-09-11.md).
