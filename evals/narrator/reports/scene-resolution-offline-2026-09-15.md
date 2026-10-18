# Avaliação offline do resolvedor de cena — 15/09/2026

## Escopo

O corpus congelado `scene_resolution_offline_v1.json` contém quatro casos
sintéticos autorados. O avaliador compara beat, proposta narrativa e projeção de
estado usando os validadores de produção. Não usa provedor, banco, relógio,
aleatoriedade ou dados de campanha.

## Resultado

Os quatro casos passaram. Diálogo e espera produziram mudança observável, mantiveram
local, NPC e agência, abriram as pendências vinculadas e projetaram a revisão
seguinte. A contraprova que omitiu a pendência foi recusada com
`scene_beat_open_thread_omitted`; a que fez o jogador agir durante uma espera foi
recusada com `scene_player_agency_violation`.

Os cinco gates — causalidade, agência, atribuição, progressão e não contradição —
foram satisfeitos no corpus. A regressão integrada posterior aprovou **273 testes**,
zero falhas e uma advertência preexistente de depreciação do `python_multipart`.

## Consequência para o plano

TASK-016 e TASK-017 estão concluídas. A avaliação não revelou uma pergunta
discriminante nova para modelos; portanto a condição de TASK-018 não foi atendida
e nenhuma inferência adicional foi aberta. TASK-019 continua sendo o gate humano
separado para ativar o resolvedor no fluxo padrão.

Este resultado não escolhe modelo, não aprova campanha, runtime ou CAP-001 e não
ativa a ponte opt-in.
