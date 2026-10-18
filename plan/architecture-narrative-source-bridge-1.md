---
goal: Implementar ponte interna optativa de fonte narrativa com commit e recuperação local
version: 1.0
date_created: 2026-09-07
last_updated: 2026-09-07
owner: Codex
status: 'Completed'
tags: [architecture, narrative, grounding, persistence]
---

# Introduction

A direção B aprovada agora tem uma ponte interna verificada entre resposta n/q, fonte atribuída, turno comprometido e recuperação após reinício. A passagem real da primeira fonte ao segundo USER foi observada no Pátio; a segunda resposta excedeu o limite e não foi admitida. A prova local abaixo não reclassifica esse resultado e não representa confiabilidade de campanha.

Este incremento usa somente FakeLLMAdapter, dados autorados e SQLite temporário. Nenhuma nova chamada, credencial, prompt ao vivo, DDL, save real, default ou rota do produto será ativada. A ponte é entrada interna explícita. Os chamadores atuais continuam v1; nenhuma seleção automática por shape da resposta.

## 1. Requirements & Constraints

- REQ-001: Protocolo integrado narrative-source-turn-v1; operação H6.narrative_source; perfil de aplicação narrative-source-application-v1 e contexto narrative-source-application-context-v1. Originais experimentais permanecem congelados. Não importar scripts em módulos de aplicação.
- REQ-002: Envelope guarda operation_id, attempt_id, narrative_id, question, projection integral, source_event_ids únicos/ordenados, presentation_sha256, invocation_operation e provenance_sha256. Não duplicar n nem derivar fatos do texto. Fonte tem SOURCE_ONLY/not_assessed.
- REQ-003: start_attempt prévio ancora narrative_contract, expected_invocation_id e expected_invocation_operation antes da geração. IDs vêm do servidor e são estáveis para replay. A mesma tentativa não pode perder essa obrigação removendo argumento e envelope.
- REQ-004: commit_turn acrescenta kw-only narrative_contract=None; ausência de obrigação B preserva v1. B exige marcador, argumento e envelope coerentes antes de transação/retorno idempotente. O context JSON com envelope entra no digest existente; sem DDL/global schema bump.
- REQ-005: Revalidar fonte/política/narrativa n+duas quebras+q/audiência/identidades/eventos e exatamente uma invocação H6 correspondente concluída sem erro. Eventos são antecedentes, não prova semântica geral. Coleções de MemoryCandidate/EpisodicMemory vazias por contrato, com fonte obrigatória.
- REQ-006: Validar o agregado antes de on_chunk e repetir na persistência. Erro não deixa turno/fonte recuperável nem publica estado. Chunk é provisório até commit; falha posterior não permite prometer remover bytes já entregues.
- REQ-007: Recuperar os últimos até2 turnos comprometidos em ordem cronológica, sem filtrar B antes de selecionar. Histórico legado incompatível, audiência não autorizada ou vínculo inválido exigido devem ser recusados, não omitidos silenciosamente. Não alimentar CONHECIDO/cena quente/consolidação v1.
- REQ-008: O perfil é restrito a cena conhecida e l/p, campos compactos vazios; n40..1600, q3..200, política completa30..150palavras e pergunta aberta. Manter n acima de600 sem corte ou cópia para resumo. Nenhum ajuste para admitir Pátio.
- REQ-009: Na entrada de aplicação, medir o USER JSON final completo (contexto, entrada do jogador, ID de turno e fatos) contra teto explícito de 12.000 caracteres; recusar antes do gateway, sem corte. Esse teto de aplicação não é uma estimativa de tokens nem altera o orçamento do piloto histórico.
- REQ-010: Antes da chamada, restringir antecedentes aos quatro tipos de fato e três tipos de evento enumerados pelo contrato. Cena livre/world.scene e player_scene_query não são elegíveis nesta ponte. Replay concluído deve conferir o pareamento terminal de tentativa/turno/auditoria antes de retornar.
- CON-001: Origem do rascunho e dos fatos tipados é responsabilidade do servidor. A ponte preserva os antecedentes determinísticos do rascunho e não chama _admit_scene_continuation/project_scene. Sem regra para afirmação canônica livre, ela permanece indeterminada.
- CON-002: A conferência do digest armazenado turn==attempt e a revalidação tipada não equivalem à recomputação integral do payload histórico: bases de commit não estão todas armazenadas como colunas. Não prometer essa recomputação, autenticação criptográfica ou rollback do PRNG global.

## 2. Implementation Steps

### Implementation Phase 1

- GOAL-001: Perfil e envelope independentes, sem mudança do caminho legado.

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-001 | Registrar interfaces/limites deste plano antes da edição; encerrar Pátio e preservar seus hashes. | Sim | 2026-09-07 |
| TASK-002 | Root: novo api/narrative_source_profile.py, adaptação explícita do perfil experimental congelado para política/versão de aplicação. | Sim | 2026-09-07 |
| TASK-003 | Socrates: api/narrative_source_turn.py com NarrativeSourceTurnEnvelope, factory create_source_turn_envelope e validate_source_turn_commit; testes próprios de identidade/autoridade/pareamento. Depende de002. | Sim | 2026-09-07 |

### Implementation Phase 2

