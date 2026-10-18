---
title: Política de Admissão do Motor Narrativo
version: 0.1
date_created: 2026-08-25
last_updated: 2026-08-27
owner: Produto Agente Storyteller
status: Direção aprovada; perfil experimental implementado; admissão humana pendente
tags: [architecture, llm-002, provider-neutral, online-api, local-inference, onboarding]
---

# Introduction

Esta especificação registra a decisão humana de recomendar APIs de modelos
on-line como caminho operacional padrão do Agente Storyteller, mantendo a
inferência local como opção avançada ou experimental. A pessoa usuária deverá
escolher explicitamente qual provedor e qual modelo servirão de motor narrativo.

A recomendação operacional não altera a arquitetura local-first: regras,
cálculos, fatos canônicos, estado, eventos e saves permanecem sob controle local.
Também não autoriza fornecedor, modelo, orçamento, roteamento ou fallback
específico. A direção foi aprovada em 2026-08-25 e está adiada até a conclusão e
aceitação do trabalho atualmente em curso.

### Atualização de implementação — 27/08/2026

Foi autorizado e implementado um perfil técnico OpenRouter para avaliação
controlada, sem torná-lo provedor padrão do produto. O perfil fixa modelo e
provedor upstream, desabilita fallback, requer os parâmetros solicitados, exige
ZDR no runtime do produto e registra modelo, rota, tokens e custo reportados. Um
corpus sintético opt-in permite comparar candidatos sem acessar campanha, saves,
banco ou `.env`.

Esta atualização não admite ainda nenhum modelo: o primeiro teste vivo, a revisão
humana da narrativa e a aceitação final continuam pendentes. Também não implementa
a tela de configuração descrita nesta especificação nem decide orçamento ou
fallback entre alvos.

## 1. Purpose & Scope

O objetivo é definir como o produto apresenta, verifica e admite um alvo LLM para
uso narrativo no MVP, sem acoplar o domínio a um fornecedor e sem esconder riscos
da opção escolhida.

O escopo futuro inclui:

- apresentar “API on-line” como opção recomendada na configuração inicial;
- apresentar “servidor local” como opção avançada ou experimental;
- exigir escolha explícita de provedor, modelo e alvo exato;
- distinguir configurações verificadas de alvos personalizados não verificados;
- executar diagnósticos seguros antes de declarar um alvo pronto;
- exibir capabilities, proveniência, latência observada e estado de verificação;
- informar riscos próprios de inferência on-line e local;
- preservar a possibilidade de trocar de alvo por ação explícita do usuário.

Ficam fora desta especificação:

- selecionar OpenRouter, Groq, Gemini, Mistral ou qualquer outro fornecedor;
- escolher um modelo padrão específico ou ordenar adaptadores;
- definir catálogo de modelos, preços, orçamento ou política “somente gratuito”;
- definir roteamento, retry entre alvos ou fallback automático;
- definir os thresholds completos de qualidade narrativa de `CAP-001`;
- definir armazenamento e ciclo de vida de credenciais de `SEC-001`;
- alterar o contrato agnóstico aprovado em `LLM-001`;
- implementar a tela de configuração antes do segundo momento.

## 2. Definitions

- **Alvo LLM**: identidade explícita e imutável de uma configuração de inferência,
  contendo ao menos identificador, rótulo de provedor e modelo exato esperado.
- **API on-line**: endpoint remoto que recebe requisições de inferência pela rede.
- **Servidor local**: endpoint de inferência executado no computador ou na rede
  local controlada pela pessoa usuária.
- **Padrão operacional**: caminho recomendado na experiência de configuração; não
  é uma restrição arquitetural nem uma escolha silenciosa de alvo.
- **Perfil verificado**: configuração cuja compatibilidade declarada foi testada
  pelo produto para uma combinação e versão identificáveis.
- **Alvo personalizado**: configuração fornecida pelo usuário que não possui selo
  atual de verificação do produto.
