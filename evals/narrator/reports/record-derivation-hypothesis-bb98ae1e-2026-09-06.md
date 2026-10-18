# Hipótese proposta — derivação de registros a partir de narrativa fixa

Data: 06/09/2026. Origem: análise do lote `bb98ae1e-529b-4645-be17-ffe42734db14`.
Status: **proposta documental pronta para decisão; implementação e execução
não autorizadas por este documento**. Nenhum novo SYSTEM, schema, runner ou
chamada foi criado. Não é decisão de arquitetura do produto nem promoção
de modelo, runtime ou CAP-001.

## Problema e hipótese

No bb98, a abertura e Mara passaram na admissão, mas os registros fortaleceram
certeza ou criaram uma ligação entre pistas ausente da narrativa. O galpão
também acrescentou causalidade somente no resumo. As correções determinísticas
do validador e do pacing não resolvem essas relações semânticas.

Hipótese a investigar: **quando a narrativa já está fixa e a tarefa da chamada
é somente derivar os registros, o candidato consegue conservar responsável,
acontecimento, estado e certeza sem completar outra história nos derivados**.

É uma hipótese operacional de capacidade, não uma causa demonstrada. Os lotes
anteriores não provam que gerar narrativa e registros juntos causa a falha,
nem que uma segunda etapa a corrige. A proposta testa a derivação isolada;
não mede ainda uma cadeia de duas chamadas nem demonstra vantagem causal.

## Por que esta hipótese é distinta

As variantes anteriores mantiveram uma chamada para gerar todos os campos e
variaram o SYSTEM. Este desenho fixa a narrativa como entrada e altera a
responsabilidade da chamada e seu schema de resposta experimental. Por isso
não é outra variante SYSTEM-only, A/B completo ou repetição de faithful.

O foco vem dos erros efetivamente observados, sem trocar de modelo ou provedor.
Usar um juiz LLM, flexibilizar os validadores ou reescrever respostas antigas
não é necessário para esta sondagem. Nenhuma dessas ações integra a proposta.

## Duas entradas fixas, com proveniência

Fonte preservada:
`eval-results/20260906T234523Z-e141618c-c050-4eab-884c-37b50558c17d/gpt-oss-120b-groq-free-synthetic-low.jsonl`.
SHA-256:
`f682846c98cd7ea0d1982ccceddea4033932bd6f1c564576a0f7e4cd9ec00288`.

| Entrada | Campo fixado | Questão observada |
| --- | --- | --- |
| Abertura, linha 3 | `proposal.narrative` integral | Uma sugestão de observação não deve virar presença certa; o lugar deve se apoiar no que a narrativa estabelece. |
| Mara, linha 9 | `proposal.narrative` integral | Papel sobre o balcão não estabelece conteúdo/endereço ou recebimento pelo jogador. |

As duas narrativas foram geradas pelo modelo com fixtures sintéticas e foram
admitidas pela política vigente; isso não aprova sua qualidade integral.
A sondagem deve tratá-las como **entradas fixas de uma avaliação separada**.
Não são predecessores importados para o corpus, cenas de campanha ou uma
substituição das respostas originais. O galpão recusado não entra como
predecessor nem como entrada desta sondagem.

O pacote de entrada incluiria somente narrativa fixa, ação original,
resultado mecânico esperado e contexto visível original necessário à cena.
Não incluiria os antigos resumo, fatos, pergunta ou pendências produzidos
pelo modelo, pois revelariam ao candidato os derivados que se quer avaliar.
As pendências e fatos do contexto anterior continuam identificados como
estado anterior. Abertura e Mara não contêm segredos protegidos neste corpus;
portanto este teste não mediria separação confidencial.

## Contrato experimental proposto

1. Uma chamada por entrada, com a narrativa imutável no pacote USER.
2. A resposta conteria apenas os campos derivados equivalentes a
   `o/l/s/p/f/t/r/q`, mantendo o contrato de atores dos fatos.
3. O avaliador experimental comporia uma nova proposta para inspeção usando
   o `n` fixo e os campos retornados, registrando suas origens separadamente.
   Não preencheria conteúdo ausente, corrigiria texto ou faria retry.
4. Schema experimental limitado aos derivados; schema final com atores e
   validadores de admissão existentes preservados. Nenhuma alteração em H6,
   eventos, memória ou contrato de runtime.
5. Resultados salvos como observação de derivação, com `full_evaluation:false`,
   sem misturá-los aos resultados CAP-001 ou ao replay de um lote completo.

