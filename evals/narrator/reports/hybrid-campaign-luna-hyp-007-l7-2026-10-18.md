# HYP-007-L7 — encerramento, correção local e prontidão L8

Data: 18/10/2026. Target: `gpt-5.6-luna`, esforço `low`.
Batch L7: `7d690675-b176-4ad6-bf91-0f7e77102ddc`.
Estado: execução encerrada; nenhum narrador admitido. Conclusão delimitada
proposta no fim, sem autorização automática de gasto posterior.

Atualização posterior: o usuário respondeu "Prossiga", pedindo informar a fila
antes de começar. A informação foi entregue antes de ativar/executar L8:
uma bateria paga preparada nesta frente, oito percursos/17 chamadas; depois,
se tecnicamente aprovada, etapa humana de narrativa/UX e ensaio a delimitar.
Não se prometeu número fixo de novas tentativas ou baterias de todo o MVP.
Pela convenção explícita, L7 aceito nessa conclusão e L8 autorizado nos limites
abaixo. Somente flags paid/live L8 ativados; prompt/código/hashes intactos.
O SHA com flags false abaixo é histórico da preparação. Próxima dependência:
entrada protegida no terminal L8 identificado. Nenhum narrador admitido.

## Observado

Após a aprovação L7 por "prossiga", a janela identificada foi aberta. Uma
verificação de prontidão foi interrompida por indisponibilidade da revisão
automática de ferramentas. Ao retomar pela checagem autorizada e somente
leitura do mesmo lançador, já havia summary terminal. Não se abriu outro lote,
consultou chave ou redirecionou saída do terminal.

| Caso/turno | Regra | Resultado | Geração local | Turno local |
|---|---|---|---|---|
| CAMP-EVAL-01/1 | R-01 | Completo; Mara orienta sobre risco e superfície seca | 5.093 ms | 5.251 ms |
| CAMP-EVAL-01/2 | R-05 | Completo; salvamento, registro preservado e encerramento | 4.062 ms | 4.321 ms |
| CAMP-EVAL-02/1 | R-03 | Rejeitado por política; lote interrompido | 3.404 ms | 3.495 ms |

Summary: `stopped`, `campaign_source_policy_failed`, três chamadas e dois
turnos completos de 17 planejados. Sem retry/fallback. Os 14 slots restantes
não são saldo para repetir o lote. Tempos são observações, não SLA ou prova
comparativa de modelo. O percurso de salvamento não prova campanha integral.

Artefatos originais preservados:

```text
eval-results/hybrid-campaign-luna-l7-7d690675-b176-4ad6-bf91-0f7e77102ddc/records.jsonl
eval-results/hybrid-campaign-luna-l7-7d690675-b176-4ad6-bf91-0f7e77102ddc/summary.json
```

SHA-256 records, conferido contra summary:
`4ecf349de785b2f4e81aaac421b20aca7eb2f9d0c9b8a35a15d05ed6d2a9c803`.
SHA-256 summary:
`b1a1d59d26670f46f7502423fd80d3236cfbf5addff5f1ea3c958b0b86410756`.
Gate paid/live L7 fechado e trava preservada. Marcador ready é histórico
pré-entrada e não representa chamadas atuais ou necessidade de nova chave.

## Diagnóstico e correção

A pergunta R-03 original foi:

> Qual é a sua próxima ação diante do risco imediato?

Tem 10 palavras; não viola o limite de 15 explicitado em v4. A realização de
R-03 retorna true, mas a validação da cena recusou:

```json
{"code":"scene_player_prompt_not_actionable","evidence":{"field":"player_prompt","rule":"open_player_action_question","reason":"does_not_invite_player_action","word_count":10}}
```

Com a mesma narrativa, remover somente o artigo ("Qual é sua próxima ação…")
passa offline. É falso positivo lexical da pergunta acionável, não falha
comprovada de agência ou progresso do modelo. O caso foi reproduzido antes da
correção: sete positivos falharam. Não reclassificar a chamada live rejeitada.

Correção local em `_validate_player_prompt`: reconhecer a forma possessiva
com artigo por fullmatch do campo inteiro, usando as mesmas escolhas pessoais
e caudas contextuais limitadas já existentes. Uma instrução prévia, segunda
frase, pergunta ao NPC ou menu não ganha autorização por terminar com um
convite válido. Limites de tamanho, agência, segredos e autoridade preservados.
Não mudou prompt v4, schema, catálogo, RNG, persistência ou estados.

22 testes novos cobrem o texto exato, equivalência com/sem artigo, contexto com
NPC, pergunta fechada, ator incorreto, instrução prévia, múltiplas perguntas e
limite de tamanho. Uma primeira contraprova de tamanho fora classificada como
longa sem contar palavras; a checagem somente leitura enumerou 15 palavras,
não mais de 15. O teste foi corrigido com asserções explícitas: 15 admitidas,
16 recusadas pelo mesmo código `scene_player_prompt_too_long`. Não se elevou
o teto ou removeu uma violação real para obter verde.

Integração com resposta original: commit único de aviso, reconstrução após
reinício e replay sem nova geração/RNG. Contraprova perguntando a próxima ação
de Mara: recusa, revisão zero, registro ameaçado, sem fonte ou entrega parcial.

