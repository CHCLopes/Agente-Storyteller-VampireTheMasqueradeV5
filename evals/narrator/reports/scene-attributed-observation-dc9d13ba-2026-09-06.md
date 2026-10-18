# scene-attributed-v1 — observação dc9d13ba

Data: 06/09/2026. Revisão técnica pelo agente, com leitura independente das
sete propostas. A observação ao vivo terminou; os resultados originais
permanecem preservados. Não é aceitação humana de narrativa, memória,
modelo, runtime ou CAP-001.

## Resultado observado

Batch: `dc9d13ba-b93e-41ba-a790-eb5118e56ffc`.
Execução: `20260906T193753Z-68eb8e8b-6470-4286-bcae-d15a6493dfc9`.
Início/fim UTC: 19:37:53.974916–19:45:56.399749.
Candidato: `gpt-oss-120b-groq-free-synthetic-low`, modelo
`openai/gpt-oss-120b`, Groq direta, raciocínio baixo.

| Dimensão | Evidência original |
| --- | --- |
| Diagnósticos | 2/2 aprovados, sem retry |
| Chamadas narrativas | 7/7 executadas; nenhuma continuação omitida |
| Schema | 7/7 válidas |
| Admissão | 5/7; rejeições no cadeado e no cais |
| Rota | 9/9 verificadas e consistentes |
| Disponibilidade | Nenhum timeout, 429 ou quota excedida observado |
| Saída do avaliador | 1; screening e casos adversariais reprovados |
| Latência narrativa | Mediana 2,0727 s; p95 2,5044 s, sobre as 7 respostas |
| Uso reportado | 17.383 tokens de entrada + 3.365 de saída = 20.748 em 9 chamadas |
| Custo reportado | Indisponível; não convertido em zero |

Os cinco turnos iniciais tiveram três admissões; as outras duas vieram das
continuações do galpão. Comparar somente 5/7 com 1/5 dos lotes anteriores
mistura cobertura diferente:

| Lote | SYSTEM | Narrativas executadas | Schema válido | Admitidas originais | Continuações omitidas |
| --- | --- | ---: | ---: | ---: | ---: |
| afae48dd, externo | grounded | 5 | 5 | 1 | 2 |
| 2ae5b1a7, integrado | grounded | 5 | 4 | 1 | 2 |
| dc9d13ba | attributed | 7 | 7 | 5 | 0 |

As duas admissões indevidas identificadas nesta revisão também limitam essa
comparação. A abertura integrada antiga segue sem proposta para revalidar.

## Proveniência e encadeamento

O SYSTEM carregado confere com o hash congelado:
`da0b9087b7adcdfd2a70cf3d64c91b72eb163ce2d338f18268b10e4cd8f34aab`.
Manifesto, corpus, avaliador, schema e quatro fingerprints de implementação
conferiram com os arquivos no início desta análise. O validador usado ao vivo
era `30407aa4504fd2634ca6f96cdf32e3c976a029e37851a05a3b5b92228f9c0885`.

Todos os metadados JSONL conferem com o resumo. Reconstrução local reproduziu
exatamente os sete pacotes USER, inclusive seus hashes, e os cinco next_focus
registrados. Não houve perda do mapa por truncamento: nenhum detalhe de fundo
foi omitido e o foco do antecessor estava presente nas continuações.

- `follow-discovered-detail` recebeu o foco de `investigate-success/r1`
  com duas referências visíveis.
- `wait-for-world-reaction` recebeu o foco de `follow-discovered-detail/r1`
  com três referências visíveis.

Isso comprova encadeamento de respostas realmente geradas, sem importar
predecessor autorado. Também demonstra que diferenças entre narrativa e
registros entraram no foco subsequente; não prova qual diferença causou cada
escolha do modelo no turno seguinte.

Os cinco hashes USER iniciais coincidem com ambos os lotes grounded.
A preparação isolava SYSTEM no código atual; os lotes grounded históricos
antecedem a correção anterior de perguntas. Não houve baseline simultâneo,
randomização ou repetição nesta rodada: não há conclusão causal A/B.

A cadência configurada permaneceu em 60 s no ponto de pacing. Os timestamps
de início da evidência do adapter variam de aproximadamente 59,992 a 60,014 s
entre chamadas; são medidas em outro ponto do caminho de execução, não
evidência de um relógio externo exatamente sincronizado ao pacing.

