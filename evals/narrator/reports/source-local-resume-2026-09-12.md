# Composição técnica local B — retomada de 12/09/2026

A composição sintética foi concluída: introdução, orientação de ações, recusa segura,
continuação confirmada, consultas, reconexão e rolagem independente foram exercitadas
no navegador. Duas falhas de encerramento foram reproduzidas e corrigidas. A preparação
não ativa um narrador real, não escolhe modelo e não aprova experiência de campanha.

O usuário retomou a execução e a inserção protegida da chave foi concluída. Nenhuma
validação do provedor ou inferência real ocorreu nesta composição. Não foram lidos
arquivos de credenciais ou `.env`; não foi alterado o checkout original.

## Encerramento ASGI e do lançador

O close duplicado da pausa foi reproduzido em dois testes com asgi_receive/asgi_send
do Uvicorn instalado: cliente 1000 e servidor 1012. Starlette mantinha application_state
conectado após marcar client_state desconectado. A factory agora exige ambos conectados
antes do close final. Não captura RuntimeError nem altera o handler ou seu settlement.
Os 29 testes da factory passaram; quatro são novos, incluindo contraprovas de propagação
de RuntimeError/CancelledError. Os oito avisos são depreciações de dependências.

A primeira composição desta retomada, d249b3fc, confirmou duas ações e preservou o banco,
mas seu lançador ainda registrou failed ao receber Ctrl+C. Esse resultado permanece
histórico. Uma reprodução em subprocesso mostrou o servidor terminando a limpeza antes
de Uvicorn reaplicar SIGINT e cancelar a tarefa principal de asyncio.run.

O lançador sintético agora usa captura local de sinais, conservando handle_exit,
should_exit/force_exit e restauração dos handlers, sem reaplicar o sinal já tratado.
Só registra stopped após serve retornar, sem interrupção forçada, tarefas/conexões
registradas ou falhas do lifespan. Uma contraprova com LifespanOn real mostrou que uma
exceção de shutdown usa error_occured, mesmo sem shutdown_failed; ambas são verificadas.
Não há captura que converta exceção ou cancelamento externo em sucesso.

Foram aprovados 33 casos distintos do lançador em etapas: 30, mais dois negativos,
mais o caso de exceção de lifespan. A última rodada revalidou os nove casos afetados,
com 24 deselecionados. Os testes vermelhos e as versões intermediárias foram preservados.
A adaptação depende da API de sinais/estado do Uvicorn 0.30.1 instalado; não demonstra
compatibilidade com versões futuras. Nenhuma dependência foi atualizada.

## Interface e orientação

A introdução tem área rolável e foco por teclado; o estado da ação ocupa seção irmã
que não encolhe. O delta visual pendente da pausa foi revisado e seu caso alterado passou.
Depois foi concluído REQ-006: a própria introdução explica os formatos de espera,
conversa com personagem nomeado e investigação, com seus limites. NOME é um molde,
sem fixar Mara no componente. O textarea referencia a orientação por aria-describedby.

O novo caso de acessibilidade passou; os 16 demais foram deselecionados pelo filtro.
Lint dos dois arquivos terminou sem erros/avisos e TypeScript da aplicação passou.
A primeira invocação da retomada visual foi impedida por EPERM antes da coleta;
a mesma verificação passou após escalada autorizada. Ambas as evidências foram
preservadas; a falha de ambiente não foi contada como teste reprovado.
O diff da orientação não muda callbacks, estado, protocolo, parser, dados ou perícias.
As suítes anteriores do hook e backend não foram repetidas sem alteração pertinente.

## Composições observadas

| Execução sintética | Ações e persistência | Consulta/reconexão | Encerramento |
|---|---|---|---|
| d249b3fc-f045-4438-97d2-4d3da9e462a9 | Duas ações confirmadas; dois P/K/H completos e dois turnos | Banco idêntico após consultas, reconexão e reload | Lifecycle failed, preservado; originou correção do lançador |
| d8abaa85-5c57-40ee-aa4e-041d95513806 | Observo a prateleira. recusado: somente P failed, zero K/H/turnos. Diálogo posterior confirmado: um P/K/H completo e um turno | Mesmos dois IDs, texto e banco após consultas e reconexão | Lifecycle stopped após Ctrl+C com socket conectado; sem failed/traceback no retorno do terminal |

