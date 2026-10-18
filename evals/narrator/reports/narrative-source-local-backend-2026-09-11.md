# Transporte B local — backend inativo verificado

O leitor agregado, a factory ASGI separada e o handler B estão implementados e
revisados. **280 casos distintos estão aprovados**: 89 do leitor, 25 da factory,
37 do handler e 129 regressões dos leitores anteriores. Este resultado não inclui
os 73 testes já arquivados do seletor nem reconta as 1.097 provas da correção de agência.

A conexão e a consulta leem um snapshot SQLite somente leitura. Somente um submit
explícito prepara a ação e pode chamar o coordenador; a publicação de n/q ocorre
depois do commit. Banco/manifesto/sessão/Host/Origin são vinculados pelo servidor
antes do accept. A aplicação ASGI independente não executa bootstrap, migração,
recuperação ou rotas do jogo atual. Nenhum listener de produto foi ativado.

## O que foi comprovado

- Snapshot único com manifesto, última narrativa e operação solicitada; rejeição
  de identidades deslocadas e históricos incompatíveis, sem criação de banco.
- Produtor exige preparação coerente; os leitores anteriores mantêm os corpos
  originais. A alteração em persistence.py é aditiva e foi revisada por diff.
- Queries não reservam, rerrolam ou geram. Submit usa deadline absoluto P/H;
  comandos extras, duplicados, inválidos ou binários são recusados com causa segura.
- Texto provisório não atravessa o socket. A prova bloqueia o commit e só aceita
  publicação depois de liberá-lo. Consulta e reconexão recuperam o já confirmado.
- Desconexão antes/durante/depois do commit e cancelamento repetido não repetem
  settlement; cancelamento da operação é sinalizado uma vez e aguardado.
- Composição ASGI com handler real, SQLite sintético e FakeLLM, além de testes
  isolados da ordenação pré-accept. Nenhuma inferência externa foi usada.

## Histórico da verificação

O leitor teve 44 falhas iniciais exclusivamente na fixture pura, que combinava
sessões diferentes; os 44 casos SQLite passaram na primeira rodada. A fixture foi
corrigida e somente o módulo puro, de 45 casos, foi repetido. O resultado de 89 é
a reconciliação dos casos distintos, não uma alegação de suíte única toda verde.

A factory teve 24 aprovações e uma falha inicial na comparação física do banco.
Diagnóstico sem aplicação reproduziu o checkpoint do WAL pela coleta de conexões
do setup: o dump lógico permaneceu idêntico. A fixture passou a concluir essa
coleta antes do baseline, preservando as asserções de bytes e contagens. A rodada
final teve 25 aprovações. Nenhuma mudança de produção foi feita para essas falhas.

Handler (37) e regressões (129) passaram na primeira execução. Hashes dos arquivos
permaneceram estáveis durante as rodadas. O aviso conhecido de python_multipart
permanece; não houve troca de dependências. Revisões independentes encerradas após
contraprovas de operação órfã e frame binário, incluídas antes dos testes finais.

## Limites

A seleção local não autentica contas ou um processo hostil no mesmo desktop.
O escopo é um operador, loopback e banco sintético novo. Não houve alteração do
App padrão, conta, proxy, acesso remoto à API, modelo default ou aprovação CAP-001.
A recuperação aqui é do estado confirmado no servidor; reload do navegador e
experiência visual ainda dependem da composição específica da interface.

Os seis artefatos brutos e as 53 cópias do comparativo 61b83a2f foram novamente
conferidos por hash, sem rerodar seu verificador contra código posteriormente
corrigido. O comparativo continua sem candidato qualificado. Nenhuma chamada real
adicional foi feita; esse resultado é técnico e sintético.

Evidências, inclusive as falhas iniciais e o diagnóstico do WAL, estão em
`eval-results/checkpoints/narrative-source-local-backend-20260911/`.
O JSON acompanha contagens, hashes e origens das cópias.

[Plano](../../../plan/feature-narrative-source-local-handler-1.md).
