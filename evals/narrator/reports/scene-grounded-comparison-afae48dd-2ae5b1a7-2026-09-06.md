# scene-grounded-v1 — comparação de duas observações

Data: 06/09/2026. Observações concluídas; ambos os lotes ao vivo reprovaram os gates.
Comparação observacional da mesma configuração, sem conclusão causal A/B,
aprovação de qualidade, CAP-001 ou promoção ao runtime. Nenhuma nova chamada
foi executada pelo agente nesta análise.

## Fontes e comparabilidade

- Externo: batch `afae48dd-840e-42e0-8628-9432541d0ac1`;
  [summary](../../../eval-results/20260906T155743Z-61410a16-34d9-4271-a68f-4d0c999d131e/summary.json)
  e [JSONL](../../../eval-results/20260906T155743Z-61410a16-34d9-4271-a68f-4d0c999d131e/gpt-oss-120b-groq-free-synthetic-low.jsonl).
- Integrado: batch `2ae5b1a7-2827-4b3e-8090-b236045d79b4`;
  [summary](../../../eval-results/20260906T160840Z-71f1f555-1887-4ee6-bf0f-09272797333c/summary.json)
  e [JSONL](../../../eval-results/20260906T160840Z-71f1f555-1887-4ee6-bf0f-09272797333c/gpt-oss-120b-groq-free-synthetic-low.jsonl).

Os resumos e todos os nove registros de cada JSONL foram lidos. As identidades
registradas coincidem: candidato GPT-OSS 120B/Groq direto, raciocínio baixo,
temperatura 0,65, teto narrativo 768, diagnósticos 128, deadline 60 s,
manifesto, corpus, SYSTEM, schema, avaliador e quatro módulos de implementação.
Os cinco pares de chamadas narrativas têm o mesmo hash de USER.
SYSTEM: `ff47d144200ddaac14c7db30f6328f73de5fb466730fe178fb49dc335dbac331`.

No horário de Fortaleza, o externo ocorreu de 12:57:43 a 13:03:46 e o integrado
de 13:08:40 a 13:14:42. Não houve sobreposição; intervalo de 293,761822 segundos
entre as janelas. Pacing configurado de 60 s, com inícios aproximadamente
60 s apartados. Os fingerprints não registram todo o ambiente/HTTP; não há
evidência de que usar terminal externo ou integrado causou as diferenças.

## Resultados históricos preservados

| Medida | Externo | Integrado |
| --- | ---: | ---: |
| Diagnósticos aprovados | 2/2 | 2/2 |
| Chamadas realizadas / previstas | 7/9 | 7/9 |
| Chamadas narrativas | 5 | 5 |
| Propostas com schema válido | 5 | 4 |
| Propostas admitidas | 1 | 1 |
| Continuações puladas | 2 | 2 |
| Identidade de rota verificada | 7/7 | 6/7 |
| Divergências de identidade | 0 | 0 |
| Timeout / 429 / quota excedida observados | 0 | 0 |
| Saída do avaliador | 1 | 1 |
| Mediana de latência das respostas com schema válido | 2,0011 s (n=5) | 2,0964 s (n=4) |
| Subtotal de tokens reportados | 13.058 (7 chamadas) | 10.704 (6 chamadas) |
| Custo | indisponível | indisponível |

A abertura integrada recebeu `invalid_request/http_400`, sem proposta,
uso ou modelo efetivo reportado. O JSONL não preserva corpo bruto, conteúdo
gerado ou `json_validate_failed`; a causa específica é desconhecida.
Não concluir que houve JSON malformado, troca de modelo ou falha de conexão
TCP a partir do rótulo `phase: connect`. Groq foi observado; falta identidade
verificável do modelo apenas nessa chamada, com zero mismatches.

Os subtotais brutos de tokens não medem economia. Nos seis pares com uso
reportado, os totais são 10.570 no externo e 10.704 no integrado, com a mesma
entrada de 8.598 tokens. A ausência de uso da abertura explica a redução do
subtotal agregado. Nas quatro narrativas comuns, as medianas são 2,07115 s
e 2,09644 s. Amostra pequena e coberturas diferentes não estabelecem ganho de
latência; os p95 históricos são máximos de quatro/cinco amostras.

## Revisão por cena

A avaliação qualitativa usa a [rubrica de fidelidade](../reviews/narrative-memory-fidelity-v1.md).
É revisão do agente; as notas humanas dos artefatos continuam não preenchidas.

| Cena | Externo | Integrado |
| --- | --- | --- |
| Abertura | Rejeição real: `jovens de couro` aparecem como atores presentes, mas faltam em `npcs_present`. Resumo/fatos acompanham a cena; prosa genérica e rótulo pouco natural. | HTTP 400; sem proposta para comparar prosa, memória ou agência. |
| Galpão | Primeiro erro é rótulo `Encapuzado` diferente de “figura encapuzada”. Também faz o jogador romper a porta, expõe a câmera do confidencial e pressupõe confronto na pergunta. “Violência recente” surge apenas no fato derivado. | Primeiro erro é rótulo de ator ausente do fato. Escadaria, livro e aparelho são tratados como atores NPCs; a narrativa passa da investigação a “ao abrir” a laje. Hipótese de vigilância aparece apenas no fato derivado. |
| Cadeado / injeção | Mantém failure, porém inventa tentativa de força. Ruído/vibração vira pressão interna aumentada e risco de colapso somente nos derivados. | Mantém failure, porém também narra força não declarada. Rejeição histórica inicial foi da pergunta; após correção local, a violação de agência continua sendo rejeitada. Os passos já vinham do contexto; “antagonistas” aparece como interpretação nova na pendência. |
| Cais / sigilo | Não expõe Xerife/emboscada, mas “ao investigar” na pergunta pressupõe ação não declarada. Resumo registra chegada de maneira mais afirmativa que a comparação em n. | Não expõe Xerife/emboscada. A pergunta sofreu falso positivo local. O hook liga brilho a algo deixado/carregado por quem passou, relação ausente de n, ainda que modalizada. |
| Mara | Admitida. NPC reage sem controlar o jogador; resumo/fatos são majoritariamente fiéis. “Decidir se Mara entregará o endereço ou fugirá” deixa o responsável ambíguo, sem provar transferência da decisão ao jogador. | Admitida. Mostra/examina/esconde papel, sem impor ação ao jogador. O fato “dificultando a comunicação” acrescenta efeito não estabelecido em n e já entra em `next_focus.visible_facts`. |

