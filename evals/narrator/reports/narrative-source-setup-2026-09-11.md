# Setup e introdução autorada da direção B — 11/09/2026

Incremento interno concluído: pedido público estrito, manifesto autorado ligado
à origem, criação atômica e consulta somente leitura, com composição até H6 via
produtor real. O manifesto não produz turno, fonte, invocação ou ação automática.
Nenhuma rota, frontend, default ou save do jogo atual foi alterado.

## Implementação e comportamento

`SourceSetupRequest` recebe local, elenco e objetivo declarado. Identidade, ficha,
relações e configuração pertencem ao servidor. `create_source_trial_setup` grava
origem e manifesto juntos em banco previamente inicializado; qualquer sessão
existente ou linha órfã da mesma sessão é recusada. Falha reverte o INSERT.
`read_source_setup_manifest` usa mode=ro e uma transação, confere história/origem
e reapresenta a mesma preparação após reinício e avanço narrativo.

O primeiro pacote H6 contém o objetivo apenas quando a ação sintética escolhida
o inclui. A introdução não é convertida em fonte. Conversa, espera e investigação
com sucesso/falha usam os serviços reais e respostas FakeLLM autoradas. Replay
antigo após novo turno preserva cápsula/fonte sem produção, RNG ou chamada nova.

## Verificação

| Etapa | Aprovados | Novos | Evidência |
|---|---:|---:|---|
| models | 210 | 121 | [JUnit](C:/Users/skate/AppData/Local/Temp/storyteller-source-setup-tests-20260911/setup-context.xml) |
| persistence | 270 | 55 | [JUnit](C:/Users/skate/AppData/Local/Temp/storyteller-source-setup-persistence-20260911/run1.xml) |
| composition | 8 | 8 | [JUnit](C:/Users/skate/AppData/Local/Temp/storyteller-source-setup-flow-tests-20260911-run2/flow.xml) |

São **488 casos distintos aprovados**, incluindo **184 novos** e 304 regressões.
Modelos e persistência passaram na primeira rodada. A primeira composição teve
4 falhas e 3 aprovações; os logs foram preservados. A causa foi a omissão de
`npc_aliases=("Mara",)` na configuração sintética: elenco da cena não preenche
automaticamente os aliases do validador. O diagnóstico com texto idêntico confirmou
recusa por pronome ambíguo sem alias e admissão com alias. Corrigido apenas o
chamador sintético, acrescentada contraprova e refeitos os oito casos afetados:
**8 passed em 4,10s**. Não se alterou texto da resposta, SYSTEM, corpus histórico
ou política para obter aprovação.

Rodadas com dotenv desativado, conftest ativo, banco temporário e rede bloqueada.
Um aviso preexistente de python_multipart por rodada. Revisão independente antes
do freeze e encerrada. Auditoria confirma 110 funções anteriores da persistência
intactas em AST e texto; schema preservado. Hashes e detalhes no
[relatório JSON](narrative-source-setup-2026-09-11.json).

## Limites e continuidade

Não houve chamada real. Estes testes não demonstram qualidade narrativa,
compreensão geral de linguagem, campanha completa ou aprovação CAP-001.
O perfil continua cena conhecida, elenco fixo e mecânica ordinária limitada.
Alias de NPC é configuração explícita do chamador, distinta do elenco de cena.
Bootstrap do banco é separado. O manifesto valida consistência, sem autenticar
autoria ou impedir todos os escritores genéricos de metadados preexistentes.

[Plano de transporte](../../../plan/feature-narrative-source-transport-1.md)
preparado sem ativação. Próxima etapa é o
[ensaio de diálogo e espera](../../../plan/feature-source-player-probe-1.md),
duas chamadas máximas com setup/produtor reais, revisão de experiência separada.
CAMP-01..24 e DEC-001/002/003 permanecem abertas. Checkout original preservado.
