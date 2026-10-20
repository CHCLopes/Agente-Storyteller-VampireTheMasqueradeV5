# HYP-007-L6 — encerramento e preparação prospectiva L7

Data: 18/10/2026. Target: `gpt-5.6-luna`, esforço `low`.
Batch L6: `adf70b63-235c-457f-86df-b0625fad10e2`.
Estado: encerrado, nenhum narrador admitido; conclusão delimitada proposta abaixo.

Atualização posterior: o usuário respondeu "prossiga" à proposta delimitada
L6/L7; conforme convenção explícita do projeto, L6 aceito nessa conclusão e
orçamento L7 autorizado nos limites abaixo. Somente os flags paid/live L7 foram
ativados, sem alterar prompt v4, hashes, código ou critérios. O SHA L7 com flags
false abaixo identifica a preparação, não o manifesto após autorização.
Próxima dependência: entrada protegida no terminal L7 identificado. Não repetir
L6 nem pedir novamente orçamento. Nenhum narrador admitido por essa aprovação.

## Observado em L6

Lote autorizado até 17 chamadas e USD 0,15 estimados adicionais, sem retry ou
fallback. Após entrada protegida confirmada pelo usuário, houve uma chamada
real, zero turnos completos. Parou no primeiro R-01 de CAMP-EVAL-01 com
`campaign_source_policy_failed`. Nenhum outro caso ou a construção R-03 de L5
foi exercitado. Não reutilizar os 16 slots restantes ou reabrir a trava.

Summary terminal e records originais preservados em:

```text
eval-results/hybrid-campaign-luna-l6-adf70b63-235c-457f-86df-b0625fad10e2/summary.json
eval-results/hybrid-campaign-luna-l6-adf70b63-235c-457f-86df-b0625fad10e2/records.jsonl
```

SHA-256 de records, conferido contra summary:
`4b706cc4188e76a2dc7bf19a192e488a7765133a9345fd54310bee4a94d86516`.
SHA-256 de summary:
`280d27d0872160f5895b62b6f487e9a3305ba17e7fb7b26a7a58003d0bb9e8b8`.

Resposta estruturada e uso foram reportados pela OpenAI; autenticação foi
funcional nesta execução, sem inspeção de chave. Geração local 4.491 ms e turno
4.586 ms: uma observação, não SLA nem comparação controlada. Gate paid/live
fechado ao observar summary; trava L6 mantida. Marcador ready é histórico,
não significa que o lançador ainda aguarda entrada.

## Diagnóstico reproduzido

O campo q original foi:

> Como prefere proceder: manter o registro na bancada e preparar a passagem, ou examinar o risco mais de perto?

Tem 19 palavras. A proposta satisfaz o schema de q (até 200 caracteres), e a
obrigação causal R-01 passa em `_realizes_rule`. O validador de cena recusa
antes da admissão, com:

```json
{"code":"scene_player_prompt_too_long","evidence":{"field":"player_prompt","rule":"open_player_action_question","reason":"word_limit_exceeded","word_count":19}}
```

O limite de `_validate_player_prompt` já era 15 palavras. É rejeição real do
contrato, não falso positivo de agência. O prompt v3 instruía 30–150 palavras
totais, q em turno aberto e q vazio no desfecho, mas não explicitava o teto de
15 palavras ou todas as condições de pergunta aberta. Isso impede atribuir
exclusivamente ao modelo a falha de instrução.

Mantendo a narrativa e substituindo somente q por "O que você faz agora?", a
mesma política passa offline. Os testes preservam o limite: 15 palavras passa,
16 e a pergunta original de 19 são recusadas. Isso não reclassifica o turno
real, não prova campanha completa e não mede satisfação com a fala de Mara.
A narrativa contém orientação de Mara para não mover o registro por enquanto;
não foi convertida em restrição canônica, nem avaliada como satisfação de UX.

Uma primeira reprodução com cápsula sintética confirmou a causa e depois
encontrou falha de limpeza SQLite/Windows (WinError 32). Não contar esse comando
como sucesso integral. O diagnóstico foi repetido sem banco e nos testes;
o único diretório temporário sintético criado por esse diagnóstico foi removido
após o processo terminar. Nenhum save existente foi lido ou modificado.

## Corrigido prospectivamente, não no histórico

Novo [prompt v4](../prompts/hybrid-campaign-source-v4.md) explicita q como uma
pergunta aberta sobre a próxima ação, até 15 palavras, terminada em ?, sem
menu restritivo. Mantém q vazio no desfecho e todos os demais limites v3.
Não altera schema, detector, RNG, persistência, estados, efeitos ou gates.
Prompt v3 e manifesto executado L6 permanecem congelados. O diff v3/v4 e um
teste de equivalência confirmam que só a instrução de q foi explicitada.

