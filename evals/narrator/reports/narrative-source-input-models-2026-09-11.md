# Modelos internos do produtor B — 11/09/2026

Concluídos TASK-001/002: contratos puros de configuração, pedido original, claim
observado, falha segura e conclusão do produtor. Somente dois arquivos novos;
reserva SQLite e produção mecânica são os incrementos seguintes.

## Comportamento entregue

- Modelos estritos, congelados, sem campos extras, com cópias e revalidação de
  instâncias adulteradas. JSON não finito, handles e segredos de configuração recusados.
- IDs do produtor dependem de protocolo, sessão e identidade lógica. Pedido original
  conserva input, horário, snapshot, estado/relacionamentos e configuração; mudanças
  nesses dados mudam fingerprints/hashes, sem inventar outra identidade de operação.
- Conclusão preparada exige cápsula vinculada integralmente ao pedido, incluindo
  estado/relacionamentos idênticos no perfil ordinário inicial. Falhas, esclarecimento
  e recusas de escopo são terminais sem cápsula.
- request_sha256 da conclusão é o hash do pedido no formato attempts, separado do
  fingerprint do modelo. Metadata terminal preserva o pedido inicial.
- newly_claimed descreve um retorno futuro da transação; construir esse modelo em
  memória não autentica uma reserva nem permite disparar produção.

## Evidência

Rodada congelada única: **167 testes passaram em 4,14 s**: 57 novos, 38 regressões
de cápsula e 72 da entrada. Zero falhas/skips; um aviso preexistente python_multipart.
Saída 0 e sucesso do shell conferidos no result.json e JUnit. Conftest e isolamento
de rede ativos, dotenv desabilitado. Nove arquivos existentes preservados no freeze.
Revisão independente do código, hashes e log encerrada sem bloqueadores.

Quatro contraprovas SQLite temporárias compararam hashes com controles existentes
completed/failed/cancelled/timeout efetivamente gravados. Elas comprovam formato;
não implementam claim nem finalização P/K. Os casos deste incremento e da entrada
totalizam 256 distintos: os 72 testes da entrada reaparecem nesta rodada.

## Limites e continuidade

Nenhuma persistência nova, RNG, classificador, serviço, chamada externa, interface
ou aprovação CAP-001 foi introduzida pelos modelos. Hash não autentica servidor.
A recuperação anterior process_interrupted exige validação separada do formato
histórico na próxima camada, sem reescrever os registros.

Próximo incremento: claim_source_input/finalize_source_input e provas transacionais
de concorrência, interrupção, replay, integridade e preservação das funções antigas.

- [Plano do produtor](../../../plan/feature-narrative-source-input-producer-1.md)
- [Evidência estruturada](narrative-source-input-models-2026-09-11.json)