- **Capability**: comportamento observável declarado pelo alvo, como streaming ou
  geração estruturada, representado pelo contrato `LLM-001`.
- **Diagnóstico sintético**: teste sem conteúdo da campanha que verifica conexão,
  contrato e resposta esperada.
- **Proveniência**: registro do alvo solicitado e das identidades efetivamente
  reportadas durante a inferência.
- **Admissão**: decisão explícita de que um alvo pode ser usado pelo produto sob
  um conjunto conhecido de capabilities e avisos.

## 3. Requirements, Constraints & Guidelines

### 3.1 Padrão operacional e escolha humana

- **ADM-001**: A configuração inicial deverá apresentar “API on-line —
  recomendada” antes de “Servidor local — avançado/experimental”.
- **ADM-002**: A recomendação on-line não poderá selecionar silenciosamente um
  fornecedor, modelo, rota ou plano de cobrança.
- **ADM-003**: A pessoa usuária deverá confirmar o alvo exato antes da primeira
  inferência que contenha dados da campanha.
- **ADM-004**: Inferência local deverá continuar disponível quando compatível com
  o contrato, sem ser descrita como universalmente inadequada ou proibida.
- **ADM-005**: Trocar provedor ou modelo exigirá ação explícita. Erro, lentidão,
  rate limit ou indisponibilidade não autorizarão substituição silenciosa.
- **ADM-006**: O caminho recomendado é política de produto, não arquitetura. O
  domínio e os módulos determinísticos deverão permanecer neutros ao fornecedor.

### 3.2 Transparência e diagnóstico

- **ADM-007**: A interface deverá exibir rótulo do provedor, modelo solicitado,
  endpoint classificado como remoto ou local, estado de verificação e data do
  último diagnóstico, sem mostrar credenciais.
- **ADM-008**: Um perfil só poderá ser chamado de verificado para a combinação
  concreta de alvo, modelo, capabilities e evidência coberta pelo teste.
- **ADM-009**: Alvos personalizados poderão ser configurados e diagnosticados,
  mas deverão permanecer marcados como “não verificado” até satisfazer o processo
  futuro de admissão; eles não poderão receber selo “recomendado” por semelhança.
- **ADM-010**: Antes de habilitar o alvo, o produto deverá executar o diagnóstico
  sintético de `LLM-001` e mostrar separadamente conexão, identidade reportada,
  geração estruturada, streaming, deadline/cancelamento e erros observados.
- **ADM-011**: Capabilities desconhecidas ou incompatíveis deverão falhar de modo
  conservador; a interface não poderá convertê-las em suporte presumido.
- **ADM-012**: Português, aderência à intenção, estrutura narrativa, repetição,
  controle indevido do jogador e latência deverão ser avaliados empiricamente.
  Os thresholds e corpus pertencem a `CAP-001`, não a esta política.
- **ADM-013**: Catálogos e identificadores de modelos deverão ser tratados como
  mutáveis. Modelo removido ou renomeado produzirá erro claro e nova escolha, não
  substituição automática.

### 3.3 Comunicação de riscos

- **RSK-001**: A opção local deverá explicar que desempenho e confiabilidade
  dependem de hardware, quantização, tamanho do contexto, servidor e modelo.
- **RSK-002**: A opção local deverá informar que maior latência, falhas de
  geração estruturada, respostas repetitivas e menor qualidade em português são
  riscos a medir no alvo concreto, não propriedades assumidas de todo modelo local.
- **RSK-003**: A opção on-line deverá informar dependência de internet, limites
  de uso, rate limits, mudanças de catálogo e possível custo.
- **RSK-004**: Antes de transmitir conteúdo real da campanha a uma API on-line,
  a interface deverá informar que prompts e contexto sairão do dispositivo e
  solicitar confirmação explícita conforme a futura política `SEC-001`.
- **RSK-005**: A indicação “recomendada” não poderá ser interpretada como
  gratuidade, privacidade superior, disponibilidade garantida ou qualidade
  idêntica entre modelos.
