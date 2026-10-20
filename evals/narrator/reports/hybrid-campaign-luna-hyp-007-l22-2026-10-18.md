# HYP-007-L22 — movimento da umidade atribuído ao jogador

18/10/2026. Batch e3666327-94cc-4794-b087-4029247cf98c. Luna low/v5,
até 17 chamadas/USD 0,15 estimados autorizados, sem retry/fallback/admissão.

## Observado e custo final

Seis chamadas/cinco turnos concluídos. CAMP-EVAL-01 completo/intacto.
CAMP-EVAL-02 avançou por R-03/R-03B/R-01 e parou em R-06, quarto turno,
com campaign_source_policy_failed. Percursos 03–08 não alcançados.
Custo final estimado USD 0,0052084, não cobrança confirmada. 18.620 tokens
entrada/1.237 saída; seis chamadas precificadas, nenhuma sem usage. Reporter
--settled reproduzido. Sem ajustes de cache/tarifas/impostos.

Diretório: eval-results/hybrid-campaign-luna-l22-e3666327-94cc-4794-b087-4029247cf98c/.

- records.jsonl SHA256: bec1f62e8ac5c158ed308ad3edeb3aa8efa83e1492aa88f92d5c7a0d4e295e29
- summary.json SHA256: 5ddcf0a8efb3fb9323303ba200c8ad939ac95d7f03ba5ff829ea3673f43473d3
- Manifesto fechado SHA256: 568979bd5cd44c7849ba6e1c74b07d4d9fe077dec2e99aa2f4dc87c91cb446b7

Gate paid/live fechado, trava/artefatos mantidos; nenhum retry/chamada adicional.

## Diagnóstico e correção

Reprodução exata: scene_player_agency_violation, undeclared_player_action,
subject voce, clause_index 0, unauthorized_concepts move. A oração
“antes que a umidade avance” possui sujeito ambiental, não jogador.
A exceção existente reconhecia apenas a variante com mais no final.
Correção em _action_signature_matches de api/scene_director_service.py torna
somente esse advérbio opcional; mantém sujeito/predicado/fronteira explícitos.
Sem mudança de prompt, critérios, autoridade ou reclassificação live.

Oito regressões novas: resposta exata, cinco contraprovas de troca de ator/ação
posterior, dois testes integrados de parcialidade/atomicidade/reinício/replay
sem geração ou RNG adicional. Duas falhas reproduzidas antes da correção.
43 focados aprovados/um aviso preexistente python_multipart; XML
eval-results/hyp-007-l22-correction-2026-10-18.xml. Não é prova semântica geral.

## Preparação e checkpoint humano

L23 separado/fechado, mesmo v5/alvo/limites, 22 hashes válidos, 17 turnos
sintéticos/zero chamadas, máximo 13.952 bytes, AST válido. 33 testes focados
aprovados/um aviso preexistente; eval-results/hyp-007-l23-readiness-2026-10-18.xml.
Suíte integral não repetida: alteração unitária e cobertura focada/integração;
limites de cobertura permanecem explícitos. L21 aceito; nenhum narrador admitido.
TASK-013/CAMP-24/MVP abertos.

Proposta delimitada: aceitar L22 inconclusivo integral/um percurso completo e
autorizar L23 até 17 chamadas/USD 0,15 estimados adicionais, Luna low/v5,
768 tokens/20.000 bytes/60s, sem retry/fallback/admissão. Continue/prossiga
aprova ambos. Até lá L23 fechado, sem terminal/chave/inferência; orçamento/slots
não consumidos de L22 não são transferidos.
