---
title: Redesenho Acessível da Interface de Jogo
version: 0.1
date_created: 2026-08-25
last_updated: 2026-08-25
owner: Produto Agente Storyteller
status: Aprovada e adiada para o segundo momento
tags: [design, ux, accessibility, light-theme, typography, responsive-layout]
---

# Introduction

Esta especificação registra a decisão humana de redesenhar a interface do
Agente Storyteller após a observação de dois problemas de uso: o modo claro não
oferece contraste confortável e a composição atual de layout e tipografia não
forma uma experiência visual coerente.

O trabalho deverá tratar contraste como requisito de acessibilidade e o restante
como um redesenho integrado, não como correções isoladas de cor, margem ou fonte.
A direção foi aprovada em 2026-08-25, mas está deliberadamente adiada até a
conclusão e a aceitação do trabalho atualmente em curso.

## 1. Purpose & Scope

O objetivo é produzir uma interface legível, confortável, responsiva e coerente
com uma experiência narrativa de Vampiro: A Máscara V5, preservando a clareza
dos controles e do estado mecânico.

O escopo futuro inclui:

- correção completa do contraste no modo claro;
- revisão do modo escuro para evitar regressões e inconsistências entre temas;
- reorganização da hierarquia e das zonas principais da interface;
- definição de papéis tipográficos distintos para narrativa, controles e acentos;
- criação de tokens semânticos de cor, tipografia, espaçamento e estado;
- comportamento responsivo para desktop, tablet e celular;
- validação automatizada e humana de acessibilidade e conforto visual;
- compatibilidade planejada com a futura bandeja de dados visível.

Ficam fora desta especificação:

- implementação imediata do redesenho;
- escolha final de paleta, famílias tipográficas ou ilustrações sem protótipo;
- alteração do motor de regras, do fluxo transacional ou do contrato LLM;
- implementação da bandeja de dados;
- mudança de identidade do produto sem revisão humana dos protótipos;
- refatoração oportunista de componentes não necessária ao redesenho futuro.

## 2. Definitions

- **Modo claro**: conjunto de superfícies, textos, bordas e estados usado quando
  o tema claro estiver ativo.
- **Contraste composto**: contraste calculado depois da aplicação real de
  transparência, sobreposição, textura e cor de fundo, e não apenas entre os
  valores nominais dos tokens.
- **Token semântico**: variável nomeada pela função visual, como texto primário
  ou borda de foco, em vez de pelo tom específico.
- **Zona narrativa**: área destinada ao histórico, à resposta em streaming e à
  leitura contínua da história.
- **Zona de ação**: área destinada à intenção do jogador, aos controles de ação
  e, futuramente, à bandeja de dados.
- **HUD**: apresentação de ficha, recursos, relacionamentos e outros dados do
  personagem necessários durante o jogo.
- **Fonte decorativa**: família de forte identidade visual, adequada apenas a
  acentos curtos e dispensável para a compreensão funcional.
- **WCAG**: Web Content Accessibility Guidelines, referência de acessibilidade
  publicada pelo W3C.

## 3. Requirements, Constraints & Guidelines

### 3.1 Contraste e acessibilidade

- **A11Y-001**: O modo claro deverá ser tratado como defeito de acessibilidade
  até que todas as combinações relevantes sejam inventariadas e validadas.
- **A11Y-002**: Texto normal deverá atingir contraste mínimo de `4.5:1`; texto
  grande poderá usar o mínimo de `3:1`, conforme WCAG 2.2 nível AA.
- **A11Y-003**: Bordas, ícones, indicadores de foco e informação visual
  necessária para identificar controles ou seus estados deverão atingir
  contraste mínimo de `3:1` contra cores adjacentes.
- **A11Y-004**: A validação deverá usar as cores finais compostas. Opacidade,
  textura, blur, hover, seleção e sobreposição não poderão reduzir o contraste
  efetivo abaixo dos limites aceitos.
