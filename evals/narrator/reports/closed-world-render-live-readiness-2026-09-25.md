# Prontidão viva — HYP-002-L2

**Data:** 2026-09-25

**Status:** preparação offline verificada; lote vivo autorizado e ainda não iniciado

## Escopo congelado

HYP-002-L2 compara os alvos exatos `qwen/qwen3.8-27b` com reasoning `none`
e `openai/gpt-oss-120b` com reasoning `low`, ambos pela rota oficial Groq.
Cada alvo recebe oito casos sintéticos novos. O máximo absoluto é 16 chamadas,
temperatura 0,65, teto de 768 tokens, deadline de 60 segundos e intervalo mínimo
global de 60 segundos.

Não existe retry, reparo, fallback, troca de alvo ou repetição de slot. O lote
não lê campanha, não altera runtime e não torna nenhum candidato elegível por si.

## Verificação offline

- 20 testes do contrato e verificador HYP-002: aprovados;
- 14 testes do runner e launcher HYP-002: aprovados;
- 66 testes combinados HYP-001 + HYP-002: aprovados;
- preflight CLI keyless: 16 slots, zero chamada e zero inspeção de credencial;
- hash canônico dos metadados do preflight:
  `dd11ec02df78d5bc01b2c7a57df0fdaeade2f51a48aa95875a03eb6bc3a9a8db`;
- parse PowerShell: zero erros;
- launcher sem a variável dedicada: exit 3 antes de criar lote ou acessar rede;
- aviso não bloqueante: depreciação preexistente de `python_multipart` no
  Starlette.

A suíte backend integral não foi repetida. O incremento cria somente o novo
harness isolado, corpus, prompt e documentação; não altera código compartilhado.
A regressão combinada cobre o harness anterior e o novo, enquanto a suíte ampla
histórica possui falhas congeladas já documentadas.

## Hashes congelados

| Artefato | SHA-256 |
|---|---|
| corpus | `1b620a84bc9a61d63f1abd51e9e08dfbd856fbb804dd0c806bd7588daf42b72b` |
| protocolo | `0ab8cec17e225bfd98cee1957c2338f9341138fda60440e8440f9d1a4c0a21fb` |
| fixtures do verificador | `22ce6d263f7f92b5a21b9055f62df20c84d2cf17c3507152e683abda8f5b9043` |
| extensão de prompt | `22a75a5808fad849f8b1cec1fd59fd5cf4c58be52913604d6e84b35a0ec83ce3` |
| preparador/verificador | `a311d5df9e736eb3f0846a7e24c1a4e348587c82c08a62d9de8939ed98a167f8` |
| runner vivo | `71e3a70fb62c044694016da28810bbe7e7d921e0801a428669535c285dfe9800` |
| launcher | `f76d59325656d4222eabb0c9971725bf5e45dda2eed800155580630c95636f9d` |
| testes de contrato | `2c6fc7612f737f3bb5088c741dcdbf229907401c63a1e892c1df0d8db9919811` |
| testes do runner | `20d8d32458768c293293492485f5dd86b24b5bbefd5528fa3b879488e4a352d3` |
| testes do launcher | `460592e0039b0f1d0d27a6ee81c57b1abe62e2010c54889ab17e145f929fc413` |
| gate vivo JSON | `16e5e92011efe3474dc23141ca41c1075d23990edf236a759f0ba934d4f7f5d6` |
| gate vivo Markdown | `3869a2f52e8df50127b09587ead5df46a5fa688cabf531db4caa95b15bd0df17` |

## Próxima ação

Executar uma única vez `scripts/run_closed_world_render_live.ps1` na sessão do
terminal que contém a credencial protegida. O launcher gera e fixa o preflight,
executa o lote, verifica os artefatos e remove a variável dedicada no `finally`.

Depois, revisar semanticamente cada narrativa e parar no checkpoint humano de
aceitação do resultado. Nenhuma admissão ou configuração produtiva é automática.
