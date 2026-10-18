# Par novo de atribuição de cor com teto de 768 — desenho prévio em 07/09/2026

Status: preparação autorizada sob continuidade após o resultado operacional válido de 95dd9fd2. Nenhuma chamada do par foi feita nesta preparação. station-clock está encerrado; não se repetem esse caso, o arquivo municipal ou observatory-a/b. O caso observatory-b omitido em 1edf4d3e não é preenchido por este experimento.

## Pergunta e informação nova

**Em duas fontes novas, com teto de 768 por chamada, o resumo preserva ou transfere indevidamente azul entre a base da luminária e a luz emitida?**

O pedido de uma chamada 95dd9fd2 concluiu transporte e schema com o teto menor. Isso informa viabilidade daquele pedido, sem garantia de disponibilidade futura ou aprovação semântica. O par anterior encerrou por falha operacional antes de obter as duas respostas; não oferece a comparação pretendida de atribuição. Duas fontes novas permitem observar as duas direções sem repetir um caso fechado ou acrescentar instruções corretivas ao SYSTEM.

As fontes têm o mesmo conteúdo periférico, 35 palavras cada e uma diferença explícita no vínculo da cor. Uma cópia integral excede 25 palavras. O experimento observa duas saídas previamente delimitadas; não mede taxa de confiabilidade nem causa dos resultados históricos.

## Fontes congeladas

A — reading-room-a:

> Na sala de leitura vazia, uma luminária de base azul ilumina um mapa dobrado. Um estojo fechado repousa junto ao marcador de páginas sobre a mesa; perto da porta, uma poltrona está afastada da estante.

B — reading-room-b:

> Na sala de leitura vazia, uma luminária emite luz azul sobre um mapa dobrado. Um estojo fechado repousa junto ao marcador de páginas sobre a mesa; perto da porta, uma poltrona está afastada da estante.

O corpus contém exatamente dois casos nas seis chaves inline já estabelecidas: schema, case_id, synthetic_only, origin, narrative e source_units. n0 contém a primeira frase completa com espaço final; n1 é a segunda frase completa, idêntica nos dois casos. A concatenação Unicode literal recompõe a narrativa. As fontes e IDs são autorados e sintéticos. O modelo não recebe rubrica, gabarito, classificação da condição, decomposição semântica, exemplos de respostas ou instruções novas sobre cor.

## Pedido e diferenças declaradas

O SYSTEM record-summary-budget-v1, SHA-256 1eca37a720951743b0f989b3ed31b1fd726663345bad71016179966d5548d5ce, permanece idêntico. Também permanecem o contrato SummaryOnlyProposal, o schema nativo estrito, o protocolo de saída record-summary-only-v1, Qwen qwen/qwen3.8-27b via Groq oficial, reasoning_effort=none, temperatura 0.65, stream=false, include_reasoning ausente e max_completion_tokens=768.

Comparado ao corpo de 95dd9fd2, cada novo pedido difere somente em messages[1].content. Isso inclui o novo case_id e a fonte completa no prefixo/formato inline de versão record-inline-evidence-v1. No procedimento, mudam identidade, fonte singular para par ordenado, máximo de uma para duas chamadas e orçamento total de 768 para 1536. Essas diferenças são explícitas; não se apresenta causal A/B nem se atribui eventual diferença ao teto.

## Critérios prévios sem gabarito

Em A, a base é azul e a cor emitida não foi especificada. Afirmar emissão azul é uma transferência sem suporte. Em B, a luz é azul e a cor da base não foi especificada. Afirmar base azul é uma transferência sem suporte. Não se acrescentam cores concorrentes para tornar o contraste uma instrução corretiva.

Paráfrases fiéis são permitidas. Omitir cor ou a relação-alvo é legítimo, mas fica não informativo nessa dimensão; não conta como evidência positiva de preservação. Expressões como luminária azul podem deixar o proprietário da cor ambíguo: registrar ambíguo, sem forçar leitura favorável ou desfavorável. Uma atribuição explícita indevida é falha mesmo que outra dimensão seja omitida corretamente. Rever também fatos e relações periféricas sem impor um resumo exato.

Revisar cada direção separadamente. Duas saídas informativas e fiéis demonstram somente esses dois resultados. Omissão, ambiguidade, falha operacional ou skip deixam a dimensão correspondente sem observação suficiente. Não se infere mecanismo causal dos lotes 21cf338b, 1edf4d3e ou 95dd9fd2, confiabilidade geral, adequação do provedor ou aprovação de produto.

## Limites, ordem e parada

Purpose/probe_kind: summary_color_qwen_probe. Experimento: record-summary-color-qwen-observation-v1. Target: summary-color-qwen-3.8-27b-groq-free-synthetic-nonthink. Operações: summary-color.reading-room-a e summary-color.reading-room-b. Linhas summary_color_call/skip permanecem fora do replay CAP.

Máximo de duas chamadas, ordem A→B, uma por caso, 768 tokens por chamada e 1536 no total. Espera local inicial conservadora de 60 segundos, intervalo mínimo de 60 segundos entre envios e deadline de 60 segundos para cada chamada iniciado depois da espera. Preflight sem chave/cliente reconstrói corpos e fingerprints. Não há diagnóstico, retry, fallback, geração narrativa, juiz LLM, novo modelo ou ciclo de tetos/esforços.

Parar na primeira falha operacional: provedor/transporte, deadline, rota indisponível ou divergente, schema inválido, erro local ou cancelamento. Persistir os casos restantes como skips. Não substituir caso nem enviar o restante depois do encerramento. Um resultado semântico ruim ou mais de 25 palavras é registrado, mas não impede B quando A cumpriu os requisitos operacionais. O par encerra depois dessas duas posições ou da primeira falha; não se repete para elevar taxa.

## Aceitação operacional e registro

O fluxo operacional exige a resposta com rota verificada e schema válido, sem erro local. A instrução de até 25 palavras usa a medição existente e não altera o exit. O resumo automático preserva semantic_fidelity_review={status:not_performed, approval:null}; nenhuma contagem, HTTP 200 ou schema válido aprova significado. Não há projeção de suporte, admissão de ator, oito campos do narrador, alteração de runtime ou CAP-001.

Persistir texto literal e medições após rota/schema, sem reparo, com uso reportado ou desconhecido e observação sanitizada. Não guardar credenciais, corpo bruto de erro ou reasoning. O pedido 95dd não assegura disponibilidade: uma recusa futura permanece evidência operacional, sem inferir ETA, reset, consumo ou fórmula de OTPM.

## Implementação e verificação delimitadas

Criar corpus, desenho/dossiê e executor/wrapper aditivos. Derivar o fluxo de duas chamadas do attachment congelado por substituições finitas de identidade, fontes, hashes, prompt.variant, teto768 e total1536. PROTOCOL permanece separado da variante. Preservar algoritmos, contratos, adapters, manifesto, fontes e artefatos históricos; nenhuma engine genérica ou monkeypatch de runtime.

Verificar reconstrução exata dos dois pedidos, ordem, corpos exclusivos, novo limite, espera/deadline, parada com skips e persistência. No wrapper, testes novos focados de cap/corpus/prompt, observações ordenadas, caso omitido, status/exit, SecureString após preflight e restauração do ambiente. A prova de derivação e os testes não repetem os 73 cenários históricos. Integração real com chave vazia antecede a dependência humana de inserção segura de chave; a preparação não envia chamada externa.
