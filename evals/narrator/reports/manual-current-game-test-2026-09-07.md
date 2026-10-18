# Uso teste do jogo completo atual — 07/09/2026

O usuário pediu experimentar o artefato antes da próxima fase e escolheu explicitamente o jogo completo atual com Groq. Esta sessão usa o fluxo existente do produto; a ponte B permanece separada.

## Abertura preparada

- URL: `http://127.0.0.1:8000/play/local.4cfd5337-1c84-487e-bd77-8fe8e4d78a29`.
- Sessão inédita: `local.4cfd5337-1c84-487e-bd77-8fe8e4d78a29`.
- SQLite isolado: `C:\Users\skate\AppData\Local\Temp\storyteller-manual-game-4cfd5337-1c84-487e-bd77-8fe8e4d78a29\storyteller.sqlite3`.
- Janela protegida: PID 26144; lifecycle em `C:\Users\skate\AppData\Local\Temp\storyteller-manual-game-4cfd5337-1c84-487e-bd77-8fe8e4d78a29\status.json`.
- Estado observado ao registrar: `awaiting_secure_credential`. Consultar o lifecycle para o estado atual; isso não é evidência de readiness remota ou jogabilidade aprovada.

O novo launcher `scripts/run_storyteller_manual_test.ps1` solicita a chave uma única vez por SecureString, fornece ambiente permitido ao filho e não lê `.env` ou chave anterior. Banco/arquivos auxiliares existentes e TestId ativo são recusados. Porta ocupada não é reutilizada; a escuta deve pertencer à árvore de processo criada. O Enter final encerra essa árvore. O banco de teste é preservado para análise.

O identificador contém ponto, recusado pelo importador de JSON legado antes de consultar arquivos; o carregamento segue apenas pelo SQLite de teste. Ficha base e catálogos do jogo continuam os existentes. Usar uma crônica inventada para esta sessão exploratória.

## Alteração necessária e verificação

O runtime não oferecia seleção Groq. Foi acrescentado `LLM_ADAPTER_KIND=groq`, que usa diretamente o GroqAdapter já existente e valida endpoint, rótulo, modelo, esforço e chave. Nenhum modelo/provedor ganhou default. O alvo do launcher é `qwen/qwen3.8-27b`, raciocínio `none`, saída de cena até768 tokens e temperatura0,65. Isso não aprova CAP-001 ou campanhas existentes.

A composição passou em54 testes:17 novos e37 existentes, incluindo HTTP simulado200/429, schema, proveniência e ausência de retry. O frontend compilou por TypeScript/Vite. Preflight passou sem provedor, chave vazia foi recusada antes do servidor e o bootstrap real local serviu a interface/capabilities antes de encerrar a própria árvore, sem chamada externa. O relançamento com o banco desse bootstrap foi recusado. Revisão independente fechou os controles de porta própria e banco inédito.

Após a chave, o launcher executa o diagnóstico padrão de até três sondagens sintéticas do jogo (texto, JSON e streaming), com deadline global60s. Só publica a fase3 de sucesso se o diagnóstico passar. Depois, a narrativa é acionada pelas entradas do jogador. Não há ação ficcional automática, retry do modelo ou troca de alvo. Esta sessão exploratória não é um novo benchmark fixo nem comparação A/B.

[Prova estruturada e hashes](manual-current-game-test-2026-09-07.json). Desenvolvimento da fase B seguinte fica subordinado ao uso teste solicitado.

## Jogo aberto e pronto

A chave foi inserida pelo usuário no prompt protegido. O lifecycle passou a `ready`,
com servidor PID23336. As três sondagens — texto, structured e streaming — passaram.
A aba do jogo foi aberta no navegador integrado e conferida pela árvore de
acessibilidade: painel de inicialização concluído, ficha visível e campo/botão de
ação disponíveis. Nenhuma ação do jogador foi enviada pelo agente.

A janela PowerShell PID26144 mantém o servidor vivo; Enter nessa janela encerra
a árvore do servidor. A prioridade agora é o uso teste pelo usuário antes da próxima
fase de desenvolvimento. Chave ou respostas do jogador não foram copiadas para este
registro.
