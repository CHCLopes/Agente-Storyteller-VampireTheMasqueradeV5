# Consulta interna de operações B — verificação local

Concluída em 11/09/2026. `SQLitePersistence.read_source_operation_status(session_id,
operation_id)` retorna uma fotografia tipada do estado da operação retida e da causa
original segura de falha. A consulta não executa novamente a operação.

## Resultado e comportamento

- Estados: `retained_unstarted`, `pending`, `completed`, `failed`, `timeout`, `cancelled`.
- Revisões da base e atuais ficam distintas; preparação antiga não ganha promessa de prontidão.
- Código/estágio de falha vêm de listas fechadas. Texto livre, narrativa, pergunta, prompt,
  ficha, relações, mensagens do provedor e campos extras não saem na resposta.
- Banco existente aberto em `mode=ro`, um único `BEGIN` anterior à leitura do schema,
  origem/história e vínculos revalidados na mesma conexão, fechamento explícito.
- Banco ausente/antigo ou história incompatível são recusados sem criação/migração.
- Cápsula, tentativa H6 e turno precisam concordar em identidades e hashes. O resultado
  concluído é recomposto com a base disponível na cápsula retida; isso não generaliza
  a recomputação a turnos históricos sem cápsula nem autentica conteúdo criptograficamente.
- Nenhuma reserva, retomada, rolagem, chamada de modelo, entrega ou commit ocorre na consulta.

## Evidência

**673 casos distintos verificados em rodadas focadas: 98 novos e 575 regressões.**

| Superfície | Resultado |
|---|---|
| Modelo puro | 59 passaram na primeira rodada, 2,48 s; evidência na saída da ferramenta, sem XML/log separado. |
| Persistência nova | 39 casos distintos com último resultado verde. Rodada inicial: 37 passaram e uma asserção usou nome de campo incorreto; dois controles afetados passaram após correção. |
| Revisão adicional | Concorrência/fechamento fortalecidos e novo caso de JSON profundo passaram, 3,10 s. |
| Regressões existentes | 575 passaram, zero falhas/erros/skips, 43,38 s, hashes estáveis durante a rodada. |

Após a regressão ampla, a única alteração de produção foi incluir `RecursionError`
na recusa da nova fronteira. A reversão desse trecho reproduz exatamente o hash
testado; a contraprova específica passou. Não houve repetição desnecessária dos 575 casos.
Um aviso preexistente de `python_multipart` permanece; nenhuma dependência foi alterada.

Os controles integrados incluem ausência/preparação/pending após reinício; falha real
do FakeLLM, timeout, política, entrega, cancelamento e recuperação explícita;
recibos mecânicos positivos/negativos; controles de revisão; quatro turnos com consulta
da operação antiga; base obsoleta; identidades deslocadas e hashes corrompidos.
A consulta concurrente observou pending/revisão anterior enquanto outro commit terminou;
uma nova leitura viu completed/revisão nova. O teste prova fechamento sem confundir
erro de thread com conexão fechada.

Revisão independente encerrada sem achados bloqueadores. Foram preservadas, com texto
idêntico, as 93 funções anteriores de `api/persistence.py`; adicionaram-se três métodos
e uma importação de tipo. Executor, coordenador, cápsula, contexto, preparação e perfil
mantiveram os hashes anteriores. O checkout original foi preservado.

[Relatório estruturado, hashes e rodadas](narrative-source-operation-status-2026-09-11.json).
Logs/XML de integração e regressão ficam nos diretórios Temp indicados no JSON;
seus hashes e resultados estão registrados ali. A rodada do modelo tem evidência de ferramenta.

## Limites e continuidade

Zero chamada externa, leitura de segredo ou acesso a campanha real. Dotenv desativado
e conftest de isolamento ativo. Default/UI, política pending/terminal, CAP-001 e
artefatos históricos de observação permanecem preservados. Esses testes não avaliam
qualidade da prosa ou aprovação de modelo.

Próxima etapa: consolidar o desenho executável da primeira entrada optativa B,
identificando o produtor anterior ao recibo e os critérios de abertura/progressão
antes de ativar qualquer rota. O diagnóstico source-context anterior continua encerrado.