- **A11Y-005**: Cor não poderá ser a única forma de distinguir conexão, erro,
  Fome, dano, seleção, foco, sucesso ou falha. Texto, ícone, forma ou padrão
  deverá fornecer uma segunda indicação quando o significado for funcional.
- **A11Y-006**: Estados `default`, `hover`, `focus-visible`, `active`, `selected`,
  `disabled`, `loading` e `error` deverão continuar identificáveis nos dois temas.
- **A11Y-007**: A interface deverá ser operável por teclado, tolerar zoom e
  reflow sem ocultar ações essenciais e respeitar preferência de movimento
  reduzido.
- **A11Y-008**: Texturas e efeitos atmosféricos deverão ser decorativos,
  desativáveis quando necessário e incapazes de degradar a leitura.

### 3.2 Hierarquia e layout

- **UXR-001**: A arquitetura visual deverá organizar quatro zonas reconhecíveis:
  cabeçalho/status, narrativa/histórico, ficha/contexto e ação/bandeja de dados.
- **UXR-002**: A narrativa deverá permanecer o foco visual primário; a ficha
  deverá apoiar a decisão sem competir continuamente com o texto narrativo.
- **UXR-003**: A zona de ação deverá permanecer acessível durante o turno e
  acomodar estados futuros de intenção, proposta de rolagem, resolução e retry.
- **UXR-004**: Em desktop, ficha/contexto poderá ocupar uma coluna auxiliar. Em
  telas menores, deverá usar navegação ou painel explícito sem encobrir
  permanentemente narrativa e ação.
- **UXR-005**: O redesenho deverá minimizar rolagens internas concorrentes,
  sobreposições ambíguas e controles fixos que cubram conteúdo.
- **UXR-006**: Estado de conexão, processamento, falha e recuperação deverá
  aparecer perto do contexto afetado, sem depender apenas do cabeçalho.
- **UXR-007**: Densidade, espaçamento e agrupamento deverão comunicar hierarquia;
  linhas e caixas não deverão ser usadas como substituto indiscriminado de
  organização visual.

### 3.3 Tipografia e leitura

- **TYP-001**: A tipografia deverá usar papéis semânticos e uma escala consistente
  para narrativa, dados, rótulos, controles, títulos e acentos decorativos.
- **TYP-002**: Uma fonte serifada legível é recomendada para narrativa e títulos
  editoriais; uma fonte sem serifa é recomendada para controles, estado e dados.
- **TYP-003**: Fontes decorativas deverão ser restritas a marca ou acentos muito
  curtos. Elas não poderão ser usadas em corpo narrativo, ajuda, formulário,
  indicador de estado ou controle necessário.
- **TYP-004**: As famílias escolhidas deverão cobrir português brasileiro,
  incluindo diacríticos, pontuação, itálico e pesos realmente usados.
- **TYP-005**: O corpo funcional não deverá ser menor que `16px` no tamanho base.
  A narrativa deverá usar altura de linha mínima de `1.5` e largura de leitura
  preferencial entre 55 e 75 caracteres por linha em desktop.
- **TYP-006**: Falha ou bloqueio no carregamento de uma fonte remota não poderá
  tornar o conteúdo ilegível, deslocar controles essenciais ou ocultar ícones.

### 3.4 Sistema visual e governança

- **DSN-001**: Cores deverão ser expostas por tokens semânticos para superfície,
  texto, borda, foco, acento e estados; componentes não deverão depender de uma
  combinação de tema codificada localmente sem necessidade.
- **DSN-002**: Um mesmo componente deverá preservar função e hierarquia entre os
  temas. Tema claro não será uma inversão aproximada do tema escuro.
- **DSN-003**: O protótipo deverá representar conteúdo realista: narrativa longa,
  nomes extensos, acentos em português, ficha densa, erros, streaming e ausência
  de dados.
- **DSN-004**: A identidade visual final e as famílias tipográficas exatas deverão
  ser aprovadas por revisão humana de protótipos antes da implementação ampla.
- **CON-001**: Esta especificação não autoriza implementação imediata. O trabalho
  começa somente depois que o escopo atual for concluído e aceito.
