# HYP-007-L5 — execução encerrada e conclusão delimitada

Data: 18/10/2026. Target: `gpt-5.6-luna`, esforço `low`.
Batch: `7b94103b-f600-4f25-a370-0efb761429cf`.
Estado: encerrado; conclusão técnica proposta inconclusiva por falso positivo
de atribuição NPC. Aceite humano pendente. Nenhum narrador/default admitido.

## Proveniência e limites

O usuário autorizou o novo lote pago após a proposta de até 17 chamadas e teto
estimado adicional USD 0,15, sem retry/fallback. A entrada protegida foi feita
no PowerShell externo identificado; chave/ambiente do processo não foram lidos.
O lançador inicial sem prompt acessível foi encerrado antes de criar lote/trava;
o segundo lançador confirmou prontidão e depois produziu um único lote real.
Não foi aberta outra execução após a entrada da chave.

Manifesto: [L5 de 18/10](hybrid-campaign-luna-l5-live-gate-2026-10-18.json).
Prompt v3 e os 22 arquivos congelados permaneceram iguais. Não houve modificação
de detector, política, RNG, persistência, critérios, reenvio ou fallback.
Preparação anterior e suas limitações: [prontidão](hybrid-campaign-luna-hyp-007-l5-readiness-2026-10-18.md).

Artefatos locais originais, não reescritos:

```text
eval-results/hybrid-campaign-luna-l5-7b94103b-f600-4f25-a370-0efb761429cf/records.jsonl
eval-results/hybrid-campaign-luna-l5-7b94103b-f600-4f25-a370-0efb761429cf/summary.json
```

SHA-256 de records, conferido contra summary:
`1c1d5a03b7225fe2310ffcd5e787e87d4fe7f79872f66c4bfd914f88e936d90c`.

## Resultado observado

| Caso/turno | Regra | Resultado | Geração local | Turno local |
|---|---|---|---|---|
| CAMP-EVAL-01/1 | R-01 | Completo; Mara explica ajuda/superfície seca | 5.163 ms | 5.312 ms |
| CAMP-EVAL-01/2 | R-05 | Completo; registro preservado na Galeria, epílogo terminal | 3.863 ms | 4.120 ms |
| CAMP-EVAL-02/1 | R-03 | Rejeitado por política; lote interrompido | 3.556 ms | 3.634 ms |

Summary: `status=stopped`, `stop_reason=campaign_source_policy_failed`,
`planned_calls=17`, `attempted_calls=3`, `completed_turns=2`.
Os 14 slots restantes não foram executados e não constituem saldo de novo lote.
As durações são três observações locais, não SLA, comparação controlada ou
prova de latência futura. O encerramento de CAMP-EVAL-01 não prova os outros
sete percursos ou satisfação narrativa. Não reclassificar a chamada rejeitada.

Trecho R-05 para julgamento da experiência, atribuído à saída Luna:

> Você retira o registro da bancada baixa do Arquivo e o leva até a superfície seca na Galeria. Ali, o registro é protegido intacto, afastado da umidade e sem novos danos. Mara acompanha o movimento com atenção, mantendo-se à distância. Quando percebe que o objeto está seguro, ela enfim relaxa os ombros e diz, em tom baixo: “Está bem. Agora o risco não aumenta mais.” O silêncio que segue confirma que o resgate foi concluído, e o registro permanece preservado na superfície seca.

Há fala direta neste percurso, mas a satisfação/imersão depende do usuário;
o gate técnico não dá nota de UX nem admite o narrador.

## Reprodução offline da rejeição

A proposta R-03 original narra espera declarada, infiltração aumentando o risco,
registro ainda seco e fala de Mara. O helper `_realizes_rule` retorna true.
`validate_campaign_source_proposal` recusa `campaign_source_proposal_invalid`;
a causa interna, observada em `validate_scene_continuation`, é
`scene_player_agency_violation`. Evidência estruturada do detector:

