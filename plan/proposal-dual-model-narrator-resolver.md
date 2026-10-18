---
title: Proposta futura — separação entre narrador e resolvedor assistido por modelo
status: Proposta não aprovada, não priorizada e sem implementação planejada
owner: Produto Agente Storyteller
tags: [future, proposal, narrator, resolver, llm]
---

# Proposta futura — narrador e resolvedor assistido por modelo

## Condição deste registro

Este documento preserva um insight para rediscussão futura. Ele não aprova mudança
de arquitetura, modelo, provedor, chave, custo, fallback, prioridade, data de
implementação ou posição no backlog. O MVP continua conforme o planejamento e as
decisões vigentes. Não iniciar spike, implementação, aquisição de credencial ou
comparação adicional por causa deste registro.

## Insight

Investigar futuramente uma separação operacional entre dois papéis:

- **resolvedor**: recebe estado canônico, regras, resultado mecânico, perfil mínimo
  e oculto de NPC, relação e consequências previamente consideradas válidas;
  seleciona ou ordena uma consequência sem escrever a cena;
- **narrador**: recebe o resultado canônico admitido e o transforma em fala,
  atmosfera, ritmo e apresentação narrativa, sem redefinir causalidade, mecânica,
  transição, segredo ou ação do jogador;
- **aplicação/UI**: continua proprietária da interação, dos componentes, dos estados
  visuais, da persistência e da apresentação ao jogador. O narrador não controla
  diretamente a interface.

Os dois papéis poderiam usar modelos, provedores e chaves de API diferentes, ou
uma combinação local/remota. A configuração e a autenticação seriam separadas por
papel, sem expor credenciais ao cliente, prompts, campanha ou logs.

## Relação com a arquitetura atual

A proposta não substitui automaticamente o resolvedor determinístico existente.
Uma hipótese preferencial para futura avaliação é preservar regras e elegibilidade
no código e limitar um segundo modelo a escolher entre opções válidas. A decisão
externa somente poderia tornar-se canônica após validação, persistência idempotente
e admissão. Replay ou retry reutilizaria a decisão congelada e jamais consultaria
o modelo novamente para obter um resultado mais conveniente.

Essa hipótese revisita a alternativa `ALT-003` de
`plan/architecture-scene-resolution-1.md`, atualmente rejeitada. Portanto, exige
nova decisão humana de arquitetura antes de qualquer implementação. A proposta não
revoga determinismo, agência, autoridade das regras, commit transacional, ausência
de fallback silencioso ou separação entre ficha oculta de NPC e futura ficha do
personagem do jogador.

## Candidatos e alternativas discutidos

- Jev como avaliador de decisões tipadas e delimitadas;
- modelo pequeno local ou remoto, como Qwen, Phi ou Gemma, com saída restrita;
- classificador especializado treinado futuramente com casos revisados;
- tabela ponderada determinística como baseline ou fallback explícito;
- manutenção integral do resolvedor determinístico atual caso um modelo não
  demonstre ganho mensurável.

Nenhum candidato está aprovado. A eventual recusa de um modelo como narrador não
implica sua recusa como resolvedor, e vice-versa.

## Benefícios hipotéticos a verificar

- especializar seleção causal e expressão narrativa;
- reduzir estagnação e respostas vagas de NPCs;
- permitir troca e avaliação independente dos dois papéis;
- manter o narrador livre para prosa sem lhe entregar autoridade mecânica;
- observar custo, latência e qualidade separadamente por função.

## Riscos e custos a verificar

- segunda chamada sequencial, latência, cota e ponto de falha;
- perda de reprodutibilidade se a decisão não for congelada antes da narração;
- dependência de provedor e governança de duas credenciais;
- vazamento de ficha oculta ou segredos por excesso de contexto;
- falsa confiança em probabilidades não calibradas;
- opções ruins ou incompletas continuarem produzindo decisões ruins;
- ampliação de complexidade sem ganho sobre a prioridade determinística atual.

## Questões abertas para uma futura rediscussão

1. O segundo modelo recomendaria, ordenaria ou vincularia uma opção?
2. Quais dados mínimos poderiam sair do domínio canônico sem expor segredos?
3. Como persistir a decisão antes de H6 e preservar retry/replay idempotentes?
4. Qual fallback explícito seria permitido em indisponibilidade ou baixa confiança?
5. Qual corpus compararia o modelo contra seleção determinística e tabela ponderada?
6. Que ganho mínimo de progressão, coerência e variedade justificaria a complexidade?
7. Os dois papéis usariam provedores distintos, projetos/chaves distintas no mesmo
   provedor ou um resolvedor local sem chave?

## Regra de retomada

Rediscutir somente por nova decisão explícita do usuário. Ao retomar, reler o
estado atual do projeto e os resultados então disponíveis; não assumir que modelos,
preços, provedores, contratos ou estimativas discutidos anteriormente continuam
atuais. Até lá, seguir o MVP como já planejado.
