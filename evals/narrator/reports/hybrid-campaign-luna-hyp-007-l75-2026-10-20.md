# HYP-007-L75 — matriz técnica integral; auditoria qualitativa impede admissão automática

Batch 6fdb6e67-3784-4e9b-892e-4c84daa39a04: 17 chamadas/17 turnos,
oito percursos completos sob perfil congelado v20. Todos os desfechos e regras
planejados executados, sem retry/fallback/troca de alvo. Gate fechado, latch/
records preservados. Auditoria independente confirmou SHA, 17 operações e
invocações distintas, identidade OpenAI/gpt-5.6-luna e 22 hashes de implementação.

Custo final estimado USD 0.0170188, 65.750 entrada/3.224 saída, 17 usages.
Não cobrança confirmada; preços são snapshot registrado, sem impostos/cache.
records SHA256 6d758eb683eb305205e27042d9375110910a8a0ab05a322fb297bba3246cf651.
44–90 palavras por turno; q aberto fixo não terminal/vazio terminal. Máximo
19.783 bytes; geração min/mediana/max 2.735/3.297/10.107 ms, turno max 10.375 ms.
Não mede UX de navegador nem comprova SLA/estabilidade estatística.
654 relacionados aprovados, XML hyp-007-l75-expanded-2026-10-20.xml.
Seleção repetida operacionalmente, não são 1.308 testes distintos.

Leitura de todos os 17 textos pelo agente: Mara fala diretamente, recusa sem
relatório de informação protegida, ajuda pertinente sem repetir a recusa,
progressão/abandono/perda/salvamento e falha sem encerrar recuperação parcial.
Não cria motivo secreto para recusa ou nova tarefa terminal. Q fixa é limitação
de variedade de UX. Uma fala R08 soa truncada: mas não daqui a informação inteira.

Auditoria encontrou lacuna material em R06/07: Mara diz Está seco agora após
transferir páginas molhadas. Superfície seca não prepara secagem das páginas.
Isto passou sob guards congelados: não esconder a lacuna nem promover só por
testes verdes. Duas falhas offline pré-fix provam aceitação indevida dessa fala
e declaração nominal equivalente. Guard prospectivo rejeita só essas afirmações
positivas imediatas no resgate wet→partial, não a negativa nem fora da água.
Cinco regressões/39 relacionados aprovados, XML hyp-007-l75-dry-audit-2026-10-20.xml;
atomicidade/reinício/replay sem RNG extra. Resultado histórico 17/17 não alterado.

V21 esclarece que superfície seca não seca páginas e pede fala natural/completa,
com prompt menor que v20. L76 é hipótese prospectiva de fidelidade física e
prosa, não repetição para selecionar melhor amostra. Mesmos oito percursos/
17 chamadas/USD 0.15 total/768 tokens/20.000 bytes/60s, primeira falha encerra,
sem retry/fallback/admissão. Autorização contínua/avaliação delegada mantidas.

Acumulado conferido nas 35 summaries L41–L75: 313 chamadas/280 turnos,
USD 0.3091700 estimados; apenas L75 matriz técnica integral nessa sequência.
Versões/guards variaram: não usar esses lotes como taxa comparável de estabilidade.
Admissão/default/CAMP-24/MVP continuam abertos. Autorização contínua segue válida;
um resultado positivo não dispensa hipótese e limites próprios de cada lote novo.
