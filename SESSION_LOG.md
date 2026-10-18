---

> [!WARNING]
> **Registro histórico, não estado canônico atual.** Este arquivo preserva decisões
> e resultados de sessões anteriores e contém arquitetura, stack e próximos passos
> já superados. Para o comportamento vigente, use `README.md`, o código e os testes.
> Em especial, referências abaixo a Ollama/Gemini, múltiplos modelos obrigatórios,
> frontend selado ou migração distribuída não constituem decisões atuais.

PROJECT: Agente Storyteller | Motor Narrativo V5 🦇
STACK: Python (FastAPI), WebSocket, Ollama, Vanilla JS (Frontend)
LAST_SESSION: 2026-06-07
SESSION_COUNT: 13

## PROPOSED_SCOPE — 2026-09-05

- **Status:** ESCOPO PROPOSTO. O usuário autorizou somente refinar e encaminhar a frente documental de pausa/retomada por indisponibilidade do Narrador.
- **Plano:** [Pausa e retomada do Narrador](plan/feature-narrator-pause-resume-1.md) (`Planned`; implementação não autorizada).
- **Trabalho documental:** refinamento dos dois últimos bloqueios concluído; implementação futura continua pendente e não autorizada.
- **Próximo gate humano:** aprovar ou ajustar o escopo, a política de `gate_scope + scope_key` para `gateway|upstream|unknown` e decidir `DEC-001` (operação suspensa ou nova operação referenciada), `DEC-002` (editor bloqueado ou rascunho editável) e `DEC-003` (A com sondagem manual controlada ou B sem sondagem sintética).
- **Não aprovado por este registro:** arquitetura da retomada, estado operacional, implementação, provedor, modelo, custo, fallback, retry automático ou dependências.

## REVIEW_GATES — PAUSA/RETOMADA — 2026-09-05

- **P0 — Gate persistente:** antes de toda chamada H0/H1/H4/H6 habilitada e imediatamente antes de qualquer rolagem, consultar localmente a disponibilidade do target exato e os bloqueios hierárquicos por `gate_scope + scope_key`. Limite `gateway` comprovado alcança todos e somente os targets da mesma plataforma/conta ou credencial correlacionada; limite `upstream` permanece na menor rota/provedor/target comprovada; `unknown` aplica policy conservadora explícita sem promovê-la a alcance reportado. Atualização é atômica, single-flight por escopo e recuperável após restart.
- **P0 — Taxonomia e linguagem:** cobrir todas as categorias normalizadas e preservar `rate_limit_origin` como `gateway`, `upstream` ou `unknown`, separando origem observada, `evidence_scope` e enforcement local. Escopo nasce apenas de headers/metadados saneados e política aprovada; correlação usa ID interno ou fingerprint opaco não reversível, nunca chave/header, e não chega ao contrato público. `rate_limit_unknown_origin` vale somente para origem desconhecida; escopo, janela e reset continuam desconhecidos quando não comprovados, e nunca se afirma “cota diária” sem evidência confiável.
- **P0 — Fallbacks:** H4 habilitado não pode degradar falha de capacidade para `static_lore` e permitir commit; H0/H1 mantêm somente fallback local, determinístico e semântico, sem autoridade mecânica ou factual.
- **P0 — Timing:** `observed_at`, `server_now`, `retry_not_before`, origem e confiança são normalizados no servidor; relógio ou timestamp do cliente não autoriza retomada.
- **P1 — Funções locais e editor:** ficha, histórico, catálogos, navegação e acessibilidade permanecem locais; `DEC-002` decidirá se o editor fica bloqueado ou permite apenas rascunho não submetível.
- **P1 — Recuperação/sondagem:** retry/retomada automática permanece proibido. `DEC-003` escolherá entre **A — sondagem manual controlada**, com uma única chamada sintética mínima, campaign-free e single-flight, seguida de decisão humana separada para retomar; ou **B — sem sondagem sintética**, sem endpoint/comando/botão de verificação, mostrando espera/estado e oferecendo somente uma tentativa direta H6 iniciada pelo jogador após a condição aprovada, com a cápsula congelada e sem H0/H1/H4/RNG. Falha atualiza o gate; nenhum ramo reenvia a ação automaticamente. Sem timing confiável, a regra de elegibilidade também permanece pendente em `DEC-003`.
- **Fechamento condicional:** a implementação futura executa exatamente um ramo; tarefas do ramo não escolhido serão marcadas `N/A por DEC-003`, não pendentes, de modo que ambos os caminhos sejam concluíveis sem dependência órfã.
- **Recomendação não aprovada:** B é o padrão sugerido por usar menos chamadas e ter menor consumo esperado quando a recuperação funciona; A adiciona diagnóstico prévio, mas pode evitar o payload narrativo completo durante indisponibilidade persistente. Em ambos os caminhos, usar consultas locais ao gate, respeitar `retry_not_before`, coalescer concorrência e nunca retomar automaticamente.
- **Estado:** todos os itens acima continuam propostas/gates para aprovação e não autorizam implementação.

