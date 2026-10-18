# Observação faithful bb98ae1e — recorrência, cobertura e correção local

Data: 06/09/2026. Lote `bb98ae1e-529b-4645-be17-ffe42734db14`.
Análise offline da única observação completa previamente delimitada. Nenhuma
chamada real foi feita pelo agente. O lote terminou com exit 1; seus artefatos
originais não foram modificados.

## Respostas às perguntas registradas

1. **A abertura preservou a agência nesta resposta.** Não há ação imposta,
   chegada, despertar ou passado inventado do jogador.
2. **Método adicional e deriva narrativa→memória reapareceram.** O cadeado
   recebeu manipulação física não declarada; o galpão acrescentou causalidade
   no resumo e Mara recebeu uma ligação entre pistas apenas num fato derivado.
3. **A continuidade do galpão continuou sem cobertura.** O primeiro turno foi
   recusado. As duas continuações foram corretamente omitidas, sem importar
   predecessor ou gerar respostas que não tiveram contexto admitido.

O critério de parada pré-registrado foi atingido: término da observação,
inclusive com falhas. Isso não autoriza repetir o mesmo lote até passar.
A revisão técnica independente chegou às mesmas conclusões.

## Resultado observado

| Dimensão | Resultado |
| --- | --- |
| Chamadas | 2 diagnósticos + 5 narrativas = 7; 2 continuações não chamadas |
| Diagnósticos | Texto e streaming passaram, sem retry |
| Schema | Todas as 5 propostas recebidas são válidas |
| Admissão histórica | 2: abertura e Mara |
| Rota | Groq / `openai/gpt-oss-120b`, verificada nas 7 chamadas |
| Disponibilidade | Nenhum HTTP 400, 429 ou timeout registrado |
| Latência narrativa | Mediana 1,9923 s; p95 2,2106 s, nas 5 respostas |
| Uso das chamadas feitas | 13.985 tokens de entrada + 2.428 de saída = 16.413 reportados |
| Custo | Indisponível; não convertido em zero |
| Resultado | Gates não passaram; runtime e CAP-001 continuam sem aprovação |

O campo de uso agregado é `partial` porque o plano completo previa nove
chamadas e duas foram omitidas. **Todas as sete chamadas realizadas informaram
uso**; nenhuma chamada efetiva está com uso ausente. No lote faithful anterior,
o HTTP 400 tinha deixado uma chamada sem uso reportado: os dois significados
de parcial não devem ser confundidos.

`all_expected_turns_schema_valid:false` inclui os dois turnos omitidos.
Não significa que alguma das cinco propostas recebidas tenha JSON ou schema
inválido. Da mesma forma, ausência de timeout/rate limit nas chamadas feitas
não transforma a cadeia incompleta em avaliação completa.

## Propostas e fidelidade

| Caso | Admissão original | Evidência e limite da conclusão |
| --- | --- | --- |
| Abertura | Sim | Agência preservada. `n` sugere observação; resumo e pendência aumentam a certeza. “Subterrâneo” e “velha fábrica” aparecem somente em `location`. |
| Galpão | Não | “Ao vasculhar” é método de busca adicional segundo a política vigente; não implica que houve toque explicitamente narrado. O resumo acrescenta “odor ... indica atividade recente”, ausente em `n`. |
| Cadeado | Não | O diagnóstico `wait` atribuiu o estado do cadeado ao jogador. Há também violação real: “Você tenta manipular o cadeado” para uma investigação sem método físico declarado. |
| Cais | Não | Fato `npc_action` veio com `actors:[]`, contrariando o contrato. A sombra não autoriza inventar uma identidade para preencher o campo. |
| Mara | Sim | NPC reage e deixa a ação do jogador livre. O terceiro fato cria o vínculo papel→endereço somente no registro e ultrapassa o máximo experimental de dois fatos. |

No galpão, a descoberta do caderno e das rotas é improviso pertinente ao sucesso.
Não é necessário que toda pista repita rádio/cadeado do contexto. O defeito
de fidelidade é a inferência temporal e causal acrescentada apenas ao resumo;
“caderno sangrado” também é uma formulação pouco natural.

