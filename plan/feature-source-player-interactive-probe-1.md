---
goal: Preparar a ligação interativa Groq do recorte local B sem ativar a experiência
version: 1
date_created: 2026-09-12
last_updated: 2026-09-12
status: 'Completed'
---

# Ligação interativa local B

O diagnóstico 291b3960 e seu diagnóstico de aliases estão encerrados. Esta etapa
prepara a participação do jogador na interface B já construída. Não é outro
comparativo de modelos, não repete respostas/cenas para obter vencedor e não adota
o SYSTEM experimental de margem, cuja observação foi não discriminante.

A autorização contínua cobre inspeção, implementação reversível e verificação
offline. A aceitação do [recorte proposto](proposal-source-player-trial-scope-1.md)
e a execução protegida continuam separadas da preparação. Concluir o trabalho
independente antes de pedir intervenção. Nenhuma chamada nesta etapa.

## Recorte técnico

- Nova sessão e SQLite sintéticos, cena Galeria, Mara presente, objetivo imediato
  de conhecer o lugar por conversa. Introdução autorada identificada, não fonte de LLM.
- Permitir somente as ações declarativas de conversa/espera reconhecidas pela
  gramática existente, com texto preservado. Excluir investigação antes de P/RNG.
- Configurar Qwen/Groq, reasoning none, SYSTEM narrative-source-progress-v1,
  schema n/q, temperatura0,65 e768tokens por chamada. Aliases de Mara fornecidos
  explicitamente pelo servidor e retidos pelo caminho B existente.
- No máximo quatro tentativas de geração no HTTP, teto solicitado3072tokens,
  espera inicial e intervalo global mínimo60s. Cada ação conserva o deadline
  atual de até60s, criado apenas depois da elegibilidade de entrada.
- Sem retry, reparo, truncamento, fallback, mudança de target, rerrolagem,
  takeover, lease ou estado paused. Leitura, query, reconexão e replay não geram.
- Loopback127.0.0.1, portas backend8018/frontend5178, origem e sessão vinculadas
  pelo servidor. Sem App/default/v1/save anterior, acesso remoto direto ou contas.

## Menor extensão interna revisada

O handler não tinha hook de admissão. A espera dentro do gateway consumiria seu
deadline absoluto. Foi acrescentado um callback síncrono opcional, defaultNone,
antes do token/deadline. Consulta e reconexão não o chamam. False ou falha
conservadora reutiliza unavailable/preparation, que o ramo de operação ativa já
emite sem criar P. Não fabricar claim ou preparation_rejected persistido.

Unavailable continua incerto e não libera Nova ação. Uma negativa da guarda deste
ensaio encerra novas admissões; não significa esperar e reenviar. A interface
evita envios prematuros com espera local conservadora após briefing/reconexão ou
resultado terminal. Esse relógio é apenas apresentação. O hook HTTP mantém a
verificação global final atômica de quatro envios, intervalo e parâmetros, sem
dormir nem renovar deadline/cápsula, inclusive entre conexões concorrentes.

Erros operacionais encerram novas admissões do ensaio. Rejeições de narrativa
mantêm seu estado real; outro envio somente por nova ação explícita permitida pelo
fluxo atual e pelos limites. Não prometer quatro respostas confirmadas.

## Entregas

| Entrega | Estado |
|---|---|
| Inspeção de deadline, gramática, projeções e fronteira interna | Concluída e revisada, sem necessidade de nova política arquitetural |
| Callback opcional e contraprovas de ausência de P/RNG/deadline | Concluída e verificada |
| Runner Groq local separado, preflight, limites, estado e encerramento | Concluída e verificada |
| Launcher PowerShell7 com credencial segura e filhos próprios | Concluída e verificada |
| Entrada visual separada e orientação/espera próprias | Concluída e verificada |
| Verificação offline, composição simulada e revisão independente | Concluída; evidência no relatório |
| Congelamento, documentação operacional e comando concreto | Concluída; evidência no relatório |
| Aceitação/ativação para participação do usuário | Não executada |

