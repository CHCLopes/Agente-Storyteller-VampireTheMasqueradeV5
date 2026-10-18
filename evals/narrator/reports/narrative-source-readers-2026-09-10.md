# Origem e leitores da direção B — 10/09/2026

Concluído o incremento interno do [plano de origem e leitores](../../../plan/architecture-narrative-source-readers-1.md).
A ponte agora exige origem persistida de campanha nova e lê a história elegível
em um snapshot SQLite antes de selecionar fontes e montar o contexto.
A prova usa narrativas autoradas, FakeLLMAdapter e bancos temporários.

## Comportamento verificado

- `create_narrative_source_campaign` registra sessão, local/elenco e fingerprint
  pela operação explícita do servidor. Recusa sessão existente, inclusive v1 vazia.
- `read_source_context_snapshot` confere origem, revisão, estado, dependências e
  todos os turnos/pares/recibos em uma transação de leitura. Só depois aplica a
  audiência e a janela das duas fontes recentes. História incompatível fora da
  janela também causa recusa; fonte inacessível não é substituída por uma antiga.
- `execute_source_turn` usa a cena registrada e exige correspondência do chamador.
  Recusa contexto livre; não chama leitores v1 de memória, consolidação ou montagem.
  Campos opacos do personagem preservados no estado não entram no pacote H6.
- O recibo `narrative_source_context` guarda origem, revisão e IDs selecionados/
  omitidos. É validado antes da entrega e novamente na mesma transação do commit.
  A reserva da tentativa ancora protocolo e revisão de estado antes da geração.
- A consulta interna direta reutiliza o snapshot sem gerar narrativa, rolar dados
  ou gravar turno. Replay concluído revalida a elegibilidade histórica e seu par,
  sem nova chamada ao modelo ou entrega. O CAS e a entrega provisória permanecem.
- Escritas genéricas não instalam, removem ou alteram a origem. Atualização de
  snapshot e conclusão de controle recusam cena/contexto conhecidos incompatíveis.
  Commit v1 não entra em campanha marcada B. Remover origem após a reserva não
  desativa a obrigação, inclusive no replay de commit.

No controle positivo de quatro turnos, a primeira narrativa tem mais de 600
caracteres; `n` permanece integral, `q` separado e a cena não recebe resumo.
Os turnos 1 e 2 usam o mesmo texto com identidades distintas, preservadas como
fontes distintas. O quarto pedido recebe fontes 2 e 3 e registra a omissão da 1.
Após reinício, a consulta recebe fontes 3 e 4 e registra as anteriores.

## Verificação e revisão

**444 testes passaram**, sem falhas, erros ou skips, em 36,16 s de pytest.
O grupo final cobre 12 arquivos: contratos B, origem, persistência, ponte,
persistência legada, execução/pipeline de turnos, memória, contexto, cena e
regressões do uso teste. Os seis arquivos de implementação/teste alterados
mantiveram os mesmos hashes antes e depois da rodada.

Antes da correção, uma contraprova mostrou a ponte aceitando campanha sem origem.
A revisão independente encontrou dois caminhos adicionais: commit/replay após
remoção da origem e gravação de cena incompatível por conclusão de controle.
Seis contraprovas desses caminhos falharam como esperado antes das guardas e
passaram depois. A revisão final conferiu as duas correções sem achado material
pendente. Não somar rodadas intermediárias ao total de 444 testes distintos.

A transação de leitura foi exercitada com uma escrita concorrente; o snapshot
conservou sua revisão e a consulta seguinte detectou a revisão nova. Outros
controles cobrem CAS após leitura/entrega, callback, cancelamento, pareamento
corrompido, contexto legado fora da janela, audiência, recibo e USER acima do teto.

Permanece um aviso preexistente de `python_multipart` em Starlette. Rede externa
foi bloqueada pelo conftest, dotenv desativado; nenhuma chamada real, acesso a
chave, mudança de default, frontend ou banco do uso teste ocorreu nesta etapa.

## Alcance da conclusão

TASK-BI-009 a 012 estão atendidas na entrada interna de cena conhecida, com seed
fixo e histórico integral B; as rotas atuais do produto continuam v1. Isso não
significa que campanhas arbitrárias v1 possam usar B, nem que consultas livres
de lore ou abertura generativa tenham sido integradas. O getter B anterior de
baixo nível mantém seu contrato histórico; a ponte exige o leitor completo novo.

O servidor continua responsável pelos produtores do rascunho, estado e fatos.
Os tipos e fingerprints não autenticam um chamador hostil ou um banco reescrito.
A validação do estado examina caminhos narrativos conhecidos, não o significado
de todo campo opaco. Toda a história é conferida, mas somente duas fontes entram
no USER; não há prova de continuidade arbitrária ou avaliação de desempenho em
campanhas longas. O teto continua 12.000 caracteres, sem corte ou resumo.

Fonte atribuída continua `source_only`/`not_assessed`; não confirma cada afirmação
da prosa. Abertura, novos NPCs, transições e encerramento de campanha continuam
frentes próprias. O feedback positivo do uso teste não reclassifica experimentos
encerrados nem aprova CAP-001. A pauta de campanha híbrida permanece adiada.

Hashes e evidências da rodada: [registro verificável](narrative-source-readers-2026-09-10.json).
