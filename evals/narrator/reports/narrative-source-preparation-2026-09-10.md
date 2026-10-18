# Preparação interna B — 10/09/2026

Concluído o [preparador delimitado](../../../plan/architecture-narrative-source-preparation-1.md)
que liga decisões e recibos do servidor ao TurnDraft consumido pela ponte B.
É o incremento seguinte à origem e aos leitores concluídos no mesmo dia.

## Comportamento

`prepare_source_turn_draft` recebe um SourceContextSnapshot revalidado, identidade
da operação, instante, texto do jogador e uma de duas variantes explícitas:

- `DeclaredActionPreparation`: o servidor já classificou a ação como declaração
  sem teste. O adaptador não deduz isso do texto e não chama classificador.
- `ResolvedActionPreparation`: conserva V5ActionPayload e ResolutionResult de
  teste ordinário já resolvido pelo servidor. Dados, sucessos, margem, resumo e
  demais valores do recibo chegam literais ao fato; dificuldade e pool são
  apresentados a partir do payload/recibo fornecidos, sem nova resolução.

O produtor gera apenas action.declaration/player_action_declared ou
mechanics.resolution/player_action_resolved, com IDs estáveis por sessão/operação
e revisões do snapshot. Não recebe fatos arbitrários ou n/q como preparação.
Referências identificam o adaptador que produziu o registro, sem afirmar que a
presença de uma etiqueta prova a execução do motor. A integração exercita essa
execução separadamente com calculate_resolution real e dados controlados.

Poderes, combate, alimentação, cura, rerrolagem e demais flags com efeitos fora
do recorte são recusados, assim como messy/bestial. Nenhum caso é convertido
silenciosamente em declaração. O adaptador não altera ficha, relações ou cena.

## Verificação

**40 testes próprios passaram em 1,04 s e 7 cenários de integração passaram em
rodadas focadas**, sem repetir os casos já verdes. Os novos arquivos e os
arquivos de referência foram conferidos por hash; nenhuma implementação do
incremento anterior mudou. A revisão independente não deixou achado material.

Os cenários verificam declaração, sucesso/falha, recibo literal no rascunho,
USER e SQLite, continuidade da fonte integral após reinício, falha narrativa
sem commit e replay sem nova geração ou rolagem. Depois da única resolução
real controlada, qualquer nova chamada ao motor/RNG faz o teste falhar.
Leitores v1 e o pipeline de H0/H1/H4 são bloqueados pelas fixtures; todas as
requisições do adaptador falso pertencem à operação H6.narrative_source.

A primeira rodada de integração teve 3 positivos e 2 expectativas incorretas:
FIRST, uma narrativa neutra, foi recusada por scene_success_not_honored ou
scene_failure_not_honored. FIRST permaneceu intacto, e esses dois casos passaram
a exigir a recusa específica, sem chunk/commit. Dois positivos separados foram
acrescentados com narrativas autoradas de descoberta ou investigação inconclusiva.
O delta de quatro casos passou em 3,08 s. Nenhum gate ou resultado histórico foi
alterado para produzir aprovação.

Somados ao grupo anterior de 444 casos, são **491 cenários distintos verificados
nesta retomada**, por etapas; não é uma execução única de toda a suíte do projeto.
O único aviso observado continua sendo python_multipart/Starlette preexistente.
Rede externa e dotenv permaneceram bloqueados; nenhuma chamada real ou chave.

## Limites e continuidade

O recibo continua uma premissa de confiança do chamador servidor. O preparador
não autentica esse chamador, não recalcula aritmética e não classifica intenção
livre. Ele verifica tipos, identidade e compatibilidade do recorte. A ponte e
SQLite continuam responsáveis pela elegibilidade atual, reserva e CAS.

O chamador deve conservar o rascunho/recibo já preparado após falha; este módulo
não implementa retenção automática nem autoriza retry de tentativa terminal.
Os controles provam transporte e comportamento com fixtures, não qualidade de
provedor, fidelidade semântica geral ou experiência completa de campanha.
O jogo atual não seleciona essa rota e o save do uso teste foi preservado.

O próximo encaixe é uma entrada interna que coordene snapshot, preparação e
retenção do rascunho do servidor antes de H6, sem executar o pipeline v1 inteiro.
Esse trabalho deve manter a reserva idempotente e recusar entrada incompatível
antes de classificadores/RNG. Abertura, progressão livre, elenco/local variável
e a campanha híbrida continuam fora destes dois incrementos concluídos.

Evidências e hashes: [registro verificável](narrative-source-preparation-2026-09-10.json).
