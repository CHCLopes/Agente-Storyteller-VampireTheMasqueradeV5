# HYP-007-L41 — interrompido; falso positivo ambiental

Autorização contínua: até 17 chamadas sintéticas, Luna low, prompt v9,
768 tokens/20.000 bytes/60s, teto total USD 0.15 estimado; sem retry/fallback.
Avaliações intermediárias delegadas ao agente até gate humano real.

Batch dbb776b9-ff4c-4bd3-9088-4eb7915b311c: três chamadas, dois turnos,
um percurso concluído (CAMP-EVAL-01, preserved). Parada no primeiro R-03 de
CAMP-EVAL-02, campaign_source_policy_failed. Recusa R-02 não alcançada;
hipótese de naturalidade integral inconclusiva. Não reclassificar L41 após fix.

Custo final estimado USD 0.0027948: 9504 tokens de entrada/745 de saída,
usage presente nas três chamadas. Não confirma cobrança. Supervisora idle,
gate fechado e latch preservado; autenticação funcional observada por respostas.
records SHA256 c911251ddfe5d64bc128fefa9200138335836706a4c7708d8447523b9b34b6e6.

Diagnóstico offline: “enquanto a infiltração avança pelas bordas da sala”
atribuído ao jogador que aguarda. Substituir apenas avança por cresce remove
a rejeição. Duas falhas reproduzidas antes da correção; oito testes novos
incluem sujeitos jogador/NPC, ação posterior e adjunto coordenado indevidos.
Correção limitada ao verbo avança nesse quadro ambiental explícito/pontuado,
sem ignorar ações posteriores. 53 relacionados aprovados, incluindo atomicidade,
reinício/replay sem RNG ou geração extra. XML hyp-007-l41-correction-2026-10-20.xml.

L42 separado: mesmo v9/alvo/corpus/limites, única alteração runtime acima.
22 hashes atuais, 17 sintéticos/zero rede/máximo 16.770 bytes; 16 preparação/
regressões aprovados (sobrepostos aos 53). Autorizado continuamente sob USD 0.15.
Falha inicial ao invocar preflight sem PYTHONPATH corrigida só na invocação;
preflight com raiz, como supervisora, passou. Sem alterar scripts por esse erro.
Sem admissão/default/release ou expansão de diálogo/lore.