## FUTURE_PROJECTION — ALVO/API PAGA — 2026-09-05

- **Status:** PROJEÇÃO FUTURA, sem aprovação, gasto, roadmap ou autorização de implementação. A fronteira LLM-001 já admite alvos compatíveis gratuitos ou pagos, sempre explícitos; isso não seleciona nem recomenda um alvo.
- **Não aprovado:** custo, orçamento, BYOK, credencial, provedor, modelo, roteamento ou fallback.
- **Gate humano futuro:** qualquer uso pago exige decisão separada sobre orçamento e teto, transparência ao usuário, gestão de credenciais e privacidade, medição e alertas, comportamento no esgotamento e identificação explícita do alvo.
- **Relação com pausa/retomada:** um alvo pago nunca pode ser fallback automático de uma pausa. Retomar preserva o alvo explícito; qualquer troca futura exige decisão humana própria.

## DECISIONS_LOCKED
- **Engine Split:** Isolamento total do Motor Mecânico V5 em relação à camada de inferência de linguagem do LLM.
- **Protocol:** Comunicação de tempo real baseada estritamente em canais WebSocket assíncronos.

## CONSTRAINTS
- **Simplicidade Cirúrgica:** Proibido o uso de frameworks ORM pesados ou abstrações corporativas complexas. O backend deve ser enxuto.
- **Isolamento de I/O:** Os arquivos em `client/` estão selados e marcados como FOUNDATION V1. Escrita proibida sem ordem de refatoração de interface.