Na primeira execução, reload iniciou a página desconectada e sem reenvio. Conexão
explícita restaurou briefing e somente a última narrativa/pergunta, com input vazio.
O histórico completo e texto/identificação locais não sobrevivem a reload; isso está
explicado na interface. Na mesma montagem, a reconexão conserva os registros locais.

Na execução final, a recusa foi identificada por 615ee0a0-1eb2-4138-8d9c-7b5e434b6d79
e o diálogo por 52cc9854-71c4-4b93-bfe8-4974c49b8718. Consultas e reconexão preservaram
os IDs e os dois artigos. Nenhum erro de console foi retornado pela ferramenta.

| Tela observada | Altura da página | Painel | Estado da ação | Histórico rolável |
|---|---:|---|---|---|
| 475×648, antes da orientação adicional | 648 | y 182–345,09 | y 308,09–328,09 | 151 px visíveis / 1.106 px de conteúdo |
| 375×667, versão final | 667 | y 182–351,75 | y 314,75–334,75 | 158 px / 957 px |
| 1250×800, versão final | 800 | y 134–800 | y 764–784 | 512 px / 582 px |

Na versão final, a introdução/orientação tem 65/672 px no telefone e 562/708 px no
desktop. A rolagem foi observada sem deslocar o estado da ação. A prova anterior
inclui foco e PageDown na introdução. Trata-se de painel de cena/ação, não ficha ou HUD
completo. As imagens foram inspecionadas inline, sem exportação de arquivos de imagem.

## Auditoria, encerramento e evidência

Snapshots SQLite somente leitura verificam esquema, contadores e hash lógico completo.
Em d249b3fc, after_actions, after_queries e after_shutdown são idênticos:
2a3b5285477d8cbf3688fdcba91d2f6d257a253897e8266ba68bc53f31c96411.
Em d8abaa85, o hash após as ações é
d703a93352aef2134c81aae34b35f454990ba0c29bed8533dbd8871e84e68c11;
a auditoria registra sua comparação após consultas e desligamento. Linhas H não são
contagem de chamadas do provedor. A ausência de inferência real decorre da fixture
autorada e de sua composição, sem adaptador externo.

Os dois Vite encerraram com exit 0. A ferramenta de execução retornou 1 ao interromper
as sessões PowerShell dos backends. No caso final, o lifecycle é stopped; o código
separado do processo Python não foi medido nessa sessão interativa. Não converter o
código do terminal em código Python. Listeners 8018/5178 ausentes foram conferidos;
abas técnicas fechadas e tamanho de viewport restaurado. A janela protegida do usuário
foi preservada.

Checkpoint: `eval-results/checkpoints/source-local-resume-20260912/manifest.json`.
Inclui provas iniciais/finais, diffs, hashes de fontes, observações do navegador e
auditorias dos dois bancos. Não inclui credenciais nem copia nenhum banco bruto.
As 75 cópias da pausa, 53 cópias do comparativo e seus seis artefatos brutos originais
conservaram os hashes. Nenhum verificador histórico foi executado contra código novo.

Worktree b008, branch codex/planejamento-agente-storyteller-v5, HEAD 5e563824.
Checkout original master limpo; 39 alterações rastreadas preexistentes no b008
preservadas, além dos arquivos não rastreados já existentes. Sem commit/push/merge.

## Limites e continuidade

As respostas são fixas e autoradas. A fixture repetiria a última resposta depois de
duas gerações; isso não foi usado como evidência de qualidade narrativa. A inspeção
do navegador não instrumenta RNG; a recusa antes de produção é sustentada pelo caminho
de classificação e pelas contraprovas do produtor, além dos snapshots sem K/H/turno.

O comparativo 61b83a2f continua encerrado sem candidato qualificado. A nova preparação
investiga a aderência do Qwen ao orçamento de palavras, com quatro slots independentes,
dois contextos autorados e margem por campo, mantendo o gate de 150 palavras. É uma
hipótese prospectiva, sem repetir o comparativo, completar seus skips ou escolher modelo.
Seu protocolo, implementação e verificação ficam em plano e evidência separados.

Aceitação do recorte pelo jogador, campanha completa, modelo default e CAP-001 não
são promovidos. O planejamento de campanha híbrida, a pauta visual futura e a criação
da ficha por último permanecem na ordem registrada.
