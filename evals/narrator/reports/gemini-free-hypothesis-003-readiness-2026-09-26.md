# Prontidão HYP-003 — Gemini Flash gratuito

**Data:** 2026-09-26

**Status:** preparação offline aprovada; zero chamada; credencial de projeto
Free Tier e confirmação de tier pendentes.

## Decisão e limite

O usuário determinou que provedores pagos estão fora de questão e pediu novos
testes no Gemini Flash gratuito. O lote congelado usa somente
`gemini-3.8-flash` na API direta Google Gemini, com orçamento autorizado de
US$ 0,00. A documentação oficial registra o modelo estável, saída estruturada,
thinking `low` e entrada/saída gratuitas no Free Tier. O mesmo Free Tier pode
usar conteúdo para melhoria de produtos; por isso o corpus é integralmente
sintético e inelegível para dados de campanha.

O projeto da chave precisa estar no Free Tier sem billing. A API não oferece no
request um seletor que converta uma chave paga em gratuita. O launcher exige a
confirmação literal `FREE` antes do prompt mascarado e para sem rede caso ela não
seja fornecida.

## Artefatos congelados

| Arquivo | SHA-256 |
|---|---|
| `evals/narrator/gemini_free_closed_world_contract_v1.json` | `93aac2f44742787de386eb57d8d313b3d64e5525f8a0254b056baa440dee34db` |
| `evals/narrator/gemini_candidates_2026-09-05.json` | `be2d3d65294d64917ad42279c662b3f0e172419eaae4421fbe1c28783940cbeb` |
| `scripts/evaluate_gemini_free_closed_world_live.py` | `fad74248cf7202de0aeac30898579a8f65c192c19b4847cf8e4f87e1f0618c1a` |
| `scripts/run_gemini_free_closed_world_live.ps1` | `9749ddd49293dd259bf459dcb6756ba9030db198c979d032331f8d770087b002` |
| `tests/test_gemini_free_closed_world_live.py` | `6abe8ba010c77a1fbea91094a215bd3c01673dcba8619f7ee5cf988a85287208` |
| `api/llm/adapters/gemini.py` | `f907a6ec49a2efbdfd6487f3d15ed738bea188b9734c66865c0edadec5662687` |
| `evals/narrator/prompts/narrative-source-progress-v1.md` | `87b9cbcd67a67b9d25b97c2b25276e83af56d48c09f53843a64b8e77303b1a0e` |
| `evals/narrator/prompts/closed-world-render-contract-v1.md` | `22a75a5808fad849f8b1cec1fd59fd5cf4c58be52913604d6e84b35a0ec83ce3` |

O preflight recompõe esses hashes antes do lote e é salvo com hash próprio. Uma
alteração posterior bloqueia a execução ou a verificação dos artefatos.

## Envelope observado offline

- oito casos inéditos nas mesmas oito classes de risco;
- slots 1–2 como único par de continuidade; demais casos independentes;
- oito chamadas no máximo, sequenciais, com intervalo mínimo de 60 segundos;
- `maxOutputTokens: 768`, thinking `LOW`, sem temperatura, top-p, top-k ou seed;
- schema nativo `n`/`q`, endpoint oficial e redirects desabilitados;
- nenhuma ferramenta, grounding, arquivo, cache, batch ou prioridade;
- timeout ou desconexão consome slot; nenhuma repetição;
- erro de autenticação, cota, rota, transporte ou proveniência para globalmente;
- resposta estrutural inválida falha seu caso, pula dependente quando aplicável e
  não é reparada;
- modelo efetivo precisa ser `gemini-3.8-flash` ou sua versão `-NNN` reportada;
- uma versão reportada diferente durante o mesmo adaptador é recusada;
- chave dedicada somente no ambiente do processo e remoção em `finally`.

## Verificação executada

Com `STORYTELLER_DISABLE_DOTENV=1`:

- 68 testes relacionados aprovados em 2,59 s;
- isso inclui os 7 testes novos, todo o adaptador Gemini e as regressões HYP-002;
- parse PowerShell: zero erro;
- preflight keyless: exit 0, `provider_calls=0`, `credential_inspected=false`;
- contraprovas: ausência de chave, ausência de confirmação Free Tier, falha de
  transporte, eco de segredo e incompatibilidade de rota param em modo fechado;
- uma advertência preexistente de depreciação em Starlette foi observada e não
  bloqueia este incremento.

Nenhuma autenticação, inferência, acesso a `.env` ou inspeção de credencial foi
realizada. O runtime v1 e seus defaults permanecem inalterados.

## Próximo passo reproduzível

1. No Google AI Studio, confirmar que o projeto da chave permanece no Free Tier
   e não tem billing habilitado.
2. Em terminal PowerShell 7 observável na raiz do worktree, executar:
   `& .\scripts\run_gemini_free_closed_world_live.ps1`.
3. Digitar `FREE` quando solicitado e inserir a chave apenas no prompt mascarado.
4. Não fechar o terminal até aparecerem `LIVE_EXIT`, `VERIFY_EXIT`,
   `SUMMARY_PATH` e `PREFLIGHT_PATH`.

Depois, verificar os artefatos sem repetir chamadas, realizar revisão semântica
proposição por proposição e parar para aceitação humana do resultado. Mesmo 8/8
não admite narrador, não cria default e não autoriza campanha híbrida.

Configuração recomendada:

- Modelo: gpt-5.6-sol.
- Esforço: low.
- Motivo: confirmação de tier e inserção mascarada são ações operacionais curtas.
- Ação humana necessária: confirmar Free Tier sem billing, digitar `FREE` e inserir a chave Gemini no prompt mascarado.
- O que continuará autonomamente depois da ação: observar a execução, verificar hashes/receipts, revisar os oito casos e preparar o checkpoint de aceitação com Sol high.
