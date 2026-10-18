# Brief prospectivo de admissão do Narrador

**Data:** 2026-09-22

**Status:** aceita; preparação offline verificada; inferência viva pendente

**Origem:** opção A do gate de admissão — nenhum candidato admitido.

**Aceitação:** o usuário respondeu `Aprovo HYP-001` em 2026-09-22. A aceitação
autorizou somente preparação offline.

## Pergunta prospectiva recomendada

Um contrato explícito de progressão fundamentada, derivado somente do estado
canônico e do resultado do resolvedor, permite que um candidato:

1. avance a cena quando existir uma transição autorizada;
2. sustente espera ou observação sem fabricar avanço quando não existir;
3. preserve agência, segredos, identidade dos atores e estado dos objetos;
4. mantenha concisão e continuidade suficientes para o MVP?

Essa pergunta é distinta do comparativo encerrado. Ela testa uma intervenção
controlada no contexto do Narrador contra uma falha compartilhada observada
(progressão fraca e estado de porta inventado), em vez de apenas trocar nomes,
NPCs ou cenários e repetir a mesma amostragem.

## Intervenção avaliada

Cada caso receberia um bloco estruturado, produzido antes da narração, contendo:

- fatos canônicos visíveis;
- resultado mecânico já resolvido, quando houver;
- transições de cena autorizadas;
- estados que permanecem desconhecidos;
- suposições explicitamente proibidas;
- intenção do jogador e obrigação de preservar sua agência.

O Narrador continuaria sem autoridade para criar resultado mecânico ou mutação
canônica. O experimento não alteraria o lote histórico nem usaria seus artefatos
para completar respostas ausentes.

## Corpus mínimo proposto

Usar casos novos e congelados, equilibrando pelo menos estas classes:

1. espera sem autorização de avanço;
2. espera com evento canônico autorizado;
3. objeto com estado conhecido;
4. objeto com estado deliberadamente desconhecido;
5. tentativa com resultado mecânico favorável;
6. tentativa com resultado mecânico desfavorável;
7. pergunta direta a NPC com segredo protegido;
8. ação ambígua que exige preservar a escolha seguinte do jogador.

Cada candidato receberia exatamente os mesmos casos, ordem, parâmetros e
orçamento. Bancos e sessões seriam novos; replay seria somente leitura e sem
gateway ou RNG.

## Limiar de admissão proposto (`CAP-001`)

Critérios fatais, exigidos em todos os casos:

- zero contradição de fato canônico;
- zero estado de objeto ou transição inventada;
- zero ação, fala, decisão ou sentimento atribuído ao personagem do jogador;
- zero vazamento de segredo não autorizado;
- identidade do alvo e proveniência exatas;
- schema e vínculo com a cápsula válidos;
- nenhuma troca, retry ou fallback oculto.

Critérios de qualidade a confirmar humanamente:

- avanço perceptível em todos os casos onde a transição foi autorizada;
- sustentação coerente em todos os casos onde avançar foi proibido;
- resposta dentro do orçamento de palavras congelado;
- continuidade sem repetição material entre turnos dependentes;
- latência e disponibilidade registradas, mas nunca convertidas em qualidade
  narrativa presumida.

Qualquer critério fatal violado torna o candidato não elegível nesse protocolo.
Não haverá relaxamento posterior para forçar vencedor. Um resultado sem
candidato permanece válido.

## Controles e limites

- O protocolo, corpus, hashes, ordem e verificador devem ser congelados antes
  da primeira chamada.
- Casos sintéticos não conterão campanha real, memória real ou credencial.
- Chamadas vivas serão opt-in e executadas somente após autorização humana.
- Nenhuma chave será passada em argumento, log ou arquivo versionado.
- Qwen e GPT-OSS podem ser reavaliados somente porque a variável testada é o
  novo contrato de progressão; sua evidência anterior permanece imutável.
- Provedor, custo, orçamento, fallback, `SEC-001` e configuração produtiva
  continuam decisões separadas.
- O resultado qualifica apenas o alvo exato, os parâmetros e o protocolo
  observados; não qualifica aliases, sucessores ou famílias de modelos.

## Preparação concluída

O corpus, protocolo, extensão de prompt, templates target-neutral, matriz de
adulterações, verificador e testes foram preparados. A evidência e os hashes
estão em `grounded-progression-contract-preparation-2026-09-22.md` e `.json`.
Foram aprovados 230 testes relacionados, com zero chamada a provedor.

## Decisão humana seguinte

A hipótese e o limiar já foram aceitos para preparação offline. Antes de criar
runner vivo ou realizar inferência, ainda é necessário aprovar alvos exatos,
parâmetros, ordem, máximo de chamadas, parada, credencial e execução opt-in.
