---
goal: Vincular a ponte B à origem persistida e fechar a elegibilidade dos leitores
version: 1.0
date_created: 2026-09-10
last_updated: 2026-09-10
status: Completed
product_default_changed: false
save_migration: none
---

# Origem e leitura de contexto na direção B

Retomada autorizada em 10/09, após o usuário aprovar o roteiro de planejamento
da campanha híbrida e concluir o uso teste por ora. O feedback sobre a experiência
foi positivo, com problemas pontuais reconhecidos. Esta frente continua do ponto
anterior ao teste com interface: TASK-BI-009 a012 do desenho de integração.
O checklist de campanha permanece para depois das tarefas em andamento.

## Resultado delimitado

A ponte interna B exige uma origem de cena registrada na criação de
uma campanha nova e um snapshot transacional de contexto. A cena vem dessa
origem; as narrativas anteriores continuam atribuídas e integrais. A leitura
não utiliza os caminhos v1 de resumo, memória, fatos reservados ou lore.

O trabalho usa fixtures e SQLite temporário. Preserva o jogo atual, seus saves,
os experimentos encerrados, o default v1 e os protocolos históricos. Não oferece
abertura generativa, novos NPCs, transições ou integração de toda a campanha.

## Requisitos

- SR-001: Criar origem versionada somente em campanha inexistente, pela operação
  interna do servidor, com sessão e seed de local/elenco. Recusar também sessão
  v1 vazia; não instalar marcador ou apagar contexto para torná-la elegível.
- SR-002: Origem é preservada pelos caminhos de escrita da aplicação. Identidade
  e fingerprint verificam integridade; não autenticam cliente hostil, provedor
  ou banco deliberadamente reescrito. Rascunhos mecânicos continuam sob autoridade
  dos produtores internos, não passam a ser confiáveis apenas por uma etiqueta.
- SR-003: Ler origem, revisão, dependências, turnos e tentativas em um único
  snapshot SQLite. Conferir toda a história elegível antes de escolher a janela.
  Memórias/candidatos/consolidações v1, fatos ficcionais incompatíveis e contexto
  rico exigido causam recusa explícita; nenhum resumo é silenciosamente promovido.
- SR-004: Local/elenco recebidos pelo executor devem coincidir com a origem
  persistida. Campos reconhecidos de cena/contexto no estado devem ser compatíveis;
  outros campos opacos preservados não são introduzidos no pacote H6.
- SR-005: Recuperar as duas fontes mais recentes, obrigatórias e autorizadas,
  preservando ordem e identidade. Fontes anteriores são omitidas inteiras segundo
  a janela já existente, com IDs registrados. Não substituir fonte inacessível
  por outra antiga nem deduplicar origens pela igualdade do texto.
- SR-006: Persistir recibo versionado de origem/revisão/seleção no contexto do
  turno, ao lado do envelope B. Validá-lo antes da entrega e novamente no commit;
  conservar a reserva idempotente da tentativa e o CAS.
- SR-007: Consultas internas B usam o mesmo leitor de snapshot sem geração,
  RNG ou commit. Abertura ausente, lore e consultas livres v1 não entram por essa
  rota; o produto continua selecionando seus caminhos atuais.
- SR-008: Manter os tetos existentes: até duas fontes e 12.000 caracteres no
  USER completo, sem corte ou resumo. Fonte source_only continua not_assessed.

## Execução

- [x] Contrato puro de origem, snapshot e seleção com erros fechados.
- [x] Criação nova e leitura transacional; guardas de escrita e compatibilidade.
- [x] Integração obrigatória ao executor B, preservando replay e validação antes da entrega.
- [x] Contraprovas de leitores indiretos, origem, audiência, orçamento e concorrência.
- [x] Revisão independente, regressões pertinentes, relatório e atualização da retomada.

## Verificação

Provar três turnos e reinício com n acima de 600 caracteres, q separado, fontes
atribuídas e cena derivada da origem. Estender a quatro turnos para conferir a
omissão explícita da primeira fonte. Cobrir registro sobre sessão existente,
origem removida ou copiada de outra sessão, cena do chamador divergente, dependência
v1 inclusive fora da janela, fatos reservados, consolidação, fonte invisível,
adulteração do recibo e CAS após leitura. Conferir ausência de leitores v1,
gateway, chunks e novos commits nas recusas anteriores à geração. Rede externa
e dotenv permanecem desativados nos testes.

Superfícies: novo api/narrative_source_context.py; api/persistence.py;
api/narrative_source_execution_service.py; testes focados e documentação.
O getter baixo nível anterior permanece compatível; a entrada B usará o leitor
completo obrigatório. Não modificar frontend, memória abstrativa, fontes de
experimentos encerrados ou o banco do uso teste.

Referências: [desenho de integração](../evals/narrator/reviews/narrative-source-integration-design-2026-09-07.md),
[ponte concluída](architecture-narrative-source-bridge-1.md),
[checklist adiado](checklist-planejamento-campanha-hibrida.md).

Fechamento: 444 testes distintos passaram em uma rodada final, com hashes estáveis
e revisão independente concluída. [Relatório e limites](../evals/narrator/reports/narrative-source-readers-2026-09-10.md).
