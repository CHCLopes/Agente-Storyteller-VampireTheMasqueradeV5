# Campanha B opt-in — integração e ensaio offline (29/09/2026)

Estado: implementação técnica offline verificada; aceitação de experiência e
ensaio Luna ainda pendentes. Nenhum narrador/default admitido. Nenhuma chamada a
provedor ou leitura de credencial foi feita neste incremento.

## Superfície implementada

- Origem B distinta da origem v1, estado de progressão versionado, histórico de
  duas fontes atribuídas e contexto fechado.
- Entrada P reivindicada em SQLite antes da classificação e do RNG; segundo
  gate de disponibilidade imediatamente antes da rolagem. Preparação K e
  conclusão P persistem juntas. Cápsula vincula entrada, recibo, beat, efeito,
  estado-base, parâmetros e rascunho à operação original.
- H reivindicado antes da geração, com nova operação explicitamente ligada à
  anterior em cada retomada. Falha deixa estado e fonte sem commit; replay
  terminal não repete RNG nem geração. O commit valida base, hash, fonte,
  proveniência, fatos, eventos e delta em `BEGIN IMMEDIATE`.
- Leitura por reconexão expõe status seguro; reconstrução do histórico rejeita
  adulteração de hash de H fracassado e do payload canônico do turno. O fluxo
  v1 não foi ativado para B e permanece separado.
- Ensaio HTTP isolado em `scripts/run_campaign_source_offline_trial.py`, com
  adaptador falso e `api/campaign_source_offline_corpus.py`. Só atende em
  loopback quando lançado explicitamente; não é montado no app do jogo. A UI
  informa que a prosa é autorada e que o custo de provedor é USD 0.

## Matriz de evidência

| Protocolo | Evidência offline | Limite |
|---|---|---|
| CAMP-EVAL-01–08 | Oito trajetórias integrais passam pela mesma P/K/H e terminam em preservação, parcial, perda ou abandono conforme o caso. | Texto autorado; não mede Luna. |
| NEG-01–06, NEG-09 | Mutação de prosa rejeitada pelo gate de proposta/autoridade. | Verificador lexical é deliberadamente estreito; sem garantia semântica geral. |
| NEG-07 | Commit genérico e atualização direta de snapshot B recusados; turno aceita somente o delta da cápsula. | Adulteração direta do arquivo SQLite está fora do modelo de adversário. |
| NEG-08 | Método plausível não catalogado retorna `campaign_source_out_of_scope`, zero turno/narração; não é narrado como falha do personagem. | Cobertura de métodos continua restrita ao recorte. |
| Pausa, replay e concorrência | Falha H seguida de H2/H3, reinício, P/H pendente recuperado, duplo clique e rollback na falha de entrega/SQLite. | UI offline não substitui aceitação humana em navegador. |

Verificação focal (sem rede), com `STORYTELLER_DISABLE_DOTENV=1` no ambiente:
`python -m pytest -q -p no:cacheprovider` sobre os sete arquivos
`test_campaign_source_*.py` deste incremento e
`test_campaign_progression_service.py`: **70 passaram**. Regressão v1 de
input/bridge/turn, direção de cena e persistência: **288 passaram**.
Teste HTTP ASGI e análise sintática do JavaScript passaram. Smoke real no
loopback respondeu HTTP 200 com identificação explícita de prosa autorada.

Correção do ensaio em navegador no mesmo dia: depois de `show()` executar
durante `busy=true`, o `finally` reabilitava o botão Enviar, mas deixava o
campo de ação desabilitado. Isso impedia a primeira ação e reaparecia ao
iniciar outra sessão ou retomar. Os três fluxos agora finalizam pelo mesmo
desbloqueio, respeitando o desfecho terminal. Regressão do script embarcado
verificou início, envio e nova sessão; os três testes focados passaram.
No navegador local foram observados dois turnos consecutivos, desfecho,
nova sessão com campo ativo e recarga com sessão reconstruída. Custo de
provedor do ensaio: **USD 0**. Essa verificação técnica não constitui
aceitação narrativa humana.

