# Prova offline da rubrica inline após 94a95216

Prova concluída sem chamada de provedor, novo teste, alteração de contrato, prompt, fonte, runtime ou critérios históricos. As classificações semânticas abaixo são anotações autoradas de revisão; o código verificou apenas schema, referências, projeção literal e contagem de palavras. Não foi criado um classificador de semântica.

## Pergunta decidida offline

É possível produzir resumos curtos, fundamentados e com modalidades separadas usando as mesmas unidades completas de evidência, sem exigir uma resposta textual única? **Sim, como possibilidade representacional local.** V1 e V2 demonstram redações distintas e fontes n1 reutilizadas em segmentos diferentes. Isso não demonstra que um modelo as produza de modo confiável.

| Caso | Classificação autorada | Palavras | Schema/projeção | Evidência |
|---|---|---:|---|---|
| V1 | satisfactory_reference | 23 | passam | Três segmentos com afirmações separadas; n1 pode sustentar mais de um segmento sem modificar a fonte. |
| V2 | satisfactory_reference | 16 | passam | Paráfrase diferente; omite legitimamente n0 e conserva observação e hipótese, sem uma resposta textual única. |
| O1 | legitimate_omission | 9 | passam | Resumo fundamentado, mas não demonstra competência na dimensão omitida. |
| N1 | semantic_counterexample | 22 | passam | A possibilidade de existência do motor vira uma existência afirmada; IDs válidos não corrigem a promoção. |
| N2 | annotation_counterexample | 23 | passam | A redação continua modalizada; a contraprova altera somente a anotação. Não classificar isso como confirmação textual do motor. |
| N3 | segmentation_counterexample | 14 | passam | Duas frases independentes, fato e hipótese, agrupadas sob um rótulo; contraria a separação expressa no protocolo. |
| N4 | question_presupposition_counterexample | 23 | passam | A pergunta preserva dúvida sobre funcionamento, mas pressupõe um motor definido. O resumo válido não absolve a questão. |
| B1 | borderline_indication_report | 12 | passam | Relato da relação indiciária com hipótese embutida; não usar para reinterpretar os lotes. Antes de pontuar novas variantes, definir se o rótulo qualifica o relato estabelecido ou a causa apenas sugerida. |
| B2 | borderline_indication_report | 12 | passam | Relato da relação indiciária com hipótese embutida; não usar para reinterpretar os lotes. Antes de pontuar novas variantes, definir se o rótulo qualifica o relato estabelecido ou a causa apenas sugerida. |

V1 concatena: “Uma lanterna vermelha ilumina a mesa coberta de pastas. Há vibração perto da porta fechada. Talvez exista um motor funcionando do outro lado.”

V2 concatena: “Perto da porta fechada há uma vibração leve. Pode existir um motor funcionando do outro lado.”

As contraprovas N1–N4 também passam a estrutura. N1 confirma a existência apenas possível; N2 conserva a incerteza no texto e erra a anotação; N3 mistura duas afirmações independentes; N4 introduz pressuposição na questão. Esses defeitos não devem ser confundidos. O1 omite legitimamente a hipótese, ficando não informativo para essa dimensão.

B1/B2 não mudam a avaliação dos lotes. São casos autorados de fronteira: um relato verdadeiro de indício pode conter uma hipótese sem afirmar sua ocorrência. A revisão futura precisa declarar o escopo do rótulo antes de exigir uma forma de segmentação; não precisa aceitar um gabarito textual único. Se a convenção continuar ambígua, registrar borderline em vez de fabricar um desacordo factual.

## Observações preservadas e hipótese de cópia

Os dois JSONL históricos foram somente lidos; o projetor atual reconstruiu exatamente as projeções persistidas. GPT-OSS 6876955e e Qwen 94a95216 têm 32 palavras no resumo e continuam fora do limite instrucional de 25. Qwen preservou o espaço entre n0/n1 e não produziu questões; a ausência é permitida e não prova competência em pressuposições. GPT-OSS omitiu esse espaço e perguntou pelo funcionamento de um motor definido.

A cópia de n0/n1 e um rótulo por unidade são observações comuns, mas não provam que a granularidade de source_units causou os erros. A redação “Use apenas as unidades completas” pode incentivar a interpretação de que a unidade de evidência também é a unidade de saída; isso é uma hipótese de leitura, não causa estabelecida nem uma correção retroativa. O contrato permite várias partes da saída sustentadas pelo mesmo ID. A cópia de n1 mantém a hipótese na redação, mas agrupa localização/vibração estabelecidas e causa hipotética sob suggested, em desacordo com a instrução histórica de separação.

## Uma próxima pergunta experimental proposta

**O mesmo perfil Qwen consegue produzir um resumo fundamentado de até 25 palavras quando se retiram da saída perguntas, referências e rótulos de modalidade?**

A preparação desta única observação foi autorizada após a prova; nenhum executor, schema, prompt ou chamada foi criado por esta prova. O tratamento é uma tarefa experimental cujo schema contém somente summary, string estrita de 8 a 600 caracteres, sem campos adicionais. O limite de 25 palavras permanece na instrução e na revisão. O USER completo atual, inclusive narrative e source_units, permanece literalmente igual, assim como o perfil Qwen none, temperatura 0,65, teto 3.072 e rota Groq nativa. As mudanças de pedido são SYSTEM (somente resumo, mantendo fidelidade e concisão e retirando tarefas de perguntas/referências/rótulos) e response_format (objeto de um campo). Não se trata de comparar apenas SYSTEM nem de adaptar a resposta anterior. Identidade e hashes do novo pedido devem ser congelados separadamente antes da observação.

Orçamento proposto: uma chamada Qwen none, teto 3.072, temperatura 0,65, espera e deadline de 60 segundos, sem retry, fallback, juiz LLM ou segunda condição. Registrar separadamente concisão e fidelidade de todas as afirmações expressas. Omissão de incerteza continua não informativa nessa dimensão; não repetir para preenchê-la. Encerrar em qualquer resultado.

Um resumo satisfatório demonstraria somente a viabilidade observada da tarefa mais simples; não provaria que metadados causaram o fracasso anterior. Outra cópia longa enfraqueceria a hipótese de que remover essas tarefas, por si só, basta neste caso. Uma falha operacional ou omissão da dimensão-alvo não decide fidelidade de incerteza. Não inferir taxa, generalização, runtime ou CAP-001.

Mudar agora a granularidade da fonte seria um isolamento pior: reescrever a sentença em unidades atômicas já fornece parte da decomposição semântica a ser investigada, e cortar literalmente antes de “sugere” pode retirar contexto ou criar fragmentos. Mantendo a entrada e removendo tarefas de saída, a nova hipótese é mais limitada e interpretável. Isso permanece desenho experimental, sem decidir arquitetura produtiva.

Os valores integrais de todos os casos, contagens, projeções e hashes protegidos estão no JSON homônimo.
