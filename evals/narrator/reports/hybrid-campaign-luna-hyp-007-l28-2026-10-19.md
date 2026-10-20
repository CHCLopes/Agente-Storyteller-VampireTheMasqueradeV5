# HYP-007-L28 — campanha v6 e falso positivo nominal R-07

## Escopo prospectivo

Humano pediu retomar testes narrativos em 19/10, após probe L27 funcional.
L28 separado: até 17 chamadas Luna low, v6, 768 tokens/20.000 bytes/60s,
USD 0.15 estimados para o lote inteiro; primeira falha interrompe. Sem retry,
fallback, best-of, admissão automática ou reclassificação de evidência anterior.
Preparação: 66 focados aprovados, 17 sintéticos/zero envios/14.457 bytes,
22 hashes atuais. Supervisora corrigida usada sem nova leitura da credencial.

## Resultado observado

Batch 090516e9-50b3-4154-b931-b85abd682dea em
eval-results/hybrid-campaign-luna-l28-090516e9-50b3-4154-b931-b85abd682dea.
12 chamadas, 11 turnos concluídos; parada campaign_source_policy_failed
em CAMP-EVAL-06/R-07. Cinco percursos completos: 01 preserved, 02 partial,
03 lost, 04 abandoned e 05 preserved. Casos 07/08 não executados.
Geração observada nos 12 slots entre 3093 e 4386 ms.
Mara usa fala direta nas respostas observadas de ajuda/aviso e salvamento parcial;
isso não mede satisfação nem comprova admissão narrativa. Há linguagem mecânica
como nova informação disponível e identidade protegida, reservada à avaliação UX.

Custo final estimado USD 0.0102126, 36669 tokens de entrada/2399 saída.
Uso disponível em todas as 12 chamadas; cobrança não confirmada, sem impostos
ou ajustes. Não confundir com custo do probe L27.

records SHA256: 7997aa1a1e063d1c23954081c0be08254ffc06a8eeb787fd7a29dbebec7b505f.
summary SHA256: ce01e8586807a2a8749e299c67698734c4ed1b53f502e494d2c5b79a7084dfc6.
Gate fechado e latch preservado; supervisor 20604 idle/last_lot=28/exit=2.

## Diagnóstico offline e correção

_realizes_rule=True; erro de cena scene_player_agency_violation,
undeclared_player_action, subject voce/clause_index 0, unauthorized_concepts move.
O substantivo partes em de suas partes ainda legíveis foi classificado como
verbo partir. Falso positivo confirmado; não é deslocamento realmente narrado.
Correção mínima em _action_signature_matches: ignora somente token partes no
quadro nominal de suas partes ainda legíveis seguido por fronteira; demais
verbos continuam inspecionados. Não altera prompt, RNG ou autoridade canônica.

Dez regressões novas; duas falhas reproduzidas antes da correção (após corrigir
fixture ao contrato existente). Contraprovas de partida/abertura posterior,
commit R-07, rejeição atômica e reinício/replay sem RNG ou geração adicional.
193 relacionados aprovados, um aviso preexistente python_multipart. XML:
eval-results/hyp-007-l28-correction-l29-readiness-2026-10-19.xml.
Diff da correção inspecionado, preservando outras mudanças preexistentes.
Suíte integral de release não executada; ampliação limitada ao risco relacionado.
Manifesto live L28 não atualizado para passar depois da correção.

## Próximo checkpoint

L29 preparado e fechado, mesma campanha/v6/modelo/limites, 22 hashes atuais,
preflight 17 sintéticos/zero chamadas/14.457 bytes. Não executado.
Proposta: aceitar L28 como campanha integral inconclusiva/cinco percursos
completos/falso positivo confirmado e executar L29 até 17 chamadas, USD 0.15
total estimado, sem retry/fallback/admissão. Continue/prossiga aprova proposta
delimitada; não pedir novamente o teto padrão. Nenhum narrador admitido;
TASK-013/CAMP-24/MVP permanecem abertos.
