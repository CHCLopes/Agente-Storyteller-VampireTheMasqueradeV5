# HYP-007-L39 — omissão da reação NPC na desistência

Autorização contínua 19/10; v7/Luna low/17 chamadas/768 tokens/20.000 bytes/
60s/USD 0.15 total, primeira falha para, sem retry/fallback/admissão.
Batch 74d69c19-f140-43c2-b9c6-a40b793ebb55 em
eval-results/hybrid-campaign-luna-l39-74d69c19-f140-43c2-b9c6-a40b793ebb55.
Dez chamadas/nove turnos; três percursos completos (01 intacto,02 parcial,03
perdido); R-09/04 rejeitado. USD 0.0087130 estimados finais, 31727 tokens
entrada/1973 saída, não cobrança. Gate fechado/latch preservado/supervisor idle/2.
records SHA256: 1bdbdc543d0ffe57315cfda4cd5ba6078aa471b6f65de6336b626660b0b61e5f.
summary SHA256: 2f2eb7e84033c80a7ef241a94dba76268471ec71ab78bd4c4fe014df80ba098b.

R-09 contém desistência e encerramento, mas omite Mara. A política vigente
_REQUIRED R-09 exige Mara e desistência; corpus aprovado também contém reação
NPC. Não flexibilizar requisito para fazer o lote passar. Três regressões novas
confirmam omissão rejeitada, contraprova com reação aceita e ação extra rejeitada;
atomicidade/reinício/replay sem RNG/geração adicional. 26 relacionados e dez
preparação aprovados em seleções sobrepostas. XML
hyp-007-l39-review-l40-readiness-2026-10-19.xml; aviso multipart preexistente.
Não muda runtime/gates nem reclassifica live L39.

V8 explicita somente reação de Mara à desistência sem insistência, ação imposta
ou nova tarefa, preservando encerramento/posição do registro. L40 separado:
mesmos alvo/parâmetros/gates, até 17 chamadas/USD 0.15 total, primeira falha
encerra, sem retry/fallback/admissão. 22 hashes/preflight 17 sintéticos/zero
rede/máximo 15.038 bytes. Autorização contínua cobre execução sem novo aceite.
Nenhum narrador admitido; TASK-013/CAMP-24/MVP abertos.
