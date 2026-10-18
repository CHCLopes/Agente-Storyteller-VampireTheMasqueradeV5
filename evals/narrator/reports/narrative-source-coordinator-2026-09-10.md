# Direção B — preparação retida e coordenação interna

Concluído em 10/09/2026, no worktree `b008`. O incremento mantém em SQLite o
recibo mecânico já resolvido, o rascunho e os argumentos estáticos necessários
à primeira execução H6 ou ao replay. A entrada permanece interna e optativa.

## Comportamento implementado

`prepare_retained_source_turn` lê o snapshot B, cria uma cápsula validada e a
retém antes de qualquer H6. `execute_retained_source_turn` recebe somente a
identidade da operação e recursos transitórios, recupera essa cápsula e usa o
executor existente. O servidor não precisa reconstruir o recibo após reinício.
Nenhuma dessas funções chama classificador, RNG ou `prepare_turn_pipeline`.

`SourceTurnCapsule` inclui snapshot-base, preparação tipada, draft, estado,
relacionamentos e configuração estática de H6. A validação reconstitui o draft
pela função pura e compara o fingerprint do conjunto. Sessão e cena são
derivadas do snapshot. Hash comprova consistência, não autenticação nem verdade
semântica. Membros aninhados são copiados e revalidados nas fronteiras.

`save_source_preparation` usa uma transação SQLite e uma operação técnica de
controle separada, com status completed e committed_turn_id nulo. Esse status
significa preparação persistida. Não cria turno nem avança revisão/estado.
`load_source_preparation` verifica origem, história completa, prefixo original,
campos da tentativa e hashes. Uma cápsula nova não pode capturar H6 já iniciada.
Repetição igual é idempotente; conteúdo diferente conflita.

| Situação | Resultado |
|---|---|
| Cápsula pronta; H6 ausente | Revalidar base e iniciar a primeira execução. |
| H6 pending | Retornar pendência; nenhum takeover ou reenvio. |
| H6 completed | Replay validado do turno original, inclusive após avanço da janela. |
| H6 failed/cancelled/timeout | Conservar terminal e cápsula; nenhuma nova chamada. |
| Base obsoleta | Recusar antes do gateway; preservar cápsula e estado atual. |

A reserva existente arbitra concorrência da mesma sessão/operação. Operações
distintas continuam disputando o CAS de commit. Um crash depois da reserva H6
pode ocorrer antes ou depois do envio; o código não presume qual ocorreu.
A recuperação legada pode cancelar pending, sem autorizar outra tentativa.

## Verificação

**575 testes distintos passaram em uma rodada final**, zero falhas, erros ou
skips, em 34.797 s. Foram 17 arquivos de testes: 491 casos
anteriores e 84 novos (38 de cápsula, 30 de persistência, 16 de coordenação).
É uma regressão focada; não uma execução da suíte inteira do projeto.

As provas incluem motor mecânico real com dados controlados para sucesso/falha,
SQLite temporário, respostas FakeLLM autoradas, reinício antes de H6, falha
terminal, dois chamadores concorrentes, interrupção depois da reserva,
cancelamentos repetidos, quatro turnos e replay após mudança da janela, mutações
de cápsula/row/história, controles que avançam somente a revisão e CAS obsoleto.
Valores literais e recibos permanecem preservados. O pacote H6 continua usando
fontes integrais atribuídas e pergunta separada; não produz memória abstrativa.

As duas questões da revisão foram corrigidas: espera da retenção diante de
cancelamentos repetidos e alinhamento da identidade da sessão entre cápsula e
persistência. A primeira rodada integrada teve 15 falhas/1 passagem pelo
desalinhamento; a seguinte, 15 passagens/1 falha por falta de `started_before`
no teste de recuperação. O teste foi alinhado à API existente. Esses resultados
intermediários permanecem em XML; a rodada final não os reclassifica.

Os hashes ficaram estáveis durante a execução final. Comparação AST com a linha
de base confirmou as funções anteriores de persistência intactas, inclusive DDL;
foram adicionados sete métodos auxiliares/públicos. O executor anterior não mudou.
O único aviso foi o PendingDeprecationWarning preexistente de `python_multipart`.
Dotenv e rede externa bloqueados pelos controles de teste. Zero chamadas reais,
nenhuma chave lida, nenhum acesso ao save do uso teste ou ativação na interface.

Prova legível por máquina: [JSON do incremento](narrative-source-coordinator-2026-09-10.json).
Evidência local: `C:\Users\skate\AppData\Local\Temp\storyteller-coordinator-20260910`. XML e saída final têm hashes no JSON.

## Limites e continuidade

A garantia começa na retenção de um recibo **já resolvido**. Esta composição não
oferece uma guarda anterior ao RNG do chamador, retry de terminal, execução
exatamente uma vez depois de crash ou a política futura de pausa/retomada.
Gateway, chave, callback, cancelamento e deadline não são persistidos.
`protected_secrets` não vazio é recusado. Conteúdo público/sintético é requisito
do chamador; não há detector semântico de credenciais em texto opaco.

Permanecem o perfil de cena conhecida/elenco fixo, source_only/not_assessed,
as duas fontes e os limites existentes. Default, UI, save, CAP-001 e planejamento
da campanha híbrida não são promovidos por esta prova.

Próximo recorte técnico: preparar um harness sintético da entrada retida completa,
com base nova e alvo explícito, que permita observar continuidade real e falhas
sem usar saves v1. Preparar e verificar esse harness localmente antes de solicitar
credencial. O produtor anterior a H0/H1/RNG e a progressão geral de campanha
continuam superfícies distintas, ainda sem implementação neste incremento.

Plano: [coordenação B](../../../plan/architecture-narrative-source-coordinator-1.md).
