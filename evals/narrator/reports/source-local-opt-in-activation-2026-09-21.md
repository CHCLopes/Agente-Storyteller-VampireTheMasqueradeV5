# Ativação do opt-in local B

Data: 2026-09-21

## Decisão

O usuário confirmou a alternativa recomendada: a entrada B atende um único
operador no desktop, exclusivamente por loopback. A API não é publicada para
acesso direto de outra máquina. Acompanhamento pelo Codex Remote não muda essa
fronteira, pois acompanha o host em vez de expor o serviço local.

## Superfície ativada

A ativação usa `scripts/run_groq_source_local_trial.ps1`, a factory ASGI separada,
`/ws/source-local/{session_id}` e `source-player-trial.html`. Sessão, banco,
Host/Origin, setup e configuração são vinculados pelo servidor. Falha de seleção B
não cai no legado. `api.main:app`, `App` e o save v1 permanecem como estavam.

Isso não cria autenticação de rede, conta, proxy, acesso remoto direto, narrador
definitivo, campanha completa ou aprovação CAP-001.

## Verificação renovada

- backend B: 598 testes aprovados, 1 deselected;
- frontend: 12 arquivos e 245 testes aprovados;
- build da entrada `vite.source-player-trial.config.ts`: concluído;
- preflight operacional: código 0, sem chave, banco, listener ou inferência;
- a deselection é a falha preexistente no Windows em que uma leitura SQLite
  `wrong_session` cria sidecars `-wal` e `-shm` sem alterar o banco principal.

Nenhuma dependência foi instalada. Nenhum `.env` ou segredo foi lido.
