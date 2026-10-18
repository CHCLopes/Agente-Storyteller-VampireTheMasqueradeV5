# Prontidão — HYP-005 SiliconFlow gratuito

**Data:** 2026-09-26

**Status:** preparação offline concluída; conta/chave e confirmação de gratuidade pendentes

## Escopo congelado

O lote prospectivo avalia três alvos chineses exatos:
`XingChenAGI/Xing4.0-29B`, `Qwen/Qwen3.5-4B` e
`THUDM/GLM-4-9B-0414`.

Cada candidato recebe os mesmos oito casos do contrato fechado. São no máximo 24
chamadas, temperatura 0,65, 768 tokens de saída por chamada, intervalo global
mínimo de 60 segundos, zero retry, reparo, fallback ou troca de alvo. O limiar é
8/8 por candidato; resultados anteriores não são agregados e não há seleção da
melhor saída.

## Fundamento de gratuidade

- O catálogo oficial SiliconFlow observado em 26/09/2026 mostra
  `XingChenAGI/Xing4.0-29B` com entrada e saída a CNY 0 por milhão de tokens.
- A documentação oficial identifica `Qwen/Qwen3.5-4B` e
  `THUDM/GLM-4-9B-0414` como modelos gratuitos.
- A política oficial informa que modelos gratuitos têm custo zero e limites
  fixos no nível da conta; alguns exigem verificação de identidade.
- O endpoint oficial é `https://api.siliconflow.cn/v1` e aceita JSON Schema.

A condição de custo será confirmada novamente pelo operador no painel antes da
entrada da chave. Qualquer mudança de preço deve interromper a execução.

## Segurança e verificação

A chave é solicitada de forma mascarada, vive somente no ambiente do processo e
é removida no bloco `finally`. O launcher não lê `.env`, não recebe a chave em
argumentos e não a persiste. Somente fixtures sintéticas podem ser enviadas.

- 44 testes focados passaram, incluindo o adaptador OpenAI-compatible;
- parse PowerShell: zero erro;
- preflight keyless: 24 slots, zero chamada e credencial não inspecionada;
- ausência da credencial encerra antes de criar o diretório do lote.

O preflight congelado tem SHA-256
`7bfbfb1708570eacb51bc75f09946b7c7178441c10e5531b9288bcba9d93f567`.
O launcher recalcula e transmite o hash do arquivo materializado antes do lote;
o verificador exige o mesmo documento após a execução.

O próximo passo depende de uma chave SiliconFlow e da confirmação visual de que
os três alvos continuam gratuitos.
