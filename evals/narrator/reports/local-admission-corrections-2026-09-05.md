# Correções locais de admissão — 05/09/2026

Continuação autorizada da revisão do batch
`e548ab8b-8fa1-4c80-ad98-966adca0c00b`. Implementação no worktree isolado;
checkout original, dados de campanha, `.env` e credenciais preservados. Sem
inferência externa, troca de modelo, instalação, migração ou alteração de corpus.
Nenhuma aprovação de CAP-001 é implícita nesta entrega.

## Correções executadas

### Mecânica e reação do mundo

`validate_mechanical_narrative` centraliza a checagem utilizada tanto pela
admissão estruturada quanto pelo contrato de prosa no fluxo real de turno.
Antes, essas duas entradas usavam expressões diferentes e podiam discordar.
O segundo contrato confere que a prosa corresponde à proposta fornecida.

- Uma reação visual delimitada — luz expondo formas anônimas — pode coexistir
  com falha em outro alvo. A exceção vale para esse predicado, não para a frase
  inteira. Identidade, prova, combinação, posse, outra concessão coordenada e
  formas que sejam o próprio objetivo continuam fora da exceção. Sem alvo
  identificável, mantém-se a rejeição conservadora.
- Uma investigação bem-sucedida pode ser corroborada por uma pista nova,
  estruturada e afirmada na narrativa. Não depende apenas de verbos exatos.
  Inspecionar um cadeado do galpão não equivale a inspecionar o galpão inteiro.
- A corroboração não usa porcentagem genérica de semelhança: preserva conteúdo,
  números e ordem dos elementos, com vocabulário relacional limitado. Os testes
  bloqueiam água/sangue, João/Pedro, 2/3 marcas, trajetória invertida, pista já
  conhecida, pista genérica, negação e hipótese.
- Perguntas, tarefas pendentes e diálogos citados não demonstram sucesso do
  personagem. Declaração de falha da investigação continua incompatível com
  resultado mecânico de sucesso.
- Estado afirmativo de barreira ativa aberta não contorna uma falha só por
  evitar o verbo “abrir”. Alvo nominal/fechamento anterior são considerados;
  boca, janela ambiental, outra porta, história passada, hipótese e incerteza
  não são automaticamente tratados como objetivo conquistado.

O resultado determinístico do motor continua sendo autoridade. Não se dá ao
modelo poder para converter falha em sucesso nem editar efeitos mecânicos.

### Agência implícita

Os controles existentes foram estendidos a construções delimitadas:

- mãos/dedos arrancando material e mão pressuposta sobre barreira;
- oração temporal de uso de instrumento, como “Ao mover a lanterna…”;
- pergunta que pressupõe seguir um rastro, entrar ou abrir algo antes de o
  jogador declarar a ação.

A validação exige família verbal e alvo compatíveis. Sensação involuntária,
NPC/ambiente explícito, percepção, evento nominal e convite condicional não são
genericamente confundidos com escolha do jogador. Nenhuma resposta é reparada
automaticamente nem nenhuma ação é executada para justificar a prosa.

### Identidade e persistência das pendências

Comparação específica ignora caixa, espaços e apenas `. ! ? …` terminais.
Palavras, acentos, números, símbolos e pontuação interna continuam significativos.
A nova projeção preserva o primeiro rótulo canônico; os eventos de abertura e
resolução não são duplicados por variações de pontuação. Uma resolução ainda
exige pendência conhecida e evidência. Propostas brutas, eventos anteriores e
saves não foram reescritos; não houve migração de dados históricos.

## Verificação

**1.205 testes passaram** na suíte completa `tests`, com rede bloqueada e
persistência isolada por fixture. Foram acrescentados **156 casos**:

- 38 de escopo/evidência mecânica e paridade com o contrato do turno;
- 30 de estado de barreira;
- 57 de agência implícita;
- 31 de identidade/projeção/eventos de pendências.

As skills `agentic-eval` e `pytest-coverage` orientaram reprodução dos erros e
contraprovas positivas/negativas, incluindo revisão independente. `pytest-cov`
não está instalado: nenhum percentual de cobertura é alegado. Único aviso da
suíte: depreciação preexistente do import `multipart` no Starlette.

## Replay das respostas originais

| Candidato | Admitidas após esta entrega | Turnos dependentes ausentes |
| --- | --- | --- |
| Qwen 3.8 27B | 2/5 | 2 |
| GPT-OSS 120B | 3/5 | 2 |

As contagens permanecem as da revisão local anterior; os motivos são mais precisos:

- Qwen/falha: sai de falso positivo mecânico para ação manual não declarada.
- GPT/investigação: sai da exigência lexical de sucesso para uso de instrumento
  não declarado. A pergunta também pressupõe deslocamento ainda não escolhido.
- GPT/falha: contato não declarado é detectado antes da mudança indevida de
  elenco, que permanece proibida.

Replays finais, sem novas gerações:

- Qwen: `20260905T223857Z-replay-8b1706c4-bf36-4262-8650-47999485100c`.
- GPT-OSS: `20260905T223858Z-replay-09fe64d7-c686-481b-bc85-fe3f783e4f94`.

SHA-256 do validador utilizado:
`2d2457c51e24c00b6591bf414a8ce4487df04464cf6990b5cc418b11fe1e4696`.
Hashes dos JSONLs originais conferidos contra a revisão anterior e novamente
após os replays: idênticos. Arquivos derivados não sobrescrevem os originais.

## Limites e próximo passo

Estas regras locais não equivalem a compreensão semântica universal. Permanecem
possíveis falsos positivos/negativos em formulações fora das construções
delimitadas, paráfrases extensas, agência metafórica ou troca de ponto de vista.
Corroborar uma pista por este mecanismo não prova a consistência de todas as
observações e frases do turno. Os problemas de voz, atmosfera sem avanço,
palavra truncada e divergência da velocidade da maré apontados na revisão
anterior não foram ocultados nem transformados em aprovação humana.

O prompt H6 e as amostras não mudaram; replay não demonstra melhora da geração.
Ambos os candidatos continuam com gates reprovados e sem avaliação completa de
continuidade. As correções locais descritas estão verificadas; a próxima rodada
ao vivo deve preservar candidatos, orçamento, corpus e todas as falhas, seguida
de revisão humana. Nenhum envio de campanha real está autorizado por esses
perfis sintéticos.
