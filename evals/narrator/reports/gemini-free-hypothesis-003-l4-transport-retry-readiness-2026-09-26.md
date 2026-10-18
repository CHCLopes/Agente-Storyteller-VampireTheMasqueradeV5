# Prontidão HYP-003 — Gemini Flash gratuito L4 integral

**Data:** 2026-09-26  
**Status:** protocolo de retry estrito verificado offline; zero chamada L4;
entrada segura de chave Free Tier pendente.

O usuário aceitou o L3 inconclusivo e aprovou explicitamente o L4 integral com
retry estrito de transporte. O lote mantém os mesmos oito casos e não agrega
respostas L2/L3. Identidade: `HYP-003-GEMINI-FREE-L4`; protocolo:
`gemini-free-closed-world-live-v4`; opção:
`GEMINI-FREE-L4-INTEGRAL-TRANSPORT-RETRY`.

## Política congelada

- oito casos, máximo global de 16 tentativas de provedor;
- até dois retries por caso, sem obrigação de consumir o teto;
- elegível somente para HTTP 408, 429 ou 5xx, `retryable=true`, fase `connect`,
  `partial_output=false` e nenhuma resposta narrativa;
- backoff base de 60 s e 180 s, acrescido de jitter determinístico de 0–15 s;
- pacing global mínimo de 60 s continua valendo entre tentativas;
- cada tentativa possui invocation ID e cápsula próprios, vínculo com a tentativa
  anterior, erro/evidência, delay e causa de esgotamento persistidos;
- resposta concluída, saída estruturada inválida, rejeição de conteúdo, erro 4xx
  não elegível, mismatch, eco de segredo ou falha sem status HTTP nunca são
  repetidos;
- zero reparo, fallback, troca de alvo, seleção de melhor narrativa ou retry
  semântico;
- US$ 0,00 de gasto pago autorizado e somente fixtures sintéticas.

## Artefatos congelados

| Arquivo | SHA-256 |
|---|---|
| `evals/narrator/gemini_free_closed_world_contract_v1.json` | `93aac2f44742787de386eb57d8d313b3d64e5525f8a0254b056baa440dee34db` |
| `evals/narrator/gemini_candidates_2026-09-05.json` | `be2d3d65294d64917ad42279c662b3f0e172419eaae4421fbe1c28783940cbeb` |
| `scripts/evaluate_gemini_free_closed_world_live.py` | `2bcacd30f0de87b15ecb4981c4eaeffe646bb77d2387cba55acb505c3d3ac8bc` |
| `scripts/run_gemini_free_closed_world_live.ps1` | `63c64266d8919408ffbbab72131ec1b9c402e4a6f7ec480935510e3c13cf5c8c` |
| `tests/test_gemini_free_closed_world_live.py` | `cae28c735c6dfcc13b45668ea6abf8c0c3e51bf0bb3d08cc81761ed284d2805d` |
| `api/llm/adapters/gemini.py` | `aa2aa26516d1f2601c0c0893cf2d81faeccf5a041413814630bcbf7e53b48354` |
| `evals/narrator/prompts/narrative-source-progress-v1.md` | `87b9cbcd67a67b9d25b97c2b25276e83af56d48c09f53843a64b8e77303b1a0e` |
| `evals/narrator/prompts/closed-world-render-contract-v1.md` | `22a75a5808fad849f8b1cec1fd59fd5cf4c58be52913604d6e84b35a0ec83ce3` |

## Verificação executada

- 47 testes diretamente focados aprovados;
- 61 testes na regressão Gemini + mundo fechado aprovados;
- parse PowerShell: zero erro;
- preflight keyless: exit 0, oito casos, teto de 16 tentativas, zero chamada;
- 503 recuperado após duas falhas e lote integral concluído em fixture;
- 503 persistente encerra após três tentativas do caso;
- teto global encerra exatamente na tentativa 16;
- saída estruturada inválida não é repetida;
- falha sem status HTTP não é repetida;
- 408, 429 e 503 são elegíveis somente sem saída parcial e na fase `connect`;
- adulteração do delay é rejeitada mesmo com hash externo recalculado;
- eco de credencial é bloqueado antes de persistir resposta/evidência.

## Próximo passo reproduzível

No terminal observável, executar `scripts/run_gemini_free_closed_world_live.ps1`.
No primeiro prompt mascarado, digitar `FREE`; no segundo, inserir a chave nova.
A mensagem posterior precisa conter `HYP-003-L4 integral`, oito casos e máximo de
16 tentativas. O processo pode demorar mais se ocorrer backoff. Não interagir até
o launcher exibir `LIVE_EXIT`, `VERIFY_EXIT`, `SUMMARY_PATH` e `PREFLIGHT_PATH`.
