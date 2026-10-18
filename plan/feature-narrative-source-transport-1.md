---
goal: Preparar transporte optativo B separado do fluxo legado e com eventos públicos mínimos
version: 1
date_created: 2026-09-11
last_updated: 2026-09-21
owner: Agente Storyteller
status: 'Completed — local opt-in accepted'
tags: [narrative-source, transport, opt-in]
---

# Introduction

![Status: Completed — local opt-in accepted](https://img.shields.io/badge/status-Completed%20local%20opt--in-brightgreen)

O setup autorado e a composição interna atendem uma cena nova B por uma entrada
optativa separada. O recorte foi aceito em 21/09/2026 para um único operador no
desktop, exclusivamente em loopback. Não substitui o jogo completo v1, não é
montado no `App` legado e não implementa campanha híbrida.

Prioridade reconciliada na retomada de11/09/2026: executar primeiro a preparação
e comparação delimitada de modelos em [feature-source-model-comparison-1.md](feature-source-model-comparison-1.md).
O comparativo histórico não autorizou a ativação. A autorização atual veio depois,
como decisão humana específica pelo recorte local-only; não aprova acesso direto
por outra máquina, conta, proxy, CAP-001, provedor ou modelo padrão.

## 1. Requirements & Constraints

- **REQ-001**: Seleção B explícita no servidor antes de load_session_state,
  load_or_migrate_campaign ou start_attempt genérico do websocket_endpoint.
  Uma flag recebida do cliente não converte save v1 nem autentica sessão B.
- **REQ-002**: Criação recebe SourceSetupRequest; identidade, ficha sintética,
  relações e SourceProducerConfig vêm do servidor. Bootstrap separado, criação
  atômica e recusa de sessão existente seguem o contrato de setup.
- **REQ-003**: Ação recebe somente SourcePlayerActionRequest. O handler chama
  prepare_source_player_action e, apenas com K pronto, execute_retained_source_turn.
  Pending/terminal não permitem takeover, nova rolagem, retry ou troca de target.
- **REQ-004**: Reapresentar briefing com origem autorada, usando leitor somente
  leitura. Reconexão não produz fala automática. Exibir último texto confirmado
  e estado da operação por leitores B, sem migrar contexto v1.
- **REQ-005**: Eventos públicos versionados são projeções explícitas; nunca
  serializar SourceInputClaim, request interno, cápsula, target, SYSTEM, estado
  integral, error_json, evidência bruta ou can_retry. Usar código/estágio seguros.
- **REQ-006**: Erro deve preservar texto e identidade da ação na interface;
  reconectar/consultar não significa reenviar. Explicar limite da gramática antes
  do uso sem despejar termos internos no fluxo do jogador.
- **CON-001**: O opt-in usa factory, rota e página separadas pelo lançador local.
  Rotas/UI/default v1 permanecem inalterados. Não é autorização CAP-001.
- **CON-002**: Manter jogo/save manual, decisões CAMP e DEC, fontes e gates.
  Não criar contas, sistema de credenciais, proxy público ou política nova de
  acesso remoto como detalhe deste transporte local.

## 2. Implementation Steps

### Implementation Phase 1

- GOAL-001: Fixar seleção e contrato público após a observação representativa.

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-001 | Em api/main.py e api/state_service.py, confirmar autenticação/vínculo da sessão e escolher ponto anterior ao legado; registrar tabela de despacho sem tratar UUID como autorização. Se novo modelo de acesso for necessário, concluir alternativa concreta e escalar só essa decisão. | Sim: factory separada e vínculo server-side local-only evitam o endpoint legado | 2026-09-21 |
| TASK-002 | Em novo api/narrative_source_transport.py, definir eventos públicos estritos para briefing, preparação pendente/recusada, narrativa pendente/completa/recusada e falha indisponível. Campo operation_id conserva identidade; texto confirmado vem do envelope validado. Nenhum objeto interno completo é retornado. | Sim | 2026-09-11 |
| TASK-003 | Em tests/test_narrative_source_transport.py, verificar projeção contra dados privilegiados, campos extras, causa desconhecida e adulteração; cobertura da seleção B anterior aos leitores e reservas v1. | Sim | 2026-09-21 |

### Implementation Phase 2

- GOAL-002: Integrar somente a superfície optativa cuja experiência foi avaliada.

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-004 | Implementar handler B separado após TASK-001/003, ligando setup, intenção, P/K/H e consultas. Usar gateway explícito do servidor, cancelamento/deadline e arbitragem existentes; nenhuma chamada diagnóstica implícita. | Sim | 2026-09-21 |
| TASK-005 | Definir arquivos client afetados após inspeção e integrar opt-in visível, briefing reapresentável, ação conservada e consulta/replay. Testar desconexão antes/depois commit sem repetir produção ou entrega. | Sim | 2026-09-21 |
| TASK-006 | Executar teste de uso limitado após provas técnicas e evidência narrativa; documentar limitações observadas, atualizar README/retomada e manter default v1. | Sim | 2026-09-21 |

### Inspeção inicial de TASK-001 em 11/09/2026

Em api/main.py, websocket_endpoint recebe session_id da URL e aceita a conexão
antes da leitura de estado (linhas647/648/696 nesta versão). Não foi encontrado
vínculo explícito de proprietário/principal nessa entrada. A declaração FastAPI
local não instala middleware de autenticação. api/core/config.py possui host
default127.0.0.1; a presença de allowed_hosts na configuração não demonstra por
si só aplicação de controle no endpoint. Não foi feita inferência sobre exposição
remota efetiva, nem inspeção de credenciais ou mudança do servidor atual.

Esse caminho legado não pode servir como prova de autorização para uma nova rota
B. A seleção deve ficar fora dele ou antes de sua inicialização; o vínculo de
acesso de uma superfície nova precisa ser especificado antes da ativação. Não
introduzir autenticação por token/contas como detalhe não aprovado. A verificação
interna sintética continua independente disso. TASK-001 permanece pendente quanto
à escolha do contrato de acesso/rota; a investigação acima já está registrada.

## 3. Alternatives

- **ALT-001**: Trocar apenas H6 no handler legado é incompatível: migração e
  reserva genérica já ocorreram antes.
- **ALT-002**: Serializar claims/cápsulas facilita implementação mas revela
  dados internos; usar projeções explícitas.
- **ALT-003**: Rota dedicada pode reduzir mistura com v1; só escolher após
  verificar vínculo de sessão e dependências na TASK-001.

## 4. Dependencies

- **DEP-001**: Setup, produtor, retenção, executor e leitores B verificados.
- **DEP-002**: Observação de diálogo e espera com setup/ação real, preparada em
  feature-source-player-probe-1.md, antes de ativar a experiência.
- **DEP-003**: Acesso remoto relatado pelo usuário não define autenticação de
  novas rotas. Não expor serviço ou porta para satisfazer um teste local.

## 5. Files

- **FILE-001**: api/main.py, api/state_service.py como referências de seleção.
- **FILE-002**: Novos api/narrative_source_transport.py e teste correspondente.
- **FILE-003**: client/ somente após TASK-005 identificar componentes de fluxo.
- **FILE-004**: README.md, relatórios e PROMPT_RETOMADA_2026-09-06.md.

## 6. Testing

- **TEST-001**: Nenhum leitor/reserva v1 chamado em seleção B e vice-versa.
- **TEST-002**: Mensagens públicas não contêm dados privados ou autoridade forjada.
- **TEST-003**: Conexões concorrentes, retomada antiga e terminal não repetem RNG/H6.
- **TEST-004**: Introdução não avança contadores; histórico rola mantendo HUD visível.
- **TEST-005**: Qualidade narrativa e conclusão da campanha não inferidas do teste técnico.

## 7. Risks & Assumptions

- **RISK-001**: Perfil local limitado pode frustrar quem espera campanha completa.
- **RISK-002**: Novo endpoint sem vínculo de acesso verificado pode ampliar exposição.
- **ASSUMPTION-001**: Plano é preparação documental; não implica entrega do transporte.

## 8. Related Specifications / Further Reading

- [Setup](feature-narrative-source-setup-1.md)
- [Entrada](feature-narrative-source-opt-in-entry-1.md)
- [Observação do produtor](feature-source-player-probe-1.md)
- [Campanha híbrida](checklist-planejamento-campanha-hibrida.md)

### Recorte interno após observação de 11/09/2026

O lote source-player83921947 encerrou tecnicamente aprovado, com experiência
parcial; não autoriza ativação. TASK-002 e a parte de projeção de TASK-003 podem
avançar independentemente do contrato de acesso, pois não criam handler/rota/UI.

Contrato local: project_source_briefing revalida manifesto/sessão; preparação
projeta pending/ready/rejected a partir de claim validado; operação revalida
snapshot/sessão/operação e, para complete, o envelope do turno confirmado.
retained_unstarted permanece distinguível de narrativa pending. Complete contém
somente operation_id e fonte integral n/q; nunca inferir turn_number atual para
replay antigo. Session/estado/target/config/claims/cápsulas/hashes internos e
diagnóstico bruto não são payloads públicos. Causa conhecida usa vocabulário
fechado; desconhecida vira unavailable, sem ocultar inconsistência de identidade.

As funções são puras: validação de consistência não autentica cliente, propriedade
da sessão ou commit de banco. O futuro chamador continua responsável por consumir
leitores confiáveis. Extras e cópias forjadas são recusados; conteúdo já confirmado
não é modificado. Testes cobrem ausência de dados privilegiados, estados, ligação
do turno e imutabilidade; despacho anterior ao legado depende de TASK-001/004 e
não será contabilizado como implementado nesta parte de TASK-003.

### Alternativas de acesso verificadas em 11/09/2026

Revisão independente confirmou: main recebe session_id na URL e aceita WebSocket
sem principal/proprietário; state_service carrega por esse ID; o frontend extrai
o ID da URL. allowed_hosts/cors_origins declarados não têm controle consumidor
encontrado na API. O launcher de uso teste fixa loopback, banco isolado e confere
o PID do listener; isso identifica o seu servidor, não autentica o jogador.
Não foi inspecionada a exposição efetiva do servidor nem o acesso remoto atual.

| Alternativa | Fronteira e trabalho necessário | Decisão |
|---|---|---|
| Ensaio de um operador no desktop | Processo optativo, loopback, banco sintético, sessão B escolhida pelo servidor; conferir seleção/sessão/origem/host antes do accept ou de leitores/reservas. Confiança explícita no desktop e nos processos locais. | Desenho/testes inativos podem aproveitar o padrão de ensaio existente. Ativação depende de experiência/aceitação do recorte. |
| Serviço acessado diretamente de outra máquina | Fronteira autenticada escolhida, revogação, vínculo de sessão/operação, backend protegido de acesso direto; não confiar em UUID ou cabeçalho livre. | Nova decisão de arquitetura humana antes de implementar identidade/proxy/contas ou abrir acesso. |

Acompanhar o desktop remotamente não exige, por si, expor a API remotamente.
Nenhuma dessas alternativas foi ativada. TASK-001 tem inspeção e alternativas
concluídas; seleção/ligação de rota continua pendente. O contrato público puro
não depende dessa escolha nem transforma consistência por hash em autenticação.

### Fechamento do contrato público puro

TASK-002 e a parte projetiva de TASK-003 concluídas e revisadas:215 casos distintos
finais verdes,205 novos+10regressões. Três casos reais de falha terminal foram
reproduzidos antes do ajuste de pares código/status; logs iniciais preservados.
[Relatório](../evals/narrator/reports/narrative-source-public-projection-2026-09-11.md).
TASK-003 ainda não comprova despacho/seleção B antes do legado: depende de
TASK-001/004. Nenhum handler, rota, UI, default, autenticação ou teste live novo.

### Retomada após comparativo e correção local

Comparativo 61b83a2f encerrado sem candidato qualificado; correção prospectiva de
agência concluída com 1.097 testes. Não há ativação automática. A
[tabela de despacho](source-local-dispatch-design-2026-09-11.md) especifica a seleção
pré-accept e seus limites. O próximo incremento independente implementa somente
factory/seletor inativos em api/narrative_source_local_selection.py e teste novo.
Vínculo pertence ao servidor; filtros de destino/habilitação/sessão/Host/Origin
antecedem a consulta B de manifesto. Falha B nunca escolhe legado. Sem montagem,
handler, accept, reserva, nova rota, main/state_service/UI ou modelo default.
TASK-001/003 não podem ser marcadas como integração comprovada por essas provas.

### Fechamento do seletor local inativo

Factory e seletor concluídos com 73 testes próprios aprovados e revisão
independente, incluindo SQLite real, ausência de criação/mutação, erros seguros
e cancelamento. [Relatório](../evals/narrator/reports/narrative-source-local-selection-2026-09-11.md).
TASK-001 possui agora desenho e contrato inativo; ligação anterior ao accept e
isolamento no lifespan ainda dependem da integração. TASK-003 comprova filtros
antes da consulta B no componente isolado, sem provar endpoint montado.
TASK-004/005/006 continuam pendentes. CON-001/002 e DEP-005 da entrada optativa
permanecem; modelo/default/experiência/CAP-001 não foram promovidos.


### Composição técnica optativa concluída em 12/09/2026

O [incremento local-handler](feature-narrative-source-local-handler-1.md) concluiu
a factory/handler isolados, entrada técnica própria e sua composição sintética.
Essas provas atendem a preparação técnica de TASK-001/003/004/005, incluindo
seleção pré-accept, ausência do bootstrap v1, consulta/reconexão e REQ-006.
As linhas pendentes acima conservam o escopo de ativação para uso do jogador;
não devem ser interpretadas como ausência dos componentes técnicos já concluídos.

Nenhuma alteração em main/App/default para ativar B; TASK-006, aceitação do recorte
e qualidade narrativa permanecem distintas. Não há nova autenticação ou exposição
remota. [Evidência da composição](../evals/narrator/reports/source-local-resume-2026-09-12.md).
O diagnóstico de orçamento por campo segue em plano próprio, sem bloquear nem
reclassificar as provas técnicas concluídas ou o comparativo anterior.

### Aceitação e renovação das provas em 21/09/2026

O usuário confirmou a alternativa recomendada: experiência local de um único
operador, limitada a `127.0.0.1`, sem publicar a API para acesso direto de outra
máquina. A entrada aceita continua sendo o lançador separado; `api.main:app` e o
`App` legado não mudam de default.

Na renovação, 598 testes backend passaram, com uma única deselection da falha
preexistente de sidecars SQLite em Windows; 245 testes frontend passaram; o build
`vite.source-player-trial.config.ts` concluiu; e o preflight operacional encerrou
com código 0 sem solicitar chave, criar banco, abrir listener ou iniciar inferência.
[Relatório de ativação](../evals/narrator/reports/source-local-opt-in-activation-2026-09-21.md).
