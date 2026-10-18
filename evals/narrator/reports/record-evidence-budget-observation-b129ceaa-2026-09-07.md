# Diagnóstico de orçamento b129ceaa — executado e analisado

Data: 07/09/2026. Status: **rodada encerrada; JSON/schema concluídos, envelope rejeitado por intervalos inválidos; revisão semântica concluída pelo agente**. Não houve retry, correção da resposta ou promoção para runtime/CAP-001.

A [preparação aprovada](record-evidence-budget-1536-v1-2026-09-07.md) foi executada em uma janela protegida. A chave foi inserida pelo usuário e o launcher terminou com exit 1. A única chamada autorizada foi consumida. O [registro JSON da análise](record-evidence-budget-observation-b129ceaa-2026-09-07.json) contém proveniência, auditoria e revisão independente.

## Resultado principal

Com teto de 1.536, esta realização terminou com **HTTP 200, `finish_reason: stop` e 1.112 tokens de saída**. O schema inicial passou. O contrato local rejeitou o envelope em `/l`, por `record_evidence_span_invalid`. A inspeção completa encontrou cinco intervalos inválidos entre seis.

Isso localiza uma nova falha verificável, mas não comprova viabilidade do envelope completo. A condição pré-registrada “envelope válido, uso maior que 768” não foi integralmente satisfeita. Não há término por comprimento indicado nesta resposta. O resultado não prova que o teto tenha causado a falha histórica.

| Medida | Lote 2c1cafde, teto 768 | Lote b129ceaa, teto 1.536 |
|---|---|---|
| HTTP | 400, json_validate_failed | 200 |
| Término explícito | Indisponível | stop |
| Entrada | 2.320, Console posterior | 2.320, resposta |
| Saída | 768, Console posterior | 1.112, resposta |
| Raciocínio contabilizado | Indisponível | 658 |
| Total | 3.088, soma dos contadores | 3.432, reportado |
| JSON/schema inicial | Sem envelope disponível | Aceito |
| Intervalos do envelope | Não avaliáveis | Cinco inválidos |
| Schema final / admissão | Não alcançados | Não alcançados |

As fontes das métricas históricas são a [consulta autenticada](groq-console-evidence-2c1cafde-2026-09-07.md) e os artefatos locais preservados. A comparação é histórica, com amostragem estocástica e sem controle contemporâneo, portanto não é causal A/B.

A saída reportada excedeu o teto anterior em 344 tokens. `1112 − 658 = 454` é somente diferença aritmética de contadores; não é medição independente dos tokens do JSON. O raciocínio foi contado pelo provedor, sem leitura ou retenção de seu conteúdo. Custo permanece indisponível.

## Falha estrutural reproduzida

O contrato exige `0 <= b < e <= len(texto_em_records[p])`, em pontos de código Unicode. IDs de `source_units` identificam a origem integral; seus índices não substituem os índices do registro.

| Campo de records | Intervalo retornado | Comprimento | Resultado |
|---|---:|---:|---|
| `/o` | [0,10) | 10 | Dentro do campo |
| `/l` | [3,25) | 22 | Inválido; primeira rejeição |
| `/s` | [0,197) | 115 | Inválido |
| `/f/0/s` | [0,197) | 63 | Inválido |
| `/t/0` | [0,197) | 30 | Inválido |
| `/t/1` | [0,197) | 28 | Inválido |

A narrativa fonte tem 197 caracteres, e o trecho `[3,25)` dessa fonte é o lugar derivado. Isso é compatível com confusão entre offsets da fonte e do registro, mas é inferência: não foi observado o processo interno do modelo.

O [SYSTEM](../prompts/record-evidence-v1.md) já exige expressamente a string decodificada do campo apontado; o [validador](../../../scripts/narrator_record_evidence.py) aplica a mesma regra. Nenhum falso positivo ou defeito local foi demonstrado. Não há base para aparar intervalos, completar referências ou converter esta amostra em sucesso. Os falsos/zeros de schema final e admissão significam etapas não alcançadas, não rejeições executadas nessas etapas.

