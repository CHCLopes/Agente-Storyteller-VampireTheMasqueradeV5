# Evidência inline — prova offline concluída

O contrato experimental de resumo e questões abertas está implementado e revisado. **86 testes passaram em 1,56 s**, sem falhas ou skips; permanece a advertência preexistente de python_multipart. [Hashes e verificação](record-inline-evidence-offline-proof-d1b9a968-2026-09-07.json).

Texto, fontes e modalidade ficam juntos em cada segmento. A projeção concatena literalmente e calcula intervalos Unicode, sem copiar citações, contar offsets no modelo ou reparar texto. Os testes cobrem limites globais, fontes e tipos inválidos, instâncias forjadas, repetições, espaços, imutabilidade e ausência de imports de runtime/transporte. Uma contraprova mostra que um texto semanticamente falso pode continuar estruturalmente válido; fidelidade e cobertura permanecem não avaliadas.

Duas correções ocorreram antes de qualquer observação: recusa de sets/iteradores e ordem dos metadados Pydantic para expressar minItems/maxItems no array de segmentos por pergunta. A guarda Python já aplicava os limites; o schema emitido não os descrevia corretamente. Não há alegação de rejeição remota desse schema, pois ele nunca foi enviado. A revisão final e a inspeção do schema normalizado confirmaram a correção. Os 23 fingerprints históricos conferidos permaneceram iguais.

Esta prova não implementa oito campos, atores, admissão de cena ou memória de produto. A próxima preparação é uma única observação de caso novo, com identidade e critérios próprios, conforme o [desenho](record-inline-evidence-design-d1b9a968-2026-09-07.md). Nenhuma chamada externa foi feita nesta prova.
