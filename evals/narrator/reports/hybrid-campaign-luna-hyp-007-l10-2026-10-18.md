# HYP-007-L10 — decisão pendente e preparação L11

Data: 18/10/2026. Target `gpt-5.6-luna`, esforço `low`, prompt v4.
Batch: `965327f4-db29-4668-afe5-0d535c2c8099`.

## Resultado observado

O usuário aceitou a conclusão delimitada L9 e autorizou L10 por Continue.
Após entrada protegida, L10 fez uma chamada e zero turnos completos; parou
no R-01/CAMP-EVAL-01 com campaign_source_policy_failed. Sem retry/fallback.
Não alcançou outros percursos; 16 slots restantes não são saldo transferível.
Gate L10 paid/live fechado ao constatar summary terminal; trava preservada.
Nenhum narrador admitido. TASK-013/CAMP-24/MVP continuam abertos.

Originais preservados em
`eval-results/hybrid-campaign-luna-l10-965327f4-db29-4668-afe5-0d535c2c8099/`.
SHA256 records: `740c57837f485f51f90ce525f172f18bed085cd0985a231f724b0dde65cd8222`.
SHA256 summary: `f061b92e3c71ec1da9a4b95ebcd3d283a6b16d6e819b80c8e10bdf6eaf897d60`.
SHA256 manifesto L10 fechado: `818084ed1cbf9878549a3195a10933ec399cbb91be895e07c18d44fda724ad0d`.

## Custo final e tempo

**USD 0,0007104 estimados**, não cobrança confirmada: 2.400 tokens de entrada,
192 de saída, uma chamada com usage, nenhuma sem. Reproduzido por
`scripts.report_luna_test_cost --settled`, com records conferidos contra summary.
Sem ajustes de cache, tarifas ou impostos. Correção/preparação adicional USD 0.
Geração 3.740 ms, turno 3.861 ms; amostra única, não SLA ou aceitação de UX.

## Diagnóstico e ajuste restrito

Trecho original: "mantendo as mãos afastadas até que você decida como proceder".
É uma decisão ainda pendente, não uma decisão já executada pelo jogador.
Reprodução bruta: scene_player_agency_violation, narrative, subject voce,
clause_index 1, unauthorized_concepts choice. Um primeiro diagnóstico auxiliar
usou outcome success com facts vazios e parou em outcome_mismatch; repetido
com expected_narrative_outcome dos mesmos facts revelou o erro de agência.

Em `_validate_declared_player_actions`, reconhecer somente até que + jogador
conhecido + decida como proceder + fronteira/pontuação/fim. Mascarar somente
decida no scan, preservando texto e offsets e os verbos seguintes. Não concede
uma decisão, não altera prompt/schema, fatos, RNG, persistência ou catálogo.
Não reclassificar a rejeição histórica nem editar a resposta original.

Dez testes em `tests/test_scene_pending_decision_regressions.py`: resposta exata,
cinco contraprovas de decisão/ação real, dois aliases registrados e integração
R-01 segura/insegura. Caso seguro confirma uma revisão, permanece threatened
sem desfecho; reinício/replay conserva envelope e uma geração/entrega sem RNG.
Decisão indevida posterior recusa atomicamente, sem revisão/fonte/entrega.
Contraprovas exigem erro de agência, não mero erro de comprimento.

Antes do ajuste: resposta exata e integração segura falharam; as duas variantes
de alias iniciais eram curtas demais, depois adequadas ao contrato. O primeiro
ensaio pós-ajuste tinha duas contraprovas ainda curtas; corrigidas as fixtures,
sem reduzir mínimo do produto. Verificação final: 58 focados de políticas e
35 focados de preparação/histórico/novo caso aprovados (sobrepostos), um aviso
preexistente python_multipart. Não somar contagens como testes únicos.

Regressão ampliada concluída: **894 aprovados**, um aviso preexistente,
95,97 segundos; XML `eval-results/hyp-007-l11-readiness-2026-10-18.xml`,
zero errors/failures. Seleção cobre históricos L5–L10/prospectivo L11,
agência, atribuição, visibilidade, diagnóstico, contratos, campanha,
persistência, custo e regressões de segurança. Não rodada suíte integral,
frontend ou build; sem alteração nessas camadas. Não declarar release verde.
Diff inspecionado e diff --check sem erros nos arquivos alterados rastreados.

## Preparação prospectiva L11 — sem gasto autorizado

Runner/preflight/lançador/manifesto/testes L11 separados, mesmo prompt v4,
modelo low, corpus oito percursos, 17 chamadas/768 tokens/20.000 bytes/60s.
Teto adicional estimado proposto USD 0,15, sem retry/fallback/admissão automática.
Paid/live false, 22 hashes válidos; preflight CLI 17 sintéticos/zero chamadas,
corpo máximo 13.614 bytes; AST PowerShell sem erros. Sem terminal, chave ou
trava live L11. SHA256 manifesto fechado:
`b96ae204e3d03eb3216b9c56185e56443cf520470681c1ff7ab5c30167cafa35`.
Testes L10 isolam hashes atuais somente em manifesto temporário e comprovam
que o manifesto executado preservado rejeita o runtime corrigido.

Conclusão delimitada proposta: L10 inconclusivo para campanha integral por
falso positivo de decisão pendente, nenhum narrador admitido. Próxima proposta:
aceitar conclusão e autorizar L11 nos limites acima. Continue/prossiga aprova
a proposta delimitada; depois entrada protegida. Não prometer última tentativa.
Fidelidade semântica e narrativa/UX continuam dependências distintas; ressalvas
R-01/R-07 de L9 e pronomes com alias continuam registradas, sem admissão por arrasto.
