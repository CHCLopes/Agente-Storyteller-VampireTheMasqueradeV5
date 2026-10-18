# Observação record-evidence — 2c1cafde

Data da análise: 07/09/2026. Resultado: **falha operacional na abertura;
nenhuma amostra semântica disponível; sondagem encerrada pela regra de parada**.

## Resultado e comparação

O usuário executou o batch `2c1cafde-7508-43a6-b415-172f2c139aa0`,
invocação `6c9951b4-2c5b-46bc-85ec-ba7cec8ea3fa`. O
[summary original](../../../eval-results/20260907T113910Z-6c9951b4-2c5b-46bc-85ec-ba7cec8ea3fa/summary.json)
e o JSONL no mesmo diretório foram lidos integralmente e preservados.

| Dimensão | Derivação c9c01a48 | Evidence 2c1cafde |
|---|---|---|
| Chamadas realizadas | 2 | 1 |
| Resposta estruturada disponível | 2 | 0 |
| Propostas finais admitidas | 2 | 0, sem proposta disponível |
| Segunda entrada | Mara executada | Mara pulada por falha operacional anterior |
| Resultado operacional | Exit 0 | Exit 1, HTTP 400 |
| Fidelidade semântica | Abertura ainda pressupõe observação; hipótese não sustentada | Não avaliável, sem registros retornados |

Essa é uma comparação histórica de resultados observados. SYSTEM, USER e
schema experimental mudaram; não há demonstração causal de que o envelope
provocou a falha nem comparação semântica entre respostas equivalentes.

A única chamada foi a abertura. Erro normalizado:
`invalid_request / groq_json_validate_failed`, HTTP 400,
`retryable=false`, `partial_output=false`.
Request externo: `req_01m1xtmhhdeyjbew0n7ffxv9tg`.
Mara recebeu `previous_operational_failure` e não foi enviada. Não houve
retry, diagnóstico, fallback ou geração de nova narrativa neste lote.

O intervalo UTC da evidência da chamada foi de
`2026-09-07T11:39:11.736863+00:00` a
`2026-09-07T11:39:14.610441+00:00` (2,873578 s).
O batch durou 3,720110 s; a latência local registrada foi 2,881183 s.
Não se mediu espaçamento entre dois despachos, pois só existiu um.

Groq consta como provedor observado. O modelo efetivo não foi reportado;
a rota completa permanece `unavailable`, sem divergência demonstrada.
Uso e custo estão indisponíveis: não significam zero consumo ou custo.

## O que a evidência permite concluir

Não existem `response_envelope`, `derived_records`, `composed_proposal`
ou `support_validation` no JSONL. Os quatro contadores de validação zerados
não demonstram rejeição pelos validadores locais. Nenhum deles chegou a
avaliar uma resposta deste lote. Os critérios de certeza, agência, origem,
cobertura e fidelidade permanecem sem amostra.

A fase normalizada `connect` é o estado do adaptador ao enviar a requisição
e conferir o status HTTP, antes de analisar uma resposta de sucesso.
O HTTP 400 foi recebido; esse rótulo não é diagnóstico de falha de conexão.

O adaptador preserva somente o código de erro reconhecido. Seu corpo textual
e uma eventual `failed_generation` não são persistidos. Não há como reconstruir
esses dados a partir do summary/JSONL. Também não sabemos se o corpo original
continha uma geração recusada ou informação suficiente para localizar a causa.

Não é possível atribuir o incidente a truncamento, teto de 768, contagem
Unicode, campo específico, keyword de schema, incompatibilidade do envelope
ou falha geral do modelo/provedor. A semelhança com um erro histórico não
identifica sua causa. Não relaxar schema, elevar orçamento ou repetir por
tentativa sem um novo desenho fundamentado.

## Investigação local concluída

O preflight atual foi reconstruído e corresponde integralmente aos metadados
do lote e da preparação: SYSTEM, USER, schema, fontes, parâmetros, candidato,
executor e nove componentes de implementação. As unidades conservam cada
narrativa literal. A recomputação offline do resumo, com o próprio agregador
experimental, coincide com o summary original; isso não é replay CAP-001.

