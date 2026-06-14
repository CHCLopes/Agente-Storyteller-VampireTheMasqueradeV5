# Especificação Técnica: Orquestrador de Narrativa RPG Vampire V5 — Arquitetura Web Distribuída

Este documento formaliza a arquitetura e o plano de migração do Agente Storyteller V5 para uma infraestrutura distribuída na nuvem (Vercel + Railway + Gemini Free API), otimizando o reúso dos componentes existentes.

## 1. Validação Executiva

A viabilidade técnica de utilizar o Google Gemini Free API (tier gratuito de 15 RPM / 60 RPM dependendo da conta) como motor de inferência exclusivo para o Agente Storyteller V5 é confirmada. Como o processamento lógico-mecânico das rolagens de dados de Vampiro, consumo de sangue, combate e gerenciamento relacional é realizado localmente pelo backend FastAPI, as chamadas à API externa limitam-se à triagem do input (H0), extração de intenções (H1), consulta e enriquecimento de lore (H4) e geração narrativa (H6). A latência média esperada de processamento com o Gemini 2.5 Flash está abaixo dos limites de tolerância para turnos de RPG textual e o volume mensal gratuito de 1M tokens é condizente com a escala projetada para o público de jogadores casuais.

Os riscos de esgotamento de quota e estouros de limite de requisições por minuto (HTTP 429) são contornados através de enfileiramento semáforo de requisições no backend FastAPI e um indicador de recarga (cooldown) transparente no frontend React. O isolamento mecânico absoluto garante que a matemática de rolagens e atualizações de trackers do personagem não dependa de alucinação do modelo de linguagem, mantendo a consistência narrativa por meio de prompts injetados contendo snapshots JSON puros como dados deterministicos.

---

## 2. Arquitetura Detalhada

### A. Estrutura de Diretórios
A organização de diretórios do repositório unificado segregará o frontend hospedado na Vercel e o backend hospedado no Railway. O frontend estará concentrado no diretório client contendo a pasta src com componentes React, hooks de estado e tipos estáticos do TypeScript. O backend residirá na pasta api contendo o ponto de entrada principal e os serviços especializados de cálculo mecânico. Arquivos estáticos de configuração como o Dockerfile para o Railway, o manifesto do Pnpm e as configurações de build ficarão na raiz do workspace. Os scripts herdados de inicialização local e atalhos Windows serão movidos para uma pasta de utilitários isolada para fins de preservação sem impacto no deploy em nuvem.

### B. Pipeline de Ação (Fluxo Detalhado)
O fluxo inicia quando o jogador submete uma ação textual no navegador através do painel de controle React. O frontend despacha esse payload em tempo real pela conexão WebSocket segura ativa. O backend FastAPI recebe a mensagem, adquire um lock assíncrono para a sessão correspondente e executa a triagem local H0 para classificar se o input é uma ação mecânica ou uma dúvida de lore. Se for uma ação, o serviço H1 extrai os atributos e perícias envolvidos na intenção do jogador. O backend processa a mecânica de rolagens locais, calcula o dano no tracker de vida, realiza os testes de Fome e atualiza as relações com NPCs. Esses dados mecânicos consolidados e enriquecidos com trechos de lore estático são formatados em um bloco JSON de contexto. O backend envia esse contexto consolidado e o prompt do narrador H6 para a API do Gemini. A stream de tokens de narração retornada pelo Gemini é transmitida de forma incremental de volta ao frontend pelo mesmo canal WebSocket para renderização em tempo real na tela do jogador.

### C. Estrutura de Dados (JSON Schema)
A estrutura de dados principal é definida por um contrato de estado centrado no personagem e na crônica. O snapshot de estado contém o identificador único da sessão, os trackers de vida e força de vontade divididos em caixas de danos superficiais e agravados, além dos valores absolutos de humanidade e máculas acumuladas. O nível de Fome do vampiro é representado por um valor inteiro delimitado de zero a cinco que afeta diretamente o conjunto de dados em testes mecânicos. O contexto de jogo armazena variáveis de ambiente como exposição a fogo ou estímulo de sangue, além do registro de rolagens pendentes para testes de frenesi. O histórico armazena uma lista ordenada dos últimos turnos contendo os papéis de narrador e jogador para manter a coerência temática sem consumir contexto excessivo da API.

### D. Orquestração de Prompts (System Prompts)
A orquestração do comportamento de IA é dividida em três instruções de sistema isoladas. A instrução do Roteador H0 direciona o modelo a classificar a entrada e extrair notas rápidas de cena em formato JSON estrito. A instrução do Especialista H4 instrui o modelo a consultar os arquivos estáticos de termos de Vampiro e gerar parágrafos explicativos condensados sobre clans, seitas e terminologias de lore. A instrução do Narrador H6 formata a personalidade poética e sombria do jogo, obrigando o modelo a respeitar o status atual contido no bloco de estado fornecido e a anexar as tags XML de fechamento contendo a saída de dados estruturados para sincronização de tela. Exemplos estruturados com delimitadores de contexto e ação do jogador guiam as poucas demonstrações de inferência para consistência do formato.

### E. API Backend — Endpoints
Embora a dinâmica de jogo ocorra prioritariamente através do WebSocket ativo de sessão, o backend expõe endpoints HTTP REST para gerenciamento do ciclo de vida da campanha. A rota de criação de campanha inicializa uma nova ficha de personagem vazia com o estado básico do clã e o nível inicial de humanidade. O endpoint de configuração de sessão recebe o identificador e popula os atributos e disciplinas iniciais escolhidos pelo jogador. As rotas dedicadas de progressão permitem o acúmulo e gasto de pontos de experiência, validando se a ficha possui XP suficiente e salvando o novo estado em disco. O endpoint de exportação agrupa os arquivos JSON do personagem, histórico de diálogos, dados de relacionamento e notas de cena em um único arquivo compactado para download manual do usuário.

