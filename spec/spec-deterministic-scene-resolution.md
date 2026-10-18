---
title: Resolução Determinística de Beats de Cena
version: 1.0
date_created: 2026-09-14
last_updated: 2026-09-14
owner: Produto Agente Storyteller
status: Ativação piloto para diálogos catalogados de Mara
tags: [scene, resolution, npc, narrative, deterministic, admission]
---

# Resolução Determinística de Beats de Cena

## Decisão

Antes da verbalização narrativa, toda ação ficcional, diálogo ou espera recebe um
beat estruturado. O resolvedor escolhe entre consequências fornecidas por regras,
usando contexto canônico, resultado mecânico já calculado, ficha mínima dos NPCs
presentes e relação persistida. H6 expressa o beat; não decide sozinho se a cena
avançou ou qual resultado vinculante ocorreu.

Comandos, consultas puras, esclarecimentos e falhas técnicas não exigem beat. O
primeiro incremento não cria aleatoriedade adicional: maior prioridade vence e o
menor `option_id` é o desempate estável. Se não existir consequência elegível, o
resolvedor recusa; ele não fabrica fallback narrativo.

## Fronteira de autoridade

O resolvedor vincula:

- resultado da intenção: `success`, `failure` ou `unresolved`;
- mudança observável que deve aparecer na cena;
- ação ou postura de NPC compatível com ficha e relação;
- transição de local explicitamente autorizada;
- pendências abertas ou resolvidas;
- pressão nomeada após o beat;
- causas, incertezas e proibições que a narrativa deve preservar.

H6 conserva:

- linguagem, ritmo e extensão dentro do contrato;
- detalhe sensorial cosmético compatível;
- composição da fala de NPC dentro do movimento vinculado;
- pergunta aberta que devolve iniciativa ao jogador.

H6 não pode omitir a consequência central, alterar causalidade ou resultado,
executar ação do jogador, promover segredo, trocar elenco/local sem autorização
ou resolver outra pendência. A proposta continua sujeita à política de admissão;
somente o commit transacional transforma beat e prosa em fatos da campanha.

## Contratos do primeiro incremento

`SceneResolutionInput` contém identidade da operação, revisão-base, ação declarada,
tipo de turno, `SceneState`, pressão atual, resultado mecânico opcional, perfis
mínimos de NPC e opções de consequência.

`SceneNpcProfile` contém ID estável, nome presente na cena, capacidades, limites,
objetivo local, postura, referência de relação, dados mecânicos existentes e
restrições secretas. Ele é
interno e separado da futura ficha visível do jogador. Segredos não atravessam
automaticamente para o beat; somente uma restrição escolhida e marcada
`storyteller` pode orientar a admissão/narração interna.

`MechanicalResolutionInput` é cópia imutável de um resultado já produzido. O
resolvedor deriva apenas `success` ou `failure` e devolve a mesma cópia. Ele não
recalcula dificuldade, margem, dados, Fome ou flags.

`SceneConsequenceOption` é conteúdo autorado por regra. Declara tipos de turno e
resultados aceitos, prioridade, NPC/capacidades/limites, mudança, movimento,
pendências, transição, pressão e restrições narrativas. Opções não são texto do
jogador nem saída de LLM.

`SceneBeatResolution` identifica a opção escolhida, preserva o resultado mecânico
e carrega hashes canônicos da entrada e da resolução. A mesma entrada deve gerar
o mesmo objeto e os mesmos bytes JSON.

## Autoria por palavras-chave

`effect_keys` são compromissos causais mínimos que a proposta H6 devolve em
`realized_effects`. Quando existem, fatos e prosa podem formular livremente o
efeito; a admissão exige os identificadores aprovados e recusa identificadores
extras. Beats anteriores sem `effect_keys` preservam a correspondência literal.

`guidance_keys` orientam personalidade, objetivo local, espectro de reação e modo
de avanço. Elas não precisam ser repetidas nem declaradas como fatos. O catálogo
não contém fala pronta, descrição pronta ou sequência de cena. A seleção continua
determinística; jogada interna permanece fora deste incremento.

O piloto cobre somente diálogo dirigido explicitamente a Mara, com Mara presente
em `Arquivo` ou `Galeria`, nos tópicos autorados. Ausência de cobertura conserva o
fluxo anterior e não cria fallback ficcional.

## Elegibilidade e seleção

Uma opção é elegível somente quando:

1. inclui o tipo de turno;
2. inclui o resultado derivado da mecânica, ou `unresolved` sem mecânica;
3. toda pendência resolvida já está aberta;
4. nenhuma pendência aberta é duplicada;
5. uma transição muda realmente de local;
6. o NPC exigido possui perfil, está na cena, tem todas as capacidades e não
   possui limite bloqueador;
