# Resumo textual sozinho — desenho prévio em 07/09/2026

Status: autorizado pela continuidade; preparação técnica em andamento. Uma única observação nova; o lote Qwen inline 94a95216 está encerrado. Não é retry ou tentativa de elevar uma taxa histórica.

## Pergunta decidível

Qwen, recebendo o mesmo pacote de origem, consegue produzir um resumo fiel com até 25 palavras quando a resposta deixa de pedir perguntas e anotações de evidência? Os dois perfis inline copiaram as fontes e excederam 25 palavras. A [prova local da rubrica](record-inline-evidence-rubric-proof-94a95216-2026-09-07.md) examina se os critérios admitem paráfrases distintas. Esta observação isola a tarefa textual; não resolve nem relaxa a anotação modal do contrato anterior.

Manter literalmente o USER inteiro de archive-vibration, inclusive source_units e o identificador de formato de entrada inline. Não atomizar as fontes nem fornecer uma decomposição semântica autorada como resposta. A narrativa e sua proveniência permanecem iguais. O SYSTEM agora pede somente resumo, preservando fidelidade, português, 25 palavras e ausência de ações inventadas. O schema solicita apenas summary, uma string estrita de 8 a 600 caracteres. Não há campo de perguntas, IDs, modalidades ou projetor.

## Corpo e parâmetros

Perfil summary-only-qwen-3.8-27b-groq-free-synthetic-nonthink, modelo qwen/qwen3.8-27b, Groq direta, none/3.072/0,65. Manifesto, adaptador e parâmetros anteriores preservados. O dossiê congela o corpo exato. Diferenças no HTTP frente ao Qwen inline: conteúdo do SYSTEM e nome/schema da resposta. O USER inteiro e os demais campos do corpo são idênticos. A mudança conjunta da tarefa e de sua instrução/schema impede atribuição causal a um componente isolado; uma amostra não permite taxa ou superioridade de modelo.

## Critérios antes da chamada

- Exigir rota/modelo reportados exatos e schema válido, sem fallback ou coerção. Conservar a resposta válida e roteada literalmente para revisão.
- Medir palavras pela expressão Unicode registrada no dossiê, com apóstrofos/hífens internos. Até 25 é cumprimento da instrução; não é prova de fidelidade. Contagem não muda retrospectivamente o exit code, que representa apenas operação/schema/proveniência.
- Revisar todos os enunciados contra n0/n1: participante, cor da lanterna, iluminação da mesa/pastas, posição da vibração junto à porta e certeza do motor. Se a hipótese for incluída, preservar a incerteza da existência, posição e funcionamento; não inventar relações/causas.
- O resumo pode omitir detalhes legitimamente; dimensões omitidas ficam não informativas. Não exigir um gabarito textual nem a reprodução completa da fonte. Sucesso de comprimento obtido por omissão da hipótese não demonstra capacidade de resumir essa hipótese.
- Perguntas e segmentação modal da saída não são avaliadas nesta tarefa. As falhas anteriores continuam registradas. Nenhuma ação/emoção/conclusão do jogador ou decisão de NPC pode ser inventada.

Se houver schema/rota válidos, avaliar separadamente limite de palavras e fidelidade das afirmações presentes. Se faltarem registros, registrar falha operacional sem julgamento semântico. O resultado decide apenas se este pedido textual foi satisfeito nesta amostra. Não conclui que a representação inline causou o erro anterior. Não usar êxito isolado como aprovação de narrativa, oito campos, runtime ou CAP-001.

## Orçamento e parada

No máximo uma chamada, espera local mínima de 60 segundos e deadline de 60 segundos iniciado após espera/preflight, teto 3.072. Encerrar em qualquer resultado. Sem diagnóstico, retry, fallback, comparação ao vivo adicional, geração narrativa, juiz LLM, substituição de caso ou correção de resposta. Preparar, testar, revisar e executar integração sem chave antes da entrada protegida. Nenhuma chave antiga, .env, compra ou mudança de plano.

Depois desta observação, encerrar este pedido e analisar a evidência antes de outro passo. Não escalar esforço/tetos nem acrescentar instruções repetidamente para corrigir a mesma amostra.
