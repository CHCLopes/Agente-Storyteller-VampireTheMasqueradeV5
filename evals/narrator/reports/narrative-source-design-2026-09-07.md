# Piloto da direção B: continuidade por fonte narrativa integral

Desenho congelado em 07/09/2026, antes de qualquer chamada. A direção B e novas observações necessárias já foram autorizadas. Este documento fixa uma hipótese nova de representação; não reabre as variantes encerradas de resumo nem aprova integração no produto.

## Hipótese e recorte

Observar se uma segunda continuação pode usar a narrativa integral anterior em uma seção atribuída, sem gerar primeiro resumo, fatos ou pendências. A cena canônica nova contém somente **Estufa**, sem NPCs. As ações são observar do lugar onde está sem tocar e, em seguida, esperar no mesmo lugar sem tocar. O servidor não fornece resolução mecânica.

O modelo produz apenas `n` e `q`. A admissão existente de linguagem, agência, sigilo, pergunta e mecânica é reaproveitada pelo perfil experimental antes de criar a fonte. A normalização explícita colapsa espaços; depois disso, `n` inteiro é conservado sem outra reescrita. `q` fica separado. `source_only` atribui o texto anterior e mantém a verdade semântica geral como `not_assessed`; não é uma afirmação atômica confirmada.

O segundo USER contém a projeção íntegra do primeiro `n`. Seu conteúdo depende da primeira resposta e não pode ser congelado literalmente antes dela. Congelam-se o código de construção, o contrato, os insumos, os limites e a primeira requisição; cada requisição efetiva terá USER literal, hash do corpo e vínculo de invocação registrados. Não há comparação A/B ou conclusão causal sobre os resumos históricos.

## Execução delimitada

- Qwen `qwen/qwen3.8-27b`, Groq direto, candidato gratuito sintético já usado, structured output nativo e reasoning `none`.
- Duas chamadas no máximo, 768 tokens por chamada e 1536 no total, temperatura 0,65. Espera inicial, intervalo mínimo e deadline individual de 60 segundos.
- USER limitado a 2000 tokens estimados por caracteres/4; excesso é recusado sem corte. O perfil permite no máximo duas fontes e 12.000 caracteres serializados, mas esta cadeia envia somente uma fonte anterior e aplica o teto adicional do USER.
- Primeira falha de operação, rota, schema, política ou projeção interrompe a cadeia. O dependente recebe skip explícito. Sem diagnóstico, repetição, reparo, retry, fallback ou juiz LLM.
- O wrapper faz preflight sem credencial; somente depois solicita entrada protegida. Antes do envio, confere novamente os metadados congelados. Após a execução, descarta a chave e reconstrói a evidência offline.

## Critérios e leitura dos resultados

O resultado operacional exige duas chamadas com rota, schema, política e projeção válidos. A análise autorada posterior examinará agência e continuidade, com trechos literais e distinção entre relação preservada, violada, ambígua ou não observada. Identidade por construção não será contabilizada como fidelidade abstrativa do modelo nem como verdade sobre o mundo.

Abertura sem cena, troca de local ou elenco, pendências estruturadas, armazenamento canônico, migração de saves, seleção automática de perfil e CAP-001 ficam fora deste piloto. O plano posterior deve proteger todos os caminhos de contexto antes de integrar a direção B ao produto.

## Fundação verificada antes do executor

O núcleo puro passou em 24 testes. O perfil passou em 57 casos distintos: a rodada inicial teve 55 aprovados e uma expectativa incorreta de código de erro; essa expectativa foi corrigida, e somente a família afetada foi repetida com três aprovações, incluindo um controle novo. Nenhuma alteração do perfil decorreu dessa falha de teste. Zero chamadas externas.

A revisão independente confirmou a separação fonte/afirmação, a premissa de fonte confiável e as recusas CAP. Antes da observação, alinhou-se o prompt ao teto já existente de 15 palavras para `q`. A hipótese de exceção Unicode no núcleo não se reproduziu: a revalidação existente já recusava a entrada, sem correção necessária.

Os hashes e as provas completas de teste estão no [registro JSON](narrative-source-design-2026-09-07.json). Na criação deste desenho, executor e wrapper ainda estavam em preparação; a validação operacional final será registrada separadamente. Nenhuma chamada ao provedor havia sido feita.

[Plano de implementação](../../../plan/architecture-narrative-grounding-1.md) · [Direção B aprovada](../reviews/narrative-memory-grounding-decision-2026-09-07.md)
