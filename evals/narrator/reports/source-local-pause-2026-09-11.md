# Pausa solicitada — composição técnica local B

Trabalho pausado por solicitação do usuário em 11/09/2026, durante a inspeção
visual da fixture sintética 03be3183-3d49-4bc1-a042-6f94059e1336. Nenhum novo teste
ou investigação foi iniciado após a pausa. Agentes interrompidos; Vite encerrado
por q (exit0) e fixture encerrada por Ctrl+C (exit1). Conferência das portas5178
e8018 após encerramento não encontrou listeners. Não foram alteradas credenciais.

## Entregas verificadas antes da pausa

Backend inativo arquivado com280casos distintos aprovados (89 leitor,25factory,
37handler,129regressões). View/protocolo tiveram95+1casos em etapas; hook/entrada,
52casos distintos, lint, TypeScript e build isolado aprovados. Fixture própria:
25testes verdes. As falhas iniciais de fixtures, lint/tipagem/invocação permanecem
nas evidências. Contagens de testes não significam validação de campanha ou modelo.

O comparativo61b83a2f continua encerrado sem candidato qualificado. Correção
prospectiva de agência e seus1.097testes permanecem documentados separadamente.
Seis artefatos brutos e53cópias do comparativo novamente íntegros por hash.
Depois daquele lote não houve chamadas externas: esta composição usa FakeLLM.

## Observação no navegador e delta pendente

A prévia conectou e apresentou o briefing. Um envio explícito de diálogo passou
por ação preparada até narrativa confirmada com n/q. A captura após desligamento
confirma uma campanha, um turno e P/K/H completos, sem operações pending/failed.
O save do jogo atual não foi usado. O helper lê snapshot lógico em mode=ro e BEGIN;
não confunde hash físico com WAL ativo nem H com contagem de chamadas do provedor.

No viewport475x648 a página continuou com648px de altura. O log tinha151px úteis,
657px de conteúdo e scrollTop506. Porém o estado da ação estava entre y486e506,
fora do aside, que terminava em y345,09. A correção separa a rolagem da introdução
do estado fixo, preservando lógica, IDs e textos. View e teste foram alterados,
mas a pausa ocorreu antes de revisão final/teste focal/lint/tsc/inspeção visual
desse delta. Não declarar o ajuste corrigido ou a UI concluída ainda.

Não houve segunda ação, consulta/reconexão comparada no browser, teste desktop
ou reload. Os testes anteriores cobrem essas semânticas em outros níveis, mas a
composição visual permanece incompleta. Nenhum override de viewport foi aplicado.

## Falha observada no encerramento

Ao encerrar a fixture, o servidor real reportou RuntimeError em
api/narrative_source_local_app.py:55: envio de websocket.close após fechamento
ou resposta já concluída. A factory testa application_state antes de fechar;
a relação com o estado de desconexão do cliente é hipótese para a investigação.
O launcher registrou failed e saiu1. Não reclassificar esse encerramento como
limpo nem confundi-lo com perda do turno, que foi conferido persistido.
Nenhuma correção ou novo teste desse erro foi iniciado devido à pausa.

## Retomada

Primeiro reproduzir o fechamento duplicado no servidor ASGI e corrigir com prova
focada. Depois concluir a revisão e checagens do delta visual e abrir uma fixture
nova para navegador estreito/desktop, consultas e reconexão sem novos turnos.
O script recusa reutilizar o run anterior: preservar esse banco como evidência.
Não iniciar chamadas de modelo automaticamente só por retomar estes testes locais.

Evidências preservadas em eval-results/checkpoints/source-local-pause-20260911/.
O JSON contém hashes das fontes atuais, marcos do navegador, lifecycle e cópias.
Planos de produto, default, modelo e CAP-001 não foram promovidos.