## Revisão semântica dos registros literais

A estrutura inválida não impede ler os registros para revisão qualitativa separada. Essa leitura não altera o summary original.

- **Certeza ampliada:** “Quem ou o que está observando?” pressupõe observação em curso. A fonte somente a sugere. O suporte `suggested` não corrige a pressuposição da pergunta.
- **Resumo com modalidade preservada:** “sussurro sugere observação” mantém a sugestão no texto. Porém, o único suporte `established` do resumo reúne fatos ambientais e sugestão, em vez de separar as afirmações como o SYSTEM exige. O intervalo inválido também impede cobertura estrutural.
- **Pergunta aberta legítima:** “Qual é a origem do sussurro?” parte de som narrado e mantém sua causa desconhecida. Não inventa observador. O suporte `suggested` não distingue o som estabelecido da origem em aberto.
- **Registros fundamentados:** corredor de pedra fria, iluminação, outcome `unresolved`, presenças/atores vazios e ausência de resoluções são compatíveis com as fontes. “O que você faz agora?” convida ação livre e não precisa inventar suporte factual.
- **Ressalva de atribuição:** “Personagem percebe” explicita um experienciador implícito na apresentação sensorial. Isso sozinho não demonstra escolha, deslocamento ou decisão impostos ao jogador.

Conclusão restrita a esta abertura: há falha de fidelidade na pendência e cobertura de suporte não demonstrada. Não generalizar para outros casos, nem transformar o resultado em avaliação CAP ou aceitação humana.

## Integridade e execução

Batch `b129ceaa-599c-4448-b095-d37c0f0411c1`; request `req_01m1y0m9wxe74thmy54k38rmdp`; rota Groq / `openai/gpt-oss-120b` verificada. Início do lote 13:22:54.624911 UTC; despacho 13:23:55.333873; término observado da chamada 13:23:59.351815. Intervalo inicial: 60,708962 s; chamada: 4,017942 s. Uma chamada, nenhum skip, diagnóstico, retry ou fallback.

O preflight foi reconstruído e coincide integralmente com summary/JSONL. O resumo foi reproduzido a partir da linha original. Schema inicial e rejeição de suportes foram revalidados com o contrato congelado. Hashes de implementação, fontes e artefatos anteriores permanecem iguais. Os 993 testes da preparação não foram repetidos ou somados à auditoria determinística posterior.

O SYSTEM ainda menciona teto 768: foi preservado deliberadamente para isolar a mudança de `max_completion_tokens`. Essa limitação não é drift a corrigir retrospectivamente.

Artefatos imutáveis:

- [summary.json](../../../eval-results/20260907T132254Z-a1b6496d-fa4b-4ce8-9a03-2ebc04c6af27/summary.json), SHA `2a76932c6762285dd516f9da9660d02176131f35f3c3370773d39d8a55a79c57`.
- [JSONL](../../../eval-results/20260907T132254Z-a1b6496d-fa4b-4ce8-9a03-2ebc04c6af27/gpt-oss-120b-groq-free-synthetic-low.jsonl), SHA `0a0506be6e039fb94a7ecfd6dc2eff1f4427eb948f229458c33338d5683f7711`.

## Próximo passo delimitado

O [próximo desenho](record-evidence-target-spans-hypothesis-b129ceaa-2026-09-07.md) deixa pronta uma alteração somente no SYSTEM para esclarecer o campo de destino dos intervalos, mantendo os validadores. É proposta concreta, sem novo runner ou chamada autorizada. A falha semântica permanece critério independente; melhorar offsets não a resolve automaticamente.

O diagnóstico de orçamento está encerrado conforme seu limite de uma chamada. Não aumentar teto, repetir para elevar taxa ou reutilizar esta identidade. A janela terminou; não há chave ou chamada pendente neste lote.
