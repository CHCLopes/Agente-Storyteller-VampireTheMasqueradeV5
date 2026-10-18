---
goal: Corrigir atribuição indevida de espera ao jogador após percepção de NPC
date_created: 2026-09-12
status: 'Completed (offline correction and integration verified)'
---

# Sujeito da espera no diálogo

O lote87e187bb está encerrado e congelado: dois HTTP, um commit e T2 recusado.
A auditoria passou70/70; 14 observações locais reproduziram o falso positivo.
O objeto você em observando você foi tratado como sujeito de esperando (Mara)
e permanece (explicação). A pergunta q e os aliases corretos não causam a falha.
Provas: ../evals/narrator/reports/source-dialogue-continuity-observation-87e187bb-2026-09-12.md.
Checkpoint anterior à correção: manifest SHA
14ec252d78315976047649c765a21825545ca6bdc2c3eaf44e575be42d307fe0, 69 cópias.

## Escopo autorizado

Correção local reversível no caminho de atribuição do observador NPC em
api/scene_director_service.py, com testes focais próprios e verificação das
superfícies de política afetadas. Manter os padrões de ação e as autorizações,
o rastreador pronominal geral, limites n/q, prompts/modelos, persistência e UI.
Não modificar avaliadores, lançadores, testes ou artefatos históricos para
reclassificar o lote. Não reutilizar sua sessão nem fazer novas inferências.

Decidir por ocorrência de verbo, preservando offsets e todos os demais matches.
Reconhecer percepção com jogador como objeto quando o NPC é sujeito nominal ou
pronome com antecedente local inequívoco fora de fala. Última menção de alias,
roster isolado, nome citado ou objeto não bastam. Colisão de aliases invalida
a inferência. Aspas delimitam autoria sem transformar fala em declaração.

O gerúndio de espera coordenado à percepção, separado por vírgula, conserva o
sujeito do observador. O predicado permanece em interrogativa indireta para
ver se ... ou se ... deve ter sujeito textual não pessoal explicitamente
identificado, sem propagar a referência corporal, posse do jogador ou novo
sujeito. Não isentar toda a cauda nem usar o texto87 como whitelist.

## Execução e aceitação local

1. Preservar o vermelho integral n/q87, sem editar prosa/fatos/aliases.
2. Preparar delta e contraprovas, revisar antes de aplicar ao core.
3. Exigir admissão integral do caso real e variantes estritamente pertinentes.
   Conservar recusas para jogador como sujeito, relativa, novo jogador, coerção,
   gerúndio ambíguo sem vírgula, antecedente apenas citado/objeto, alias em
   colisão, sujeito corporal/possessivo e ação posterior não declarada.
   Recusas conservadoras herdadas não são prova de violação semântica em toda
   hipótese ou desejo expresso por NPC; registrar os limites com precisão.
4. Verificar regressões existentes de NPC objeto/Mara holding e o recorte de
   agência afetado. Ampliar somente conforme o risco do delta ou falhas reais.
5. Exercitar n/q capturados no fluxo P/K/H em SQLite sintético NOVO, sem rede,
   com fonte T1 em T2, dois commits e replay sem produção; isso é contraprova
   local sobre a correção, não nova execução do provedor ou sucesso retroativo.
6. Revisão independente, hashes, relatório e atualização da retomada. Somente
   então definir a próxima necessidade de produto/observação com base na
   evidência existente; não abrir automaticamente outro lote idêntico.

Se a regra exigir interpretação arbitrária ou liberalização dos controles,
manter o resultado conservador e registrar a limitação antes de ampliar escopo.
Esta correção não aprova modelo, runtime padrão, campanha ou CAP-001.

Concluído localmente; ver ../evals/narrator/reports/source-dialogue-observer-correction-2026-09-12.md.
A observação87 conserva um único commit e a recusa original.
