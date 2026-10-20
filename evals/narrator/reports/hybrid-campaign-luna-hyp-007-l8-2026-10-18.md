# HYP-007-L8 — encerramento, condicional e prontidão L9

Data: 18/10/2026. Target `gpt-5.6-luna`, esforço `low`.
Batch: `d3ff90c3-c6aa-406a-a0e6-8d029363d6a5`.
Estado: encerrado; conclusão delimitada proposta abaixo, nenhum narrador admitido.

## Observado em L8

Depois da aprovação L8 e esclarecimento da fila antes de começar, o usuário
confirmou entrada protegida. O mesmo lote fez uma chamada, zero turnos completos;
parou no primeiro R-01/CAMP-EVAL-01 com `campaign_source_policy_failed`.
Não alcançou salvamento ou os outros percursos. Sem retry ou fallback.
Os 16 slots não executados não constituem saldo para outro lote.

Geração local 4.519 ms; turno local 4.638 ms. Observação única, não SLA.
Uma resposta estruturada com usage foi recebida, sem inspeção da credencial.
Gate paid/live fechado ao observar summary terminal e trava mantida. Marcador
ready e seu zero de chamadas são históricos pré-entrada, não status atual.

Artefatos originais preservados:

```text
eval-results/hybrid-campaign-luna-l8-d3ff90c3-c6aa-406a-a0e6-8d029363d6a5/records.jsonl
eval-results/hybrid-campaign-luna-l8-d3ff90c3-c6aa-406a-a0e6-8d029363d6a5/summary.json
```

SHA-256 records, conferido contra summary:
`32aeb6c8035f9c45c51a4389dae76037df79c63d31b2842a99cfc5db7a437e83`.
SHA-256 summary:
`af65bc6b2e09ad68a9c436f6927ac3887088cb237a8475ffd302ac8f9ca32bfc`.

## Causa reproduzida e correção delimitada

Trecho original:

> Se você precisar movê-lo, a superfície seca na Galeria é o lugar seguro para apoiá-lo.

É uma hipótese, não afirma que o jogador moveu o registro. O scanner leu a
forma normalizada `move-lo` como a ação `interact/move_object`. Diagnóstico:

```json
{"code":"scene_player_agency_violation","evidence":{"field":"narrative","rule":"undeclared_player_action","subject":"voce","clause_index":0,"unauthorized_concepts":["interact"]}}
```

Cinco positivos falharam antes do ajuste e sete contraprovas já eram recusadas.
Correção no tratamento existente de hipóteses de `_validate_declared_player_actions`:
reconhecer apenas se/caso + sujeito jogador conhecido + precisar + infinitivo
movê-lo/la/los/las + vírgula, incluindo negação de necessidade. Mascara somente
o verbo hipotético no scan, preservando clítico, offsets, texto original e
verificação das ações seguintes. Não declara nova autorização de movimento.

Prosa exata L8 passa offline sem reescrita. Movimentos afirmativos, comandos,
coerção, promessa e movimento posterior não declarado permanecem recusados.
Não alterados RNG, persistência, catálogo, protocolo, schema, prompt v4 ou gates
de autoridade. O turno real L8 permanece rejeitado historicamente.

Integração com adaptador falso: a pergunta de ajuda confirma R-01 uma vez,
mantendo registro ameaçado e sem desfecho; reinício/replay não geram outra
resposta ou RNG. Acrescentar "Você move o registro" recusa o turno e mantém
revisão zero, sem fonte ou entrega parcial. Não confundir admissão offline
com resultado de nova inferência ou aceitação humana de UX.

## Limitação separada, não corrigida por arrasto

Uma variante autorada registra o alias do jogador (Neófito/Violeta), cita esse
nome dentro da hipótese e depois usa "Ela" para Mara. O gate de pronome mantém
recusa conservadora por `ambiguous_pronoun`/`wait`. Nomear Mara explicitamente
nessa variante passa. Isso é outro recorte, não a condição original L8 com
aliases vazios e "você". Não ampliar correferência ou enfraquecer o gate para
forçar aceite desses casos. A limitação foi registrada e permanece testada.

Os testes de aliases isolam a condicional com NPC explícito e também conservam
as variantes ambíguas como recusadas. A resposta live original continua intacta
em seu teste dedicado. Não se afirma cobertura semântica universal ou ausência
de outros falsos positivos em português livre.

## Verificado

