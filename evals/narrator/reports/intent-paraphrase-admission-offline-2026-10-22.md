# Catálogo C — admissão de seis paráfrases, 22/10/2026

## Resultado

O catálogo C foi executado como uma variante offline e isolada. A versão
`intent-paraphrase-catalog.v1` contém exatamente seis correspondências revisadas;
a função só consulta a string completa e não normaliza, usa substring, infere,
executa consequência, sorteia ou altera sessão.

Os doze casos foram compostos por seis entradas aprovadas e seis controles
negativos. Não houve gateway, chamada de modelo ou custo de provedor.

| Medida | Resultado |
|---|---:|
| Entradas aprovadas elegíveis | 6/6 |
| Controles aceitos pelo catálogo | 0/6 |
| Correspondências da baseline atual nas seis aprovadas | 0/6 |
| Custo de provedor | USD 0 |
| Chamadas de provedor | 0 |

As seis entradas são: “Quero saber qual é a tarefa.”, “Mara, o que eu posso fazer
para ajudar?”, “Fico esperando.”, “Vou retirar o registro da bancada.”, “Analiso o
registro.” e “Não participarei do resgate.”. Elas foram tratadas como equivalências
explícitas do estudo, não como descoberta automática de semântica.

## Controles

“Não retiro o registro.”, a fala citada a Mara, a ação composta, a quase
correspondência sem pontuação, o método do casaco e a injeção de estado foram
recusados pelo catálogo. A baseline ainda classifica a fala citada como pedido de
ajuda; isso é uma diferença observável e reforça que o catálogo C é uma camada de
decisão revisada, não uma simples cópia do classificador.

## Verificação

77 testes focados passaram, incluindo 61 do contrato B e 7 do browser A2 além dos
casos do catálogo. A observação está em
`eval-results/intent-paraphrase-admission-offline-2026-10-22/`; seu manifesto
registra os hashes do avaliador e do catálogo. A evidência é sintética e autorada;
não mede acurácia de modelo e não comprova improvisação geral.

## Limite e próximo gate

O catálogo reduz seis falsos bloqueios conhecidos com baixo custo e rejeita os seis
controles, mas ainda é uma lista fechada. Não deve ser conectado ao A2 ou ao jogo
sem um aceite separado: a integração teria de definir quando a proposta vira
entrada elegível, como preservar o contrato e como impedir que novas paráfrases
entrem por similaridade implícita.

O próximo gate é escolher entre:

- **E — integrar o catálogo exato ao ensaio A2**, mantendo a integração experimental,
  sem produto principal, sem novas equivalências e com replay/estado preservados;
- **F — manter o catálogo somente como evidência**, sem integração, até definir uma
  fonte independente de validação para entradas fora das seis.

Nenhuma opção fecha CAMP-13..16 ou CAMP-24, admite narrador ou autoriza a proposta
dual-model/ALT-003.
