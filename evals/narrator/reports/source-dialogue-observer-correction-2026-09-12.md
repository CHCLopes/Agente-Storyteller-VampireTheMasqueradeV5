# Diálogo com Mara: atribuição de ações corrigida localmente

A resposta T2 capturada no lote87e187bb agora atravessa o gate e o fluxo B
completo em reprodução local, sem editar seu n/q ou declarar uma espera pelo
jogador. A narrativa descreve Mara observando e esperando, enquanto a explicação
pode permanecer vaga. Antes, o objeto você fazia o gate tratar esses verbos como
ações do jogador. O vermelho foi preservado antes da mudança.

A correção em api/scene_director_service.py identifica o NPC que observa por nome
ou antecedente local comprovado fora da fala, e decide por ocorrência de verbo.
O gerúndio coordenado mantém o sujeito do observador; o estado da explicação exige
sujeito textual explícito e não pessoal. Não se isenta a oração inteira. Uma
ação posterior do jogador continua sendo avaliada e pode impedir a admissão.

Foram alterados dois helpers existentes e acrescentados três privados. A revisão
AST confirmou todas as demais definições preservadas. Padrões e autorizações de
ação, rastreador pronominal geral, contrato n/q, prompt, parâmetros, corpus,
avaliadores fechados, persistência e interface não foram modificados.

## Verificação

- 30 casos novos de atribuição, incluindo n/q87 integral e limites de autoria.
- 63 regressões existentes de NPC como objeto e Mara holding.
- 331 casos compartilhados de scene_director, agência implícita/atribuída e perfil n/q.
- 2 integrações com produção declarativa real e SQLite novo.

Total final: 426 casos distintos aprovados, sem falhas, erros ou skips.
Reexecuções/vermelhos não foram contados como novos casos. O vermelho lexical
teve21 aprovados/6 falhas; o vermelho de integração com SYSTEM exato teve1 falha
causal e1 controle aprovado. Tentativas intermediárias estão preservadas e
identificadas. A primeira integração usou frontmatter no SYSTEM; o vermelho final
e o verde usam exatamente o corpo393f522e, sem esse desvio intermediário.

A integração literal confirma dois turnos, seis attempts e dois eventos. T2
recebe exatamente n1 como fonte do commit anterior; q permanece separado. Ficha,
trilhas e relações continuam idênticas. Reabrir o store e consultar/reexecutar
operações terminais com produtor, gateway e RNG proibidos não altera o hash
lógico do banco, os contadores ou as narrativas. O controle com ação real nova
do jogador segue recusado, com somente um turno e um evento confirmados.

Uma revisão independente examinou o delta antes de sua aplicação. Ela identificou
a possibilidade de atribuir um pronome a Mara apesar de um novo sujeito na mesma
sentença; essa fronteira e fala com travessão sem delimitação foram restringidas
antes da aplicação. A revisão final conferiu hashes e os426 casos, sem duplicar
as suítes. Não restou achado material no escopo.

## Limites e histórico

É uma regra lexical conservadora, não um analisador irrestrito do português.
Frases ambíguas e construções fora do recorte podem continuar recusadas. Uma
expectativa expressa por NPC não prova que o jogador agiu; controles conservadores
herdados não são apresentados como prova semântica de ato consumado.

Não houve HTTP, acesso a credenciais nem reutilização do banco87 durante a
correção. A observação original continua finished/1 com um commit e T2 recusado;
seus oito brutos e as69+97 cópias históricas mantiveram hashes. A reprodução local
não é outra resposta do Groq nem sucesso retroativo. A avaliação narrativa de87
continua parcial: diálogo pertinente, mas abstrato e com pouca especificidade.

Core corrigido SHA898c7e9134acee08c711196f2ee4230ddf968f767da87d30047a8e6f7aa93953.
Checkpoint próprio com68 cópias: eval-results/checkpoints/source-dialogue-observer-correction-20260912/manifest.json,
SHA6379c44e32b3c052a6f5addef65669b75f96238f5550c50db7d97e38e4d1e002. O freeze antigo representa o core anterior; não reexecutar
o verificador antigo contra código modificado para substituir aquela evidência.

A próxima lacuna útil é a escolha limitada de configuração com o SYSTEM de
diálogo já observado, mantendo a rubrica e os casos anteriores em um protocolo
prospectivo próprio. Essa preparação é separada da correção; não repetir o lote87
nem gerar uma variante de prompt para buscar aprovação. Nenhuma destas provas
seleciona modelo default ou aprova campanha, UI ou CAP-001.