No cadeado, o resultado permaneceu `failure`, o arquivo continuou inacessível
e a injeção não concedeu atributos ou prova. Isso não autoriza completar uma
tentativa física pelo jogador. A resposta integral precisa continuar recusada
por essa violação, mesmo depois de corrigido o motivo falso.

No cais não foi observada divulgação específica do Xerife ou da emboscada,
inclusive nos registros. A passagem de sombra para “figura misteriosa” merece
ressalva de certeza; não demonstra identificação do responsável. A regra de
participante obrigatório para `npc_action` está correta e foi preservada.

Em Mara, o contexto já menciona um endereço procurado, mas isso não estabelece
sua ligação com o novo papel. O SYSTEM proíbe introduzir essa relação apenas no
registro, inclusive usando “pode”. “Entrega” frente a “desliza sobre o balcão”
é uma ressalva de precisão: não prova recebimento pelo jogador. Não há
contradição demonstrada sobre mãos, pois a narrativa não especifica a mesma mão.

As contagens por separação em espaços de `n/s/q` são:

| Caso | Narrativa | Resumo | Pergunta | Fatos |
| --- | ---: | ---: | ---: | ---: |
| Abertura | 35 | 13 | 5 | 2 |
| Galpão | 51 | 16 | 8 | 2 |
| Cadeado | 38 | 11 | 15 | 1 |
| Cais | 34 | 15 | 5 | 2 |
| Mara | 53 | 14 | 6 | 3 |

O cais fica uma palavra abaixo das 35–70 solicitadas; Mara supera dois fatos.
São desvios do SYSTEM experimental, sem alteração dos limites do schema/runtime.
Os resumos e perguntas respeitam os limites solicitados. Uma admissão automática
não equivale a fidelidade semântica, como os dois casos admitidos demonstram.

A auditoria JSON inclui três pares com contrapontos autorados para revisar
certeza, causalidade e relação entre pistas. Eles classificam somente essa
dimensão e não são respostas reais, correções dos artefatos, narrativas
obrigatórias ou prova de admissão integral.

## Proveniência e comparação histórica

Antes da correção, coincidiram avaliador, contexto/foco, atores, validador,
serviço de cena, manifesto, corpus, SYSTEM e schema com os hashes registrados.
Os metadados foram conferidos nas nove linhas; os sete IDs de invocação são
distintos. Os cinco pacotes USER e os dois focos das propostas historicamente
admitidas foram reconstruídos exatamente.

SYSTEM: `76a9ffdb37296be672e94e1a8c741d90cb5c44164c8dcf888107d308865218d2`.
Schema: `bdbda5ab60a1d9c4af44bcadf3be3d09b333b566b61cad9f68cfa7e8a9065bd2`.
O adaptador Groq permaneceu `dbcde3da86ad591d2ccc2891d0425e30b3d9a5eb7ea09af5132e7417e1e94328`;
o registro da avaliação não inclui seu hash, portanto essa verificação é local.

Os cinco USERs coincidem com o [primeiro faithful](scene-faithful-observation-aa2ea81c-2026-09-06.md);
a abertura coincide também com a [sondagem estruturada](structured-error-observation-8636fac3-2026-09-06.md).
As fontes históricas mantiveram seus hashes. Os validadores mudaram entre os
lotes; não se trata de A/B causal.

| Observação | Abertura | Galpão/continuações | Admissões originais |
| --- | --- | --- | --- |
| Faithful aa2ea81c | HTTP 400, sem proposta | Predecessor recusado; 2 skips | Cais e Mara |
| Probe 8636fac3 | Schema válido; pergunta recusada, depois ação indevida demonstrada offline | Não fazia parte do probe | Nenhuma |
| Faithful bb98ae1e | Schema válido e agência preservada | Predecessor recusado; 2 skips | Abertura e Mara |

A nova abertura é um resultado observado melhor nessa dimensão; uma amostra
não demonstra consistência ou melhora causada pelo prompt. A quantidade de
admissões ficou igual à do primeiro faithful, mas os casos admitidos mudaram.
Nenhuma proposta nova preenche retroativamente lacunas dos lotes anteriores.

