# Comparação Qwen/GPT-OSS com diálogo — lote 095e7efd

O lote `095e7efd-081b-474f-b5ed-179658373ec2` encerrou `finished/1` em
13/09/2026. A auditoria técnica oficial passou, mas nenhum candidato satisfez a
regra prospectiva de elegibilidade. O resultado não escolhe modelo, não altera
default e não aprova campanha, runtime de produto ou CAP-001.

## Integridade operacional

Foram oito chamadas HTTP200 com `finish_reason=stop`, schema válido e rota
verificada; seis turnos foram commitados e quatro slots dependentes ficaram
`skipped/previous_chain_failure`. Não houve parada global, retry, fallback,
reparo, diagnóstico no provedor ou chamada fora dos slots autorados.

| Configuração e cena | Chamadas | Confirmados | Recusa | Skips |
|---|---:|---:|---|---:|
| Qwen none / Oficina | 3 | 3 | — | 0 |
| GPT-OSS low / Oficina | 1 | 0 | T1: agência | 2 |
| GPT-OSS low / Arquivo | 3 | 3 | — | 0 |
| Qwen none / Arquivo | 1 | 0 | T1: 167 palavras, teto 150 | 2 |

Cada candidato fez quatro chamadas e confirmou três turnos. O total persistido é
de 24 attempts, seis turnos e seis eventos; os bancos dos blocos recusados têm três
attempts e nenhum turno/evento. O lote durou 492,977782 s. A espera inicial foi de
60,322244 s; os intervalos HTTP ficaram entre 61,130258 e 62,259458 s. Todas as
respostas terminaram antes do deadline, com margem mínima de 57,622431 s.

Uso reportado: 15.768 tokens de entrada, 1.457 de saída e 17.225 totais. Qwen
reportou 8.152/771/8.923 e não informou reasoning; GPT-OSS reportou
7.616/686/8.302, incluindo 137 tokens de reasoning. Foram solicitados 6.144 tokens
de saída nos oito slots enviados, abaixo do teto agregado de 9.216.

O CLI próprio de verificação retornou `verified=true`/exit0 para os artefatos de
uma observação exit1. Ele reconstruiu summary/JSONL, tempos, requests, recibos,
cápsulas, tentativas, commits, replays e cópias dos SQLite; os hashes dos originais
ficaram idênticos antes e depois. `summary.json` SHA
`4af734e8cc9def6d75a6a35526e4762e76fed314ca02cec8f308af323006f230`;
`records.jsonl` SHA
`e802ad2cea4e3437bf84dfdb6412ce62f1048175a284022b13cd1ef87e6e8f17`.

## Revisão narrativa principal

Todos os oito textos produzidos foram lidos. Propostas recusadas recebem análise
descritiva, mas não contam para elegibilidade; skips não recebem nota.

| Texto | Situação | Utilidade | Avanço | Clareza |
|---|---|---:|---:|---:|
| Qwen / Oficina T1 | Confirmado | 2 | 2 | 2 |
| Qwen / Oficina T2 | Confirmado | 2 | 1 | 2 |
| Qwen / Oficina T3 | Confirmado | 2 | 2 | 2 |
| GPT-OSS / Oficina T1 | Proposta recusada | 2 | 2 | 1 |
| GPT-OSS / Arquivo T1 | Confirmado | 2 | 2 | 2 |
| GPT-OSS / Arquivo T2 | Confirmado | 2 | 2 | 2 |
| GPT-OSS / Arquivo T3 | Confirmado | 2 | 0 | 2 |
| Qwen / Arquivo T1 | Proposta recusada | 2 | 2 | 1 |

Qwen responde concretamente na Oficina com poeira, parafuso, esteira e possível
arrasto. Na espera, Nina reage e direciona o olhar a uma mancha de graxa, mas não
desenvolve um elemento anterior numa mudança forte; por isso, avanço 1. O terceiro
turno retoma as fontes e oferece uma direção de investigação. Sua proposta do
Arquivo tem destino e motivo úteis, porém 167 palavras e densidade excessiva.

GPT-OSS propõe na Oficina quatro sinais concretos. A forma enumerativa reduz a
clareza, mas a leitura semântica não encontra busca executada pelo jogador:
“dependendo do que você procura” qualifica a relevância dos sinais. No Arquivo,
Rui indica a ala Norte e, na espera, transforma-a em direção visível. No terceiro
turno, porém, afirma que nada mudou e repete a oferta de condução; o turno responde
à pergunta, mas mantém a cena estagnada, recebendo avanço 0.

Ambos preservam o elenco e a próxima escolha. Causas e informações introduzidas
em fala de NPC permanecem atribuídas, não confirmação independente do cânone.
A revisão semântica secundária foi concluída em 14/09 por um modelo diferente da
revisão principal e independente dos geradores. Ela coincide com todos os oito
vetores de nota e gates semânticos acima. A separação tem um limite explícito: o
contexto desta tarefa já continha identidades e conclusão principal, portanto a
segunda leitura não é cega, organizacionalmente independente ou parecer humano.

## Diagnóstico e correção prospectiva

A proposta GPT-OSS/Oficina falhou em política com
`scene_player_agency_violation`, regra `undeclared_player_action`, sujeito `voce`
e conceito `inspect`. Reprodução offline com o texto capturado confirmou que o
gate interpretava “dependendo do que você procura” como busca consumada. Trocar
essa formulação por interesse não verbal passava; uma busca com objeto ou ação
posterior continuava recusada.

A correção local posterior reconhece somente a construção condicional terminal e
mascara apenas o verbo para a checagem de autoria. “Você procura nas bancadas” e
“você abre o painel” permanecem bloqueados. A suíte final combinada aprovou 525
casos distintos. Nenhuma inferência, resposta, banco ou resultado deste lote foi
reexecutado ou reclassificado. O core usado no lote continua identificável pelo
preflight; o core prospectivo atual tem SHA
`30e7635f124698f7e44e52cb586b2470aebfb6415ee2d1f92372991a907e4aa4`.

## Conclusão e limite

Qwen não tem os três commits do Arquivo; GPT-OSS não tem os três da Oficina.
Logo, nenhum possui os seis turnos tecnicamente e semanticamente aprovados
exigidos pela regra de piloto. Mesmo se a proposta GPT-OSS recusada fosse somente
descrita como semanticamente válida, o texto confirmado do Arquivo contém um
eixo0. Não há vencedor inequívoco e o lote não deve ser repetido para forçá-lo.

O checkpoint final ancora os brutos, a auditoria, as duas leituras e esta
reconciliação. A escolha de modelo fica encerrada sem candidato qualificado.
Qualquer nova avaliação exigirá hipótese e protocolo próprios.

A próxima pergunta arquitetural é se a proposta já registrada de resolvedor
determinístico de cenas deve ser promovida a planejamento. Ela atacaria o limite
comum observado — progressão dependente somente da prosa do modelo — sem transformar
esta comparação em aprovação do resolvedor ou de sua implementação.
