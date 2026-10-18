# Pátio — preparação concluída

A observação suplementar está pronta, após correção local do falso negativo da pergunta. **66 testes de executor/wrapper passaram** na versão final, incluindo preflight real e chave vazia sem envio ou novo resultado. A correção de pergunta foi verificada separadamente em274 testes,30 novos. Esses grupos se referem a superfícies diferentes e não são somados aos152 históricos como contagem única. Zero chamadas externas na preparação.

## Pacote congelado

Novo caso courtyard-observe-wait, cena Pátio coberto sem NPC; observar sem toque e depois aguardar no mesmo lugar. Mesmo SYSTEM narrative-source-v1 e perfil n/q da direção B. Segundo USER depende exclusivamente da primeira fonte integral validada, com q separado. Duas chamadas no máximo,768 tokens cada/1536 total, Groq/Qwen fixo, none/0,65, espera inicial/intervalo/deadline60 segundos. Primeira falha encerra com skip, sem retry/reparo/fallback/diagnóstico/juiz.

Primeiro corpo: `675fc683b16c053baaec0b1c6b6b942f33551a0d6d6b21e9a76cd95ceb1f0249`. USER: `c38b444f7b58a9c14136374857c3dbb5bffb9038fc90ae1083baa6ad2ac19351`,140 tokens estimados. O segundo corpo só é conhecido depois da primeira resposta admitida. Os metadados, hashes de implementação, provas e launcher estão no [JSON preparado](narrative-source-courtyard-preparation-2026-09-07.json).

O executor recusa --live da Estufa antes de ler a credencial; preflight/verificação offline preservam o caso histórico. O wrapper aceita somente Pátio. A revisão independente fechou esse ponto antes da rodada final. O lote f97 e seus hashes/prepared_* continuam históricos; não será repetido nem completado.

## Execução encerrada

O lote f6483710 terminou com2 chamadas,2schemas válidos,1fonte admitida e a segunda resposta recusada por155 palavras contra150. A passagem integral da primeira fonte ao segundo USER foi auditada; não houve dois turnos admitidos. [Resultado e leitura autorada](narrative-source-courtyard-observation-f6483710-2026-09-07.md). Chave descartada, janela NoExit pode permanecer; não relançar.

Campos preparados acima são históricos. Próximo incremento local: ponte optativa fonte/turno/persistência/recuperação com adaptador falso e SQLite temporário; semnova chave, prompt, lote ou ativação de produto.