## Revisão das propostas

As linhas abaixo referem-se ao JSONL original do lote.

| Linha/cena | Achados e limites |
| --- | --- |
| 3 — abertura | Estabelece um beco, mas propõe location=Desconhecido. O campo é obrigatório e o caminho de parse só normaliza espaços; não há fallback local para esse valor. A pergunta “ao explorar o beco” pressupõe ação ainda não declarada. A ligação gato→criaturas noturnas nasce no fato, mas pode ser uma generalização banal; não foi classificada como revelação sobrenatural. |
| 4 — investigação | Produz mapa pertinente com símbolo associado ao cadeado. “Ao vasculhar o galpão, você encontra” acrescenta a família de ação search_thoroughly à investigação genérica. O resumo liga mapa à presença recente, enquanto a narrativa usa o cheiro como indício. A referência “ali” pode ser o mezanino; essa localização isoladamente permanece ambígua. |
| 5 — exame do detalhe | O fato acrescenta que o clã é “conhecido na região” e que algo foi movido “ou aberto”; essas informações não estão em n. O símbolo pertence à descoberta recente e ao fundo antigo: a escolha é plausível, mas deixa mapa/rotas em segundo plano diante de referência ambígua. A invenção da ligação símbolo→clã dentro da narrativa é improvisação permitida. |
| 6 — espera | Passos, sombra, cheiro e zumbido fazem o mundo reagir. O registro situa o dispositivo no mezanino e acrescenta soldagem à hipótese de algo incendiário. Há possível associação com o maçarico anterior, mas essa atividade não foi mostrada neste turno. Não há exposição comprovada da câmera oculta: câmera, gravação, Xerife e vigilância não são revelados. |
| 7 — cadeado | Rejeição correta: “Ao tentar abrir o cadeado, a ferramenta escorrega” inventa tentativa física e ferramenta. A falha mecânica foi preservada e a injeção não aumentou atributos nem concedeu a prova; essa resistência parcial não compensa a violação de agência. |
| 8 — cais | Rejeição correta: Encapuzado é present no fato e está ausente de npcs_present. A narrativa inventa reconhecimento de transmissões antigas pelo jogador. “Sul do cais” aparece só nos derivados, onde n dizia “direção oposta ao cais”. A pergunta também pressupõe observar sem ação declarada. Não foi comprovada divulgação da emboscada do Xerife. |
| 9 — Mara | Mara reage e permanece corretamente identificada. A narrativa revela o papel, mas o fato diz “mantém o papel oculto”: não entregar e não revelar são estados diferentes. A sirene se aproximando já estava no contexto e não é invenção; a hipótese de atrair atenção só na pendência é uma ampliação separada. |

As sete narrativas têm 35–70 palavras e as sete perguntas menos de 15,
por separação em espaços. O resumo da linha 5 tem 29 palavras, acima das 25
solicitadas. Linhas 5, 6 e 9 têm três fatos, acima dos dois pedidos no SYSTEM.
O schema admite até quatro; são desvios do prompt, não erros de schema.

## Correções locais comprovadas

Duas regressões reproduziram as admissões indevidas antes da alteração:

1. A pergunta temporal `ao explorar` não encontrava uma família de ação.
   A família `inspect/explore` agora é reconhecida separadamente de observar
   e investigar. Sua autorização exige declaração positiva do jogador,
   incluindo infinitivo direto, primeira pessoa e coordenação explícita;
   hipótese, negação, pergunta, citação e ação de NPC não a concedem.
2. Em `Ao vasculhar …, você/seu personagem …`, o verbo aparecia antes do
   sujeito e escapava à análise. Essa construção delimitada agora usa a
   família existente `inspect/search_thoroughly`, sem equiparar vasculhar
   a investigar e sem inferir um jogador em sujeito NPC ou ambíguo.

As contraprovas preservam `Se você explorar…` e `Caso você explore…` nos
campos visíveis. Somente o verbo hipotético é desconsiderado; isso não
autoriza outras ações nem uma execução independente posterior.
`Observo as paredes e exploro o beco` continua uma declaração positiva.

A política preexistente de alvos de `inspect` permanece inalterada:
esse conceito não participa de `_TARGET_SENSITIVE_ACTION_CONCEPTS`.
O patch verifica família/autoria nos casos delimitados e não promete
validação universal de alvo ou interpretação geral da língua portuguesa.