- **RSK-006**: Tokens, chaves e cabeçalhos de autenticação nunca poderão aparecer
  em diagnóstico, log, telemetria, evento canônico, memória ou exportação.

### 3.4 Limites arquiteturais

- **CON-001**: Regras, cálculos, resultados mecânicos, estado e fatos canônicos
  permanecerão locais e determinísticos, independentemente do motor narrativo.
- **CON-002**: O LLM poderá construir narrativa a partir de contexto estruturado,
  mas não poderá criar sozinho fatos canônicos nem sobrescrever resultados.
- **CON-003**: O perfil admitido deverá usar a fronteira `LLM-001`; nenhum SDK ou
  formato específico de fornecedor poderá atravessar para o domínio.
- **CON-004**: Esta especificação não decide custo, gratuidade, fallback,
  roteamento, retries entre alvos ou armazenamento de segredo.
- **CON-005**: O bloqueio original de implementação foi substituído pela
  autorização humana de 27/08/2026 apenas para a integração OpenRouter e a bateria
  comparativa. Tela de configuração, admissão final, orçamento e fallback entre
  alvos continuam fora desse escopo.

## 4. Interfaces & Data Contracts

### 4.1 Perfil conceitual de admissão

Os nomes finais deverão reutilizar os tipos de `LLM-001`. Nenhuma credencial
pertence a este payload de apresentação.

```json
{
  "narrative_engine_profile": {
    "profile_mode": "online_api",
    "recommendation": "recommended",
    "selection": "explicit_user_choice",
    "target": {
      "target_id": "stable-user-selected-id",
      "provider_label": "user-selected-provider",
      "model": "exact-user-selected-model"
    },
    "verification": {
      "status": "verified_or_unverified",
      "evidence_version": "profile-evidence-version",
      "checked_at": "ISO-8601-or-null"
    },
    "capabilities": "LLM-001 capability snapshot",
    "risk_notices": [
      "internet_required",
      "campaign_context_leaves_device",
      "cost_and_limits_may_apply"
    ]
  }
}
```

Um perfil local usa `profile_mode: "local_server"` e deverá acrescentar avisos
de dependência de hardware e latência observada, mantendo a mesma identidade de
alvo, capabilities e proveniência.

### 4.2 Estados mínimos da configuração

```text
unconfigured
  -> target_selected
  -> synthetic_check_running
  -> technically_compatible | incompatible | unavailable
  -> quality_verified | custom_unverified
  -> user_confirmed
  -> active
```

Uma transição de `active` para outro alvo deverá voltar a `target_selected` e
repetir diagnóstico e confirmação. Nenhum erro produz transição automática para
um alvo diferente.

### 4.3 Separação de responsabilidades

| Item | Responsabilidade |
|---|---|
| `LLM-001` | Contrato, capabilities, streaming, erros, proveniência e teste sintético |
| `LLM-002` / esta especificação | Perfis admitidos e apresentação on-line/local |
| `CAP-001` | Corpus, thresholds e qualidade narrativa mínima |
| `LLM-003` | Adaptadores concretos e sua ordem de implementação |
| `SEC-001` | Credenciais, consentimento, privacidade, retenção e redaction |
| Política de custo | Limites, gratuidade, orçamento, cobrança e alertas |
| Política de fallback | Se e como uma troca explícita ou automática poderia ocorrer |

## 5. Acceptance Criteria

- **AC-001**: Dada uma nova configuração, quando a escolha de motor aparecer,
  então “API on-line — recomendada” e “Servidor local — avançado/experimental”
  são opções separadas e igualmente explicadas.
- **AC-002**: Dada a opção on-line, quando o usuário avançar, então nenhum
  fornecedor ou modelo já está escolhido silenciosamente.
- **AC-003**: Dado um alvo selecionado, quando o teste sintético executar, então
  nenhum fato, narrativa, memória, ficha ou segredo da campanha entra no prompt.