L7 tem runner/preflight/lançador próprios e
[manifesto separado](hybrid-campaign-luna-l7-live-gate-2026-10-18.json), com
22 hashes do código atual, mesmos oito casos/17 turnos, alvo Luna low,
768 tokens de saída/chamada, 20.000 bytes/requisição e prazo de 60 s.
Trava e variável de entrada protegida são distintas de L6. Sem retry/fallback,
dados de save ou admissão automática. Flags paid/live false.

Prompt v4 SHA-256:
`5d043c5c8def46cfbea295b9ce23ee2289e21eb4167cfb7fcc6ea6f4f62bb66f`.
Manifesto L7 com flags false SHA-256:
`dc2d96b72df8fba484474b3ba73a5e1cbe0e062324e0222436c274018be2dcd4`.
Manifesto L6 fechado preservado SHA-256:
`b0e582b28d46cb015f8e11aa7a6e0f37b26458168704a139963297fce1eb1c49`.

## Verificado

- 13 testes focados L7 passaram antes da seleção ampliada.
- 127 testes relacionados passaram, incluindo os 13, com um aviso de
  depreciação preexistente. Não somar contagens sobrepostas. Cobrem limite q,
  contrato v4, gates L6/L7, histórico, preflight sem credencial/dispatch,
  latch concorrente, cronograma fake, atribuição NPC, política e custo.
- Preflight CLI: 17 turnos sintéticos, zero chamadas reais, maior corpo
  13.614 bytes. Sem trava live L7 criada ou launcher executado.
- AST do PowerShell válido. Diff e whitespace/links do incremento inspecionados.
- Não repetida suíte integral ou frontend/build: runtime/UI inalterados.
  As falhas históricas da consolidação Git permanecem; não é release verde.

```powershell
$env:STORYTELLER_DISABLE_DOTENV = '1'
.venv\Scripts\python.exe -m scripts.evaluate_hybrid_campaign_luna_l7_live --preflight
.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider --tb=short --junitxml=eval-results/hyp-007-l7-readiness-2026-10-18.xml tests/test_hybrid_campaign_luna_l7_preparation.py tests/test_hybrid_campaign_luna_l6_preparation.py tests/test_campaign_source_profile.py tests/test_scene_validation_diagnostics.py tests/test_scene_npc_gaze_speech_regressions.py tests/test_luna_test_cost.py
```

## Custos separados

**CUSTO FINAL LUNA L6 ESTIMADO: USD 0,0007156. Não é cobrança confirmada.**
Usage reportado: 2.372 tokens de entrada, 201 de saída, uma chamada com usage,
zero sem usage. Reproduzido com `scripts.report_luna_test_cost --settled`.
Sem ajustes de cache, tarifas de serviço ou impostos. Conta/saldo não consultados.

**CUSTO FINAL LUNA DA PREPARAÇÃO L7: USD 0 (nenhuma chamada iniciada).**
Custos dos stubs nos testes não são cobrança. Novo teto estimado adicional
proposto L7: USD 0,15, até 17 chamadas; não autorizado por sobra de L6. Guard
local estimado não é trava financeira garantida da conta. Mantidos os preços
de referência anteriormente verificados em 18/10, sem nova consulta de cobrança.

## Limitações e próxima proposta humana

Conclusão proposta: **L6 inconclusivo para a campanha integral por rejeição
real do limite de q e lacuna de instrução; nenhum narrador admitido.**
L5 permanece aceito; L6 não comprova live a correção de sujeito de L5 e não
chegou a resgate, demais trajetórias ou aceitação de experiência.

Próxima proposta: aceitar essa conclusão delimitada e autorizar/ajustar
L7 até 17 chamadas Luna low, USD 0,15 estimados adicionais, sem retry/fallback.
Continue/prossiga aprova a proposta nos limites apresentados conforme convenção
explícita do usuário, sem frase ritual. Não manter aceites já concedidos
pendentes; também não inventar aceite do resultado L6 a partir do "feito" da
entrada da chave. Até aprovação, L7 fechado e sem terminal/credencial.

Depois: revalidar, abrir Windows Terminal identificado, confirmar novo marcador,
pedir entrada protegida fora do chat, executar uma vez, verificar custo/gates e
fechar live. Não ler `.env*`, chaves, saves ou ambiente/memória de terminais.
TASK-019 fecha diagnóstico/preparação, não TASK-013/CAMP-24, narrador ou MVP.
Alterações locais sem commit/push; checkout original preservado.
