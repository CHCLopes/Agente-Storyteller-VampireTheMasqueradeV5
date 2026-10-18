# Ponte local da direção B — concluída em 07/09/2026

A entrada interna optativa `execute_source_turn` agora liga resposta n/q, fonte atribuída, commit e recuperação. Três turnos autorados passaram pelo fluxo com FakeLLMAdapter e SQLite temporário, incluindo reinício entre turnos. O primeiro n tem mais de 600 caracteres e foi preservado integralmente. A pergunta ficou separada, e os dois turnos seguintes receberam as fontes anteriores na seção atribuída. A novidade narrativa não foi convertida em fato ou memória canônica.

## Contrato e comportamento implementados

O protocolo é `narrative-source-turn-v1`, com operação `H6.narrative_source`, perfil `narrative-source-application-v1` e contexto `narrative-source-application-context-v1`. O perfil experimental permanece congelado. Uma comparação AST confirmou os mesmos algoritmos e validadores, descontando apenas docstrings e as três mudanças declaradas de identidade/metadado.

A reserva servidor da tentativa registra a obrigação B e a invocação esperada antes da geração. O envelope conserva fonte integral, pergunta, identidades, referências a eventos, hash de apresentação e hash de auditoria. O agregado é validado antes de `on_chunk` e novamente no commit. Remover argumento e envelope não dispensa a obrigação persistida.

`commit_turn` mantém o padrão v1 quando não há obrigação B. A nova leitura seleciona os últimos até dois turnos comprometidos antes de conferir compatibilidade, devolve fontes cronologicamente e recusa dependência legada incompatível ou audiência não permitida. Nenhuma tabela, DDL, schema global ou migração foi criada. O diff da persistência contra a fotografia anterior à ponte tem 193 adições e uma remoção.

A entrada exige cena conhecida com l/p e campos compactos vazios, contexto do chamador vazio e antecedentes com tipos enumerados pelo contrato. O USER final, incluindo fatos e entrada, tem teto de 12.000 caracteres, distinto do orçamento do experimento; excessos são recusados antes do gateway, sem corte. O alvo, o gateway, o SYSTEM, os parâmetros e o deadline são explícitos.

Replay concluído confere tentativa/turno/auditoria e retorna sem nova geração ou entrega. Cancelamento durante o commit aguarda o resultado: um commit que venceu permanece concluído; se perdeu, a tentativa é auditada como cancelada. O callback continua provisório até o commit.

## Verificação

| Superfície | Casos distintos aprovados | Evidência |
|---|---:|---|
| Envelope e fronteira de identidade/autoridade | 85 | Rodada final após cinco contraprovas de normalização silenciosa de IDs. |
| Persistência B | 29 | 25 casos iniciais e quatro contraprovas adicionais de replay. |
| Compatibilidade da persistência existente | 7 | Commit, idempotência, coerência, rollback, concorrência e CAS. |
| Integração de aplicação | 31 | Três turnos, reinício, política, orçamento, replay, mutação do chamador e dois resultados de cancelamento durante commit. |

São **152 cenários distintos** nas rodadas focadas deste incremento, sem somar repetições. Não são uma execução única da suíte completa. A rodada integrada final passou em 3,32 s com hashes estáveis; o único aviso foi a depreciação prévia de `python_multipart`. A evidência JSON vinculada preserva comandos, estágios e hashes: 85 substitui a rodada inicial de 80; a única falha inicial da persistência era uma fixture de 584 caracteres, corrigida isoladamente; os quatro RED do replay foram corrigidos com cinco controles focados, incluindo um positivo já contado.

Os controles integrados incluem uma saída dentro de 1.600 caracteres mas acima de 150 palavras, recusada por `scene_narrative_too_long`. Portanto, a prova local não afrouxa o limite que recusou o Pátio. Também verifica schema, agência, sigilo, pergunta, resultado mecânico, cena/contexto incompatíveis, tipos de antecedentes, orçamento completo, pares adulterados e ausência de chamada oculta no replay.

Conftest manteve o bloqueio de rede; ambiente de teste com dotenv desativado, adaptador falso e banco temporário. Nenhuma chamada externa, credencial ou campanha real foi usada nesta ponte. `git diff --check` passou; os módulos legados enumerados no JSON mantiveram os hashes anteriores à ponte. Revisões cruzadas localizaram e fecharam as falhas de literalidade e pareamento de replay.

## Limites da conclusão

`source_only/not_assessed` conserva origem textual; não afirma verdade geral, qualidade narrativa, implicação semântica ou autenticação independente do provedor. O servidor ainda responde pela origem de rascunho, fatos, estado e cena fornecidos. Um save v1 arbitrário não ganhou adaptador de origem nem aprovação B.

O getter de fontes faz uma leitura SQLite consistente. O replay do serviço usa leitores públicos separados; não promete uma única fotografia entre eles. O pareamento de hashes armazenados não recompõe o digest histórico completo, pois nem todas as entradas originais são persistidas separadamente. A entrega de bytes e o commit também não são atomicamente reversíveis. Não há rolagem adicional no fluxo testado nem garantia de rollback global do PRNG.

Esta ponte cobre cena conhecida e até duas fontes anteriores. Abertura, progressão canônica livre, histórico longo, lore, consultas diretas e ativação dos leitores de campanha permanecem fora deste incremento. Default, frontend, composition root e saves reais continuam sem ativação B; CAP-001 não foi aprovado.

O Estufa segue encerrado com rejeição de q e skip dependente. O Pátio segue encerrado com uma fonte passada integralmente ao segundo USER e segunda saída recusada por 155 palavras. Os quatro brutos desses lotes conservaram os hashes; nenhum resultado foi repetido ou reclassificado.

## Artefatos

- [Prova estruturada, hashes e comandos](narrative-source-local-bridge-2026-09-07.json).
- [Plano concluído da ponte](../../../plan/architecture-narrative-source-bridge-1.md).
- [Desenho de integração mais amplo, com limites e leitores restantes](../reviews/narrative-source-integration-design-2026-09-07.md).
- [Observação do Pátio encerrada](narrative-source-courtyard-observation-f6483710-2026-09-07.md).

A autorização contínua para preparação técnica local e observações necessárias está preservada. Não há lote, janela nova ou chave pendente neste fechamento.