- **AC-004**: Dada divergência entre modelo solicitado e reportado, quando o alvo
  responder, então a admissão falha e nenhuma substituição é aceita.
- **AC-005**: Dada capability requerida como desconhecida ou indisponível, quando
  o diagnóstico terminar, então ela é mostrada como incompatível, sem degradação
  silenciosa.
- **AC-006**: Dado um alvo local, quando a configuração for revisada, então os
  avisos de hardware, latência e qualidade aparecem antes da confirmação e são
  acompanhados por resultados observados quando disponíveis.
- **AC-007**: Dado um alvo on-line, quando a primeira transmissão real estiver
  prestes a ocorrer, então os riscos de privacidade, internet, limites e custo
  são apresentados e a confirmação explícita é registrada.
- **AC-008**: Dado que a confirmação de transmissão não foi concedida, quando o
  jogo tentar enviar contexto a uma API on-line, então a chamada não ocorre.
- **AC-009**: Dado um alvo personalizado, quando ele passar apenas pelo teste
  sintético, então pode ser descrito como tecnicamente compatível, mas não recebe
  selo de qualidade narrativa verificada sem `CAP-001`.
- **AC-010**: Dado erro, timeout, rate limit ou indisponibilidade, quando a
  inferência terminar, então o alvo permanece o mesmo e o produto oferece retry
  no mesmo alvo ou escolha humana, nunca fallback oculto.
- **AC-011**: Dado que um modelo deixou de existir no catálogo remoto, quando a
  chamada falhar, então o produto exibe o identificador indisponível e solicita
  nova escolha sem adotar o sucessor sugerido pelo fornecedor.
- **AC-012**: Dado que o usuário troca de alvo, quando a próxima narrativa for
  gerada, então o novo alvo foi diagnosticado e confirmado e sua proveniência é
  registrada nos resultados correspondentes.
- **AC-013**: Dado qualquer log ou tela diagnóstica, quando for inspecionado,
  então não contém chave, token ou cabeçalho de autenticação.
- **AC-014**: Dado um alvo gratuito ou pago, quando ele for avaliado por esta
  política, então o preço não é convertido em capability ou qualidade presumida.

## 6. Test Automation Strategy

- **Unitários**: máquina de estados de configuração, ordenação dos perfis,
  rótulos, confirmação explícita e ausência de escolha automática.
- **Contrato**: suíte `LLM-001` para identidade, capabilities, structured output,
  streaming, cancelamento, deadline, erros e proveniência.
- **Integração**: diagnóstico sintético com fake gateway, target mismatch,
  catálogo indisponível e mudança explícita de alvo.
- **Segurança de fronteira**: provar que payload de diagnóstico não contém dados
  de campanha e que valores de credencial são redigidos; detalhes pertencem a
  `SEC-001`.
- **End-to-end**: configuração on-line, configuração local, alvo personalizado,
  recusa de consentimento, falha de conexão e troca humana de modelo.
- **Qualidade**: corpus e thresholds de português, intenção, estrutura,
  repetição, agência e latência serão definidos por `CAP-001`.
- **Dados de teste**: usar alvos falsos e respostas sintéticas por padrão; testes
  vivos deverão ser opt-in e nunca depender de credencial em CI comum.

## 7. Rationale & Context

Os módulos determinísticos reduzem o trabalho do modelo: regras, cálculos,
estado e consequências mecânicas não precisam ser improvisados pela geração.
Isso, porém, não elimina a exigência central do motor narrativo. Um narrador
repetitivo, controlador, lento ou incapaz de seguir a intenção do jogador é uma
falha fatal de experiência, ainda que a mecânica esteja correta.

APIs on-line são recomendadas operacionalmente porque tendem a reduzir a
dependência do hardware do usuário e oferecem uma rota mais simples para modelos
capazes. Essa é uma hipótese de produto que deverá ser validada nos alvos
concretos, não uma afirmação de que todo serviço remoto supera todo modelo local.

