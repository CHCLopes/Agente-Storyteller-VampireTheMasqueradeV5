# Casos independentes — resultado d1b9a968

O lote encerrou com exit 1 após uma chamada à biblioteca. Groq/GPT-OSS120B retornou HTTP 200/stop e schema válido, mas o envelope falhou em `record_quote_evidence_quote_missing`. A oficina foi registrada como não chamada, conforme a regra de parada. Não haverá lote substituto para preencher essa amostra. [Auditoria completa](record-evidence-independent-cases-observation-d1b9a968-2026-09-07.json).

O suporte de índice 6 aponta `/t/0`, cujo texto é “O que está causando o ruído?”. Sua citação copia a frase da fonte sobre o ruído e o possível mecanismo, ausente nesse destino. A recusa foi reproduzida com o contrato congelado; os seis suportes anteriores têm citações exatas e únicas. Nenhum defeito local demonstrado. Composição, schema final e admissão não foram alcançados; seus zeros não são rejeições observadas nessas etapas.

A redação preserva “sugere” e “talvez”. A pergunta sobre a causa do ruído está fundamentada no ruído estabelecido e não confirma o mecanismo. Entretanto, os suportes 3 e 5, em `/s` e `/f/1/s`, usam established sobre trechos que incluem fato e hipótese. A separação de modalidades é inadequada, apesar da fidelidade do texto nessa dimensão. O resumo copia as 31 palavras da fonte, excedendo as 25 pedidas pelo SYSTEM; isso é descumprimento de instrução, distinto da rejeição estrutural efetivamente executada.

Os demais campos são compatíveis: resultado unresolved, biblioteca, listas de presença e resoluções vazias, fatos públicos sem atores inventados e convite livre em segunda pessoa com cinco palavras. A oficina não tem resultado para revisão sensorial. A revisão externa não altera os campos brutos not_performed e não aprova semântica automaticamente.

Uso informado: 2.894 tokens de entrada, 1.380 de saída, 4.274 total; 777 de raciocínio contabilizado, sem leitura de seu conteúdo. Custo indisponível. Request `req_01m1ybfz1megx90r0hykt90gs0`. O agregado é parcial pelo caso não chamado. Houve 60,665291 s do início do lote ao adaptador e 4,003674 s no intervalo UTC do adaptador. Sem segunda chamada, não há intervalo entre inícios a medir; timestamps locais não comprovam a chegada remota ou a espera monotônica exata.

Preflight e summary foram reconstruídos exatamente; 23 fingerprints, os dez arquivos da preparação e seis artefatos históricos conferiram. Os 494 testes pertencem à preparação e não foram reexecutados ou somados novamente. JSONL SHA `27bb788b…`; summary `02aa85c9…`. PID 24764 terminou às 16:33:52 UTC, com a chave descartada. Não há chamada ou credencial pendente neste lote.

A falha de citação reapareceu em uma entrada nova, sem estimativa de frequência ou conclusão causal. O próximo trabalho é a [prova offline de segmentos com evidência no próprio campo](record-inline-evidence-design-d1b9a968-2026-09-07.md), limitada a resumo e questões abertas. Eliminar cópia redundante não resolve por si só modalidade ou fidelidade. Runtime e CAP-001 permanecem sem aprovação.
