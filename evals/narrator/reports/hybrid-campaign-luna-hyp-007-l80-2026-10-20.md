# HYP-007-L80 — parcialidade e secagem não preparada

Batch fbd22686-e605-4693-829a-026e994238e4: 17 chamadas/16 turnos, encerrado
na primeira rejeição (último R-06/CAMP-EVAL-07). USD 0.0168512 estimado,
65698 tokens entrada/3093 saída, uso nas 17 chamadas, não cobrança confirmada.
SHA256 records a33a16e618e54e03261b766db632d60459586ad5eb100082ba826057400f3290.
Fonte: eval-results/hybrid-campaign-luna-l80-fbd22686-e605-4693-829a-026e994238e4.
Gate fechado, evidência preservada, sem retry/fallback/admissão.

Detector de agência aceita a frase; _realizes_rule não reconhecia e apenas o
que permaneceu legível é salvo como parcialidade. A resposta também dizia Está
seco por fora, consequência física não preparada. Offline: versão fiel com Está
fora da água falhou antes do fix; original segue rejeitada. Ajuste delimitado
reconhece a preservação parcial afirmativa e bloqueia essa secagem na transição
wet→partial/R-06, preservando negativas/fora da água e atomicidade/restart/replay
sem RNG extra. 31 focados/integração passam, XML hyp-007-l80-fix-2026-10-20.xml.

As 17 respostas foram lidas. Fala direta de Mara, recusa contextual sem relatório
interno de segurança, ajuda sem repetição da recusa, progressão e desfechos são
observáveis. Prosa ainda expositiva em pontos; última resposta com secagem não
é fidelidade suficiente, mesmo que outro gate pudesse aceitá-la. Não admitir.

L81/v22 é hipótese prospectiva: correções delimitadas e troca somente de
Superfície seca não seca páginas por Retirar da água não seca registro nem
páginas. Mantém matriz integral/ordem/alvo/22 hashes/tetos 17 chamadas/768 tokens/
20000 bytes/60s/USD 0.15 total; preparação keyless antes do despacho único,
primeira falha encerra, sem retry/fallback/best-of/admissão automática.
Autorização contínua e avaliação intermediária delegada vigentes.
L41–L80: 371 chamadas/333 turnos/USD 0.3669740 estimados; versões variaram,
não é taxa de estabilidade nem teto cumulativo ou confirmação de cobrança.
