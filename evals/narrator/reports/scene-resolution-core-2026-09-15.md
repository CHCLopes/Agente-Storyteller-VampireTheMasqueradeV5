# Núcleo determinístico de resolução de cena — 15/09/2026

As decisões DEC-RES-001 a DEC-RES-005 foram aprovadas e as fases 0, 1, 2 e 3 do
plano `architecture-scene-resolution-1.md` foram concluídas localmente. Nenhuma
chamada ao provedor, rolagem de teste, alteração de default ou ativação de produto
ocorreu.

## Entrega

`api/scene_resolution_service.py` define entrada, perfil mínimo de NPC, opções
autoradas, resultado imutável, adaptação da mecânica já encerrada, seleção por
prioridade/ID e verificação por hashes. O módulo não chama LLM, não persiste, não
muta estado e não importa `random`.

`api/scene_resolution_integration.py` é uma ponte explicitamente opt-in. Ela
anexa um fato provisório `world.scene.beat_resolution` com visibilidade
`storyteller`, projeta somente diretivas necessárias no pacote H6 e devolve novo
`TurnPipelineResult`; o objeto recebido permanece inalterado. O caminho padrão não
importa nem chama essa ponte.

`validate_scene_continuation` aceita `scene_beat` opcional. Quando fornecido,
confere resultado, pendências, transição, mudança observável, ação estruturada de
NPC e restrições exatas. Quando ausente, a chamada e o comportamento anteriores
permanecem válidos. A instrução vinculante fica no pacote do turno, sem ampliar o
SYSTEM H6 que possui teto contratual de 400 palavras.

## Verificação

A primeira suíte focal do núcleo passou com 23 casos. Após os adaptadores, a suíte
de núcleo e regressões passou com 151. A ponte elevou o conjunto a 162. Uma primeira
execução com pipeline encontrou somente o teto do SYSTEM, pois a instrução havia
sido duplicada no prompt: 226 passaram e um falhou. A duplicação foi removida.

A rodada posterior aprovou 227 casos. A rodada final ampliada, incluindo direção
de cena, modelos de turno, admissão B, pipeline, executor transacional e WebSocket,
aprovou **272 casos distintos**, com uma advertência preexistente de depreciação
do `python_multipart`. Não somar as reexecuções como casos adicionais.

Na fase transacional, o executor valida a identidade do beat provisório antes da
chamada narrativa, persiste o recibo no mesmo `commit_turn` e o reidrata em replay
terminal. Um teste de contradição entre proposta e pendência obrigatória confirmou
rollback: turno, eventos e avanço de revisão permaneceram ausentes. A chamada
idempotente do caso aprovado manteve um único acesso ao adaptador.

## Limites

Não existe catálogo canônico de consequências nem ativação automática. A ponte
exige que uma camada confiável forneça perfis e opções estruturados. A ponte ainda
não é chamada pelo caminho padrão; quando usada, o executor persiste e reidrata o
recibo. Correspondência livre entre
prosa e causalidade continua parcialmente semântica: a validação atual cobre os
campos estruturados exatos e não afirma compreender toda paráfrase.

Modelo, campanha, CAP-001, pesos, escala numérica, aleatoriedade adicional,
catálogo de consequências, UI e ficha do jogador permanecem fora desta entrega.
