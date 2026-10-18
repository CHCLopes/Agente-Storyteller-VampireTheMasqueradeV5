# Correções do primeiro uso teste — jogo atual

O usuário relatou falta de continuidade, ausência de introdução e narrativa expandindo
a página até tirar o HUD de vista. O escopo desta rodada foi corrigir o uso teste
atual, preservando sua sessão e a separação da direção B.

## Observação

O SQLite isolado continha 10 tentativas, 5 turnos concluídos e 5 falhas. Houve
9 invocações de H6; um cumprimento falhou antes do provedor porque os fatos
obrigatórios somavam 200 tokens estimados diante do orçamento192. As outras falhas
foram 3 `scene_player_prompt_not_actionable` e 1 `scene_thread_resolution_without_evidence`.
As saídas recusadas não estavam retidas; não há prova de falso positivo. Não foi
atingido um limite de respostas do teste. As cinco narrativas aceitas repetiam
pressão e silêncio, incluindo a ausência de resposta à pergunta sobre os NPCs.

## Correções

- Página limitada à janela; narrativa e ficha rolam internamente, com controles
  visíveis. Texto sem espaços quebra no painel; HUD móvel fechado não cobre Ficha.
- Terminais de falha deixam aviso idempotente, sem exibir saída rejeitada ou
  registrar sucesso. Hidratações preservam os itens locais já presentes.
- A criação da sessão apresenta local e presenças antes da primeira ação, sem
  inventar passado, encontro ou evento; não há inferência automática na abertura.
- Pedido de teste com só atributo pede a perícia. Erro de orçamento recebe código
  específico e mensagem fechada. O launcher agora configura768 para este teste;
  o limite global192 e os gates de agência, visibilidade e admissão permanecem.
- H6 recebe orientação para falas/mudanças concretas, resposta a perguntas relatadas,
  pergunta final simples e resolução de pendências sustentada em narrativa explícita.
  Isto é uma correção de orientação ainda sem prova de melhoria ao vivo.
- Retomada explícita mantém sessão e banco de origem em novo namespace de logs.
  Preflight verifica a sessão via SQLite read-only. TestId encerrado não é reutilizável;
  só preparação offline pode transitar para uma abertura. Nenhuma chave é recuperada.

## Verificação

99 cenários backend distintos passaram: rodadas88 e44 com33 casos em comum.
Frontend:25 testes de protocolo e5 de componentes. TypeScript/Vite passaram.
Sete verificações do launcher em processos reais usaram somente fixtures locais,
sem chave ou rede, e preservaram os bancos de origem. A revisão independente
identificou reutilização do ID de retomada; a guarda e contraprova foram aplicadas.

Com50 mensagens sintéticas, quatro janelas (1366×768,390×844,320×568,844×390)
mantiveram altura do documento igual à janela, rolagem interna, controles visíveis
e HUD acessível. O build servido é idêntico ao verificado visualmente. A aba do
usuário não foi recarregada, e nenhuma ação foi submetida pelo agente.

## Estado operacional

Servidor anterior PID23336 identificado por executável, comando, processo pai e
dono do socket; encerrado somente depois de conferir zero tentativas pendentes e
fazer snapshot consistente read-only. Seus5turnos/10tentativas foram preservados.
Janela antiga PID26144 pode continuar aberta com texto antigo; ela não indica o
estado atual. Nova janela protegida PID13828 aberta para a chave da retomada.

Novo run: `588b8d22-a985-42aa-80cc-63974c875353`.
Mesma sessão: `local.4cfd5337-1c84-487e-bd77-8fe8e4d78a29`.
Estado atual: `C:\Users\skate\AppData\Local\Temp\storyteller-manual-game-588b8d22-a985-42aa-80cc-63974c875353\status.json`.
No momento do registro: **awaiting_secure_credential**, sem servidor novo ainda.
O SQLite permanece na pasta original do teste. Consultar o status novo antes de agir.

## Limites e próximo passo

Melhoria narrativa exige observação subsequente; as falhas históricas não foram
reclassificadas ou reenviadas. Reload recupera narrativas comprometidas, mas ainda
não recupera entradas/erros locais ausentes do payload histórico. A introdução
aparece em novas sessões; retomar não reabre a história já jogada.

Usuário insere a chave somente no novo prompt protegido. Depois de readiness,
atualizar a mesma aba para carregar o frontend e continuar o uso teste. Não
reenviar ações pelo jogador nem avançar integração B antes do feedback do teste.

Provas, hashes e detalhes no JSON correspondente. Evidência operacional em
`Temp/storyteller-playtest-feedback-20260908`, revisão visual em
`Temp/storyteller-layout-scroll-20260908`, regressões locais em
`Temp/storyteller-manual-game-local-regressions-20260907` e protocolo em
`Temp/storyteller-narrative-protocol-playtest-20260907`.
