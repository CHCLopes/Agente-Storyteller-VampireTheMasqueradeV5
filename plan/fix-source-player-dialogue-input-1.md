---
goal: Permitir fala natural no ensaio com Mara por composição explícita da entrada existente
date_created: 2026-09-12
status: 'Completed'
---

# Correção do campo de conversa do ensaio B

O usuário executou o recorte apresentado e informou a primeira fala:
`Mara, me fale sobre este lugar`. Essa informação vem da mensagem posterior do
usuário; não foi recuperada de journal, banco ou captura de tela.

A sessão6486b938 iniciou e encerrou stopped/0, sem força, com
admission_unavailable e zero chamadas. Auditoria somente leitura confirmou zero
P/K/H, tentativas, turnos e eventos; 45 inputs e 50 entradas do binding íntegros.
A guarda atual exige fala delimitada como Digo a Mara: "...". A frase livre não
corresponde a essa gramática. O relatório distinguirá reprodução dessa recusa da
ausência de um motivo específico no status original.

## Mudança mínima

- Apenas a entrada interativa real oferece Conversar/Aguardar. O jogador escolhe
  explicitamente o tipo de ação; no modo Conversar, escreve a fala normalmente.
- A interface compõe Digo a Mara: seguido da fala literal entre um dos pares de
  aspas já aceitos. Não interpreta texto livre como ação mecânica, não expande o
  parser e não altera silenciosamente o conteúdo da fala.
- Aguardar produz Aguardo. somente após escolha e envio explícitos. Trocar modo
  não envia, não aloca operação e não apaga o rascunho antes do envio.
- Validar composição antes de gerar ID/dispatch/send. Conteúdo vazio/incompatível
  com o envelope existente, excesso de500pontos de código, NUL ou conflito com
  todos os delimitadores recebe erro local, conserva o rascunho e não fecha a sessão.
- Manter deadline, cooldown, consultas, identidade, unavailable, backend, parser,
  RNG, alvos, SYSTEM e teto de quatro chamadas. Default ordinary/fixture preservados.
- Helper puro no arquivo de view já congelado, evitando dependência fora da lista
  de inputs. SourcePlayerTrial fornece explicitamente Mara para este recorte fixo.

Não há mudança de arquitetura, narrador ou regras. Trata-se da apresentação de
ações que o núcleo já aceita. A execução do recorte pelo usuário não aprova sua
qualidade; nenhuma inferência ocorreu nessa sessão. Não relançar nem repetir a
ação fechada automaticamente. Próxima execução será outra sessão delimitada.

## Verificação e preservação

Baseline antes de editar, contraprova da fala crua e composição, testes focais da
view/entrada e um turno com HTTP simulado: fala preservada no USER, aliases de Mara,
sem RNG; consulta não gera outra chamada. Lint/TypeScript/build e preflight conjunto
no código final. Guardar a observação6486 com as fontes do checkpoint anterior,
sem atualizar retroativamente seus hashes, resultados ou conteúdo do banco.

Status: implementação e revisão concluídas.51 casos UI reconciliados,2 backend simulados, lint/TypeScript/build e preflight final aprovados. Nenhuma chamada real nesta correção. Evidência em [relatório](../evals/narrator/reports/source-player-dialogue-correction-2026-09-12.md).