- **CON-002**: O redesenho não poderá alterar fatos canônicos, regras, protocolo
  de turno ou autoridade do backend por conveniência visual.
- **CON-003**: A implementação futura deverá preservar a interface funcional
  durante a transição e evitar uma reescrita total sem migração incremental.

## 4. Interfaces & Data Contracts

### 4.1 Zonas de interface

| Zona | Responsabilidade | Conteúdo mínimo |
|---|---|---|
| Cabeçalho/status | Identidade e estado global | sessão, conexão, tema, ajuda |
| Narrativa/histórico | Leitura e continuidade | ações, narrativa, streaming, erros contextuais |
| Ficha/contexto | Apoio à decisão | atributos, recursos, relações e estado relevante |
| Ação/bandeja | Agência do jogador | intenção, envio, proposta e futura rolagem |

### 4.2 Contrato conceitual de tokens

Os nomes finais serão refinados no design system, mas os papéis mínimos deverão
ser equivalentes a:

```yaml
theme:
  surface:
    canvas: required
    panel: required
    elevated: required
  text:
    primary: required
    secondary: required
    inverse: required
  interactive:
    accent: required
    focus: required
    disabled: required
  semantic:
    error: required
    warning: required
    success: required
    hunger: required
  border:
    subtle: required
    strong: required
```

Todo token deverá ter valor definido para tema claro e escuro, com pares de
contraste documentados. O contrato não fixa aqui valores hexadecimais.

## 5. Acceptance Criteria

- **AC-001**: Dado o modo claro, quando qualquer texto normal for medido contra
  o fundo final composto, então o contraste é igual ou superior a `4.5:1`.
- **AC-002**: Dado um controle interativo em qualquer estado relevante, quando
  seu limite, ícone ou indicador necessário for medido, então atinge `3:1` e
  permanece identificável sem depender apenas de cor.
- **AC-003**: Dado um usuário navegando por teclado, quando percorrer os controles,
  então a ordem é lógica, o foco é sempre visível e nenhuma ação essencial fica
  presa ou inacessível.
- **AC-004**: Dada uma narrativa longa em desktop, quando for exibida, então a
  coluna de leitura permanece dentro da largura preferencial e não é comprimida
  desnecessariamente pela ficha.
- **AC-005**: Dada uma tela de celular, quando ficha ou ajuda forem abertas,
  então o jogador pode retornar à narrativa e à ação sem perda de conteúdo ou
  controle encoberto.
- **AC-006**: Dado zoom de `200%`, quando a tela principal for usada, então o
  conteúdo essencial reflui e não exige rolagem bidimensional para concluir a ação.
- **AC-007**: Dada preferência por movimento reduzido, quando ocorrer streaming,
  transição ou futura rolagem, então a informação textual permanece imediata e
  a animação não é obrigatória.
- **AC-008**: Dada falha de carregamento da fonte preferencial, quando os fallbacks
  forem usados, então texto, ícones e controles continuam legíveis e operáveis.
- **AC-009**: Dado o mesmo componente nos temas claro e escuro, quando seus
  estados forem comparados, então a função e a hierarquia são equivalentes.
- **AC-010**: Dado um protótipo com conteúdo realista, quando submetido à revisão
  humana, então contraste, layout e tipografia são aceitos antes da migração ampla.
- **AC-011**: Dada a futura bandeja de dados, quando inserida na zona de ação,
  então não exige a reconstrução das demais zonas nem encobre a narrativa.

## 6. Test Automation Strategy

- **Contraste**: validação automatizada dos pares de tokens e inspeção das cores
  compostas para cada tema e estado.
- **Componentes**: testes de acessibilidade para nome, papel, estado, teclado e
  foco em cada componente interativo.
- **Responsividade**: matriz de viewports para celular estreito, celular amplo,
  tablet, notebook e desktop largo, incluindo zoom e textos extensos.
- **Regressão visual**: snapshots dos dois temas e dos estados críticos, com
  tolerâncias pequenas e revisão humana de alterações intencionais.