Indecisão de Mara, endereço pendente e sirene aproximando-se já pertencem ao
contexto; não classificá-los como invenções. Tampouco concluir que o papel
mostrado contém o endereço. Improvisar uma pista em n continua permitido;
criar uma ligação nova somente no registro derivado é problema distinto.

As nove narrativas disponíveis têm 42–51 palavras; resumos 12–24 e perguntas
9–14, por divisão em espaços. Os limites de extensão pedidos não foram o
problema desses lotes. O galpão externo e galpão/cais/Mara integrados têm três
fatos, acima do máximo dois do SYSTEM; o schema permite quatro, portanto
schema válido não equivale a cumprimento integral do prompt. O schema não
foi alterado para preservar a comparação e os critérios vigentes.

As duas continuações do galpão foram puladas em cada lote devido à rejeição
do predecessor. Não existe narrativa nesses registros, nem prova de
continuidade autogerada. O primeiro erro de admissão não enumera todos os
defeitos: atores são validados antes dos demais gates.

## Correção local e revalidação offline

Dois falsos positivos foram reproduzidos antes da alteração:

- “Qual será sua próxima tentativa para acessar o arquivo?” falhava; trocar
  apenas “tentativa” por “ação” passava.
- “Qual próximo passo deseja tomar para investigar o brilho ou o vulto?”
  falhava; acrescentar apenas “você” antes de “deseja” passava.

A correção em `api/scene_director_service.py` reconhece “tentativa” na forma
possessiva e a construção elíptica inicial “Qual (o) próximo passo deseja tomar”.
O match é limitado a término ou cauda de contexto/objetivo sem vírgulas, e é
usado para convite aberto, destinatário e posição do jogador. Sujeitos NPCs
invertidos, vocativos e cues subordinados não recebem essa nova autorização.

Limite: a forma possessiva herda a detecção de vocativo baseada em NPC
cadastrado. Vocativo desconhecido após uma pergunta possessiva já era
limitação das formas “atitude/ação”; não se afirma cobertura semântica universal
nem se ampliou esta intervenção para resolver esse problema geral.

Foi feita revalidação em memória das propostas originais, com o schema
focused, atores, corpus, entradas, mecânica e segredos preservados. Nenhum
texto gerado foi corrigido e nenhum turno pulado foi gerado. O
[registro derivado](scene-grounded-comparison-afae48dd-2ae5b1a7-2026-09-06.json)
contém hashes dos quatro artefatos originais, configuração comum e resultados:

| Cena | Externo após correção local | Integrado após correção local |
| --- | --- | --- |
| Abertura | Rejeitada: roster | Não revalidável: sem proposta |
| Galpão | Rejeitado: rótulo de ator | Rejeitado: rótulo de ator |
| Cadeado | Rejeitado: tentativa física não declarada | Rejeitado: tentativa física não declarada |
| Cais | Rejeitado: investigação pressuposta | Admitido pelos gates atuais, com ressalva qualitativa de memória |
| Mara | Admitida, com ressalva de clareza da pendência | Admitida, com ressalva de fidelidade do fato derivado |

Assim, o externo continua com 1/5 propostas admitidas; o integrado tem 2/4
propostas disponíveis admitidas na revalidação offline. Seus resultados ao
vivo originais continuam 1/5 chamadas narrativas admitidas em cada lote.
A abertura integrada não foi reinterpretada como sucesso nem repetida.

## Verificação e próximo passo

- Antes da correção: 16 casos positivos falharam e dois já passavam no grupo
  de perguntas, confirmando o defeito e um controle existente.
- 61 regressões novas em `tests/test_grounded_player_question_regressions.py`.
- 324 testes focados passaram, com um aviso.
- Suíte completa: **2.142 passaram, 126 omitidos, um aviso, zero falhas**,
  código de saída 0 em 312,62 s. Os 126 skips são os testes operacionais
  do PowerShell 5 por indisponibilidade do módulo de política, já
  documentados na preparação; nenhum contorno foi aplicado. O aviso
  é o PendingDeprecationWarning existente de python_multipart.
- `STORYTELLER_DISABLE_DOTENV=1`, persistência isolada e bloqueio de rede do
  pytest preservados. Sem dependências, servidor, saves, commits ou alteração
  do checkout original.
- Diff do serviço revisado contra snapshot anterior; prompts congelados,
  corpus, manifesto e artefatos históricos preservados.

Próximo passo: usar os casos de agência, atores e deriva narrativa–memória
desta revisão para definir a próxima intervenção isolada antes de nova
observação. Repetir a bateria idêntica não resolve os defeitos demonstrados.
A fidelidade semântica ainda requer revisão; acrescentar outra regex genérica,
mudar modelo/provedor, reduzir critérios ou promover runtime não decorre
destes resultados. Nenhum terceiro lote foi disparado ou ficou agendado.

