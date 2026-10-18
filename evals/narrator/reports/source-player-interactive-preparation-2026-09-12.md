# Preparação do uso interativo local B — 12/09/2026

A ligação interativa está preparada e verificada. Nenhuma inferência ou credencial
real foi usada nesta preparação. A participação do jogador permanece pendente da
aceitação do recorte descrito em `plan/proposal-source-player-trial-scope-1.md` e
da execução protegida. A direção B já está aprovada; não se reabre essa decisão.

## Experiência pronta para execução explícita

Nova sessão sintética na Galeria, com Mara presente e o objetivo de conhecer o
lugar pela conversa. Introdução autorada identificada. Continuação experimental
com Qwen `qwen/qwen3.8-27b` via Groq, reasoning none, SYSTEM
`narrative-source-progress-v1` preservado, schema n/q, temperatura 0,65.

Somente diálogo/espera pela gramática existente, com aliases confiáveis de Mara
fornecidos pelo servidor. Investigação é recusada antes de P/RNG. Até quatro
tentativas HTTP, 768 tokens por chamada e teto solicitado de 3.072; intervalo
inicial e entre inícios HTTP de pelo menos 60 s. O deadline da ação continua
limitado a 60 s após admissão. Sem espera dentro do gateway, renovação de prazo,
retry, reparo, fallback, mudança de target ou rerrolagem.

Exemplos: `Aguardo.` ou `Pergunto a Mara: "O que você pode me contar sobre este lugar?"`.
Ao conectar, a tela espera 60 s antes de liberar envio; depois de um resultado,
aguarda novo intervalo. Consulta/reconexão não reenvia a ação. A quarta entrega
terminal, uma negativa da guarda ou uma falha operacional observada pode encerrar
a sessão. Não se prometem quatro respostas confirmadas. Cancelamento sem entrega
terminal fecha a elegibilidade, mas pode depender de parada pelo lançador.

O lançamento cria banco e sessão novos em `eval-results/source-local-groq-trial-UUID`.
Não altera App/default, saves anteriores ou as fixtures de observações encerradas.
Serviços somente em 127.0.0.1, portas 8018 e 5178. Host/origem/sessão são vinculados;
isso não é autenticação por conta nem publicação para acesso direto remoto.

## Implementação e revisão

O handler recebeu um callback síncrono opcional antes de token/deadline. Default
None conserva o fluxo existente. Recusa utiliza unavailable/preparation, sem
fabricar claim ou terminal. Queries não chamam a guarda. O runner separado aplica
o limite final no envio HTTP; dados/parametrização e arquivos congelados são
reconferidos. Uma indisponibilidade da operação ativa agora também encerra a
elegibilidade após entrega, conforme contraprova causal e revisão independente.

O novo PowerShell 7 usa uma cópia do SecureString somente no ambiente do próprio
backend. Preflight e Vite não recebem chave. A resolução de Node foi corrigida
para selecionar a primeira aplicação explicitamente resolvida no PATH; os hashes
são registrados. Filhos ocultos e próprios recebem stop pelo stdin, com fallback
limitado a esses Process. Backend tem 65 s de grace e 75 s de espera cooperativa
no launcher. Não matar por nome/porta nem ler outra janela de PowerShell.

A entrada `client/source-player-trial.html` é separada da fixture autorada.
Propriedades opcionais da view e callback de apresentação preservam consumidores
anteriores. Sem novo estado de protocolo, contador autoritativo local ou retomada
automática. Unavailable permanece incerto e bloqueia novos envios. Reload perde
a cópia local de texto/ID e só apresenta o último n/q confirmado após conectar.
Relançar cria outra sessão e não constitui recuperação dessa ação.

## Evidência e limites

| Frente | Evidência aprovada |
|---|---|
| Handler | 47 casos na suíte final, 10 novos; vermelho causal preservado |
| Runner | 66 casos distintos em etapas; seleção afetada final 9, sem repetir 57 |
| Launcher | 55 casos na suíte final, incluindo credencial sintética/isolamento |
| UI | 81 casos distintos em etapas; seleção final 3; lint, TypeScript e build |
| Preflight conjunto | exit 0; 45 inputs verificados; sem chave/DB/listener |
| Vite real isolado | stop por stdin, exit 0, sem força, porta 5178 liberada |
| Navegador | entrada renderizada, orientações e controles desabilitados sem conexão |

Não somar reexecuções ou tratar contagens em etapas como uma suíte final única.
Falhas iniciais dos testes e contraprovas causais permanecem guardadas. A composição
com HTTPX MockTransport e SQLite confirmou quatro turnos/12 attempts, consulta e
reconexão sem novo HTTP ou RNG. Investigação ficou com zero P/K/H. O TestClient
pode reabrir o app em memória após stop; a execução real encerra o servidor.

O preflight conjunto fac261ca passou com hash
`398bbddbd71f5f147167325c8a33c9621aa0e7a8dd233c63494026461de4f5c1`. A inspeção do navegador usou a árvore acessível,
não assertivas de pixel/viewport; nenhum backend foi conectado. O CSS global
existente referencia Google Fonts. Ctrl+C nativo com backend real não foi
exercitado; não confundir o stop real do Vite com essa prova. Status é snapshot
de ciclo de vida; stopped/exit 0 comprova cleanup, não narrativa aceita ou quota.

Revisões independentes de runner, launcher e preflight encerradas sem achado
acionável restante. Checkpoint: `eval-results\checkpoints\source-player-interactive-preparation-20260912\manifest.json`, 152 cópias
verificadas, SHA-256 `a79b073a95833a8bf996f0d60c922d1b95abcb71b398c15afe7ad66fcb71273d`. As 51 cópias dos checkpoints do diagnóstico
anterior conservaram hashes; summary/JSONL históricos também foram preservados.

## Operação protegida e próximo passo

Na mesma janela PowerShell 7 em que o usuário guardou o SecureString:

```powershell
& 'C:\Users\skate\.codex\worktrees\b008\AgenteStoryteller\scripts\run_groq_source_local_trial.ps1' -Credential $StorytellerGroqKey
```

Se aquela janela/variável não existir, executar o script sem `-Credential`; ele
pedirá a chave com Read-Host -AsSecureString depois do preflight. Nunca enviar
a chave pelo chat, colocar em argumento literal, arquivo .env ou histórico.
Para só verificar novamente o preparo, `-PreflightOnly` não pede chave.

O lançador mostra o endereço da nova sessão. Abrir esse endereço, conectar e
usar somente ficção sintética nos formatos indicados. Manter a janela aberta;
preferir Enter para encerrar os próprios serviços. Chaves de outra janela não
são acessíveis ao agente e não devem ser extraídas. A execução explícita desse
recorte pelo usuário é separada da aprovação de qualidade/default/CAP-001.

Nenhum modelo foi qualificado pelo comparativo anterior. O diagnóstico 291b3960
continua encerrado e não discriminou a margem de palavras; os aliases ausentes
eram do harness fechado, já fornecidos pelo caminho B. Não repetir lotes ou
alterar prompts/gates para buscar um vencedor. O próximo passo é a participação
do jogador neste recorte, não outro ciclo equivalente de comparação.