O menor delta entre timestamps UTC de início foi **59,979375 s**, 20,625 ms
abaixo de 60 s. Esses timestamps são capturados no adaptador, depois do pacer
e de trabalho local de preparação; não são registros dos despachos do provedor.
O relógio UTC local é ajustável e tem resolução declarada de 15,625 ms. Portanto
o delta sozinho não demonstra a causa nem mede exatamente o intervalo remoto.

A inspeção revelou um defeito independente e reproduzível no pacer: após
`sleep(remaining)`, o código somava o atraso solicitado ao horário antigo,
sem reler o relógio. Numa simulação sem provedor, uma espera excedida em 25 ms
produziu inícios em 0, 60,025 e 120 s; o último intervalo ficou em 59,975 s.
Essa demonstração justifica a correção, mas não atribui retrospectivamente a
ela o desvio deste lote.

A correção relê o relógio após cada espera e recalcula o restante até cumprir
o intervalo. O relógio padrão passou a `perf_counter`, que neste Python 3.12.2
usa QueryPerformanceCounter, é monotônico/não ajustável e tem resolução
declarada de 100 ns; `monotonic` usava GetTickCount64 com 15,625 ms.
O intervalo configurado continua 60 s. Isso verifica o agendamento local,
sem alegar medição de chegada das requisições ao servidor remoto.

## Correções locais e revalidação

O escopo foi restrito ao validador de cena, ao pacer do avaliador e aos testes
necessários. Não foram alterados SYSTEM, USER, schema, contrato de atores,
adaptador, corpus, modelo ou parâmetros de geração.

**Atribuição e manipulação.** A cláusula iniciada por “Você” incluía também
“mas ele permanece firme”; o verbo do cadeado era classificado como espera
do jogador. A resolução de pronome podia repetir o mesmo erro. A correção
reconhece somente o predicado de estado físico de barreira com sujeito explícito
ou antecedente direto e compatível. Ela isenta apenas esse verbo; não ignora
ações seguintes, um pronome ambíguo ou o próprio jogador.

“Manipular” não fazia parte das ações reconhecidas. Um controle sintético
com “Você tenta manipular o cadeado” era indevidamente admitido para
“Investigo o cadeado”. A nova família exige declaração positiva e alvo
compatível; investigar não passa a autorizar manipular. Formas nominais,
negações, hipóteses, texto citado e ações de NPCs são distinguidos nas
contraprovas. A revisão independente do primeiro patch encontrou recusas de
condições posteriores e passagem de algumas referências corporais possessivas
na nova dispensa de NPC; esses casos foram corrigidos antes da verificação
final. Os controles de aliases iguais a nomes de objetos já eram recusados
integralmente, portanto não motivaram alteração adicional. O ajuste preserva as verificações gerais; não é uma alegação
de interpretação universal do português.

Com o código final, a **proposta original e integral do cadeado continua
recusada**, agora por `scene_player_agency_violation`, campo `narrative`,
regra `undeclared_player_action`, sujeito `voce`, cláusula 0,
conceito `interact`. Não houve edição de sua narrativa, resumo, fatos ou contexto.

As cinco propostas originais mantêm as mesmas decisões finais: duas admissões
e três recusas. O galpão continua com `undeclared_player_temporal_search`;
o cais, com `npc_action_requires_actor`. Os dois skips foram preservados.
Mudar o primeiro motivo de rejeição não melhora a geração ou a taxa de admissão.

**Agendamento.** O pacer foi corrigido conforme a reprodução descrita acima.
O teste antigo recebeu somente uma amostra adicional de relógio após a espera;
a expectativa de uma espera de 4,5 s permaneceu intacta. As novas regressões
cobrem espera excedida, retorno antecipado, cancelamento, intervalo zero e
intervalo já transcorrido. Nenhuma chamada de provedor participa desses testes.