Correção adicional após relato `campaign_source_campaign_missing`: cada
inicialização pelo lançador cria um banco sintético novo, enquanto o navegador
retém o ID da sessão anterior. O cliente agora descarta o ID vencido quando a
leitura retorna 404 ou a operação informa campanha ausente, bloqueia o envio
na sessão inválida e oferece uma nova sessão. Respostas tardias da leitura ou
do status não podem sobrescrever uma sessão nova. O teste do script embarcado
cobre a sessão vencida, o erro explícito e a recuperação. Em navegador real,
um servidor de teste reiniciado com outro banco mostrou a mensagem de sessão
indisponível; a nova sessão aceitou e concluiu o primeiro turno. O servidor
principal continuou em `8021` com seu banco sintético anterior preservado.
Essa observação comprova a recuperação do cliente, não a origem exata do
erro visto pelo usuário no navegador externo; um novo erro numa sessão recém-
criada exigirá investigação do caso concreto.

O usuário informou ter feito o reteste externo e pediu continuidade, mas não
registrou o resultado funcional nem um julgamento da experiência narrativa.
TASK-013 e CAMP-24 permanecem abertos; o reteste não foi interpretado como
aceitação implícita ou autorização de inferência paga.
Após as correções da interface, os oito arquivos focados de campanha,
progressão, trajetória e ensaio HTTP foram reexecutados: **71 passaram**,
sem falha e sem rede externa.

O usuário esclareceu em seguida: envio e nova sessão funcionaram como
planejado; a microcena teve progressão e resposta pertinente de Mara, e atingiu
seu objetivo de teste. Satisfação de UX não foi medida. A fala de Mara pareceu
curta e impessoal, com discurso relatado em vez de diálogo direto. Essa
preferência futura foi registrada separadamente em
[observação de fala direta](../../../plan/observation-npc-direct-dialogue-1.md),
sem mudar gates ou corpus.
O aceite é limitado à microcena autorada observada; não conclui todos os
percursos CAMP-EVAL-01–08, CAMP-24, admissão de Luna ou TASK-013 integral.

Após executar o procedimento adicional de CAMP-EVAL-02 (salvamento parcial),
CAMP-EVAL-03 (perda) e CAMP-EVAL-04 (abandono), o usuário confirmou que “as
conclusões foram executadas como esperado”. Isso aceita os desfechos desses
três percursos no ensaio autorado. Não há declaração equivalente sobre todos os
percursos 05–08, satisfação de UX, desempenho do Luna ou sua admissão.

Em 30/09, o usuário avaliou CAMP-EVAL-05 e 08 detalhadamente e confirmou que
CAMP-EVAL-01 já havia sido executado. Em 05, a retirada e preservação foram
como esperado. Em 08, a recusa de segredo, a orientação de Mara e o salvamento
fizeram sentido como respostas à ação; o relato cobriu a sequência pedida após
recarregar a página, sem apontar problema técnico. Não há medição separada do
estado visual imediatamente após o reload. O usuário aprovou a ambientação do
registro na bancada e a devolução da iniciativa, mas apontou que o diálogo
indireto de Mara reduz participação e imersão. Trata-se de prosa autorada:
nem resultado do Luna, nem defeito de transporte demonstrado. A preferência
futura e sua fronteira de escopo estão em
[observação de diálogo](../../../plan/observation-npc-direct-dialogue-1.md).

A suíte ampla diagnóstica chegou a **2.608 aprovados** antes de parar na falha
preexistente Windows `wrong_session`: os sidecars SQLite `-wal`/`-shm` violam
uma asserção histórica de diretório inalterado. Não é causada pela nova rota.
Uma execução diagnóstica posterior de `test_narrator_record_evidence_execution`
parou em hash congelado de schema de ator antigo (`Final actor schema differs`),
também fora deste incremento. A suíte ampla, portanto, **não está verde**.

## Próximo checkpoint

CAMP-EVAL-01–05 e 08 têm execução/objetivo causal relatados pelo usuário no
recorte autorado; 06/07 dependem de RNG e não devem ser
repetidos manualmente até alcançar um recibo desejado; o teste offline cobre
suas expectativas causais. A avaliação de UX identificou a mediação impessoal
de Mara como problema de imersão; não há aceite integral de experiência do MVP.
A prosa autorada não permite admitir Luna. Qualquer
lote Luna posterior precisa de orçamento, corpo, parâmetros, limite de
chamadas, modo de chave e relatório final de custo congelados antes da execução.
