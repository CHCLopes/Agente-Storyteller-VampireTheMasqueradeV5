# HYP-007-L23 — violação real de agência; hipótese v6 preparada

18/10/2026. Batch 831812c6-fb54-4367-9624-37de554fd759. Luna low/v5,
até 17 chamadas/USD 0,15 estimados autorizados, sem retry/fallback/admissão.

## Observado e custo final

Quatro chamadas/três turnos concluídos. CAMP-EVAL-01 completo/intacto,
CAMP-EVAL-02 parou em R-03B/turno 2 com campaign_source_policy_failed.
Demais percursos não alcançados. Para Espero, resposta afirmou Você permanece
em silêncio. Espera não autoriza impor silêncio/imobilidade: distinção já
estabelecida no validador e em test_scene_focus_wait_regressions.py.
Não é falso positivo; não flexibilizar o gate para fazer a amostra passar.

Custo final estimado USD 0,0032892, não cobrança confirmada; 11.076 tokens
entrada/895 saída, quatro chamadas precificadas/zero sem usage. Reporter
--settled reproduzido. Sem cache/tarifas/impostos.

Diretório eval-results/hybrid-campaign-luna-l23-831812c6-fb54-4367-9624-37de554fd759/:

- records.jsonl SHA256: d1a378c996a4373bc86dc4519b1757fb60d60e9aeb19ba20ec7f61d94c838c47
- summary.json SHA256: 19f9082858639b2610ca8fa427e1965c2ae2f917caa45dd5de3b70f0f78cf582
- Manifesto fechado SHA256: 9ea2042b27e8f8421c4a19d08d2a1378dbb074335b691428419d40786d511cf3

## Verificação sem alterar runtime

Reprodução: scene_player_agency_violation/undeclared_player_action, subject voce,
clause_index 0, unauthorized_concepts wait. Seis regressões novas verificam
Espero/Aguardo sem silêncio, equivalência com espera literal e integração R-03B.
Caso exato rejeitado atomicamente: estado continua warned/turno 1/uma fonte,
sem chunk novo. Contraprova Você espera aceita wet/turno 2; reinício/replay
sem geração/RNG extra. 72 focados aprovados, um aviso preexistente; XML
eval-results/hyp-007-l23-review-2026-10-18.xml. Runtime/critério inalterados.

Gate L23 fechado, trava/artefatos preservados, sem retry/chamada adicional.
Nenhum narrador admitido. L22 aceito; TASK-013/CAMP-24/MVP abertos.

## Preparação L24/v6 e limites

Prompt v6 acrescenta somente instrução de que esperar/aguardar não autoriza
silêncio, imobilidade, olhar/postura do jogador; usar espera declarada e efeito
canônico, NPC/ambiente dentro do pacote. Não altera produto/autoridade ou gate.
Prompt SHA256: 3ca16eeb31dfdc625b3123d8c3fcc4698f43998a1893e38c2fcb5e29c906568a.
L24 separado/fechado, mesmos alvo/limites/22 hashes. 31 testes de preparação/
integração aprovados, um aviso preexistente; XML
eval-results/hyp-007-l24-readiness-2026-10-18.xml. Teste herdado de drift foi
corrigido: L23 permanece válido/fechado porque runtime não mudou, só novo prompt.
Preflight 17 sintéticos/zero chamadas, máximo 14.457 bytes/AST válido.
Suíte integral não repetida: runtime preservado e cobertura focada/integração.
Não afirmar que a eficácia narrativa v6 foi demonstrada offline.

Proposta: aceitar L23 com violação real de agência, campanha integral inconclusiva,
um percurso completo, nenhum narrador admitido; autorizar L24/v6 até 17 chamadas/
USD 0,15 estimados adicionais, Luna low/768 tokens/20.000 bytes/60s, sem retry/
fallback/admissão. Continue/prossiga aprova ambos. Até lá L24 fechado, sem
terminal/chave/inferência; não transferir orçamento/slots anteriores.