18 testes novos de condicional/integração, 43 na checagem focada conjunta com
L8/L9 e seleção ampliada final de **850 aprovados**, um aviso de depreciação
preexistente. Contagens sobrepostas, não somar. A seleção cobre consumidores da
política, agência, aliases/roster, visibilidade, campanha, commit/rollback/replay,
gates históricos/prospectivos, custo e segurança local.
JUnit: `eval-results/hyp-007-l9-readiness-2026-10-18.xml`.

Testes L8 usam manifesto temporário isolado, como L2/L3/L5/L6/L7. Um teste
dedicado exige hash executado intacto e recusa do runtime corrigido pelo gate
histórico. Não atualizar hashes de lote executado para obter verde.
Diff inspecionado, whitespace/links do incremento verificados. Não repetidos
suíte integral/frontend/build: sem alteração UI e regressão relacionada foi
ampliada após focados passarem. Falhas históricas do amplo continuam registradas;
não é alegação de release verde ou campanha aceita.

## L9 preparado, não autorizado

Scripts próprios e [manifesto L9](hybrid-campaign-luna-l9-live-gate-2026-10-18.json).
Equivalência por identidade de lote dos três scripts é testada. Mesmo prompt
v4, alvo Luna low, oito casos/17 turnos, até 768 tokens de saída/chamada,
20.000 bytes/requisição e 60 s. Sem retry/fallback, saves reais ou admissão
automática. Flags paid/live false; trava/variável de entrada separadas.

22 arquivos congelados após correção. SHA-256 do manifesto L9 com flags false:
`aca5e8156e5aa6083e044962f4f3d9ddb52ccb831cd0a4de757cc713a05bd35f`.
Prompt v4 preservado SHA-256:
`5d043c5c8def46cfbea295b9ce23ee2289e21eb4167cfb7fcc6ea6f4f62bb66f`.
Manifesto executado L8 fechado preservado SHA-256:
`67e56e9ac2c6018f6045263a3cfef63105e6ed975c2649e0c1ca2f0c5c842d5c`.

Preflight CLI: 17 turnos sintéticos, zero chamadas reais, maior corpo 13.614
bytes. AST PowerShell válido. Sem launcher, chave, janela ou trava live L9.
Nenhuma leitura de `.env*`, saves existentes, chaves ou ambiente de terminal.

```powershell
$env:STORYTELLER_DISABLE_DOTENV = '1'
.venv\Scripts\python.exe -m scripts.evaluate_hybrid_campaign_luna_l9_live --preflight
.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider --tb=short tests/test_scene_conditional_move_regressions.py tests/test_hybrid_campaign_luna_l8_preparation.py tests/test_hybrid_campaign_luna_l9_preparation.py
```

## Custos separados

**CUSTO FINAL LUNA L8 ESTIMADO: USD 0,0007162. Não é cobrança confirmada.**
Usage: 2.375 tokens de entrada e 201 de saída; uma chamada com usage, nenhuma
sem uso registrado. Total reproduzido por `report_luna_test_cost --settled` e
hash conferido. Sem ajustes de cache, tarifas de serviço ou impostos; conta
e cobrança efetiva não consultadas.

**CUSTO FINAL LUNA DA CORREÇÃO/PREPARAÇÃO L9: USD 0 (nenhuma chamada iniciada).**
Stubs nos testes não são cobrança. Teto proposto L9: USD 0,15 adicionais, até
17 chamadas; não transferir orçamento de L8. Guard local estimado não garante
bloqueio financeiro da conta. Mantidos os preços de referência já verificados
em 18/10, sem nova consulta de chave, saldo ou cobrança.

## Próxima proposta humana

**L8 inconclusivo para a campanha integral por falso positivo de ação em
condicional, nenhum narrador admitido.** L7/L6/L5 aceitos não voltam a ficar
pendentes. O "feito" da entrada protegida não aceita resultado ainda não visto.

Proposta: aceitar essa conclusão delimitada e autorizar L9 até 17 chamadas Luna
low, USD 0,15 estimados adicionais, sem retry/fallback. Continue/prossiga aprova
a proposta nos limites apresentados; não exigir frase ritual. Até lá L9 fechado.
Não prometer número fixo de tentativas futuras ou que essa será a última; a
ressalva sobre a fila foi informada antes de L8 e permanece válida.

Depois: revalidar, abrir Windows Terminal identificado, confirmar novo marcador,
pedir chave protegida fora do chat, executar uma vez, conferir custo/gates e
fechar live. Nenhum narrador admitido; TASK-013/CAMP-24 e MVP continuam abertos.
TASK-022/023 fecham correção/preparação, não produto. Alterações locais sem
commit/push; checkout original preservado.