O [dossiê de requisição](record-evidence-request-dossier-2c1cafde-2026-09-07.json)
contém o corpo reconstruído offline, com identificação explícita dessa origem.
Não é captura de rede nem prova do que o servidor processou internamente.
Não contém headers, autorização, chave ou corpo de resposta, e não foi enviado.

A reconstrução usa `strict:true`, `stream:false`,
`openai/gpt-oss-120b`, `reasoning_effort:low`,
`include_reasoning:false`, temperatura 0,65 e `max_completion_tokens:768`.
O hash do schema enviado coincide com o congelado:
`870dae95abab2212da69ebb6ba340f87eef450cd7c5bf060f3d6d8f1b667b407`.
Cinco objetos têm todos os campos requeridos e rejeitam campos extras;
cinco referências locais resolvem; não há `allOf` ou `default`.

A documentação oficial consultada lista GPT-OSS 120B entre os modelos com
modo estrito, exige campos requeridos e objetos fechados e solicita reproduções
de HTTP 400. Ela não determina a causa deste request nem substitui a observação.
[Groq Structured Outputs](https://console.groq.com/docs/structured-outputs).
A [referência da API](https://console.groq.com/docs/api-reference) documenta
os parâmetros usados. Não se adotou modo flexível ou troca de modelo.

Os dois exemplos autorados existentes foram revalidados localmente em
Pydantic, referências, intervalos e composição, com 171/221 tokens estimados.
São controles locais, não respostas desta rodada. Não houve validação por
biblioteca JSON Schema independente: jsonschema e os entrypoints usuais do
Ajv não estavam disponíveis nos ambientes existentes inspecionados. Nenhuma
dependência foi instalada; a compilação do schema no provedor não foi
verificada por essa auditoria.

A verificação focada do tratamento de HTTP 400, distinção de falha local de
schema, aborto sem retry e persistência segura teve **30 testes aprovados**
em 28,25 s, um aviso preexistente de python_multipart, sem falhas ou skips.
Não foi necessário alterar código ou repetir a suíte ampla da preparação.
Os 2.998 testes anteriores permanecem históricos e não se somam aos 30.

## Próximo passo e limite real

A análise autorizada e a preparação do dossiê estão concluídas. O próximo dado
necessário para localizar a causa é o detalhe do processamento desse request
no provedor: etapa que falhou, regra de validação, indicação de término ou
truncamento e eventual diagnóstico conservado pelo serviço, se disponíveis.
A [solicitação técnica local](record-evidence-provider-request-2c1cafde-2026-09-07.md)
está pronta para revisão e eventual envio pelo usuário; nenhuma mensagem foi
enviada a terceiros e não se presume que o provedor conserve esses dados.

Uma nova execução também precisaria de um escopo específico e observabilidade
que pudesse discriminar hipóteses. Não há nova chamada pendente apenas de chave.
A regra aprovada diz: “Erro operacional de provedor/rota/schema/envelope na
primeira entrada encerra a sondagem.”
[Desenho aprovado](record-evidence-hypothesis-c9c01a48-2026-09-07.md).
A segunda chamada não utilizada não é saldo para outro experimento.

A autonomia para analisar nova evidência e corrigir um defeito local
demonstrado permanece válida, sem confirmação intermediária. Nenhum defeito
local foi demonstrado nesta investigação. A causa remota permanece desconhecida.
CAP-001, fidelidade narrativa e promoção ao runtime seguem sem aprovação.

Hashes originais:
- summary: `f8726f97ca49d7845ed59c8fd3c4fa7227e47b1c713a26fb2d291eb7137553cd`;
- JSONL: `1ce49265ddfd8702691ca586360d0f27066dbd7d8dd2161251273b7e66e95eac`.

O [registro da análise](record-evidence-observation-2c1cafde-2026-09-07.json)
separa conclusão operacional, semântica indisponível, verificações e dependência.
