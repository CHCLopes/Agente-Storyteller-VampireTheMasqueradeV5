# Derivação c9c01a48 — operação aprovada, hipótese semântica não sustentada

Data: 07/09/2026. Batch `c9c01a48-a69d-43bd-9fa2-414ad0d6685b`.
**Análise concluída.** As duas chamadas tiveram rota, schema e admissão aceitos.
A abertura ainda transforma uma observação apenas sugerida em pressuposição
nos registros. O critério pré-registrado de fidelidade dos dois casos não foi
satisfeito. Exit 0 continua correto para o significado operacional definido.

Fonte integral:
[summary](../../../eval-results/20260907T102110Z-8db00c2e-ec83-4c63-b80a-399db4be6599/summary.json)
e [duas respostas JSONL](../../../eval-results/20260907T102110Z-8db00c2e-ec83-4c63-b80a-399db4be6599/gpt-oss-120b-groq-free-synthetic-low.jsonl).
[Proveniência e análise estruturada](record-derivation-observation-c9c01a48-2026-09-07.json).

## Auditoria operacional

| Medida | Resultado |
| --- | --- |
| Chamadas / IDs distintos | 2 / 2 |
| Schema de derivados / final / admissão | 2 / 2 / 2 |
| Diagnósticos, retries, erros, skips | 0 |
| Rota das duas chamadas | Groq / `openai/gpt-oss-120b`, verificada |
| Parâmetros | 768 tokens, temperatura 0,65, reasoning low |
| Saída reportada | 435 e 521 tokens, ambas abaixo de 768 |
| Uso conjunto | 3.234 entrada + 956 saída = **4.190 tokens**, reportado nas duas |
| Custo | Indisponível; não equivale a zero |
| Intervalo entre inícios UTC do adapter | **60,249545 segundos** |
| Duração do lote | 63,165010 segundos |

Os metadados completos da preparação, preflight reconstruído, summary e duas
linhas JSONL coincidem. Todos os hashes registrados correspondem aos arquivos
atuais. Os dois USERs foram reconstruídos exatamente: 854 caracteres / 214
tokens estimados e 1.267 / 317, sem omissões. O teto USER é uma estimativa por
caracteres/4; o uso reportado inclui SYSTEM e schema, não deve ser confundido
com esses 214/317.

Composição reconstruída e validações de atores/admissão confirmadas offline
em 2/2. `summarize(rows)` reproduziu o summary inteiro e exit 0.
As narrativas compostas são literais e idênticas à fonte bb98; nenhum derivado
antigo foi inserido no USER. Não houve chamada real adicional pelo agente.

O intervalo é uma observação UTC local, não horário de chegada remota ao provedor
nem registro persistido do relógio monotônico. O código registrado usa o pacer
corrigido; não apareceu discrepância que justifique repetir chamadas.

## Abertura: a modalidade ainda muda

Narrativa fixa:

> Um corredor de pedra fria se estende, iluminado por lâmpadas de néon piscantes; o cheiro de fumaça e chuva encharca o ar, e um sussurro distante ecoa, sugerindo que algo ou alguém observa ao longe.

O campo `t[0]` pergunta **“Quem ou o que está observando ao longe?”**.
A identidade está aberta, mas a pergunta pressupõe que a observação existe.
A origem estabelece apenas uma sugestão. Essa é a evidência decisiva da
recorrência, já prevista no [critério da hipótese](record-derivation-hypothesis-bb98ae1e-2026-09-06.md).

O resumo diz “um sussurro distante que indica presença observadora”.
Isso favorece a mesma leitura mais forte, embora “indica”, isoladamente, também
possa ter sentido evidencial. Não transformar esse verbo em prova mecânica
suficiente ou em proibição por regex.

| Campo | Revisão |
| --- | --- |
| `o` | unresolved, coerente com a mecânica original |
| `l` | “corredor de pedra fria”, sustentado por n; não repete subterrâneo/fábrica |
| `s` | Fortalece a leitura de presença; “com fumaça, chuva” pode abreviar o cheiro, sem prova inequívoca de chuva interna |
| `p` | [], sem identificação de NPC invisível |
| `f[0].s` | Conserva “sugerindo”, mas reduz “algo ou alguém” a “alguém”; estreitamento secundário de alternativas |
| `t[0]` | Pressupõe a observação que deveria continuar em dúvida |
| `t[1]` | Pergunta pela origem do sussurro efetivamente narrado |
| `r` | [], sem resolução inventada |
| `q` | “O que você faz agora?”, preserva agência |

O booleano de pendência de um fato não é um rótulo de certeza epistemológica.
Não usei `pending:false` como prova de afirmação factual.

## Mara: o erro específico papel→endereço não reaparece

Narrativa fixa:

