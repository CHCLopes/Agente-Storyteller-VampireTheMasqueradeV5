# HYP-007-L73 — recuperação parcial e parte nominal

Batch 0c8b91a8-fb5f-459e-9e19-66e0721a62d2: 15 chamadas/14 turnos,
parada R-07/06 campaign_source_policy_failed. Texto examina registro sobre a
bancada e recupera parte da informação contida nas páginas, mantendo estado
parcial/bench e fala direta de Mara. Duas causas reproduzidas: marcador de
sucesso não reconhece recupera parte da informação; guard de agência lê
parte nominal como partida do jogador. Não foi partida narrada real.

Custo final estimado USD 0.0149588; 57.988 entrada/2.801 saída, 15 usages.
Não cobrança confirmada. records SHA256
330cc0aea9c30b2d4ea0a5788902136535d50bee414ae8d4ae31d83040cd79aa.
Gate fechado/histórico mantido. 636 ampliados anteriores aprovados, XML
hyp-007-l73-expanded-2026-10-20.xml.

Duas falhas pré-fix; primeira correção do marcador deixa integração vermelha,
diagnóstico de causa interna identifica nominal. Fix adicional exclui somente
parte imediatamente após recupera/recuperou e antes de da informação. Marcador
exige sujeito afirmativo do jogador, incluindo exame sobre a bancada; hipótese/
negação/pergunta/NPC/citação não sustentam sucesso. Mesma recuperação vedada
na falha; partida real posterior/coordenada e ação extra seguem bloqueadas.
212 relacionados aprovados, XML hyp-007-l73-partial-fix-2026-10-20.xml;
R07 commit/reinício/replay com uma rolagem/geração, sem mudar efeito preparado.

L74 separado com mesmo v19/alvo/matriz integral/ordem/tetos até 17 chamadas/
USD 0.15 total, primeira falha encerra/sem retry/fallback/admissão automática.
Autorização contínua/avaliação intermediária delegada mantidas.
