# Prontidão HYP-003 — Gemini Flash gratuito L3 integral

**Data:** 2026-09-26  
**Status:** preparação offline aprovada; zero chamada L3; entrada segura de chave
Free Tier pendente.

O usuário aceitou o L2 inconclusivo e aprovou explicitamente um L3 integral.
Este lote executará novamente os oito casos congelados como conjunto autônomo,
sem agregar as duas respostas L2. Identidade: `HYP-003-GEMINI-FREE-L3`;
protocolo: `gemini-free-closed-world-live-v3`; opção:
`GEMINI-FREE-L3-INTEGRAL`.

Modelo, corpus, prompts, schema, thinking `LOW`, limite de 768 tokens, pacing de
60 segundos, orçamento US$ 0,00 e gates permanecem iguais. O máximo é oito
chamadas sequenciais; não há retry, reparo, fallback ou troca de alvo. Erro de
autenticação, cota, rota, transporte ou proveniência encerra o lote.

## Proteção de credencial

Os dois prompts do launcher agora são mascarados. O primeiro recebe apenas a
confirmação `FREE`; o segundo recebe a chave. Se uma chave for colada por engano
no primeiro prompt, ela não aparecerá no terminal e o processo encerrará antes
da rede. A chave existe somente no ambiente do processo e é removida em
`finally`.

## Artefatos congelados

| Arquivo | SHA-256 |
|---|---|
| `evals/narrator/gemini_free_closed_world_contract_v1.json` | `93aac2f44742787de386eb57d8d313b3d64e5525f8a0254b056baa440dee34db` |
| `evals/narrator/gemini_candidates_2026-09-05.json` | `be2d3d65294d64917ad42279c662b3f0e172419eaae4421fbe1c28783940cbeb` |
| `scripts/evaluate_gemini_free_closed_world_live.py` | `f25b1bafcd4636e9376f7f04013ca1fce0964059f35b9fcaf34aaf3774fc3ec8` |
| `scripts/run_gemini_free_closed_world_live.ps1` | `5b0bae8de12dbdcf78138aed4752813bde3009d3b2b5d01b5fbad6514bcb1b4d` |
| `tests/test_gemini_free_closed_world_live.py` | `c02c499d929f39459338044a3d61e6b3882e91d97c472fb59ac50f9b3b752bb6` |
| `api/llm/adapters/gemini.py` | `aa2aa26516d1f2601c0c0893cf2d81faeccf5a041413814630bcbf7e53b48354` |
| `evals/narrator/prompts/narrative-source-progress-v1.md` | `87b9cbcd67a67b9d25b97c2b25276e83af56d48c09f53843a64b8e77303b1a0e` |
| `evals/narrator/prompts/closed-world-render-contract-v1.md` | `22a75a5808fad849f8b1cec1fd59fd5cf4c58be52913604d6e84b35a0ec83ce3` |

## Verificação executada

- 37 testes diretamente focados aprovados;
- 51 testes na regressão Gemini + mundo fechado aprovados;
- parse PowerShell: zero erro;
- preflight keyless: exit 0;
- confirmação Free Tier e chave protegidas por `SecureString`;
- nenhuma autenticação, chamada ou inspeção de credencial durante a preparação.

## Próximo passo reproduzível

No terminal observável do chat, executar
`scripts/run_gemini_free_closed_world_live.ps1`. No primeiro prompt mascarado,
digitar `FREE`; no segundo, inserir a chave nova. A mensagem posterior precisa
conter `HYP-003-L3 integral` e UUID novo. Depois, não interagir com o terminal até
o launcher exibir `LIVE_EXIT`, `VERIFY_EXIT`, `SUMMARY_PATH` e `PREFLIGHT_PATH`.
