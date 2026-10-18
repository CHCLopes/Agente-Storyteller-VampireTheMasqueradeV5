# Atribuição de cor em fontes independentes — desenho prévio em 07/09/2026

Status: preparação autorizada sob continuidade, após o encerramento do lote summary-only 21cf338b. Nenhuma chamada deste par foi feita durante a preparação. O caso archive-vibration e os pedidos anteriores permanecem encerrados e intocados.

## Pergunta e informação nova

**Em duas fontes novas, Qwen transfere indevidamente o atributo verde entre a carcaça da luminária e a luz emitida quando muda apenas o vínculo dessa propriedade?**

O resumo anterior respeitou 21 de 25 palavras, mas transferiu a cor da lanterna para a luz. Isso já impede considerá-lo integralmente fiel; não é preciso outra chamada para registrar essa conclusão. Encerrar toda observação agora evitaria custo e deixaria sem resposta se o erro reaparece em fontes novas com vínculo inequívoco. Este par oferece a menor contraprova transferível para essa dúvida, sem repetir o arquivo municipal, biblioteca, oficina, opening ou um pedido anterior.

As fontes têm 32 palavras cada e o mesmo conteúdo periférico. A cópia integral não satisfaz o limite de 25. A expressão carcaça verde torna explícita a propriedade do objeto, sem uma segunda cor concorrente ou uma instrução corretiva. Por isso o par testa atribuição sob evidência explícita; não identifica o mecanismo causal do resultado 21cf338b nem uma taxa de erro.

## Fontes congeladas

A — observatory-a:

> No observatório vazio, uma luminária de carcaça verde ilumina um painel fosco. Um caderno fechado repousa junto à régua metálica sobre a bancada; perto da janela, uma cadeira está afastada da mesa.

B — observatory-b:

> No observatório vazio, uma luminária emite luz verde sobre um painel fosco. Um caderno fechado repousa junto à régua metálica sobre a bancada; perto da janela, uma cadeira está afastada da mesa.

Cada entrada preserva as seis chaves do pacote inline: schema, case_id, synthetic_only, origin, narrative e source_units. n0 contém a primeira frase completa com espaço final; n1 contém a segunda frase completa, idêntica nos dois casos. A concatenação reproduz a narrativa literalmente. Os IDs de caso são neutros. O modelo recebe somente fatos autorados, sem nomes das condições, rótulos semânticos, rubrica, gabarito ou exemplos de resumos corretos. As expectativas no dossiê são exclusivamente de revisão e não integram o corpo HTTP.

## Pedido e parâmetros

Preservar literalmente SYSTEM record-summary-only-v1 e schema SummaryOnlyProposal: somente summary, string estrita entre 8 e 600 caracteres. Protocolo record-summary-only-v1 permanece; o identificador do formato de entrada e o prefixo PACOTE SINTÉTICO INLINE também permanecem.

Candidato qwen-3.8-27b-groq-free-synthetic-nonthink; alvo summary-attachment-qwen-3.8-27b-groq-free-synthetic-nonthink; Groq direta, qwen/qwen3.8-27b, effort none, temperatura 0,65, teto 3.072 por chamada. Model, response_format e todos os parâmetros HTTP permanecem iguais ao pedido summary-only anterior. Só messages[1].content muda para o caso novo. A identidade experimental/proveniência é nova e fica fora do corpo HTTP.

Novo propósito/probe_kind summary_attachment_qwen_probe; experiment_version record-summary-attachment-qwen-observation-v1. O dossiê congela dois corpos em requests, com case_id, índice, pedido inteiro, hashes e orçamento de entrada. Não alterar adaptador, manifesto, contrato ou artefatos anteriores.

## Critérios prévios

1. Exigir rota e modelo reportados exatos, schema válido e preservação literal da resposta. Operação/schema/proveniência são separados da revisão de concisão e fidelidade.
2. Medir até 25 palavras pela mesma regra Unicode já congelada. A medição é informativa e não muda o exit operacional ou bloqueia o segundo caso.
3. Em A, verde pertence à carcaça; a cor da emissão não foi informada. Uma luminária verde pode ser elipse compatível da carcaça verde. Afirmar que a luz é verde acrescenta informação sem fonte. Em B, verde pertence à luz; a cor da carcaça não foi informada. Atribuir verde à carcaça também acrescenta informação sem fonte.
4. Aceitar paráfrases fundamentadas sem exigir um resumo exato. Se a atribuição não puder ser resolvida pela redação produzida, registrar ambígua; não transformar ambiguidade em demonstração positiva ou impor uma leitura arbitrária.
5. Omissão legítima é permitida. Cor omitida, ou descrição que não permite avaliar seu portador, fica não informativa para essa dimensão. Não exigir um campo de cor nem repetir a chamada para preencher a dimensão.
6. Revisar também todas as demais afirmações contra fonte: observatório, luminária/painel, caderno, régua, bancada e posição da cadeira. Não premiar o vínculo correto se o resumo inventar outros fatos, ações ou relações.
7. Registrar separadamente o resultado de cada direção do par. Duas respostas informativas e fiéis valem somente para essas amostras. Um erro em qualquer direção é uma contraprova local; não prova mecanismo causal, taxa, superioridade de modelo ou segurança de produto. Perguntas, anotações inline, oito campos, ator, runtime e CAP-001 continuam fora do escopo.

## Orçamento e regra de parada

No máximo duas chamadas, na ordem A e B, uma por caso, teto de 6.144 tokens de saída somado. Espera local mínima de 60 segundos antes da primeira chamada e entre chamadas; deadline de 60 segundos por chamada iniciado após espera e revalidação. Instância de observação independente por chamada; nenhuma conversa compartilhada entre casos.

Encerrar no primeiro erro operacional: transporte/provedor, prazo, rota ausente/divergente, schema inválido, erro local ou cancelamento. Persistir resultado parcial e skips dos casos não chamados. Falha de palavras não é erro operacional. Revisão semântica ocorre depois dos registros; não usar um juiz LLM ou uma decisão semântica online para abortar o par.

Sem diagnóstico, retry, fallback, geração narrativa, substituição de caso, alteração de prompt, aumento de teto/esforço, segunda rodada ou nova condição neste lote. Encerrar após os dois resultados ou o primeiro bloqueio operacional. Preparar/verificar/revisar e integrar sem chave antes da inserção protegida necessária à execução. Não ler .env, reutilizar chave anterior, alterar plano ou comprar capacidade.

## Limites de interpretação

O par é controlado na autoria e no conteúdo periférico, mas duas respostas estocásticas com ordem fixa não estabelecem efeito causal ou confiabilidade estatística. O objetivo é encontrar ou não uma atribuição indevida explicitamente observável nesta tarefa. Se houver omissão ou falha operacional, a dimensão correspondente continua não informativa. O resultado não reabre nem corrige o lote 21cf338b.