### F. Tratamento de Erros & Rate Limiting
A resiliência contra instabilidades de rede e limites de requisições baseia-se em mecanismos redundantes de proteção. O backend implementa um semáforo de concorrência global que limita o número de requisições simultâneas para a API do Gemini a fim de evitar estouros de cotas. Em caso de falha de conexão ou HTTP 429 da API, a camada de transporte captura a exceção, inicia um fluxo de retentativa com backoff exponencial limitado a três execuções e, se a indisponibilidade persistir, retorna um evento estruturado de falha de conexão. O frontend intercepta essa mensagem, exibe um painel de alerta informativo no HUD com contagem regressiva para liberação de novas ações e bloqueia os botões de envio para evitar a fadiga do usuário.

---

## 3. Mapa de Implementação

| Arquivo Original | Classificação | Ação de Refatoração / Reaproveitamento |
|---|---|---|
| `api/core/config.py` | Refatorar | Adicionar variáveis para `GEMINI_API_KEY`, `GEMINI_MODEL` e redefinir a base URL e headers do LLM. |
| `api/main.py` | Refatorar | Adaptar o websocket `/ws/initialization` para simular logs de diagnose offline e adicionar autenticação do Gemini. |
| `api/parser_service.py` | Refatorar | Ajustar a requisição httpx para injetar `Authorization: Bearer` com a chave do Gemini. |
| `api/h0_controller_service.py` | Refatorar | Ajustar a chamada HTTP POST para uso de cabeçalhos dinâmicos. |
| `api/h4_lore_expert_service.py` | Refatorar | Ajustar a chamada HTTP POST para uso de cabeçalhos dinâmicos. |
| `api/orchestrator_service.py` | Reaproveitar | Manter 100% da lógica mecânica do motor de regras. Adaptar apenas a chamada do streaming `run_narrator_stream`. |
| `api/state_service.py` | Reaproveitar | Mantido 100% para carregar e salvar snapshots em JSON de forma assíncrona. |
| `api/rules_service.py` | Reaproveitar | Mantido 100% (testes de dados, pools, etc). |
| `api/combat_service.py` | Reaproveitar | Mantido 100% (cálculo de dano). |
| `api/economy_service.py` | Reaproveitar | Mantido 100% (rouse checks). |
| `api/discipline_service.py` | Reaproveitar | Mantido 100%. |
| `api/relationship_service.py` | Reaproveitar | Mantido 100% (motor relacional). |
| `client/src/App.tsx` | Reaproveitar | Mantido 100%. |
| `client/src/hooks/useWebSocket.ts` | Reaproveitar | Mantido 100% (cálculo dinâmico de wss://). |
| `client/src/components/*` | Reaproveitar | Todos os componentes de HUD visual são mantidos intactos. |

*Novos Arquivos Requeridos:*
- `Dockerfile` (Na raiz, para o deploy do backend FastAPI no Railway).
- `client/vercel.json` (Configurações de roteamento SPA React na Vercel).

---

## 4. Fases de Delivery

### Fase 0 (Setup de Infraestrutura)
- **Início**: Configuração das variáveis de ambiente na Vercel e Railway. Criação do arquivo `Dockerfile` na raiz do projeto baseado em `python:3.11-slim` para hospedar o backend.
- **Fim**: Pipeline de integração contínua (CI/CD) funcional, com o frontend rodando na Vercel e o backend no Railway em modo de espera (.env.example atualizado).

### Fase 1 (Simulação de Diagnose e Mocks)
- **Início**: Adaptação da rota de inicialização `/ws/initialization` no backend.
- **Fim**: O frontend carrega e simula com sucesso a diagnose ("Gemini API Key validada com sucesso") sem depender dos binários e scripts locais do Windows.

### Fase 2 (Integração Gemini)
- **Início**: Refatoração do `api/core/config.py` e injeção do cabeçalho de autenticação do Gemini nos serviços de IA.
- **Fim**: Conclusão da integração com a API do Gemini via modo de compatibilidade OpenAI, substituindo a inferência do LM Studio local. Todos os testes mecânicos e de texto fluindo.

### Fase 3 (Persistência e Rollback)
- **Início**: Implementação de salvar/carregar snapshots no volume persistente do Railway.
- **Fim**: Endpoint REST de exportação ZIP de campanha e funcionalidade de Rebobinar Turno (Rollback) habilitados e validados no cliente.

---

## 5. Checklist de Viabilidade

| Item de Viabilidade | Confirmado (Sim/Não) | Justificativa Técnica |
|---|---|---|
| Suporte a Gemini Free API | Sim | O volume de chamadas por jogador é baixo e as chamadas mecânicas rodam localmente no backend Python, preservando os limites de RPM da API gratuita. |
| Reúso de WebSockets | Sim | O hook do React `useWebSocket.ts` já implementa backoff e reconexão dinâmicos, que são suportados por conexões seguras WSS no Railway. |
| Desempenho em PCs com 8GB RAM | Sim | Toda a inferência de linguagem e cálculos matemáticos pesados rodam em nuvem (Railway/Gemini). O cliente executa apenas a renderização de elementos estáticos e reativos simples do React. |
| Persistência sem Custo | Sim | O uso de serialização JSON combinada com armazenamento em IndexedDB/LocalStorage no cliente e SQLite local no Railway dispensa a contratação de bancos gerenciados caros. |
| Robustez contra Falhas 429 | Sim | O backend intercepta os limites de taxa da API e emite sinais informativos estruturados que travam a interface de forma controlada. |
