# HYP-007-L35 — pergunta aberta de intenção

Autorização contínua 19/10, v7/Luna low/17 chamadas/768 tokens/20.000 bytes/
60s/USD 0.15 total, primeira falha encerra; sem retry/fallback/admissão.
Batch 10021029-5ee3-42bc-b8a5-7684a436120a em
eval-results/hybrid-campaign-luna-l35-10021029-5ee3-42bc-b8a5-7684a436120a.
Uma chamada/zero turnos, rejeição R-01/01. Custo final estimado USD 0.0007748,
2644 tokens entrada/205 saída, não cobrança. Gate fechado/latch preservado,
supervisor idle/exit=2. Sem repetir lote nem atualizar seus hashes live.
records SHA256: 2dd64e8e0bdb288fadccd383918a911bd41bf829a87381137423c8e7b69bb029.
summary SHA256: 94fac944a332adbf9de3354ad743ebbe3a658b23c14e094318c9f0ad42e6dc32.

Diagnóstico: scene_player_prompt_not_actionable/does_not_invite_player_action,
q de seis palavras Que ação você pretende realizar agora?. Pergunta aberta
legítima, sem escolha executada. Adicionado reconhecimento fullmatch dessa
formulação + cauda modal existente; não aceita instrução anterior, ator NPC,
vocativo, menu, pergunta dupla ou ação presumida. Limite 15 palavras mantido.
Testes de pergunta ampliados para 31, incluindo contraprovas/integridade;
duas falhas antes da correção. 165 agência/integração/terminal aprovados,
38 preparação/pergunta sobrepostos aprovados, aviso multipart preexistente.
XML hyp-007-l35-correction-l36-readiness-2026-10-19.xml. Commit/rejeição
atômica/reinício/replay sem RNG/geração extra demonstrados.

L36 novo: observar campanha integral após correção da pergunta, mesmo v7/alvo/
parâmetros/gates/17 chamadas/USD 0.15 total; primeira falha para, sem retry ou
fallback/admissão. 22 hashes/preflight 17 sintéticos/zero rede/14.763 bytes.
Autorização contínua cobre execução. Nenhum narrador admitido, MVP aberto.
