# Raciocínio medium — resultado 84ea2c0c

A única chamada terminou com HTTP 400 e `json_validate_failed`, exit 1. O Console identificou a falha: ausência da propriedade obrigatória `supports` no objeto raiz. O lote está encerrado; não há resposta admitida para avaliar qualidade ou melhoria semântica. [Auditoria e observação do Console](record-evidence-reasoning-medium-observation-84ea2c0c-2026-09-07.json).

O observador local recebeu um corpo de erro completo de 981 bytes; `failed_generation` tinha 586 caracteres e passou em `json.loads`. Isso mede somente sintaxe, não conformidade ao schema. O conteúdo rejeitado e o raciocínio não foram recuperados ou persistidos. Não existem envelope, registros derivados ou proposta composta neste JSONL.

Nos artefatos da API, modelo efetivo, tokens, custo e finish_reason continuam indisponíveis. A rota mantém provider Groq observado, mas não satisfaz a verificação completa. Não reescrevemos esses campos com dados do painel.

| Evidência complementar do Console | Valor |
|---|---|
| Linha correlacionada | 07/09/2026 12:49:35, sufixo `4z4z`, GPT-OSS120B, HTTP 400 |
| Entrada / saída | 2.936 / 3.072 tokens |
| Latência / TTFT | 6,873564 / 0,377679 s |
| Validação | `/required`: falta `supports` no objeto raiz |

O identificador completo local é `req_01m1y8z10kezpvxctck41d4z4z`; a correlação do painel usa horário, sufixo, modelo e status, pois o botão apresenta o ID abreviado. O painel mostra saída igual ao teto. Pressão do orçamento é uma hipótese plausível para a omissão, não uma causa demonstrada: não há finish_reason nem decomposição do raciocínio nessa evidência.

O preflight e o summary foram reconstruídos exatamente. Dezenove hashes de entradas/implementação conferiram. O intervalo UTC do início do lote ao adaptador foi 60,583209 s, e o intervalo do adaptador 7,627076 s; estes incluem processamento e não medem o sleep monotônico nem a chegada ao servidor. O código preserva espera e deadline configurados em 60 s. O launcher PID 21268 terminou às 15:49:43 UTC, sem chave ou chamada pendente.

JSONL SHA `33dd4ba6…` e summary `758b7d4d…` estão intactos. A preparação teve 219 testes distintos aprovados; isso não transforma a chamada em sucesso. Os zeros de schema, envelope e admissão significam etapas não alcançadas, não múltiplas rejeições locais.

O mesmo schema foi aceito em low no lote 9192b8fa. Não há defeito local demonstrado nem base para declarar medium melhor ou pior semanticamente. Nenhum aumento para high, de teto ou de instruções será feito nesta linha na abertura. O próximo desenho usa casos sintéticos independentes para investigar a transferência das falhas; nenhum experimento aprova runtime ou CAP-001.
