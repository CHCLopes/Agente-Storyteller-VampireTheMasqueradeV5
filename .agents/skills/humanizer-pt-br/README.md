# Humanizer PT-BR

Skill para remover traços de escrita gerada por IA em textos em português brasileiro.

Ela ajuda a reescrever textos para que soem mais naturais, diretos e humanos, preservando o sentido original e ajustando o tom para roteiros, artigos, posts, textos falados e materiais editoriais.

## O que a skill faz

- Detecta padrões comuns de texto gerado por IA.
- Reescreve trechos artificiais com linguagem mais natural.
- Remove excesso de conectivos, frases de preenchimento e conclusões genéricas.
- Reduz tom promocional, bajulador ou mecânico.
- Mantém o significado central do texto.
- Ajusta ritmo, voz e personalidade quando o texto está limpo, mas sem pulso humano.

## Instalação

Clone este repositório dentro da pasta de skills:

```bash
mkdir -p ~/.claude/skills
git clone https://github.com/mackswendhell/humanizer-pt-br.git ~/.claude/skills/humanizer-pt-br
```

Se você usa um ambiente local de agentes com pasta `~/.agents/skills`, pode instalar assim:

```bash
mkdir -p ~/.agents/skills
git clone https://github.com/mackswendhell/humanizer-pt-br.git ~/.agents/skills/humanizer-pt-br
```

Depois, reinicie o agente ou a sessão para que a skill seja descoberta.

## Como usar

Peça algo como:

```text
Use a skill humanizer-pt-br para humanizar este texto.
```

Ou use gatilhos naturais como:

- humanizar texto
- remover IA
- texto artificial
- soar natural
- roteiro humano
- reescrever texto
- tirar traços de IA
- texto robótico
- parece IA

## Padrões que a skill detecta

1. Exagero de significado, legado e tendências mais amplas
2. Ênfase indevida em notabilidade e cobertura midiática
3. Linguagem promocional e publicitária
4. Análise rasa com gerúndio no final
5. Atribuição vaga e linguagem imprecisa
6. Seções formulaicas de "desafios e perspectivas futuras"
7. Intervalos falsos
8. Vocabulário excessivo de IA em português
9. Evasão do verbo "ser"
10. Paralelismo negativo
11. Regra dos três usada em excesso
12. Rotação forçada de sinônimos
13. Uso excessivo de travessão
14. Uso excessivo de negrito
15. Listas com subtítulos em negrito
16. Emojis decorativos
17. Title Case em títulos e headings
18. Aspas tipográficas em vez de aspas retas
19. Ganchos dramáticos e frases de revelação artificial
20. Rastros de conversa com chatbot
21. Linguagem bajuladora
22. Isenções de responsabilidade sobre data de corte
23. Conclusões genéricas e otimistas
24. Frases de preenchimento comuns em português
25. Qualificação excessiva

## Estrutura

```text
humanizer-pt-br/
├── README.md
└── SKILL.md
```

## Crédito

Skill criada para humanização de textos em português brasileiro, com base em padrões documentados de escrita gerada por IA e adaptada para uso prático em fluxos editoriais.