> Mara fixa o olhar na sua postura, os dedos tremem levemente dentro do casaco. Ela respira fundo, deixa escapar um suspiro cansado e desliza, quase imperceptivelmente, um pedaço de papel amassado sobre o balcão. Não fala, mas o gesto indica que algo está prestes a ser revelado, enquanto a sirene ecoa na rua.

Os fatos “Mara desliza papel amassado sobre o balcão” e “Sirene ecoa na rua”
têm origem direta em n. Mara tem referência de ator `present`, coerente com
o elenco; a sirene não ganha um ator inventado. Não há fato atribuindo
endereço ao papel ou recebimento ao jogador.

“Mara entregará o endereço?” vem legitimamente da pendência anterior
“Descobrir se Mara entregará o endereço”. Preservar essa pergunta não equivale
a dizer que o papel contém o endereço. `l=Bar fechado`, `p=[Mara]`,
`o=unresolved` e `r=[]` permanecem coerentes.

A pergunta “O que você faz em resposta ao papel deixado por Mara?” deixa a
ação livre. “Deixado” não demonstra retirada de Mara nem recebimento pelo jogador.

Duas ressalvas não foram promovidas a violações certas: o resumo enumera verbos
em ordem diferente, mas não usa marcadores temporais explícitos; a pendência
“Qual será a reação do jogador ao papel?” é genérica e redundante, mas não impõe
uma reação nem transfere a decisão de Mara ao jogador.

## Limites formais e comparação histórica

| Caso | Palavras em s | Palavras em q | Fatos | Pendências |
| --- | ---: | ---: | ---: | ---: |
| Abertura | 19 | 5 | 1 | 2 |
| Mara | 17 | 11 | 2 | 2 |

Limites de 25/15 palavras e dois fatos/pendências respeitados. Contagem por tokens
lexicais Unicode, com apóstrofo/hífen internos preservados. Estes limites
experimentais não foram convertidos em novos gates de runtime.

Comparado aos derivados bb98 para os mesmos n: o local adicional da abertura
desapareceu, assim como a associação papel→endereço; Mara tem dois fatos em vez
dos três anteriores. A pressuposição de observação permanece. São diferenças
observadas entre execuções; não demonstram efeito causal da separação de tarefas.

As duas fixtures têm zero segredos protegidos. Não foi avaliada confidencialidade,
generalização, qualidade de novas narrativas ou benefício de duas etapas no jogo.

## Próximo passo offline concluído

Foi produzida a [matriz de modalidade e pendências](../reviews/modality-thread-matrix-c9c01a48-2026-09-07.md).
Nove execuções em memória (duas respostas, seis mutações de campo e um controle
literal) tiveram schema/atores 9/9 e admissão 8/9. Não são nove amostras do modelo.

Resumo modal e resumo que “confirma” observação passam pelos mesmos gates;
fato de Mara literal e fato que inventa endereço também passam. Um controle que
atribui pegar o papel ao jogador é recusado. Isso delimita o que a admissão
atual verifica. Não há comparação semântica universal n→registros nesses gates.

Dois achados ficam separados: uma contraprova autorada de resolução prematura
é admitida por causa de “revelado” em “prestes a ser revelado”; uma projeção em
memória retém rótulos semanticamente duplicados de pendência. Nenhum ocorreu
como efeito de estado na sondagem: r real=[], e o executor não projeta cena.
Detalhes e limites estão na matriz. Código/runtime não foram alterados.

Verificação deste trabalho: reconstrução dos dois artefatos, reprodução integral
do summary, revalidação das propostas e matriz confirmada também pela revisão
independente. Os hashes de fontes foram preservados. Sem alterações em código,
não houve repetição da suíte ampla ou dos wrappers. A falha temporal de
persistência da preparação continua histórica, sem ser reclassificada.

## Conclusão e limite de continuidade

A [hipótese aprovada](record-derivation-hypothesis-bb98ae1e-2026-09-06.md) não foi
sustentada nesta sondagem porque a relação indevida reapareceu na abertura.
Isso não prova incapacidade universal do candidato nem invalida as diferenças
favoráveis em Mara.

A revisão semântica foi concluída pelo agente neste documento separado.
O campo original `semantic_fidelity_review:not_performed` permanece no summary,
pois descreve o momento da execução; não foi reescrito. CAP-001, aceitação humana
de produto, runtime e causalidade continuam sem aprovação.

O ciclo de duas chamadas está encerrado. A análise, a matriz offline e a
[próxima hipótese documental](record-evidence-hypothesis-c9c01a48-2026-09-07.md)
estão prontas. O novo desenho tornaria explícitas origem e modalidade das
afirmações; muda o schema experimental e exige decisão específica antes da
preparação. Não existe nova chamada pendente de chave. Não repetir a sondagem
c9c01a48 ou faithful para obter aprovação.
