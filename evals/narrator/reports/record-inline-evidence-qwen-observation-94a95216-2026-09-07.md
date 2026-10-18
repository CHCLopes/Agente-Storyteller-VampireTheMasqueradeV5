# Qwen inline — lote 94a95216 encerrado

A única observação Qwen de `archive-vibration` terminou com **sucesso operacional, código 0**, mas não satisfez todos os [critérios prévios](record-inline-evidence-qwen-design-6876955e-2026-09-07.md). O resumo reproduz fielmente a narrativa, com o separador correto, porém tem 32 palavras e mantém fatos e hipótese sob o mesmo rótulo em um segmento. A lista vazia de perguntas é permitida e não informa a capacidade de formular perguntas sem pressuposições indevidas.

Batch `94a95216-9d0b-479e-85d3-e6c577ce4fa3`; PID 19232 confirmado `finished` em 2026-09-07T17:59:49.5067634Z, código 0. A chave foi descartada, o limite de uma chamada está esgotado e não há entrada de credencial pendente para este lote. Não relançar a janela nem repetir o pedido.

## Evidência operacional

Houve uma chamada Groq direta, modelo reportado `qwen/qwen3.8-27b`, HTTP 200/`stop`, rota verificada, schema e projeção válidos. Parâmetros: `none`, temperatura 0,65 e teto 3.072; espera local e deadline de 60 segundos conforme o pedido congelado. Sem diagnóstico, retry, fallback, juiz LLM ou geração narrativa.

Uso reportado: **774 entrada + 97 saída = 871 tokens**. O contador de raciocínio é `null`, não zero; não foi inferido a partir de `reasoning_effort:none`. Custo indisponível. Nenhum conteúdo de raciocínio ou credencial foi consultado nesta análise.

[Summary original](../../../eval-results/20260907T175847Z-83c88116-fb4c-4fff-b479-11d91ee655d7/summary.json), SHA `795cc05b6211fdbf0961d61b938fb3f14a02a8b688fb541c61584c8c1e98edee`; [JSONL original](../../../eval-results/20260907T175847Z-83c88116-fb4c-4fff-b479-11d91ee655d7/qwen-3.8-27b-groq-free-synthetic-nonthink.jsonl), SHA `cb39f07387198c31b66f8bab564ed72284985c055b08ffd274e681db349ff21a`. [Análise e auditoria separadas](record-inline-evidence-qwen-observation-94a95216-2026-09-07.json).

A auditoria independente confirmou igualdade exata e tipada entre preflight, metadados preparados e persistidos, e reconstruiu summary, projeção e auditoria de segmentos. No momento da auditoria, oito fingerprints de preparação, 32 históricos e dez brutos históricos permaneciam intactos. Não houve contradição operacional acionável. O helper inicialmente executado no checkout original obteve campos Git indisponíveis; executar a auditoria no diretório do worktree resolveu a proveniência. Nenhum código do projeto foi alterado por esse ajuste.

O intervalo UTC do início do run ao início do adaptador foi 60,538557 s; a duração UTC do adaptador, 1,204156 s, e a medição local, 1,206501 s. Os timestamps não medem chegada remota nem reconstituem a espera monotônica exata ou o deadline absoluto, que não foram persistidos.

Os 240 testes distintos pertencem à [preparação](record-inline-evidence-qwen-v1-2026-09-07.md), não constituem uma nova rodada de testes deste resultado. O encerramento documental não executou testes nem chamadas.

## Revisão integral da resposta

| Campo e modalidade | Texto retornado | Avaliação |
| --- | --- | --- |
| `summary[0]`, `established`, `n0` | “No arquivo municipal, a luz de uma lanterna vermelha ilumina uma mesa coberta de pastas. ” | Fiel. Preserva lugar, iluminação, mesa e pastas; a cor é da lanterna, não da luz. O espaço final pertence à resposta e foi mantido. |
| `summary[1]`, `suggested`, `n1` | “Perto da porta fechada, uma vibração leve sugere que talvez exista um motor funcionando do outro lado.” | A redação conserva `sugere` e `talvez exista`, sem confirmar o motor. A porta fechada e a vibração perto dela são estabelecidas, mas foram agrupadas com a hipótese de motor sob o único rótulo `suggested`, contrariando a separação de modalidades instruída. |
| `open_questions` | `[]` | Permitido. Não é falha por omissão nem evidência de formulação correta de perguntas. A dimensão de pressuposições em perguntas fica não informativa. |

O resumo tem **32 palavras e 191 caracteres**, contra a instrução de até 25 palavras. Os segmentos têm 15 e 17 palavras, 89 e 102 caracteres. A cópia literal não é, por si só, uma falha de fidelidade; neste caso ela excede o limite solicitado. Não houve ampliação textual de certeza, mudança de participante, posição ou atributo, nem ação/estado interno acrescentado ao jogador ou a NPCs.

A projeção é exatamente a narrativa de entrada. Os intervalos `/summary` `[0,89)` e `[89,191)` reconstituem os segmentos, inclusive o espaço entre frases. Não houve reparo nem defeito demonstrado no projetor. Schema, IDs e intervalos corretos não avaliam a correspondência semântica de cada rótulo.

## Comparação descritiva com 6876955e

| Dimensão observada | GPT-OSS 6876955e | Qwen 94a95216 |
| --- | --- | --- |
| Palavras do resumo | 32 | 32 |
| Caracteres do resumo | 190 | 191 |
| Espaço entre segmentos | Ausente: `pastas.Perto` | Presente: `pastas. Perto` |
| Segundo segmento e rótulo | `suggested`, mistura fatos e hipótese | Idênticos |
| Perguntas | Uma, com pressuposição indevida de motor | Nenhuma; dimensão não informativa |

As fontes são iguais. O primeiro segmento difere apenas pelo espaço final; o segundo é idêntico ao [lote anterior](record-inline-evidence-observation-6876955e-2026-09-07.md). Não se atribui causalmente essa diferença ao modelo: mudaram modelo, perfil de raciocínio e parâmetro específico de GPT-OSS. Não houve controle contemporâneo, repetição ou importação dos contadores antigos. A ausência de uma pergunta problemática não demonstra melhora na capacidade de escrever perguntas.

Não há impossibilidade demonstrada nos critérios: o contrato permite paráfrase concisa, até oito segmentos no resumo e o mesmo ID de fonte em segmentos distintos. Unidades de fonte completas não exigem cópia integral das frases no resumo. Essa avaliação não redefine os critérios nem estabelece uma paráfrase única como gabarito.

## Encerramento e continuidade offline

Os marcadores automáticos originais de revisão semântica/cobertura permanecem `not_performed`, aprovação `null`. A avaliação do agente é documentada separadamente. Oito campos e admissão de atores não foram avaliados; uma amostra não comprova frequência de erro, generalização ou aprovação de runtime/CAP-001, nem remove os bloqueios históricos do candidato.

O próximo trabalho autorizado é **refinar e verificar uma rubrica documental offline e preparar uma observação de resumo textual sozinho**, em artefatos separados. A preparação está em curso; sua pergunta experimental, pedido e verificações devem ser conferidos no estado próprio. Essa continuidade não reescreve respostas ou critérios históricos e não declara uma nova execução pronta. Completar autonomamente o trabalho independente de credenciais; depender do usuário somente para eventual chave ou intervenção direta necessária. Não repetir os lotes encerrados nem executar uma nova observação sem preparação delimitada e verificada.
