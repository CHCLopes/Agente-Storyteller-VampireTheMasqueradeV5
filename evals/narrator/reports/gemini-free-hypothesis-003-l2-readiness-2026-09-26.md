# Prontidão HYP-003 — Gemini Flash gratuito L2

**Data:** 2026-09-26  
**Status:** correção de transporte verificada offline; zero chamada L2; credencial
de projeto Free Tier e confirmação de tier pendentes.

L2 preserva as oito fixtures sintéticas, modelo `gemini-3.8-flash`, thinking
`LOW`, 768 tokens por resposta, intervalo mínimo de 60 segundos e todos os gates
L1. Ele muda somente a identidade do protocolo e o valor REST de
`responseFormat.text.mimeType` para o enum documentado `APPLICATION_JSON`.

## Artefatos congelados

| Arquivo | SHA-256 |
|---|---|
| `evals/narrator/gemini_free_closed_world_contract_v1.json` | `93aac2f44742787de386eb57d8d313b3d64e5525f8a0254b056baa440dee34db` |
| `evals/narrator/gemini_candidates_2026-09-05.json` | `be2d3d65294d64917ad42279c662b3f0e172419eaae4421fbe1c28783940cbeb` |
| `scripts/evaluate_gemini_free_closed_world_live.py` | `728bf76deb3a568ed8b53b76d57ea64cb08200984bb7d5af3dfa19e58fc68cd4` |
| `scripts/run_gemini_free_closed_world_live.ps1` | `972cc02f1cb88e8eefcb79721de30a0ab1773d30767ecc87d88f486a1b9e36ed` |
| `tests/test_gemini_free_closed_world_live.py` | `702a2e9c1a81dfd4762ea50aec27a05dc0fbffddbd93efbd9be8fdd7223013da` |
| `api/llm/adapters/gemini.py` | `aa2aa26516d1f2601c0c0893cf2d81faeccf5a041413814630bcbf7e53b48354` |
| `evals/narrator/prompts/narrative-source-progress-v1.md` | `87b9cbcd67a67b9d25b97c2b25276e83af56d48c09f53843a64b8e77303b1a0e` |
| `evals/narrator/prompts/closed-world-render-contract-v1.md` | `22a75a5808fad849f8b1cec1fd59fd5cf4c58be52913604d6e84b35a0ec83ce3` |

## Verificação

- 36 testes focados aprovados;
- 50 testes na regressão relacionada Gemini + contrato de mundo fechado;
- parse PowerShell: zero erro;
- preflight keyless: exit 0;
- a regressão exige literalmente `APPLICATION_JSON` no novo `responseFormat`;
- L1 permanece falho e imutável; L2 terá novo UUID e novo preflight;
- nenhuma chamada, autenticação ou inspeção de credencial ocorreu na preparação L2.

## Próxima ação

Executar `scripts/run_gemini_free_closed_world_live.ps1`, confirmar `FREE` e
inserir a chave apenas no prompt mascarado. Depois, verificar os artefatos sem
repetição e revisar semanticamente as oito respostas.