- GOAL-002: Persistir e recuperar fonte sem tabelas novas nem promoção episódica.

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-004 | Peirce: argumento optativo no commit, obrigação na tentativa, guarda antes de replay, novo get_recent_narrative_source_turns(session_id,limit=2,allowed_visibilities=('public','player')). Validar exatamente a assinatura pura alinhada. | Sim | 2026-09-07 |
| TASK-005 | Peirce: tests/test_narrative_source_persistence.py; positivo, marcador/envelope ausentes, auditoria/IDs/audiência, replay/digest/rollback e legado. Preservar antigos testes de persistência. | Sim | 2026-09-07 |

### Implementation Phase 3

- GOAL-003: Entrada interna completa e prova local de três turnos, com reinício.

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-006 | Popper: api/narrative_source_execution_service.py, entrada explícita com rascunho servidor/cena/l/estado, invocação pré-ancorada, recuperação tipada e agregado antes da entrega. Sem novo gateway/default ou import de evaluator. | Sim | 2026-09-07 |
| TASK-007 | Root: tests/test_narrative_source_bridge.py com3 respostas FakeLLM autoradas, SQLiteTemp/reinício, fonte>600, q separado, nenhuma memória/fato ficcional novo, gates antes chunk, callback/cancelamento/CAS/replay sem nova chamada ou RNG. | Sim | 2026-09-07 |
| TASK-008 | Revisão cruzada, testes focados pertinentes e comparação do diff com baseline anterior. Registrar prova e atualizar estado. Serviços de leitor geral/default/save continuam fora desta ponte. | Sim | 2026-09-07 |

## 3. Alternatives

- ALT-001: Envelope no context JSON selecionado por obrigação servidor — adotado para esta prova; digest/transação existentes, sem DDL.
- ALT-002: Reutilizar MemoryCandidate/EpisodicMemory ou confirmar por presença da proposta — recusado; mistura autoridade da fonte com resumo.
- ALT-003: Importar scripts do experimento em runtime ou alterar seus fingerprints para a aplicação — recusado; módulo de aplicação tem versão própria, original congelado.
- ALT-004: Ativar frontend/H6/default/save e adaptar todos os leitores nesta primeira prova — fora de escopo; dependerá dos resultados locais e do desenho de integração completo.

## 4. Dependencies

- DEP-001: APIs existentes de rascunho, invocação, auditoria, tentativas, SQLite e política narrativa; nenhum pacote novo.
- DEP-002: Contrato puro de source/binding/assessment já verificado. Cópia integral não autentica o chamador nem afirma verdade de mundo.
- DEP-003: Fixture de cena/rascunho fornecida pelo harness como dado servidor. Save v1 arbitrário não ganha elegibilidade B.

## 5. Files

Novos: api/narrative_source_profile.py, api/narrative_source_turn.py, api/narrative_source_execution_service.py e seus testes delimitados. Existente modificado: api/persistence.py, apenas obrigação optativa B/recuperação. Documentos correlatos: este plano, relatório da ponte, retomada e README. Não editar fontes de experimentos encerrados.

## 6. Testing

- TEST-001:3 turnos com FakeLLM e banco temporário, restart e fontes integrais no2º/3ºUSER, q separado e sem CONHECIDO.
- TEST-002: Trocas de identidade/texto/q/auditoria/protocolo/visibilidade e remoção da obrigação falham antes de entrega ou commit, sem promover fonte inválida.
- TEST-003: Recusa estrutural/narrativa/agência/sigilo/mecânica não entrega chunk; callback/cancelamento/CAS falham sem snapshot novo. Sem rolagem adicional ou rerrolagem.
- TEST-004: Replay terminal não chama LLM; metadados diferentes com mesma operação conflitam. Envelope no digest, pareamento com tentativa e restauração tipada verificados.
- TEST-005: Legado sem obrigação B mantém comportamento; referência B ilegível não entra pelo ramo v1; cenas compactas ricas/inexistentes e fontes incompatíveis falham antes da chamada.
- TEST-006: n601..1600 preservado sem entrar em summary; budgets/refusals explícitos. Novas coleções episódicas/canônicas derivadas do texto são recusadas.
- TEST-007: Revisão independente e uma rodada focada por superfície congelada; repetir somente por correção/falha/risco novo. Conftest mantém bloqueio de rede externa e dotenv desativado.

## 7. Risks & Assumptions

Fonte narrativa pode ser repetitiva/contraditória mesmo quando íntegra. O perfil não resolve progressão canônica geral, abertura, novos NPCs, lore, histórico longo ou todos os leitores v1. Não declarar integração de campanha concluída ao fechar esta ponte. O servidor continua responsável por origem do rascunho; etiquetas e hashes não substituem essa confiança. O retorno de chunk e SQLite não são atomicamente reversíveis.

## 8. Related Specifications / Further Reading

- [Direção B e plano inicial](architecture-narrative-grounding-1.md)
- [Desenho de integração e rotas restantes](../evals/narrator/reviews/narrative-source-integration-design-2026-09-07.md)
- [Pátio encerrado](../evals/narrator/reports/narrative-source-courtyard-observation-f6483710-2026-09-07.md)

Fechamento: 85 casos de contrato, 29 de persistência B, 7 legados e 31 integrados passaram em rodadas focadas, com hashes e correções preservados no [relatório da ponte](../evals/narrator/reports/narrative-source-local-bridge-2026-09-07.md). Nenhuma ativação do produto ou alegação de verdade semântica geral.