Manter a escolha explícita preserva agência, privacidade e rastreabilidade. Manter
a fronteira neutra evita que a recomendação de hoje se torne dependência rígida
de um catálogo que pode mudar amanhã.

## 8. Dependencies & External Integrations

### External Systems

- **EXT-001**: Endpoint de inferência escolhido pelo usuário, remoto ou local,
  compatível com um adaptador admitido posteriormente.

### Data Dependencies

- **DAT-001**: Snapshot de capabilities e evidência de diagnóstico sem dados da
  campanha.
- **DAT-002**: Proveniência por invocação para distinguir alvo solicitado e
  efetivamente reportado.

### Technology Platform Dependencies

- **PLT-001**: Fronteira agnóstica `LLM-001` e composição explícita de alvo.
- **PLT-002**: Tela futura de configuração capaz de mostrar estado, avisos e
  resultado de diagnóstico.

### Compliance Dependencies

- **COM-001**: `SEC-001` deverá definir consentimento, credenciais, retenção e
  comunicação de privacidade antes do lançamento de perfis on-line.

Não há fornecedor, modelo, SDK, plano comercial ou serviço obrigatório definido
por esta especificação.

## 9. Examples & Edge Cases

### Exemplo de escolha on-line

```text
Motor narrativo

( ) API on-line — Recomendada
    Menor dependência do hardware local. Requer internet e pode enviar
    contexto da campanha a um terceiro. Limites e custos podem existir.

( ) Servidor local — Avançado/experimental
    Mantém a inferência sob seu controle, mas qualidade e tempo de resposta
    dependem do seu hardware, servidor e modelo.
```

Depois da escolha, a interface solicita e mostra o provedor e o modelo exatos,
executa o diagnóstico sintético e somente então solicita confirmação.

### Casos de borda obrigatórios

- endpoint remoto compatível com protocolo, mas modelo reportado diferente;
- servidor local rápido, mas sem geração estruturada confiável;
- alvo tecnicamente compatível, porém ainda não avaliado em português;
- modelo remoto gratuito que muda limite ou deixa o catálogo;
- alvo pago selecionado sem política de orçamento aprovada;
- falta de internet durante uma campanha que usa API on-line;
- credencial ausente, inválida ou revogada;
- rate limit depois de parte do stream;
- usuário recusa envio de conteúdo e volta à seleção;
- troca deliberada de modelo no meio de uma campanha;
- provedor sugere substituição automática de modelo;
- servidor local potente que passa por todos os critérios futuros.

## 10. Validation Criteria

- A experiência recomenda o perfil on-line sem selecionar fornecedor ou modelo.
- A alternativa local permanece disponível, honesta e testável.
- Todo alvo é explícito, diagnosticado e acompanhado de proveniência.
- Perfil verificado e alvo personalizado não são apresentados como equivalentes.
- Nenhuma falha troca alvo ou cria gasto por conta própria.
- Dados de campanha não entram no diagnóstico sintético.
- Riscos on-line e locais são apresentados antes do uso correspondente.
- O domínio continua sem SDKs ou tipos específicos de fornecedor.
- Provedores, modelos, orçamento, fallback, `CAP-001`, `LLM-003` e `SEC-001`
  permanecem decisões separadas.
- Nenhuma implementação começa antes da conclusão e aceitação do trabalho atual.

## 11. Related Specifications / Further Reading

- `plan/architecture-llm-memory-turns-1.md` — implementação predecessora de
  `LLM-001`, eventos, contexto e memória; deve ser concluída e aceita primeiro.
- Itens posteriores relacionados: `CAP-001`, `LLM-003`, `SEC-001`, política de
  custo e política de fallback.
- Decisão humana de 2026-08-25: APIs on-line recomendadas por padrão operacional,
  escolha explícita do alvo e inferência local mantida como opção avançada ou
  experimental com limitações transparentes.