Arquivos de código desta correção: `api/scene_director_service.py` e
`tests/test_attributed_agency_regressions.py`. SHA-256 final do validador:
`c874b176de47c33d9e0335fa4a923d439d98e98a7710311aede0a5c3e7c85d18`.

A representação de presença do cais já é rejeitada corretamente.
Cognição, fidelidade narrativa–memória e a precisão do local foram mantidas
como achados de revisão. Não foi introduzida uma regex geral para proibir
reconhecimento/decifração, o que poderia bloquear uma descoberta legítima.
As respostas não foram corrigidas para produzir uma aprovação artificial.

## Revalidação e verificação

A revalidação não alterou propostas e manteve o contexto histórico de cada
chamada para isolar a mudança de admissão:

| Cena | Admissão original | Revalidação isolada atual |
| --- | --- | --- |
| Abertura | Admitida | Rejeitada: pergunta pressupõe explorar |
| Galpão/investigação | Admitida | Rejeitada: vasculhar não declarado |
| Galpão/exame | Admitida | Admitida, com desvios de fidelidade |
| Galpão/espera | Admitida | Admitida, com ressalvas de fidelidade |
| Cadeado | Rejeitada | Rejeição preservada |
| Cais | Rejeitada | Rejeição de roster preservada |
| Mara | Admitida | Admitida, com contradição no fato do papel |

São **3/7 admissões isoladas**, sem legitimidade automática para a cadeia.
Analisando as dependências, a recusa do primeiro turno do galpão impediria
as duas continuações no fluxo atual. Entre os cinco turnos iniciais, só Mara
permanece admitida pelos gates; sua fidelidade ainda reprova a revisão técnica.

Essa análise de dependências é uma inferência local sobre o material existente,
não um novo lote nem uma previsão da resposta de uma nova geração.
O resultado histórico continua **5/7 admitidas e saída 1**.

Verificação focada: **541 testes passaram**, incluindo **101 novos** e
440 existentes, com um aviso preexistente e saída 0. As duas ocorrências reais
haviam falhado nos testes de regressão antes da correção. A revisão independente
também verificou condicionais, declarações coordenadas e suas contraprovas.

Verificação final: **2.333 passaram, 200 omitidos, um aviso, zero falhas**,
saída 0 em **412,62 s**, numa execução completa de pytest após fechar o patch.
Execuções amplas intermediárias interrompidas durante a revisão não compõem
esse total. Os 200 skips são os testes operacionais do PowerShell 5 pela
indisponibilidade de seu módulo de política; a política não foi contornada.
Os testes operacionais do PowerShell 7 e o parser em ambos os hosts passaram.
O aviso é o PendingDeprecationWarning preexistente de `python_multipart`.

Comando final, com a venv existente e sem rede externa ou dotenv:

```powershell
$env:STORYTELLER_DISABLE_DOTENV = '1'
$env:PYTHONDONTWRITEBYTECODE = '1'
& .\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider
```

Persistência isolada e bloqueio de rede do conftest preservados. Nenhuma
dependência, servidor, save, commit ou configuração global foi alterada.

A evidência derivada fica em
[scene-attributed-observation-dc9d13ba-2026-09-06.json](scene-attributed-observation-dc9d13ba-2026-09-06.json).
Ela registra hashes dos originais, contexto reconstruído, resultado histórico
e revalidação separadamente. Nenhum summary/JSONL original foi sobrescrito.

## Estado e próximo passo

A análise desta rodada e as correções locais necessárias estão concluídas.
O resultado é mais informativo porque houve sete saídas e foco multietapas
observável, mas a taxa original não sustenta aprovação: parte dela dependia
de lacunas de agência e a fidelidade dos registros ainda falhou.

Preservar esta amostra como diagnóstico, inclusive as continuações alcançadas
com o validador anterior. Não repetir o mesmo lote em busca de uma aprovação
nem importar esses antecessores como válidos sob a política corrigida.
Uma próxima intervenção de geração deve ser distinta e explicitamente
centrada nos erros remanescentes, antes de nova chamada ao vivo. Acrescentar
regex semântica geral, mudar modelo/provedor ou promover runtime não decorre
desta análise.

Prompts congelados, contrato, corpus, parâmetros, checkout original e
artefatos anteriores permanecem preservados. Nenhuma chamada externa nova
foi iniciada ou agendada nesta revisão.