7. o beat contém resposta ou mudança concreta.

As opções elegíveis são ordenadas por prioridade decrescente e `option_id`
crescente. O primeiro item é escolhido. Ordem de entrada, relógio, hash aleatório,
processo, modelo e estado global não participam da decisão.

## Estados nomeados

Pressão inicial do primeiro incremento: `calm`, `watchful`, `tense`, `immediate`.
Postura de NPC: `open`, `guarded`, `resistant`, `hostile`, `supportive`. Esses
nomes não formam escala matemática nem autorizam automaticamente transições. Uma
regra deve fornecer a mudança causal específica.

## Exemplos autorados

### Diálogo pertinente

Entrada: jogador pede a Mara que fale sobre o Arquivo; Mara está presente,
`guarded`, pode explicar história local e não pode revelar o segredo do fundador.

Opção elegível: Mara responde e indica o índice de entradas recentes; abre a
pendência da entrada rasurada; pressão passa de `calm` a `watchful`.

Beat obrigatório: a resposta e o índice aparecem; identidade ligada ao segredo
permanece apenas em restrição `storyteller`. Uma prosa que descreve o ambiente e
promete resposta posterior contradiz o beat.

### Espera com mudança

Entrada: jogador aguarda; não há rolagem.

Opção elegível: água alcança a borda do livro-caixa; abre a pendência de impedir
o dano. O beat não move, toca ou decide pelo jogador.

Contraprova: “nada muda; o que você faz?” não contém mudança observável e não pode
ser uma opção de consequência.

### Ação com sucesso

Entrada: recibo mecânico imutável com margem positiva para examinar o índice.

Opção elegível: a rasura revela uma sequência interrompida, sem identificar o
autor. O beat preserva todos os dados do recibo e não cria outra rolagem.

Contraprova: opção de falha é inelegível; prosa que diz que o exame falhou deve ser
recusada pela futura validação beat/proposta.

### Ação com falha

Entrada: recibo mecânico imutável com margem negativa.

Opção elegível: o objetivo não é alcançado; Mara fecha o índice e a pressão muda
para `tense`. A consequência movimenta a cena sem conceder a descoberta.

Contraprova: revelar a identidade procurada contradiz a falha.

### Limite do NPC

Entrada: opção exige `reveal_founder_secret`; o perfil de Mara registra o mesmo
item como limite.

Resultado: opção inelegível. Outra resposta compatível deve existir ou o resolvedor
retorna `scene_no_eligible_consequence`; H6 não improvisa por cima do limite.

### Transição

Entrada: jogador permanece no Arquivo.

Resultado: somente opção de tipo `transition` com `transition_to` diferente pode
autorizar mudança ao Corredor Norte. Repetir o local atual não constitui avanço.

## Erros seguros

- `scene_turn_does_not_require_beat`: o tipo de turno está fora do resolvedor;
- `scene_no_eligible_consequence`: nenhuma regra satisfaz a entrada;
- `scene_resolution_mismatch`: resolução armazenada ou recebida não coincide com
  a recomputação determinística.

Evidências de erro contêm apenas tipo de turno, resultado, contagem de opções e
hashes. Ação do jogador, segredos, prosa e credenciais não entram no diagnóstico.

## Persistência futura

O núcleo puro não persiste. Na integração, o beat será incorporado ao `TurnDraft`
e ao pacote H6. Beat, fatos, eventos, narrativa, memória, relações e snapshot
serão confirmados pela transação existente. Falha antes do commit preserva o
estado anterior. Retry terminal recupera o mesmo beat e narrativa sem resolver,
rolar ou chamar H6 outra vez.

## Aceite do núcleo puro

- mesma entrada gera resultado e hash idênticos;
- opção de maior prioridade vence; empate usa `option_id`;
- diálogo e espera geram resposta/mudança sem dado;
- sucesso/falha usam e preservam o recibo fornecido;
- capacidade ausente, limite presente, transição inválida e pendência desconhecida
  tornam a opção inelegível;
- perfis fora do elenco são recusados;
- segredo não selecionado e ação do jogador não são copiados para o resultado;
- objeto é estrito, imutável e revalidável;
- módulo não importa gateway, adaptador de provedor ou `random`.

## Não escopo

Integração H6, persistência, ativação, catálogo completo de consequências,
balanceamento, escala numérica, agenda global de NPCs, campanha macro, bandeja de
dados, UI de perícias, criação da ficha e escolha de modelo permanecem posteriores.