```json
{"field":"narrative","rule":"undeclared_player_action","subject":"voce","clause_index":1,"unauthorized_concepts":["social"]}
```

Reprodução sem rede usando a cápsula sintética R-03 de
`tests/test_campaign_source_capsule.py::capsule`, player_input `Aguardo`, roster
Mara, `_PolicyView` e a proposta original da terceira linha dos records:

| Variante local, não saída live | Resultado |
|---|---|
| Texto original | Rejeitado; ação social atribuída a `voce` |
| Apenas `o registro permanece seco` → `o registro continua seco` | Mesma rejeição |
| Apenas `Você aguarda na quietude do Arquivo.` → `Você aguarda.` | Mesma rejeição |
| Apenas `Ela ergue os olhos para você e fala` → `Mara ergue os olhos para você e fala` | Mesma rejeição |
| Apenas `Ela ergue os olhos para você e fala em voz baixa:` → `Mara diz em voz baixa:` | Admitido offline |

Isso delimita um falso positivo na atribuição de sujeito/objeto na coordenação
do NPC. Não prova equivalência semântica universal, ausência de outras falhas,
ou sucesso dos percursos não executados. A cápsula de reprodução é autorada;
não é reconstrução de banco live descartado pelo runner. Não houve alteração
do texto live nem do detector para produzir um aceite retroativo.

Um tratamento posterior deve preservar proteção contra ação social real do
jogador não declarada, pronome ambíguo e mudanças de sujeito. Não ampliar a
frente lexical geral registrada separadamente por arrasto, nem repetir o lote
antes de corrigir/delimitar o caso com contraprovas e preparação prospectiva.

## Custo final

**CUSTO FINAL LUNA ESTIMADO: USD 0,0022452. Não é cobrança confirmada.**

Usage reportado: 7.656 tokens de entrada e 595 de saída, três chamadas com
usage, zero sem usage. Total reproduzido por `scripts.report_luna_test_cost`
com `--settled` e hash de records conferido. Sem ajustes de cache, tarifas de
serviço ou impostos. O custo disponível no provedor não foi consultado.

```powershell
$env:STORYTELLER_DISABLE_DOTENV = '1'
.venv\Scripts\python.exe -m scripts.report_luna_test_cost --run-directory eval-results/hybrid-campaign-luna-l5-7b94103b-f600-4f25-a370-0efb761429cf --settled
```

## Fechamento técnico e checkpoint humano

Gate paid/live fechado ao observar summary terminal; trava
`eval-results/hybrid-campaign-luna-l5-once` preservada. O marcador ready é
histórico pré-credencial, não prova de espera atual. Não consultar memória ou
ambiente do terminal para verificar exclusão de chave; o lançador tem remoção
em finally, mas essa remoção não foi inspecionada externamente.

33 testes focados passaram: preparação L5, política de campanha e custo, com
um aviso de depreciação preexistente. JUnit local:
`eval-results/hyp-007-l5-closure-2026-10-18.xml`. Os 78 testes da preparação
continuam evidência daquela etapa; contagens não são somadas como testes únicos.
Não foi repetida suíte integral/frontend: nenhum código runtime ou UI mudou.
As falhas históricas documentadas na consolidação Git continuam existentes.

Comando de fechamento:

```powershell
.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider --tb=short --junitxml=eval-results/hyp-007-l5-closure-2026-10-18.xml tests/test_hybrid_campaign_luna_l5_preparation.py tests/test_campaign_source_profile.py tests/test_luna_test_cost.py
```

Proposta para aceite: **HYP-007-L5 inconclusivo por falso positivo de atribuição
NPC; nenhum narrador admitido.** Dois turnos completos não autorizam considerar
TASK-013/CAMP-24, campanha ou MVP encerrados. Próxima ação humana: aceitar ou
contestar a conclusão delimitada. Em seguida, tratar o caso prospectivamente
sem reclassificar L5 ou assumir novo orçamento. Mudanças locais sem commit/push;
checkout original e `.env*` preservados.
