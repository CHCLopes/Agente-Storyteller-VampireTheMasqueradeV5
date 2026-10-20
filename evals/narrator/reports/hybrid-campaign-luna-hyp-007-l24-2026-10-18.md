# HYP-007-L24/v6 — local canônico confundido com alvo da espera

18/10/2026. Batch 9933c25d-e8b9-467f-b2c2-4ef2df8f6b81. Luna low/v6,
até 17 chamadas/USD 0,15 estimados autorizados; sem retry/fallback/admissão.

## Observado e custo final

Quatro chamadas/três turnos. CAMP-EVAL-01 completo/intacto; parada R-03B/02
no segundo turno. Demais percursos não alcançados. Para Espero, a resposta
descreveu Você aguarda no Arquivo enquanto a água alcança o registro.
A amostra rejeitada não repete o silêncio imposto de L23; isto não demonstra
que v6 resolveu universalmente o problema. Nenhum narrador admitido.

Custo final estimado USD 0,0033604, não cobrança confirmada; 11.378 tokens
entrada/904 saída, quatro chamadas precificadas, zero sem usage. Reporter
--settled reproduzido. Sem ajustes de cache/tarifas/impostos.

Diretório eval-results/hybrid-campaign-luna-l24-9933c25d-e8b9-467f-b2c2-4ef2df8f6b81/:

- records.jsonl SHA256: 83b3f34de3bb60ec8cd60f9eb8f4956c719a6e62d350e4f5c6abb5dbc7975ed2
- summary.json SHA256: 64279dabc7a1a9044dde48cccbc858864ffaa33caa5039fae40c4b6b31eba419
- Manifesto fechado SHA256: 911d8d07e039d6e4ee609472fea011c14eeb06045eb06737a197a45298a60fb8

## Diagnóstico e correção

Reprodução: scene_player_agency_violation/undeclared_player_action, subject voce,
clause_index 0, unauthorized_concepts wait. Equivalência Espero/aguarda comparava
alvo vazio com Arquivo; o adjunto do local já canônico foi tomado como alvo novo.
Caso com Aguardo já passava, evidenciando a assimetria entre famílias.

Correção restrita em _validate_declared_player_actions: para espera explicitamente
declarada sem alvo, ignora somente o adjunto no/na mais o local canônico exato
de Você espera/aguarda, com fronteira ou enquanto; preserva offsets e todo verbo
posterior. Não libera outro destino, espera com alvo declarado, silêncio ou
imobilidade. Sem mudança de prompt, orçamento ou autoridade canônica.

Oito regressões novas: texto exato/ambas famílias, local diferente, alvo distinto,
ação posterior, silêncio e dois testes integrados R-03B. Duas falhas reproduzidas
antes da correção. 80 focados aprovados (inclui agência de espera/silêncio/custo).
Rejeição atômica/reinício/replay sem geração/RNG adicional verificados.
XML eval-results/hyp-007-l24-correction-2026-10-18.xml. Live não reclassificado.

## Preparação e limite restante

L25 separado/fechado, mesmo v6/alvo/limites/22 hashes. 149 testes aprovados,
incluindo preparação, integração e suíte do diretor de cenas; um aviso
preexistente python_multipart. XML eval-results/hyp-007-l25-readiness-2026-10-18.xml.
Preflight 17 sintéticos/zero chamadas, máximo 14.457 bytes, AST válido.
Suíte integral não executada; verificação ampliada relacionada, não release gate.
Gate L24 fechado, trava/artefatos mantidos. L23 aceito; MVP/TASK-013/CAMP-24 abertos.

Proposta: L24 inconclusivo integral/um percurso completo e L25 até 17 chamadas/
USD 0,15 estimados adicionais, Luna low/v6/768 tokens/20.000 bytes/60s,
sem retry/fallback/admissão. Continue/prossiga aprova ambos. Até lá gate L25
fechado, sem terminal/chave/inferência; não transferir slots/orçamento anteriores.