O desenho exige um caminho novo no avaliador e um schema de resposta
experimental. Isso é uma mudança material em relação ao experimento vigente
de uma chamada SYSTEM-only. Esta proposta não aprova sua implementação.

## Limites para a eventual execução

- Candidato fixo `gpt-oss-120b-groq-free-synthetic-low`, Groq direta,
  modelo `openai/gpt-oss-120b`, reasoning `low`; somente dados sintéticos.
- **No máximo duas chamadas**, uma por entrada, sem gerar novas narrativas,
  diagnósticos adicionais, retries, fallback ou substituição de rota.
- Temperatura 0,65 e até 768 tokens de saída por chamada: teto solicitado
  conjunto de 1.536 tokens de saída. Uso de entrada e saída efetivamente
  reportado deve ser registrado; custo ausente continua indisponível.
- Até 2.000 tokens estimados no pacote USER por entrada, pelo método já usado
  de caracteres/4. Não omitir silenciosamente a narrativa ou o contexto.
- Pacing local de pelo menos 60 s pelo pacer corrigido e deadline de 60 s após
  a espera. Sem execução concorrente em dois terminais.
- Chave somente por entrada protegida local. Preparação e testes offline
  terminariam antes de depender da inserção da chave.
- Erro operacional de provedor/rota na primeira chamada encerra a sondagem,
  com motivo e segunda entrada não chamada. Rejeição semântica em uma resposta
  não autoriza reenvio; as duas entradas são independentes.

## Critério de análise e parada

Registrar todas as respostas e os erros. A observação termina ao consumir as
duas chamadas previstas ou ao encontrar o erro operacional que exige aborto.
Não repetir para melhorar a taxa.

Analisar separadamente schema/rota, admissão e fidelidade semântica:

- O evento, ator, objeto, posição e grau de certeza continuam os de `n`?
- Algum derivado acrescenta causa, identidade, recebimento ou relação entre
  pistas? A modalidade “pode” não dispensa origem.
- Local/presença/pendências anteriores foram preservados quando aplicáveis?
- Resumo/pergunta/fatos respeitam os limites experimentais e a agência?

Os contrapontos autorados no relatório bb98 são instrumentos de revisão,
não respostas obrigatórias nem textos enviados ao candidato. Paráfrases fiéis
continuam válidas. Revisão pelo agente pode ser concluída sem pausa para uma
avaliação intermediária do usuário; não preenche aceitação humana de produto.

Se qualquer relação indevida reaparecer, a hipótese não terá sido sustentada
por esta sondagem. Se ambas as respostas forem fiéis, isso mostrará somente
sucesso nesses dois casos fixos. Não provará generalização, superioridade
causal, fidelidade de novas narrativas ou benefício de uma cadeia em produção.
Nenhum desses resultados autoriza ampliar automaticamente o experimento.

## Implementação delimitada para decisão

Se este desenho for aprovado, a preparação local deve:

1. Criar o caminho experimental de derivação com os dois casos fixos e
   validação de seus hashes, mantendo avaliadores existentes compatíveis.
2. Criar o schema somente de registros, instrução de derivação e wrapper
   com chave protegida, orçamento fixo e classificação explícita de sondagem.
3. Testar offline imutabilidade de `n`, separação entre origens, teto de chamadas,
   ausência de retry/fallback, aborto operacional, rota e persistência dos
   artefatos, além da composição/admissão da proposta.
4. Revisar diff e testes; então disponibilizar uma única execução dependente
   de chave protegida. Não usar credencial antiga nem executar por arrasto.

A decisão solicitada abrange **somente preparar este experimento isolado e,
depois da preparação verificada, disponibilizar sua execução limitada**.
Não abrange migrar o Narrador para duas etapas, usar API paga, acrescentar
provedor, mudar aceitação ou fazer chamadas com credenciais recuperadas.

## Dependência humana específica

A formulação, as variáveis, os limites e o critério de parada estão completos.
O passo restante é decidir se o escopo experimental pode mudar de geração
integral em uma chamada para derivação separada com schema próprio.

O limite vem do [AGENTS.md local](../../../AGENTS.md): “Essa autorização não
amplia o produto nem revoga decisões aprovadas” e “ampliação material de escopo”.
A retomada e o relatório anterior também vedam acrescentar outro SYSTEM por
arrasto. A escolha de um caminho novo de geração experimental não será
disfarçada como correção de regex ou agendamento.

Até essa decisão, não existe nova implementação ou chamada pendente de chave.
A análise e todas as correções do bb98 continuam concluídas.
