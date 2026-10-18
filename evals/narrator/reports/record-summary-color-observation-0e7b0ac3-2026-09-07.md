# Atribuição de cor — observação 0e7b0ac3 encerrada

O lote `0e7b0ac3-b88a-4962-b383-cc6f813c9d4a` terminou com **duas chamadas HTTP 200/stop, rotas Groq/Qwen e schemas válidos, exit 0**. Os dois resumos têm 20 palavras e cumprem o comprimento. A pergunta de atribuição da cor permanece **não resolvida por ambiguidade**: ambos usam “luminária azul”, formulação já classificada como ambígua nos critérios prévios. Não há demonstração de preservação nem transferência explícita inequívoca entre base e luz.

PID 25276 confirmado `finished` em `2026-09-07T21:17:39.7995660Z`, chave descartada e lote encerrado. Duas chamadas, nenhum skip, retry, diagnóstico, fallback ou reparo. [Preparação histórica](record-summary-color-v1-2026-09-07.md), [desenho prévio](record-summary-color-design-95dd9fd2-2026-09-07.md), [dossiê](record-summary-color-dossier-95dd9fd2-2026-09-07.json) e [registro detalhado](record-summary-color-observation-0e7b0ac3-2026-09-07.json).

## Leitura independente das respostas

**A — reading-room-a: 20 palavras, 129 caracteres.** A fonte diz “uma luminária de base azul ilumina um mapa dobrado”.

> Sala de leitura vazia com luminária azul iluminando mapa, estojo fechado, marcador e poltrona afastada da estante perto da porta.

“Luminária azul” não explicita o vínculo com a base. Não forçar a leitura como luz azul nem premiar a expressão como preservação demonstrada. Sala vazia, mapa iluminado, estojo fechado, presença do marcador e afastamento poltrona–estante encontram suporte.

“Iluminando mapa, estojo fechado, marcador e poltrona” pode estender a iluminação à lista inteira, embora a fonte só explicite o mapa; também admite um inventário sob “com”. Registrar essa ambiguidade, sem impor a primeira leitura como falha categórica. Mapa dobrado, localização na mesa, proximidade estojo–marcador e especificação “de páginas” foram omitidos ou reduzidos; essas dimensões ficam não informativas.

**B — reading-room-b: 20 palavras, 121 caracteres.** A fonte diz “uma luminária emite luz azul sobre um mapa dobrado”.

> Sala de leitura vazia: luminária azul sobre mapa, estojo e marcador na mesa; poltrona afastada da estante perto da porta.

“Luminária azul” deixa de distinguir a cor emitida da cor do objeto. Conforme o desenho, isso é ambíguo, sem concluir base azul como afirmação inequívoca. “Luminária azul sobre mapa” também perde a distinção entre luz projetada sobre o mapa e posição da própria luminária. A leitura posicional excederia a fonte; a compressão não resolve qual relação foi expressa.

Sala vazia, existência dos objetos, estojo/marcador na mesa e afastamento da poltrona têm suporte ou são compatíveis com a formulação da fonte. Estado fechado do estojo, mapa dobrado, proximidade estojo–marcador e especificação “de páginas” foram omitidos ou reduzidos. Nos dois resumos, “poltrona afastada da estante perto da porta” torna menos claro se “perto da porta” qualifica poltrona ou estante; a fonte situa a poltrona perto da porta. Nenhuma ação de jogador/NPC foi acrescentada.

O limite de 25 palavras foi satisfeito, mas não resolve essas ambiguidades. Omissão permitida não conta como preservação positiva. A análise autorada não altera o bruto `semantic_fidelity_review: not_performed/approval: null` e não aprova fidelidade integral. Nenhum defeito local de retenção ou medição foi demonstrado.

## Operação e integridade

Cada chamada reportou 482 tokens de entrada e 39 de saída, total 521. Agregado: **964 + 78 = 1.042**. Raciocínio permanece `null`/não reportado, não zero; custo indisponível. Ambas reportaram o modelo efetivo Qwen e observaram Groq, com identidade verificada. Texto literal e medições foram preservados.

A auditoria independente SHA `db18f75aaaee3951586a236c0af78e25474ce0fd52f39152386340dbb7824412` reconstruiu preflight inicial/final, metadados preparados e brutos, os dois corpos, resumo operacional, schema e medições. Confirmou 9 arquivos de preparação, 71 históricos e 18 brutos históricos intactos; os conjuntos podem se sobrepor. Essa constatação se refere ao momento da auditoria, antes de evolução posterior do arquivo compartilhado em novas preparações.

Intervalo UTC inicial: 60,477648 s; entre inícios dos adaptadores: 60,244213 s. Durações UTC A/B: 1,151343/1,069281 s; perf_counter: 1,152241/1,071545 s. Esperas monotônicas exatas e deadlines absolutos não foram persistidos; tempos locais não provam espaçamento de chegada remota. Houve reconstrução dos pedidos, sem captura de tráfego bruto.

- [summary.json original](../../../eval-results/20260907T211537Z-dd5ca339-6fe5-4f8d-8aeb-81abaf5c26b0/summary.json): SHA `d10d14c885452e1e3b160056c46b1e531b1b7da8710caad273d07bab6325919e`.
- [JSONL original](../../../eval-results/20260907T211537Z-dd5ca339-6fe5-4f8d-8aeb-81abaf5c26b0/qwen-3.8-27b-groq-free-synthetic-nonthink.jsonl): SHA `3d415e680deed39fd496e2bdd57116baf240876c60afec4812b3645c09e20480`.

Os 68 testes são da preparação e não foram repetidos nesta análise. Os campos `prepared_metadata`, `files`, `verification`, `scope` e `evidence_files` permanecem literalmente preservados. Não se alteraram fontes, critérios, prompts, código ou brutos. Duas respostas não estabelecem taxa, causalidade, efeito do teto, mecanismo dos erros históricos ou aprovação de produto/CAP-001.

## Continuidade

Preparar a observação experimental de compressão relacional: dois braços, controle budget e variante de orientação para selecionar poucas afirmações completas em vez de inventário, sobre UMA mesma fonte sintética NOVA, com USER idêntico nos dois. Manter Qwen/Groq gratuito, SummaryOnlyProposal, reasoning_effort=none, temperatura 0,65 e teto de 768 por chamada (1.536 total). Ordem controle→variante, uma chamada por braço, espera inicial e intervalo entre inícios de pelo menos 60 segundos, deadline de 60 segundos após a espera e parada no primeiro erro operacional. O desenho está em curso, ainda não declarado pronto; nenhum novo envio consta deste fechamento. Uma amostra por braço permite apenas comparação descritiva, sem conclusão causal. Encerrar a investigação após os dois braços ou primeiro erro, sem sequência de reformulações para elevar taxa. Não repetir fontes ou casos encerrados; não recuperar credenciais antigas. A autorização contínua dispensa nova confirmação genérica; concluir trabalho local antes de uma dependência real de credencial.

Todos os lotes anteriores e este par permanecem encerrados. Perguntas, anotações inline, oito campos, atores, runtime e CAP-001 continuam sem aprovação.
