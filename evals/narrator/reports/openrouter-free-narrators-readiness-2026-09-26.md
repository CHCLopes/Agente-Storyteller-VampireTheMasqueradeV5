# Prontidão — HYP-005 OpenRouter gratuito e multiorigem

Data: 26/09/2026  
Hipótese: `HYP-005-OPENROUTER-FREE-L1`  
Estado: preparação offline verificada; credencial protegida pendente

## Escopo autorizado

O usuário solicitou avaliar modelos chineses com API gratuita, depois pediu a
inclusão de modelos não chineses que cumprissem os mesmos critérios e mandou
continuar. Esta hipótese substitui a rota SiliconFlow inviável para cadastro
estrangeiro e não reabre os lotes aceitos de Qwen, GPT-OSS ou Gemini.

Foram congelados três slugs OpenRouter `:free`, todos documentados com
`response_format` por JSON Schema:

1. `nvidia/nemotron-3-super-120b-a12b:free` — NVIDIA, não chinês;
2. `liquid/lfm-2.5-2.6b:free` — Liquid AI, não chinês;
3. `deepseek/deepseek-v4-flash-0731:free` — DeepSeek, chinês.

Gemma gratuito ficou fora porque a rota gratuita oferece JSON sem imposição do
schema. `openrouter/free` ficou fora porque seleciona o modelo dinamicamente.
GLM 5.3 Flash ficou fora porque o catálogo consultado não comprovou JSON Schema
estrito para a rota gratuita. Qwen 3.8 não foi repetido porque HYP-002/HYP-004 já
o classificaram como variável e inelegível.

## Contrato da bateria

- oito casos congelados por candidato; máximo de 24 chamadas;
- somente fixtures sintéticas, sem campanha, dados pessoais ou lore privado;
- temperatura `0.65`, máximo de 768 tokens por resposta e deadline de 90 s;
- intervalo global mínimo de 4 s, compatível com teto inferior a 20 RPM;
- zero retry, reparo, best-of, agregação ou troca de alvo;
- slug explícito; sem `models` e sem router dinâmico;
- `provider.allow_fallbacks: false` e `provider.require_parameters: true`;
- cada resposta deve reportar custo exatamente zero `OPENROUTER_CREDITS`;
- ausência de custo reportado ou valor diferente de zero encerra o lote;
- proveniência exige modelo exato e provedor efetivo reportado;
- admissão exige 8/8 e revisão humana independente; nenhum default automático.

O uso de `data_collection: allow` é deliberado e limitado às fixtures sintéticas,
pois endpoints gratuitos podem registrar dados. Isso não autoriza tráfego de
campanha nem altera a política do runtime.

## Verificação observável

- `80 passed` nos testes do runner novo, runner-base, adaptador OpenRouter e
  isolamento de rede;
- preflight keyless: 24 slots, zero chamada, credencial não inspecionada;
- launcher PowerShell: zero erro de parse;
- ausência da variável dedicada encerra antes de criar diretório do lote;
- teste do corpo confirma JSON Schema estrito, slug único, usage e fallback
  desativado;
- teste de custo distingue zero reportado de ausente, inválido ou positivo.

Nenhuma autenticação ou chamada OpenRouter foi realizada durante a preparação.
Nenhuma chave foi lida, exibida, copiada ou persistida.

## Fontes de catálogo

- https://openrouter.ai/nvidia/nemotron-3-super-120b-a12b:free
- https://openrouter.ai/liquid/lfm-2.5-2.6b:free
- https://openrouter.ai/deepseek/deepseek-v4-flash-0731:free
- https://openrouter.ai/docs/guides/features/structured-outputs
- https://openrouter.ai/pricing

## Próximo gate

Executar `scripts/run_openrouter_free_narrators_live.ps1` em terminal observável.
O operador confirma `FREE` e insere uma chave OpenRouter por prompt mascarado.
Após o lote, verificar os artefatos e realizar revisão semântica independente antes
de qualquer classificação ou admissão.
