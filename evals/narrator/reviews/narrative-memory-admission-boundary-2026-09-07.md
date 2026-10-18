# Narrativa → evento → memória: fronteira verificada

Auditoria local encerrada em 07/09/2026. O fluxo preserva referências, visibilidade e o conteúdo já admitido, mas não comprova todas as relações entre narrativa e resumo. Três controles autorados demonstraram o alcance dessa proteção, e um defeito estreito de classificação da origem foi corrigido. Nenhuma chamada real, dado de campanha ou aprovação de produto nesta auditoria.

## Resultado dos três controles

| Controle autorado | Resultado observado |
| --- | --- |
| Narrativa com “luminária de base azul”; resumo preserva base azul | Turno concluído, candidato aceito, evento/cena/memória com mesmo texto e recuperação em CONHECIDO. |
| Referência de evento inexistente | Validação direta rejeitou a referência; nenhuma memória adicional foi promovida. |
| Mesma narrativa; apenas resumo muda para “Uma luminária emite luz azul sobre o mapa dobrado na sala vazia.” | Turno concluído e candidato aceito; o resumo com cor atribuída à luz reaparece em CONHECIDO. A narrativa só atribui azul à base. |

Os controles fiel e infiel diferem apenas em `scene_summary`. Percorrem `execute_prepared_turn`, adaptador falso, SQLite temporário, recuperação e montagem reais do contexto. O controle de referência inválida atua diretamente na validação após um turno fiel, pois o schema do modelo não recebe IDs canônicos. Nenhum segundo turno/inferência foi chamado. **3 testes passaram em 1,21 s**, uma rodada, zero falhas/skips, zero rede; os 13 hashes de código/helpers/controle/runner permaneceram iguais. O aviso de assert rewriting do anyio decorre do carregamento do conftest no harness local.

Passar o controle de transferência caracteriza uma limitação; não aprova a transferência nem transforma esse texto autorado em resposta observada de modelo. Os seis resumos históricos permanecem no [corpus separado](record-summary-semantic-corpus-v1-2026-09-07.md), sem importação para runtime ou replay CAP.

## Rastreabilidade

| Etapa | Fonte e garantia | Limite |
| --- | --- | --- |
| Proposta e política | [scene_director_service.py](../../../api/scene_director_service.py), linhas 68, 844 e 2631: campos distintos, schema e verificações delimitadas de mecânica, agência, segredo, transição, NPCs, pergunta e pendências. | Não há prova geral de implicação entre n e s/f/t. |
| Projeção e evento | [scene_director_service.py](../../../api/scene_director_service.py), linha 1000; [turn_execution_service.py](../../../api/turn_execution_service.py), linhas 452 e 587: IDs/fontes do produto, s copiado para cena/evento, fatos visíveis para detalhes e segredo separado. | Origem e passagem pela política não comprovam equivalência narrativa–resumo. |
| Evento e candidato | [memory_service.py](../../../api/memory_service.py), linha 163: escolhe resumo explícito, canônico ou narrativa; copia fontes/metadados. O turno fornece s novamente, na linha 1122. | Na linha 1139 do turno, `semantic_grounding_confirmed=proposal is not None` sinaliza proposta admitida. |
| Validação e promoção | [memory_service.py](../../../api/memory_service.py), linhas 210 e 309: referências, cobertura narrativa, fatos, sessão/turno e visibilidade; só ACCEPTED promove. | A confirmação recebida do chamador não resulta de um confronto semântico geral neste helper. |
| Commit e recuperação | [persistence.py](../../../api/persistence.py), linhas 2092 e 2659: correspondência candidato/memória, fontes, commit e filtro/seleção; turno confirma o agregado na linha 1206. | Persistência fiel não corrige uma relação que já entrou no evento. |
| Contexto | [orchestrator_service.py](../../../api/orchestrator_service.py), linha 1125; [context_service.py](../../../api/context_service.py), linha 162; [scene_service.py](../../../api/scene_service.py), linha 111. | Summary vira content; cena contém resumo/detalhes/pendências, sem nova avaliação semântica. |

O requisito [REQ-015](../../../plan/architecture-llm-memory-turns-1.md) exige memória sem fatos novos e com fontes/visibilidade preservadas. [AC-IMP-005](../../../spec/spec-improvisational-scene-direction.md) exige que a próxima geração receba conteúdo admitido. O teste existente `test_turn_pipeline_integration.py`, linhas 1026–1043, verifica essa entrega; foi inspecionado, sem nova execução. A mesma especificação, linhas 148–149, reconhece o limite de qualidade semântica da admissão determinística. A auditoria localiza esse limite; não reclassifica todo o desenho como defeito recém-descoberto.

## Correção local concluída

Em `derive_memory_candidate`, `summary=""` com `event.summary=None` já selecionava a narrativa por fallback, mas a condição de origem só reconhecia `None`. Isso podia marcar o texto como DETERMINISTIC e dispensar o estado pendente exigido para proposta LLM.

A condição passou de `summary is None and event.summary is None` para `not summary and not event.summary`, acompanhando a mesma seleção já existente. Narrativa usada por ausência de resumo fica LLM/PENDING; resumo canônico existente conserva origem determinística; espaços em branco continuam recusados pela validação normal.

A regressão foi demonstrada antes da correção: None passou e vazio falhou exatamente na origem. Depois, **15 testes do módulo passaram em 0,33 s**, com um aviso preexistente de Starlette. Foram adicionados cinco cenários aos dez existentes. A produção mudou uma linha; testes 33 linhas adicionadas/duas removidas. `git diff --check` passou, e a revisão independente não encontrou achado material nem repetiu os testes. Não foi demonstrado alcance do argumento vazio nos chamadores normais de cena ou incidente em campanha.

O helper foi corrigido depois do lote faad. Fingerprints anteriores continuam históricos: não reescrever preparação ou brutos para apresentar o código novo como já usado naquelas observações.

## Evidência e próximo passo

[JSON durável](narrative-memory-admission-boundary-2026-09-07.json) incorpora resultados, hashes, fontes do harness, diff da correção e a auditoria final do corpus. As evidências originais de Temp permanecem identificadas e intactas. A cópia documental permite avaliar a prova mesmo se os arquivos temporários forem removidos posteriormente.

A hipótese de reformular SYSTEM está encerrada. O corpus e esta auditoria não justificam repetição para elevar taxa ou um classificador geral improvisado. A [proposta de decisão sobre a autoridade dos registros](narrative-memory-grounding-decision-2026-09-07.md) compara manter o comportamento atual em avaliação e revisar o contrato de canonização. Alterar esse contrato é uma decisão de produto/arquitetura distinta das correções locais já autorizadas. A chamada extra obrigatória continua rejeitada como padrão em ALT-004.

Nenhum novo lote ou chave está agendado. O trabalho local delimitado está concluído; a escolha de nova direção não foi convertida em decisão aprovada.
