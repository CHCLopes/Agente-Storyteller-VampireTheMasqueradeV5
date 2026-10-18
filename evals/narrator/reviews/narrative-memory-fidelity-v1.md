# Fidelidade narrativa → memória: exemplos para revisão

Status: material offline de avaliação preparado pelo agente em 06/09/2026.
Não é conjunto aprovado por revisão humana, novo gate CAP-001, prompt de geração,
resposta de referência do jogo ou alteração do contrato de persistência.

Motivação: nos lotes `e15dd4d1` e `baf5d410`, campos destinados a resumo/fatos
acrescentaram informações não estabelecidas pela narrativa. Preservar improviso
não significa permitir que diferentes campos contem acontecimentos diferentes.

## Critério qualitativo existente

1. A narrativa pode propor pistas, ações de NPCs e mudanças ambientais coerentes
   com mecânica, agência, estado e visibilidade. Não precisa copiar uma história.
2. O resumo e os fatos daquele acontecimento devem representar o que essa
   narrativa estabeleceu, sem acrescentar participantes, ações, composição,
   causalidade ou certeza. Uma paráfrase fiel é permitida; cópia literal não é
   obrigatória nem prova de fidelidade.
3. Contexto anterior pode orientar a cena. Repetir nele um fato já conhecido não
   equivale a inventá-lo, mas não o torna novidade narrada neste turno.
4. Intenção, hipótese, sinal sensorial e acontecimento consumado são diferentes.
   Preservar essas diferenças importa para o contexto do turno seguinte.
5. Qualquer campo visível pode divulgar segredo. Uma recusa em `n` não compensa
   divulgação em `s`, fatos, lugar, pergunta ou pendências.

Esse critério deriva do contrato experimental `scene-focus-v1` e da premissa de
improvisação do produto. Os exemplos não cobrem equivalência semântica universal
e não são uma especificação de regex.

## Pares revisados pelo agente

As colunas observadas resumem conteúdo dos artefatos preservados. Os contrapontos
são **escritos para avaliação offline**, não saídas reais do modelo nem correções
aplicadas às respostas. Classificam somente a dimensão indicada; não afirmam
que uma resposta inteira passaria em todos os critérios.

| Caso | Narrativa observada | Campo derivado observado | Falha de fidelidade | Contraponto derivado fiel, autorado |
| --- | --- | --- | --- | --- |
| Tinta — e15dd4d1 | Tinta azul com brilho metálico e odor de óleo queimado. | Contém partículas metálicas; pode ser selo ou mecanismo oculto. | Aparência vira composição; a hipótese de mecanismo aparece só no derivado. | A faixa azul tem brilho metálico e odor de óleo queimado. |
| Beco — baf5d410 | Grafites neon entre magenta e azul. | Uma caveira alada vermelha sugere uma gangue. | Desenho e vínculo novos, não mostrados em `n`. | Grafites neon cobrem as paredes do beco. |
| Mapa — baf5d410 | Mapa rasgado marcando rotas de contrabando. | O mapa traz símbolo semelhante ao cadeado. | Acrescenta uma ligação entre pistas. | O mapa rasgado marca rotas de contrabando. |
| Cadeado — baf5d410 | O metal range e o acesso continua bloqueado. | O som alerta que alguém próximo está atento. | Ruído não estabelece que um terceiro o ouviu/reagiu. | O metal range, mas o cadeado não cede. |
| Mara — baf5d410 | Mara revela um envelope e parece hesitar. | Mara desliza o envelope até a borda do balcão. | Hesitação vira uma ação adicional, alterando posição do objeto. | Mara revela um envelope selado e parece hesitar. |
| Cais — baf5d410 | Estalo e movimentação ambiental, sem revelar responsáveis. | Segredo do Xerife e emboscada iminente no resumo/pendências. | Confidencial é exposto fora da prosa principal. | Um estalo distante interrompe o silêncio do cais. |

## Contrapontos que preservam improvisação

- **Nova pista válida nesta dimensão:** se a própria narrativa descrevesse uma
  caveira alada num grafite, registrá-la como observação poderia ser fiel. A
  vinculação a uma gangue ainda precisaria ter sido estabelecida, não presumida.
- **Ação de NPC válida:** se a narrativa mostrasse Mara deslizando o envelope,
  um fato `npc_action` com esse acontecimento seria fiel. A liberdade do jogador
  para pegar, ignorar ou questionar continuaria intacta.
- **Hipótese preservada:** “o ruído pode vir de dentro da parede” não deve virar
  “há um mecanismo em movimento na parede”. Tampouco é preciso eliminar o ruído
  para evitar certeza indevida.
- **Fato anterior:** passos já estabelecidos no contexto não são invenção apenas
  por reaparecerem no resumo. É diferente de narrar que alguém reagiu a um ruído
  novo sem essa reação ter sido estabelecida.
- **Método do jogador:** um resultado de sucesso permite descoberta coerente,
  não autoriza abrir uma porta ou forçar um cadeado no lugar do jogador. Esse é
  um critério de agência independente da fidelidade entre campos.

## Uso na próxima etapa

Revisar n/s/f/pendências em conjunto antes de tratar o próximo foco como fiel.
Separar: conteúdo novo legítimo; detalhe apenas derivado; certeza ampliada;
ação atribuída a outro participante; contexto antigo; confidencial exposto.
Manter casos ambíguos como ambíguos, com justificativa, em vez de inventar score.

Não executar outro modelo julgador, corrigir automaticamente respostas, extrair
apenas palavras-chave ou usar estes exemplos como história obrigatória. Nenhum
caso altera os resultados históricos ou dispensa a aceitação técnica humana.
