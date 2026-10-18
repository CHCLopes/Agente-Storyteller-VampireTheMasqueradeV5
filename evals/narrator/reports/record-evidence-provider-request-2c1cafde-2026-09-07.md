# Solicitação técnica preparada localmente — Groq HTTP 400

Status: **rascunho local; não enviado**. Dados exclusivamente sintéticos.
Não incluir chave, header Authorization ou credenciais ao compartilhar.

Pedido: investigar o HTTP 400 `json_validate_failed` do request
`req_01m1xtmhhdeyjbew0n7ffxv9tg`, ocorrido em 07/09/2026,
entre 11:39:11.736863 e 11:39:14.610441 UTC.

Rota solicitada: POST https://api.groq.com/openai/v1/chat/completions,
`openai/gpt-oss-120b`, JSON Schema com `strict:true`,
`stream:false`, `reasoning_effort:low`, `include_reasoning:false`,
temperatura 0,65, `max_completion_tokens:768`.

Foi feita uma chamada; não houve retry ou fallback. A segunda entrada do
experimento foi pulada. O cliente reteve somente o código de erro seguro e
o request ID; não reteve mensagem detalhada, saída recusada, uso ou motivo
de término. Portanto não foi possível localizar a falha pela evidência local.

Após autenticação, o controle de cópia do Console confirmou o request ID
completo e created_at 2026-09-07T11:39:11.789Z. O modelo registrado é
openai/gpt-oss-120b, com 2.320 tokens de entrada, 768 de saída, TTFT
0,331918 s e latência 1,959371 s. A saída coincide com o teto solicitado.
O objeto de erro copiado traz invalid_request_error/json_validate_failed
e param vazio; menciona failed_generation, mas não contém esse campo nem
finish_reason. [Evidência recuperada](groq-console-evidence-2c1cafde-2026-09-07.md).

O [corpo de requisição anexo](record-evidence-request-dossier-2c1cafde-2026-09-07.json)
foi reconstruído offline a partir de fontes e código congelados. É uma
reconstrução, não uma captura do tráfego da chamada. Os hashes de SYSTEM,
USER e schema coincidem com os registrados no lote.

Se houver diagnóstico disponível para esse request, favor esclarecer:

1. A falha ocorreu ao aceitar/compilar o schema, durante geração ou ao validar
   a saída gerada?
2. Qual regra ou caminho foi rejeitado? O erro foi sintático, estrutural ou
   relacionado à conclusão da geração?
3. Houve término pelo limite de tokens, truncamento ou outro motivo de parada?
4. Os 768 tokens de saída incluem quantos tokens de raciocínio e quantos
   de conteúdo? Há finish_reason ou geração recusada preservados além do
   que o Console expõe?
5. Caso seja necessário reproduzir novamente, qual hipótese concreta e quais
   dados adicionais permitiriam distinguir a causa?

Não se solicita execução adicional automática, alteração de plano, cobrança,
promoção de modelo ou compartilhamento de dados de campanha.