- **Fluxos end-to-end**: inicialização, ação, streaming, erro, reconexão, abertura
  da ficha e retorno ao jogo sem controle oculto.
- **Teste humano**: revisão com tarefas reais de leitura e ação; conformidade
  automática não substitui avaliação de conforto, hierarquia e ritmo narrativo.
- **Ferramentas**: a escolha de bibliotecas específicas fica para o plano de
  implementação; a especificação fixa os comportamentos, não o fornecedor.

## 7. Rationale & Context

O problema observado no modo claro não é apenas estético: baixo contraste
transforma conteúdo existente em conteúdo praticamente indisponível e produz
desconforto contínuo. A correção deve considerar a composição real de cores,
porque fundos translúcidos e texturas podem invalidar um par que parece adequado
quando medido isoladamente.

Layout e tipografia formam um único sistema de leitura. A história deve ter ritmo
editorial, enquanto controles e números precisam ser rápidos de escanear. Uma
família decorativa aplicada amplamente enfraquece ambos os objetivos; usada como
acento, ela pode preservar atmosfera sem comprometer clareza.

## 8. Dependencies & External Integrations

### Infrastructure Dependencies

- **INF-001**: Pipeline frontend capaz de executar testes de componentes,
  acessibilidade e regressão visual.

### Data Dependencies

- **DAT-001**: Cenários realistas de narrativa, ficha, erro, streaming e estados
  vazios para prototipação e testes.

### Technology Platform Dependencies

- **PLT-001**: Aplicação React existente e sua estratégia atual de temas.
- **PLT-002**: Suporte do navegador a preferências de cor e movimento reduzido.

Não há dependência de provedor LLM, serviço de nuvem ou nova tecnologia de
persistência para decidir ou prototipar este redesenho.

## 9. Examples & Edge Cases

### Hierarquia pretendida

```text
[ Sessão | conexão | tema | ajuda ]

[ Narrativa e histórico                 ][ Ficha/contexto ]
[ Texto do narrador e ações do jogador  ][ Recursos       ]

[ Intenção / ação / futura bandeja de dados                ]
```

### Casos de borda obrigatórios

- narrativa de vários parágrafos com itálico e pontuação em português;
- ficha com nomes longos e valores ausentes;
- streaming simultâneo a indicador de conexão instável;
- mensagem de erro extensa na zona afetada;
- modo claro sob tela com baixo brilho ou reflexo;
- contraste após opacidade, overlay e textura;
- zoom de `200%` e tamanho de fonte do sistema ampliado;
- teclado sem mouse;
- movimento reduzido;
- carregamento lento ou falha de fonte remota;
- inserção futura da bandeja de dados.

## 10. Validation Criteria

- Todos os requisitos `A11Y-*`, `UXR-*`, `TYP-*` e `DSN-*` possuem evidência de
  teste ou revisão registrada.
- Nenhum par de contraste é aprovado apenas pelo valor nominal antes da composição.
- Modo claro e modo escuro passam pela mesma matriz de estados e viewports.
- A narrativa mantém prioridade visual e legibilidade prolongada.
- Controles e dados usam tipografia funcional consistente.
- A fonte decorativa não aparece em conteúdo necessário para operar o produto.
- Os protótipos finais recebem aceitação humana antes da implementação ampla.
- Nenhum código é alterado com base nesta especificação antes do segundo momento.

## 11. Related Specifications / Further Reading

- [Bandeja de Dados V5 Visível e Interativa](design-visible-v5-dice-tray.md)
- `plan/architecture-llm-memory-turns-1.md` — trabalho predecessor que deve ser
  concluído e aceito antes desta continuação.
- [WCAG 2.2 — Contraste mínimo de texto](https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html)
- [WCAG 2.2 — Contraste não textual](https://www.w3.org/WAI/WCAG22/understanding/non-text-contrast.html)
- Decisão humana de 2026-08-25: contraste claro tratado como acessibilidade;
  layout e tipografia submetidos a redesenho coerente com papéis distintos.