Limitação narrativa observada: "marcado como advertido" expõe linguagem de
estado na prosa. Registro separado em
[observação sem nova prioridade](../../../plan/observation-campaign-state-language-1.md).
Não foi criado filtro/roteiro nem presumida satisfação de UX. Aceitar o
diagnóstico técnico não admite imersão, campanha completa ou narrador.

## Verificação

Passaram 34 testes focados (22 da pergunta e 12 de L8). Depois, a seleção
ampliada final aprovou **819 testes**, um aviso de depreciação preexistente,
sem falhas. Inclui gates históricos/prospectivo, política de cena, agência,
roster/aliases, visibilidade, campanha B, integração/rollback/replay, custo e
segurança local. As contagens se sobrepõem e não devem ser somadas.
JUnit: `eval-results/hyp-007-l8-readiness-2026-10-18.xml`.

Testes L6/L7 foram isolados em manifestos temporários, como L2/L3/L5, mantendo
testes dedicados que exigem hashes executados intactos e recusa do runtime
corrigido pelo manifesto histórico. Nenhum hash histórico foi atualizado.

Diff inspecionado e whitespace/links do incremento verificados. Suíte integral
e frontend/build não repetidos: sem alteração UI, e a seleção dos consumidores
da política foi ampliada após focados passarem. Falhas históricas da
consolidação Git continuam documentadas; não é alegação de release verde.

## L8 preparado, ainda sem gasto autorizado

Runner/preflight/lançador próprios e
[manifesto L8](hybrid-campaign-luna-l8-live-gate-2026-10-18.json).
Os três scripts só diferem dos L7 pela identidade de lote/paths/trava/variável
de entrada protegida, equivalência testada. Mesmo prompt v4, Luna low, oito
casos/17 turnos, até 768 tokens de saída/chamada, 20.000 bytes/requisição e 60 s.
Sem retry, fallback, save real ou admissão automática. Flags paid/live false.

22 arquivos congelados após correção. Manifesto L8 fechado SHA-256:
`67e56e9ac2c6018f6045263a3cfef63105e6ed975c2649e0c1ca2f0c5c842d5c`.
Prompt v4 inalterado SHA-256:
`5d043c5c8def46cfbea295b9ce23ee2289e21eb4167cfb7fcc6ea6f4f62bb66f`.
Manifesto L7 executado/fechado preservado SHA-256:
`dc2d96b72df8fba484474b3ba73a5e1cbe0e062324e0222436c274018be2dcd4`.

Preflight CLI: 17 turnos sintéticos, zero chamadas reais, maior corpo 13.614
bytes. AST PowerShell válido, launcher L8 não executado; nenhuma trava live L8
ou janela de credencial. Nenhuma leitura de `.env*`, chaves ou saves existentes.

```powershell
$env:STORYTELLER_DISABLE_DOTENV = '1'
.venv\Scripts\python.exe -m scripts.evaluate_hybrid_campaign_luna_l8_live --preflight
.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider --tb=short tests/test_hybrid_campaign_luna_l8_preparation.py tests/test_scene_articled_player_question_regressions.py
```

## Custos separados

**CUSTO FINAL LUNA L7 ESTIMADO: USD 0,0022832. Não é cobrança confirmada.**
Usage: 7.696 tokens de entrada e 620 de saída, três chamadas com usage,
nenhuma sem uso registrado. Total reproduzido pelo relatório `--settled` e
hash conferido. Sem ajustes de cache, tarifas de serviço ou impostos; conta
e cobrança efetiva não consultadas.

**CUSTO FINAL LUNA DA CORREÇÃO/PREPARAÇÃO L8: USD 0 (nenhuma chamada iniciada).**
Custos de stubs não são cobrança. Teto L8 proposto: USD 0,15 adicionais,
até 17 chamadas. Guard local estimado não é bloqueio financeiro garantido da
conta. Não transferir teto ou slots de L7. Preços de referência mantidos dos
manifestos verificados em 18/10, sem nova consulta de cobrança ou chave.

## Próxima proposta humana

**L7 inconclusivo para campanha integral por falso positivo de pergunta
acionável; nenhum narrador admitido.** Conclusão delimitada agora apresentada,
sem presumir que o "prossiga" usado para retomar ferramentas aceitava resultado
ainda não mostrado. L6 e L5 já aceitos não ficam pendentes novamente.

Proposta: aceitar a conclusão L7 e autorizar L8 até 17 chamadas Luna low,
USD 0,15 estimados adicionais, sem retry/fallback. Continue/prossiga aprova a
proposta nos limites apresentados; não exigir frase ritual. Até lá L8 fechado.
Depois: revalidar preflight, abrir Windows Terminal identificado e confirmar
novo marcador antes de pedir chave protegida; executar uma vez, verificar
custo/gates/resultado e fechar live. Nunca inspecionar ambiente de terminais.
TASK-020/021 fecham correção/preparação, não TASK-013/CAMP-24, narrador ou MVP.
Alterações locais sem commit/push; checkout original preservado.
