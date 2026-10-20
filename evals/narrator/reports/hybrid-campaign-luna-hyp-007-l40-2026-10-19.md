# HYP-007-L40 — campanha integral tecnicamente concluída; aceitação humana pendente

## Aceite humano posterior — 20/10/2026

Resultados aprovados com ressalva explícita de naturalidade: remover anúncios
de informação/identidade protegida da fala ao jogador. Aprovação recebida;
não repetir pedido de aceite dos mesmos resultados. Correção orientada por v9
e L41 prospectivo, sem reescrever respostas/evidências L40 ou admitir default
automaticamente. Visão de diálogo colateral registrada separadamente; não
implementada por arrasto. O restante deste relatório retrata o fechamento original.

## Escopo e autorização

Autorização contínua explícita em 19/10 para testes necessários ao escopo aprovado
com teto planejado <= USD 0.15 por lote. L40 prospectivo após omissão NPC L39:
prompt v8 explicita reação à desistência sem insistência/ação imposta/nova tarefa.
Runtime/critérios não alterados por v8. Luna low, até 17 chamadas/768 tokens/
20.000 bytes/60s/USD 0.15 total; primeira falha para, sem retry/fallback/best-of/
admissão. 22 hashes/preflight 17 sintéticos/zero rede/máximo 15.038 bytes.

## Evidência observada

Batch 7295e209-3a13-4fd0-8224-3e7318fcfdb2 em
eval-results/hybrid-campaign-luna-l40-7295e209-3a13-4fd0-8224-3e7318fcfdb2.
Status completed, stop_reason null; 17 chamadas/17 turnos, oito percursos
completos. Todos com proveniência OpenAI/gpt-5.6-luna e usage disponível.

| Caso | Turnos | Desfecho canônico |
|---|---:|---|
| CAMP-EVAL-01 | 2 | preserved |
| CAMP-EVAL-02 | 4 | partial |
| CAMP-EVAL-03 | 3 | lost |
| CAMP-EVAL-04 | 1 | abandoned |
| CAMP-EVAL-05 | 1 | preserved |
| CAMP-EVAL-06 | 1 | partial |
| CAMP-EVAL-07 | 2 | partial |
| CAMP-EVAL-08 | 3 | preserved |

Geração: mínimo 2962 ms, mediana 3650 ms, máximo 4320 ms. Medição desta amostra,
não garantia de latência. Texto n+q de 47 a 107 palavras (faixa 30–150); q até
15 palavras, vazio em desfechos. Investigação e posição do objeto respeitaram
efeitos previstos; recusa de fundadora sem identidade revelada nesta amostra.
Mara tem fala direta em ajuda/aviso/desistência e conclusões. Não é medida de UX.

Custo final estimado USD 0.0152410, 54371 tokens entrada/3639 saída, não cobrança.
Sem confirmação de faturamento, cache/tarifas/impostos. Estimativa usa tabela
registrada no avaliador; não é nova consulta de preço. Nenhuma chamada adicional.
records SHA256: eff60427c29badf8055146ad8bf93acef61eef3a8feadec7b724d1e3af60432c.
summary SHA256: 56a442a05c82961e1534b32c47ceb38026a755efb666b0c246df6b181be3ab03.
Gate fechado/latch preservado, supervisor 20604 idle/last_lot=40/exit=0,
deadline original 20/10 00:00 Fortaleza mantido.

## Verificação técnica final

521 testes relacionados aprovados, um aviso preexistente python_multipart.
XML eval-results/hyp-007-l40-final-related-2026-10-19.xml. Cobre correções de
agência/condicionais/perguntas/mecânica, integrações, negação, persistência,
rejeição atômica, reinício/replay sem RNG/geração extra e segurança do receptor.
Diff inspecionado e git diff --check sem erros nas superfícies afetadas.
Hashes/contagem/proveniência/uso/faixa de palavras/efeitos do lote conferidos
separadamente; conjunto humano contém 17 respostas literais verificadas.
Suíte integral de release e ensaio interativo de UI não executados nesta etapa.
Não reclassificar lotes falhos nem afirmar estabilidade estatística de um único lote.

## Custos desta autorização contínua (L30–L40)

| Lote | Chamadas | Turnos concluídos | USD estimados |
|---|---:|---:|---:|
| L30 | 5 | 4 | 0.0043758 |
| L31 | 5 | 4 | 0.0043730 |
| L32 | 1 | 0 | 0.0007964 |
| L33 | 12 | 11 | 0.0106532 |
| L34 | 13 | 12 | 0.0111458 |
| L35 | 1 | 0 | 0.0007748 |
| L36 | 9 | 8 | 0.0080752 |
| L37 | 1 | 0 | 0.0007564 |
| L38 | 12 | 11 | 0.0103988 |
| L39 | 10 | 9 | 0.0087130 |
| L40 | 17 | 17 | 0.0152410 |
| Total | 86 | 76 | 0.0753034 |

Não inclui L26–L29, ensaios antigos ou custos da assinatura Codex. Cada novo lote
foi precedido de diagnóstico/alteração pertinente e manifesto próprio; nenhum
retry do mesmo lote. USD 0.15 é teto por lote, não alegação de cobrança máxima
do provedor nem novo limite acumulado acordado.

## Única intervenção imediata: julgamento narrativo

Leia luna-l40-human-review-2026-10-19.md: oito percursos/17 respostas reais.
Avaliar progressão sem loop, pertinência/role play de Mara, clareza de recuperação
parcial/falha/perda e conclusão sem tarefa imposta. Se reprovar, citar caso/turno.
Frases sobre informação conhecida/protegida e estado/posição ainda podem soar
mecânicas: satisfação e imersão são julgamento humano, não gates automáticos.
Observação Podemos examiná-lo após resgate pertence a L34, não reatribuir a L40.

Nenhum narrador admitido/default alterado; TASK-013/CAMP-24/MVP permanecem abertos.
Autorização contínua de testes <= USD 0.15 permanece vigente para trabalho
necessário após a avaliação; não pedir novo teto/aceite para cada teste. Não
rodar repetições adicionais só para elevar taxa ou substituir aceitação humana.
Após julgamento registrar aceite/restrições, tratar problemas dentro do escopo
e seguir checklist aprovado sem nova decisão arquitetural silenciosa.