## FILE_STATUS
| Arquivo | Status | Sessão |
|---|---|---|
| client/index.html | COMPLETED - React Scaffold | 14 |
| client/src/App.tsx | COMPLETED - React with Init integration | 15 |
| client/src/components/InitializationPanel.tsx | COMPLETED - Visual feedback HUD | 15 |
| client/src/hooks/useInitializationLog.ts | COMPLETED - Custom React Hook | 15 |
| client/src/components/* | COMPLETED - React UI Components | 14 |
| client/src/hooks/* | COMPLETED - Custom React Hooks | 14 |
| client/vite.config.ts | COMPLETED - Vite/Vitest Config | 14 |
| api/main.py | COMPLETED - Added Init WS & REST + locks | 16 |
| api/state_service.py | DONE - Injetado Locks de Concorrência | 16 |
| scripts/initialize_game.py| COMPLETED - Async logging feedback loop | 16 |
| scripts/generate_ico.py   | COMPLETED - ICO Gen | 14 |
| scripts/update_shortcut.ps1| COMPLETED - Shortcut Gen | 14 |
| DESIGN.md | COMPLETED - Atualizado para React/Tailwind | 16 |
| DESIGN_SYSTEM.md | COMPLETED - Atualizado para React/Tailwind | 16 |
| Iniciar o Jogo.lnk | COMPLETED | 14 |
| README.md | COMPLETED - Dev Core | 14 |
| AgenteStoryteller_Public/README.md | COMPLETED - Player Focus | 14 |
| PLANO_GERADO.md | COMPLETED | 12 |
| PRODUTO.md | COMPLETED - Atualizado para React/Tailwind | 16 |
| pyrightconfig.json | COMPLETED | 9 |
| requirements.txt | COMPLETED - Incluido Pillow | 16 |
| sync_public.py | COMPLETED | 14 |
| DESIGN_MIGRACAO_DISTRIBUIDA.md | COMPLETED - Blueprint de Migração Distribuída | 17 |
| Dockerfile | COMPLETED - Setup de container Railway | 18 |
| netlify.toml | COMPLETED - Setup de redirecionamento SPA Netlify | 18 |
| api/.env.example | COMPLETED - Configurações backend | 18 |
| client/.env.example | COMPLETED - Variáveis React/Vite | 18 |
| api/requirements.txt | COMPLETED - Dependências de produção | 18 |
| scripts/validate_phase0.py | COMPLETED - Validador automático | 18 |
| api/core/__init__.py | DONE | 5 |
| api/core/config.py | COMPLETED - Pydantic Settings & Gemini | 18 |
| .env.example | DONE | 5 |
| api/orchestrator_service.py | DONE | 12 |
| api/parser_service.py | DONE | 5 |
| api/state_service.py | DONE | 5 |
| api/rules_service.py | DONE | 5 |
| tests/test_concurrency.py | COMPLETED | 3 |
| tests/test_websocket_flows.py | COMPLETED | 3 |
| tests/test_remorse.py | COMPLETED | 5 |

## COMPLETED
- [Sessão 18] Implementação da Fase 0 (Setup de Infraestrutura) da migração distribuída: criação de Dockerfile para Railway, netlify.toml com redirecionamentos SPA e proxy de API para Netlify, arquivos de template api/.env.example e client/.env.example, requirements.txt do backend com versões exatas, refatoração de api/core/config.py com Pydantic Settings/Gemini e criação do script de validação de pré-deploy scripts/validate_phase0.py.
- [Sessão 17] Elaboração da especificação de arquitetura distribuída (DESIGN_MIGRACAO_DISTRIBUIDA.md) detalhando integração com Gemini Free API, persistência distribuída via snapshots JSON sem estado (stateless prompt injection) e plano de deploy Vercel + Railway.
- [Sessão 16] Resolução de incompatibilidades de infraestrutura baseadas na auditoria forense. Correção do arquivo `INICIAR_JOGO.bat` com 4 passos de diagnóstico, automatização do build do frontend e tratamento de erro estruturado com pause. Adição de `Pillow==11.0.0` no `requirements.txt` e alinhamento dos tipos de dados de disciplinas em `data/sheets/base_player.json` de `boolean` para `int`. Configuração de concorrência no backend `api/main.py` e `api/state_service.py` injetando locks de exclusão mútua em chamadas WebSocket de sessão e lock de concorrência global de LLM. Refatoração do script `scripts/initialize_game.py` substituindo prints genéricos por logger estruturado de Python escrevendo logs persistentes em `initialize_game.log`. Atualização de design e produto em `DESIGN.md`, `PRODUTO.md` e `DESIGN_SYSTEM.md` alinhando a documentação da stack com React 19 / Tailwind CSS v4.
- [Sessão 15] Implementação do novo fluxo de inicialização da Fase 2.5. Refatoração do script `scripts/initialize_game.py` para usar um loop assíncrono e enviar logs via HTTP POST com fallback e tratamento de seleção de navegador no terminal. Criação do hook React `useInitializationLog.ts` e do componente de HUD `InitializationPanel.tsx` no client, integrando-o ao `App.tsx` com transições de fade (fade-in 0.3s nos logs, fade-out 0.5s no painel e fade-in no HUD). Adição das rotas WebSocket `/ws/initialization` e endpoints REST `/api/initialization/logs` e `/api/initialization/retry` em `api/main.py`. Validação realizada com build do Vite e pytest bem-sucedidos.
- [Sessão 14] Migração total do frontend de Vanilla JS para React 18+ com TypeScript strict mode e Tailwind CSS v4. Implementação de testes unitários com Vitest e cobertura completa de pips. Inclusão de Dark/Light mode com persistência e acessibilidade WCAG AA. Criação de script de inicialização inteligente em cascata (initialize_game.py) que detecta LM Studio no Windows, testa portas, modelos locais e serve o client compilado de forma transparente. Geração de ícone personalizado (vampire-icon.ico) e atalho do Windows atualizado. Configuração e sincronização de ambos os READMEs (dev e public) com caminhos e guias rápidos simplificados. Refinamento das especificações de IA definindo a obrigatoriedade dos três LLMs locais e seus papéis segregados de mitigação de alucinações. Repositório público sincronizado.
- [Sessão 13] Criação de atalho Windows 'Iniciar o Jogo.lnk', estruturação do repositório de distribuição pública limpo em AgenteStoryteller_Public, geração de README.md humanizado focado em jogadores e escrita do script sync_public.py de sincronização.
- [Sessão 12] Implementação e homologação de todos os Acceptance Criteria pendentes em PLANO_GERADO.md: injeção dinâmica de ficha/lore no Narrador, rotas POST de gerenciamento e upgrades de XP, e testes unitários/latência de cobertura.
- [Sessão 11] Execução do spec-driven-executor para gerar e atualizar PLANO_GERADO.md contendo referências de especificações, 9 ACs (com AC 1, AC 2 e AC 3 marcados como DONE) e alinhamento do design.
- [Sessão 10] Criação do commit inicial (root-commit) do repositório contendo fontes, testes e especificações atualizadas, omitindo arquivos temporários.
- [Sessão 9] Correção de desvios de contrato de infraestrutura: criação de pyrightconfig.json e ajuste de stack do frontend no log para Vanilla JS.
- [Sessão 7] Unificação da especificação técnica em DESIGN.md contemplando diagramas ASCII, padrões de código e targets de performance.
- [Sessão 6] Unificação de escopo, restrições e novos Acceptance Criteria (AC 1 a AC 9) em PRODUTO.md com Decision Log arquitetural.
- [Sessão 5] Módulo D: config centralizada via `pydantic-settings`. Módulo C: schema de Humanidade e Remorso com testes aprovados.
- [Sessão 4] Correção de anotação de tipo de `status_override`, e warnings do Pyright com inclusão de `types-aiofiles` e `aiofiles` nas dependências.
- [Sessão 4] Refatoração de `save_session_state` e movimentação de `sync_event_from_context` para `state_service.py` para corrigir assinaturas.
- [Sessão 3] Schemas de estado sob JSON alvo, persistência com asyncio.Lock contra condições de corrida e testes concorrentes de I/O.
- [Sessão 3] Middleware Interceptor em api/main.py contra TORPOR, gatilho de Fome crítica e teste de Frenesi por WebSocket.

## IN_PROGRESS
Bloqueio: NENHUM

## NEXT_STEP
1. Executar validação local via scripts/validate_phase0.py e iniciar a Fase 1 (Mocks e stubs do backend).

## ERROS_ENCONTRADOS_E_RESOLUCOES_IMPLEMENTADAS
- **ValidationError ao instanciar TrackersModel em testes unitários:** O script de validação obrigatório de humanidade e máculas resultava em falha de inicialização por ausência de `health` e `willpower` no payload.
  *Resolução:* Os atributos `health` e `willpower` foram reconfigurados como `Optional[TrackerDetail] = None` em `api/state_service.py` para permitir inicializações e validações parciais no motor e nos testes unitários.
- **Instabilidade no teste test_pipeline_willpower_reroll:** O arquivo residual de teste em disco `test_wp.json` persistia em execuções consecutivas do `pytest`, causando acúmulo indesejado de dano superficial no tracker.
  *Resolução:* Remoção do arquivo residual antes das execuções e limpeza na fixture do teste.
- **TypeError em save_session_state:** A alteração do schema de estado na Sessão 3 gerou exceções nas chamadas que enviavam 4 argumentos posicionais.
  *Resolução:* A assinatura de `save_session_state` foi ajustada para aceitar polimorficamente `StateUpdateEvent` ou `dict`.
- **Erro de Atribuição de Tipos (status_override):** O parâmetro `status_override` estava anotado com o tipo estrito `str` mas possuía valor padrão `None`.
  *Resolução:* A anotação do parâmetro foi alterada de `str` para `Optional[str] = None`.

## BLOCKERS
- NENHUM
