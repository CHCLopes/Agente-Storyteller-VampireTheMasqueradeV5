# HYP-005 L2-B — preparação para execução gratuita

Data: 2026-09-27  
Hipótese: `HYP-005-OPENROUTER-FREE-L2-OUTPUT-BUDGET`  
Estado: preparação offline verificada; credencial e execução pendentes

## Autorização e escopo

O usuário aceitou formalmente HYP-005 L1 sem candidato elegível e aprovou L2-B.
A única variável experimental alterada é `max_output_tokens`, de 768 para 2048.
O máximo permanece em 24 chamadas, agora com teto agregado de 49.152 tokens de
saída.

Permanecem idênticos a L1:

- três slugs `:free` exatos e a ordem dos 24 slots;
- oito fixtures sintéticas por candidato;
- prompt, corpus, JSON Schema, temperatura 0,65 e deadline de 90 segundos;
- política de raciocínio sem configuração explícita;
- `provider.allow_fallbacks: false` e `require_parameters: true`;
- plugins de web, response healing e context compression desabilitados;
- zero retry, reparo, troca de alvo, fallback, best-of ou agregação;
- custo reportado exatamente zero `OPENROUTER_CREDITS` por resposta;
- admissão somente com 8/8 e revisão semântica independente;
- nenhuma promoção automática de candidato ou default.

## Implementação

- runner: `scripts/evaluate_openrouter_free_narrators_l2_live.py`
- launcher: `scripts/run_openrouter_free_narrators_l2_live.ps1`
- gate: `evals/narrator/reports/openrouter-free-narrators-l2-live-gate-2026-09-27.json`
- testes: `tests/test_openrouter_free_narrators_l2_live.py`

O runner L1 congelado não foi alterado. L2 reutiliza o adaptador de rota e custo de
L1 e configura o executor compartilhado somente no processo L2.

## Evidência offline

- preflight final: `bdb6969a598932d1f4bf9c4acbb744a97130b5bc3d0c03e4de4437c07c5f35fc`
- runner: `cb8bf46b4ecc9c30ee121de4347297541cca7f6381691da53a07b7d17343ef1b`
- launcher: `2a7de4a832d36d984853ad874301aef8097d1bc030ba67bf239d787bbfbc1de2`
- gate: `b926b89c38ddf7042fa7b8d7d335b3041f6a20e2aa93cad7ff7618170e028f91`
- manifesto reutilizado: `ca70b0d1eb94a0f000306e7018ed9fd0a906266017ae2a5aa34e5631ec6f1ea3`
- parse PowerShell: zero erro
- preflight: zero chamada e nenhuma inspeção de credencial
- testes focados finais: 104 aprovados

Os testes comparam preflights L1 e L2, provam que os campos de segurança e o
cronograma permanecem iguais, inspecionam o corpo final com `max_tokens: 2048`
e ausência de alteração de raciocínio, verificam a parada sem chave antes da
criação do diretório e auditam entrada mascarada e limpeza da credencial.

## Execução humana restante

Executar em terminal observável:

```powershell
& ".\scripts\run_openrouter_free_narrators_l2_live.ps1"
```

O launcher pedirá `FREE` e a chave em dois prompts mascarados. Antes disso, o
operador deve confirmar que os três slugs continuam `:free` com entrada e saída
a USD 0. O launcher congela o preflight, executa no máximo 24 chamadas, verifica
os artefatos e remove a credencial no bloco `finally`.
