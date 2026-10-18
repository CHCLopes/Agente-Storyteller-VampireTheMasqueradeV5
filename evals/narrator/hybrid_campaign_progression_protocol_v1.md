# Protocolo offline — campanha híbrida mínima v1

Data: 2026-09-29. Estado: ritmo A aprovado; avaliação live não executada.
Decisões de recorte/arquitetura: DEC-PROG-001/002 aprovadas.
[Contrato candidato](../../spec/spec-architecture-hybrid-campaign-progression.md).

## Hipótese e separação de evidências

Consequências estruturadas, continuidade de estado e resposta pertinente de Mara
podem reduzir o loop percebido. Primeiro provar determinismo com conteúdo autorado;
depois avaliar a realização por Luna low. Não atribuir causalidade a comparação
com HYP-006, que usou outro prompt, tarefa e composição.

Nenhuma chamada autorizada por este protocolo. Nenhum candidato admitido.
Os casos abaixo são expectativas autoradas, não saídas de modelos.

## Matriz de trajetórias completas

Estado inicial de cada trajetória independente: record=threatened, outcome=null,
Mara presente no Arquivo. IDs de teste estáveis não são IDs de operação do produto.

| Caso | Entradas e regras candidatas | Estado final esperado | Prosa deve demonstrar |
|---|---|---|---|
| CAMP-EVAL-01 | Pergunta tarefa R-01; resgate R-05 | preserved/preserved | Mara responde; ação do jogador produz salvamento; epílogo reconhece escolha |
| CAMP-EVAL-02 | Espera R-03; espera R-03B; pergunta tarefa R-01; resgate R-06 | partial/partial | Primeiro aviso, depois água atinge registro; resposta usa condição molhada; perda parcial não é restaurada |
| CAMP-EVAL-03 | Espera R-03; espera R-03B; espera R-04 | lost/lost | Três mudanças causais distintas; conclusão sem loop |
| CAMP-EVAL-04 | Recusa explícita R-09 | threatened/abandoned | Mara reconhece decisão; nenhum movimento inventado ou gancho obrigatório |
| CAMP-EVAL-05 | Resgate por método equivalente R-05 sem conversa prévia | preserved/preserved | Solução antecipada válida, sem bloquear por ordem de cenas |
| CAMP-EVAL-06 | Investigar R-07 com recibo de sucesso autorado | partial/partial | Objetivo de recuperar conteúdo obtido, recibo intacto |
| CAMP-EVAL-07 | Investigar R-08 com falha; resgate R-06 | partial/partial | Falha não descobre conteúdo; água muda condição; resgate posterior aproveita o possível |
| CAMP-EVAL-08 | Pergunta segredo R-02; pergunta tarefa R-01; resgate R-05 | preserved/preserved | Recusa pertinente, segredo protegido e ajuda possível |

Para CAMP-EVAL-01, repetir com paráfrases “Como posso ajudar?” e “O que precisamos
fazer?”. Para R-02 repetir pergunta para verificar contexto, sem punir repetição
ou vazar a identidade. Repetições não são novas amostras live autorizadas.

## Contraprovas obrigatórias

| ID | Mutação autorada | Resultado esperado |
|---|---|---|
| NEG-01 | ID de efeito correto, mas n só descreve luz/poeira | Falha de realização narrativa; não contar como progressão |
| NEG-02 | Estado wet seguido de prosa que torna registro intacto sem regra | Contradição |
| NEG-03 | Falha de investigação narra leitura bem-sucedida | Violação mecânica |
| NEG-04 | Narrador decide que jogador retira documento após apenas perguntar | Violação de agência |
| NEG-05 | Mara fornece identidade protegida | Violação de segredo |
| NEG-06 | Epílogo reabre objetivo resolvido para evitar fim | Violação de encerramento |
| NEG-07 | Fonte atribuída vira novo delta não listado | Violação de autoridade |
| NEG-08 | Método plausível fora do catálogo tratado como fracasso mecânico | Limitação técnica disfarçada de ficção; reprovar |
| NEG-09 | Texto diz retirar registro, mas ignora destino autorizado | Verificar ação/efeito; não aprovar por palavra isolada |

## Persistência, operação e portabilidade

Para CAMP-EVAL-06/07: interromper antes do RNG, depois do recibo e durante H6;
reconstruir preparação; exigir mesmo operation_id, recibo, beat e revisão-base.
Retomada somente H6; replay terminal faz zero chamadas e zero RNG.
Dois submits concorrentes: no máximo uma reserva válida; nenhum delta parcial.
Consulta/reconexão não avança água. Candidato alternativo recebe o mesmo pacote
causal, fonte e rubrica; seu adaptador não muda as expectativas.

## Rubrica prévia à observação

Por turno: estrutura; autoridade/agência/sigilo; fidelidade ao efeito; resposta à
intenção; continuidade. Por trajetória: opções significativas, consequência,
variação pertinente de NPC, clímax e conclusão reconhecíveis.
Gates de segurança obrigatórios são separados do julgamento narrativo humano.
Não usar médias para compensar violação crítica nem inventar nota de qualidade.

Cada execução futura registra versão/hashes de contrato, conteúdo e entrada,
identidade da operação e alvo, duração local/provedor/commit, tokens/custo,
estado antes/depois e avaliação vinculada aos bytes efetivamente produzidos.
Registrar indisponibilidade e truncamento, nunca preencher com nova tentativa.

Primeira implementação do avaliador: fixtures positivas/negativas e adaptador
falso; não usar outro LLM como árbitro. Aprovação offline não substitui leitura
humana e não permite generalizar precisão de verificadores lexicais.

## Futura etapa live — ainda não ativada

Luna low primeiro. Antes de executar: congelar corpo, parâmetros, preços,
quantidade de chamadas e orçamento; revalidar capacidade/credencial via mecanismo
seguro. Reportar custo final em todos os encerramentos. Outros candidatos só
depois de pergunta discriminante e condições operacionais compatíveis.
Não reabrir HYP-006 ou consumir a autorização antiga OpenRouter por arrasto.
