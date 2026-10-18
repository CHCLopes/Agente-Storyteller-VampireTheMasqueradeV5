# Matriz offline de modalidade e pendências — c9c01a48

Data: 07/09/2026. Material de diagnóstico produzido pelo agente após a sondagem.
Não é corpus aprovado, novo gate, saída de modelo ou alteração dos resultados.
Fonte: [JSONL original](../../../eval-results/20260907T102110Z-8db00c2e-ec83-4c63-b80a-399db4be6599/gpt-oss-120b-groq-free-synthetic-low.jsonl).

## Método

Nove execuções de validação em memória: duas propostas originais, seis mutações
de um único campo e um controle que repete o fato literal de Mara. Não são nove
amostras independentes nem uma estimativa de precisão.

Cada mutação conserva a narrativa fixa, o contexto original e todos os campos
não indicados. Schema final, contrato de atores e admissão recebem a proposta
inteira. A classificação semântica da tabela vale **somente para a dimensão
alterada**: um resumo autorado fiel não corrige a pendência problemática que
continua presente na proposta original da abertura.

Nenhum texto autorado foi enviado ao candidato, importado como predecessor,
salvo em campanha ou usado para reescrever o JSONL. Nenhuma API foi chamada.

## Resultados

| Caso e campo | Valor observado ou autorado | Dimensão semântica | Schema / atores / admissão |
| --- | --- | --- | --- |
| opening_original — unchanged | s/t[0] observados | Compressão de modalidade; t[0] pressupõe observação. | passa / passa / passa |
| mara_original — unchanged | registros observados | Vínculo papel=endereço não reaparece; reação futura permanece livre. | passa / passa / passa |
| opening_modal_summary — s | Um corredor de pedra fria, luzes de néon e um sussurro sugerem possível observação distante. | Preserva modalidade nesta dimensão; demais campos permanecem iguais ao original. | passa / passa / passa |
| opening_confirmed_summary — s | Um sussurro distante confirma que uma presença observa o corredor de pedra fria. | Reforço inequívoco de certeza sem suporte. | passa / passa / passa |
| opening_modal_thread — t[0] | Há algo ou alguém observando ao longe? | Mantém a existência em dúvida. | passa / passa / passa |
| mara_literal_fact_control — f[0].s | Mara desliza papel amassado sobre o balcão | Controle literal idêntico ao campo observado; não é amostra independente. | passa / passa / passa |
| mara_address_fact — f[0].s | Mara desliza sobre o balcão um papel que contém o endereço. | Vínculo papel=endereço inventado. | passa / passa / passa |
| mara_player_action — t[0] | Você pega o papel. | Ação do jogador não declarada. | passa / passa / **recusa** |
| mara_premature_resolution — r | `["Descobrir se Mara entregará o endereço"]` | Resolução não sustentada pela narrativa; saída real tem r=[]. | passa / passa / passa |

Totais de execução: **schema 9/9; atores 9/9; admissão 8/9**. A recusa do
controle de agência foi `scene_player_agency_violation`, em
`open_threads[0]`, regra `undeclared_player_action`, conceito `take`.

A matriz demonstra a cobertura atual: são admitidas formulações modais e
formulações semanticamente mais fortes. O contrato de atores não promete
provar a implicação da prosa; a revisão qualitativa permanece uma verificação
separada. Não criar uma regex específica para fazer essas frases isoladas passar
ou falhar, nem chamar a taxa 8/9 de qualidade do modelo.

## Dois achados de acompanhamento separado

**Resolução prematura, somente no controle autorado.** A função
[`_thread_resolution_is_grounded`](../../../api/scene_director_service.py:2673)
encontra `revelado` em “prestes a ser revelado”; o marcador de pendência não
reconhece essa construção. O único token compartilhado com a pendência resolvida
é `mara`. O controle é admitido, embora a revelação continue futura.
A resposta real devolveu `r=[]`: não atribuir esse problema ao candidato nesta
rodada. Não houve alteração no gate; esse defeito merece investigação própria
antes de qualquer aprovação de resolução de pendências em runtime.

**Duplicação semântica de rótulos, somente numa projeção em memória.** O
[`project_scene`](../../../api/scene_director_service.py:1026) conserva pendências
não resolvidas e agrega por rótulo. A projeção de Mara manteve “Descobrir se Mara
entregará o endereço”, “Mara entregará o endereço?” e a questão sobre a reação do
jogador. Houve três rótulos, sem apagar a pendência anterior. A sondagem ao vivo
não projetou estado, portanto não houve efeito em cena, memória ou campanha.

Ambos os achados foram registrados sem correção oportunista: não bloqueiam a
análise dos dois resultados e não justificam nova chamada do experimento.
Valores e classificação estruturada estão no
[registro de análise](../reports/record-derivation-observation-c9c01a48-2026-09-07.json).
