# Prontidão HYP-004 — replicação Qwen/GPT-OSS

**Data:** 2026-09-26  
**Hipótese:** `HYP-004-QWEN-GPT-OSS-REPLICATION-L1`  
**Status:** preparação offline verificada; credencial mascarada pendente.

O usuário aceitou o HYP-003-L4 como inconclusivo e solicitou uma nova execução
dos testes com Qwen e GPT-OSS para confirmar a incerteza observada antes de buscar
alternativas. A bateria HYP-004 é uma replicação independente do HYP-002-L2. Ela
preserva os mesmos oito casos por modelo, alvos exatos, prompts, temperatura,
raciocínio, teto de saída, pacing e gates semânticos.

O lote possui UUID, preflight e diretório próprios. O máximo é de 16 chamadas:
oito para `qwen/qwen3.8-27b` com reasoning `none` e oito para
`openai/gpt-oss-120b` com reasoning `low`, pela rota Groq direta. Não há retry,
reparo, fallback, troca de alvo, seleção de melhor saída ou gasto pago autorizado.
Somente fixtures sintéticas podem ser enviadas.

Os resultados serão comparados caso a caso com HYP-002 para observar estabilidade
ou variação. As duas execuções não serão agregadas para admissão, e uma melhora
isolada não promove candidato, narrador ou default. A revisão humana independente
continua obrigatória.

## Evidência offline

- 17 testes focados aprovados;
- 85 testes na regressão relacionada aprovados;
- parse PowerShell sem erros;
- preflight keyless confirmou 16 slots, zero chamada e credencial não inspecionada;
- execução sem a variável dedicada encerra antes de criar o diretório do lote;
- o lote HYP-002 original foi reverificado após a implementação com exit 0;
- os dois prompts do launcher são mascarados, e a credencial é removida no `finally`.

Os avisos de teste foram o `PendingDeprecationWarning` conhecido do Starlette e a
impossibilidade de gravar `.pytest_cache`; nenhum teste falhou.

## Artefatos congelados

| Arquivo | SHA-256 |
|---|---|
| `evals/narrator/closed_world_render_contract_v1.json` | `1b620a84bc9a61d63f1abd51e9e08dfbd856fbb804dd0c806bd7588daf42b72b` |
| `evals/narrator/closed_world_render_contract_protocol_v1.md` | `0ab8cec17e225bfd98cee1957c2338f9341138fda60440e8440f9d1a4c0a21fb` |
| `evals/narrator/groq_candidates_2026-09-05.json` | `de31691d9562e7cc8abe2b13d004098967976cda321c975d2f3ed7a147a15de6` |
| `evals/narrator/reports/closed-world-render-replication-live-gate-2026-09-26.json` | `a499411af3d258dd977f82c5cc9992b653eada6708a0e9ca692dc265c3ead9b7` |
| `scripts/evaluate_closed_world_render_live.py` | `71e3a70fb62c044694016da28810bbe7e7d921e0801a428669535c285dfe9800` |
| `scripts/evaluate_closed_world_render_replication_live.py` | `da109d54676292f0ed61679c2f7cf80225f0a4c9adec8c0e25317561fff329d8` |
| `scripts/run_closed_world_render_replication_live.ps1` | `95c2de1c62f36c664d8b3874383bf997f9637a68b96ec55a431092d41daf0d75` |
| `tests/test_closed_world_render_replication_live.py` | `45d15ba361d8f7a67b0ac0a9b0fa4ab035fd11dde9d629af0c36959a9cfb5409` |
| `evals/narrator/prompts/narrative-source-progress-v1.md` | `87b9cbcd67a67b9d25b97c2b25276e83af56d48c09f53843a64b8e77303b1a0e` |
| `evals/narrator/prompts/closed-world-render-contract-v1.md` | `22a75a5808fad849f8b1cec1fd59fd5cf4c58be52913604d6e84b35a0ec83ce3` |

Nenhuma chamada ou autenticação HYP-004 foi feita durante a preparação. A única
dependência humana é inserir `FREE` e a chave Groq em prompts mascarados no
terminal observável.
