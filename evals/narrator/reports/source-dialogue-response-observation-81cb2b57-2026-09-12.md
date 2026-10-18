# Observação encerrada: resposta de NPC

Lote `81cb2b57-adbe-4b21-a0dd-e16da56f6df1`, executado pelo usuário em 12/09/2026, finalizou
`finished/0`, com resumo `completed/0`. A auditoria técnica passou em 65/65
checks, e o verificador CLI separado confirmou integridade sem alterar os
arquivos. Foram três HTTP 200/stop e três admissões, sem skips, repetição ou
chamadas adicionais. Uso reportado: 4.729 tokens de entrada, 481 de saída,
5.210 totais. A primeira chamada esperou 60,881507 s; intervalos seguintes
60,831661 e 61,077821 s. Todos os deadlines foram respeitados.

O alvo foi Qwen qwen/qwen3.8-27b via Groq, SYSTEM dialogue-v1, temperatura
0,65, reasoning none, teto de 768 tokens por chamada. As 25 entradas e o
lançador correspondem à preparação congelada. Os cinco arquivos brutos
permaneceram idênticos durante as duas verificações. Não houve SQLite,
commit de campanha ou uso de chave real pelos revisores.

## Leitura narrativa

| Caso | Observação | Avaliação |
|---|---|---|
| Pergunta direta | Mara diz “É um acervo”. Há informação atribuída, mas grande parte do texto é hesitação e ambiente. | Pertinência mínima; utilidade limitada. |
| Após silêncio | Mara diz “Aqui não é um lugar para perguntas” e volta à espera. | Recusa reconhecível; recuperação parcial pela baixa especificidade. |
| Espera | A gota atinge o papel antes seco e a mancha cresce. | Consequência observável, coerente com a fonte. |

Agência preservada nos três casos. O convite falado não move o jogador, e
“O que você faz?” não pressupõe resposta ou ação ausente. Os nove critérios
originais foram avaliados individualmente em parecer independente; nenhum
critério novo foi usado para reclassificar o lote. Pedir responsividade não
obriga Mara a obedecer, saber a verdade ou revelar segredos. A ressalva da
recusa é sua pouca especificidade e retorno à suspensão da conversa.

Holofotes, obras, vidro e verniz no primeiro caso são improvisação permitida;
não contradizem as tochas de outro caso independente. “Acervo” continua fala
atribuída da NPC, sem promoção automática a fato canônico. Em relação à sessão
49 há agora falas efetivas e perguntas finais coerentes; a comparação é
descritiva, sem baseline, replay sequencial ou demonstração causal A/B.

## Limites e próximo passo

O resultado narrativo é parcial. Não comprova qualidade global, seleção de
modelo, default, campanha ou CAP-001. Três contextos independentes com fontes
autoradas não demonstram continuidade de uma conversa no fluxo persistido.
A lacuna seguinte é n gerado → commit → seleção da fonte → novo diálogo.

Foi iniciada preparação prospectiva de dois diálogos encadeados usando o
mesmo SYSTEM, modelo e limites por chamada sobre APIs B existentes. Banco
sintético novo, aliases explícitos, limite de dois envios e sem UI/default.
O segundo contexto deverá conter a narrativa realmente commitada no primeiro,
sem edição manual nem promoção de sua fala a verdade canônica. Preflight congela
ações e construção; o corpo dinâmico de T2 será vinculado após T1.
Plano: `plan/verify-source-dialogue-continuity-1.md`; protocolo:
`evals/narrator/source_dialogue_continuity_protocol_v1.md`.
Nenhuma nova inferência foi feita ao preparar ou registrar este fechamento.

## Preservação

Checkpoint `eval-results/checkpoints/source-dialogue-response-observation-81cb2b57-20260912/manifest.json`:
41 cópias verificadas, SHA `5827173504c4538ffd5d644c6605b66707712cf2fcf5cb9bd8bd95d0efdfd4e9`. A âncora de preparação
conserva 127 cópias verificadas. Summary/JSONL originais permanecem históricos,
inclusive o campo automático que informa revisão semântica não realizada;
esta análise existe como documento separado e não reescreve aquele campo.