Validador anterior: `3c963e608942919361444ec9d07504a38b62ebcbbceebbca2c6ec4368911bdfb`.
Validador final: `520ad02bd4c0cac2961bb11556533f93eaa94cbfeac3cbb4ef20df14b49cbc58`.
Avaliador anterior: `c040ea187a5631bf796f9ff041508fe22e966f03329ca91c89d1585bb7919ea0`.
Avaliador final: `0fc29dc11b4472bd6b67db9be0980beed9f69f3e4947a87f811727af644f0e82`.

O [JSON de auditoria](scene-faithful-observation-bb98ae1e-2026-09-06.json)
distingue esses hashes locais dos hashes sob os quais o lote foi executado.

## Verificação corrente

A execução final foi feita com os hashes de código congelados e dois grupos
disjuntos:

| Grupo | Passaram | Duração | Saída |
| --- | ---: | ---: | ---: |
| Suíte Python, exceto os dois módulos com wrappers | 2.616 | 103,94 s | 0 |
| Integração Python da sondagem estruturada (`-k 'not wrapper'`) | 38 | 2,22 s | 0 |
| Total corrente | **2.654** | Grupos paralelos | **0** |

Sem falhas ou skips nos grupos executados. As **73 novas regressões**
(64 de estado/agência e 9 de pacing) estão incluídas nesses números.
As 16 contraprovas integrais independentes ficaram com 16 classificações
corretas e não foram somadas ao total do pytest. Nenhum achado acionável
restou na revisão delimitada.

Cada grupo apresentou somente o aviso preexistente de `python_multipart`.
Os runners PowerShell e seus testes permaneceram inalterados.
`tests/test_prompt_experiment_runner.py` não foi reexecutado; os 78 testes
operacionais/parser da sondagem foram deselecionados. Os 38 testes Python
da sondagem foram executados. Não houve contorno de política de PowerShell.

Comandos usaram o venv existente, `STORYTELLER_DISABLE_DOTENV=1`,
`PYTHONDONTWRITEBYTECODE=1` e `-p no:cacheprovider`, com persistência isolada
e rede externa bloqueada pelo `conftest.py`. Não houve instalação, acesso
a credencial, edição de artefatos originais de avaliação ou mudança no checkout original.

Arquivos de código/teste deste ciclo: `api/scene_director_service.py`,
`scripts/evaluate_narrator_models.py`, `tests/test_narrator_eval.py`,
`tests/test_faithful_object_state_regressions.py` e
`tests/test_narrator_pacing_regressions.py`. O diff do teste antigo altera
somente a amostra de relógio já descrita. Os demais deltas do worktree
precedem este ciclo e foram preservados.

## Encerramento e limites do próximo passo

A análise, as correções locais demonstráveis e a revalidação desta observação
foram concluídas. O resultado continua insuficiente: método físico foi
acrescentado, registros alteraram relações da narrativa e a cadeia do galpão
permaneceu sem cobertura.

Nenhum novo SYSTEM, geração adicional, retry narrativo, fallback ou modelo
julgador foi preparado ou executado. Não corrigir automaticamente as respostas,
substituir predecessor recusado ou transformar os contrapontos autorados em
evidência gerada pelo modelo.

A [hipótese de derivação separada](record-derivation-hypothesis-bb98ae1e-2026-09-06.md)
já está formulada: duas narrativas sintéticas fixas, uma chamada de derivação
por entrada, no máximo duas chamadas, sem gerar outra narrativa, sem retry ou
fallback. O documento especifica entradas, schema experimental proposto,
variáveis, análise, critério de parada e preparação offline necessária.

Essa proposta ainda não está implementada. O passo restante depende de uma
decisão específica: autorizar a mudança do escopo experimental de uma chamada
SYSTEM-only para derivação separada com schema próprio. Isso não se confunde
com avaliação intermediária das correções locais, que já foram concluídas.
Não há comando novo pendente nem credencial a inserir neste momento.

A avaliação técnica do agente não preenche os campos reservados à aceitação
humana de produto/CAP-001. Nenhum resultado deste desenho promoverá o runtime
ou uma arquitetura de duas etapas automaticamente.
