# HYP-007-L59 — formulação retrospectiva ambígua na falha

Batch 9c071f9f-248f-453d-b7aa-b105c0b3bfdf: 16 chamadas/15 turnos,
sete percursos completos, parada R-08/07. Texto afirma nenhuma recuperação e
dano wet, mas termina “a tentativa deixa de revelar o que você procurava”.
Guard genérico: undeclared_player_action/inspect, por procurava retrospectivo;
guard mecânico: failure_granted_goal por revelar sob deixa de, não reconhecido
como negativa. Diagnósticos conservadores, não prova de concessão canônica real.
Manter rejeição e não dispensar objetivos retrospectivos não declarados nem
enfraquecer regra de sucesso para acomodar essa formulação ambígua.

Custo final estimado USD 0.0157842, 60123 entrada/3133 saída, 16 usages.
Não confirma cobrança. records SHA256
c0fccec16a715bf94474207cdd86949e2d89dc88ac9d509164f1c8daa6eae7a4.
Gate fechado/latch/saídas preservados, sem retry/fallback/admissão.

Quatro regressões novas: original rejeitado, alternativa autorada troca apenas
fechamento por investigação termina sem recuperar conteúdo, aceita mesmo dano/
posição wet/bench sem concluir resgate. Ação extra e sucesso posterior rejeitados;
commit/reinício/replay com uma rolagem/geração. 79 relacionados aprovados, XML
hyp-007-l59-prompt-correction-2026-10-20.xml. 494 ampliados antes desse ajuste
de prompt aprovados, seleções sobrepostas.

V14 = v13 mais falha direta sem objetivo anterior presumido/revelação que cessou.
L60 novo mantém alvo/matriz integral/ordem 08 primeiro/limites, até 17 chamadas/
USD 0.15 total estimado por lote, 768 tokens/20.000 bytes/60s, primeira falha para.
Autorização contínua/avaliação intermediária delegada; guards/runtime inalterados.
