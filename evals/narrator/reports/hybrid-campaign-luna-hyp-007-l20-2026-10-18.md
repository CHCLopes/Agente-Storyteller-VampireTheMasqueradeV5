# HYP-007-L20 — salvamento concluído; campanha integral inconclusiva

Batch 685a737d-81de-414e-9a8e-c1bb0f9b4f56, 18/10/2026. Mesmo Luna low/v5,
17 chamadas máximas/USD 0,15 estimados; sem retry/fallback/admissão automática.

## Observação e custo final

Três chamadas, dois turnos concluídos. CAMP-EVAL-01 concluído com registro
intacto e q terminal vazio. CAMP-EVAL-02 parou em R-03/turno 1 com
campaign_source_policy_failed. Demais percursos não alcançados. O HTTP 429
não se repetiu: três respostas com uso reportado; isto não prova disponibilidade
futura nem ausência de outros limites. Remoção do limite anterior USD 0,05 foi
informada pelo humano, não extraída do registro L19.

Custo final estimado USD 0,0023168, não cobrança confirmada; 7.960 tokens entrada,
604 saída, três chamadas precificadas, nenhuma sem usage. Reporter --settled
reproduzido. Sem tarifas, impostos ou ajustes de cache.

Diretório: eval-results/hybrid-campaign-luna-l20-685a737d-81de-414e-9a8e-c1bb0f9b4f56/.

- records.jsonl SHA256: 103a4343588f25b295666f83dd028a02268acd83203beffbb82933d53a81fb87
- summary.json SHA256: b91bcc4c38257515653207c11236a0d1c330e3a9a1c9ab28ec12429b480d5b2a
- Manifesto fechado SHA256: 27a98bc018ff7c59292ab6a35d39a9f884ba76532593b0f833fedd2f6a7a61bd

Gate paid/live fechado; trava única e artefatos preservados. Não repetir L20.

## Diagnóstico e correção local

Reprodução exata retornou scene_player_agency_violation, undeclared_player_action,
subject voce, clause_index 0, unauthorized_concepts move. Na frase
“Enquanto você aguarda, a infiltração se espalha pelas paredes do Arquivo,
aproximando-se da bancada baixa”, quem se aproxima é a infiltração, não o jogador.
Correção restrita em _action_signature_matches ignora apenas o gerúndio com
esse sujeito ambiental/predicado/destino explícitos. Não isenta verbos seguintes.
Nenhuma alteração de prompt, orçamento, contrato ou autoridade canônica.

Nove regressões novas: caso exato, seis contraprovas de troca de ator/ação
posterior, dois casos integrados de commit/rejeição atômica e reinício/replay
sem RNG ou geração adicional. 39 testes focados aprovados, um aviso preexistente;
eval-results/hyp-007-l20-correction-2026-10-18.xml. Não reclassificar resposta live.

## Preparação e limite restante

L21 separado/fechado, mesmo v5/alvo/limites, 22 hashes atualizados somente para
novo lote/correção. 34 testes focados aprovados/um aviso preexistente;
eval-results/hyp-007-l21-readiness-2026-10-18.xml. CLI sintético e AST aprovados,
zero chamadas ao provedor na preparação. Nenhum narrador admitido.
Suíte integral não repetida; verificações limitadas à correção e integração.

Proposta: aceitar L20 como campanha integral inconclusiva, um percurso completo,
e autorizar L21 até 17 chamadas/USD 0,15 estimados adicionais, 768 tokens,
20.000 bytes/60s, sem retry/fallback/admissão. Continue/prossiga aprova esta
proposta delimitada. Novo terminal/chave apenas após autorização; nenhuma
autorização anterior ou slot não usado foi transferido para L21.