Arquivos entregues: api/narrative_source_local_handler.py;
scripts/run_source_local_groq_trial.py; scripts/run_groq_source_local_trial.ps1;
client/source-player-trial.html; client/vite.source-player-trial.config.ts;
client/src/sourcePlayerTrialMain.tsx; client/src/components/SourcePlayerTrial.tsx;
props opcionais em client/src/components/SourceTrialView.tsx e
client/src/hooks/useSourceTrialConnection.ts. Testes próprios do handler, runner,
launcher e SourcePlayerTrial; testes antigos da view/hook permanecem preservados.
Fontes finais, hashes e provas estão no checkpoint indicado no relatório.
Os harnesses e fixtures de avaliações encerradas não foram alterados.

## Credencial e processos

PowerShell7, Read-Host -AsSecureString ou cópia do SecureString do próprio usuário.
Chave somente no ambiente do filho backend real, allowlist explícita e dotenv
desabilitado. Não ler outra janela, histórico, arquivos de chave ou .env. Nenhum
broker de credenciais, segredo em argumento, UI, logs ou status. Sem chave em
preflight, verificadores, Vite ou testes.

Filhos auxiliares ocultos e controlados por seus objetos Process. Pode existir
um comando literal de encerramento por stdin do próprio filho, sem segredo;
isso não é canal de coleta de credencial de outro processo. Encerramento cooperativo
com fallback limitado aos filhos efetivamente criados; nunca matar por nome/porta.
Preservar status failed/interrupted quando o encerramento não for comprovado.

## Contraprovas necessárias

- DefaultNone preserva o handler atual; negativa/erro não cria P/RNG/token/deadline
  ou gateway. Query/reconexão não consomem a guarda. Cancelamento continua propagado.
- A guarda reconhece a gramática integral existente e recusa investigação,
  ambiguidade e ações fora do recorte antes de RNG. Aliases vêm da configuração.
- Quinto envio, concorrência, intervalo curto, corpo/modelo/schema/temperatura/teto
  divergentes são bloqueados antes do HTTP. Não zerar medidas ausentes.
- Resposta, recusa, erro de provedor, timeout e cancelamento preservam estado,
  identidade e evidência; nenhum contador/status deve afirmar chamada que não ocorreu.
- Preflight não lê chave, cria SQLite ou listener. Freeze detecta drift. Input,
  stdout/stderr e falhas hostis não expõem segredo sintético. Cleanup só dos filhos.
- UI distingue autorado/real, mostra somente conversa/espera, preserva ação e
  consulta, não libera nova ação incerta e não trata timer como quota do servidor.
- Verificação do recorte simulado sem inferência real, seguida de lint/TypeScript/
  build da entrada nova e revisão independente das fronteiras alteradas.

## Interpretação

Esta preparação não comprova disponibilidade futura, qualidade narrativa ou
aceitação do usuário. A pergunta de uso é se introdução, ações, estados e
continuidade ficam compreensíveis na interação limitada. Agência, fidelidade e
reação útil continuam critérios de qualidade. Limitações conhecidas dos modelos
permanecem registradas; não criar exceção para qualificar um deles.

Referências: [resultado291b](../evals/narrator/reports/source-word-budget-observation-291b3960-2026-09-12.md),
[matriz de evidências](../evals/narrator/reports/source-model-choice-status-2026-09-12.md),
[transporte](feature-narrative-source-transport-1.md) e
[composição técnica anterior](feature-narrative-source-local-handler-1.md).

## Fechamento verificado

Preparação offline concluída. O uso pelo jogador continua pendente. Evidência, contagens em etapas, limites e comando protegido em [relatório](../evals/narrator/reports/source-player-interactive-preparation-2026-09-12.md). Nenhuma chamada real nesta preparação. Checkpoint com 152 cópias verificadas.
