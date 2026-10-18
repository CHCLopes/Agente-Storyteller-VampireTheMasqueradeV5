# Revisão do comparativo de diálogo `e6827c97`

Data: 2026-09-16  
Escopo: comparação sintética Qwen/Groq e GPT-OSS/Groq, quatro blocos independentes, até três turnos retidos por bloco.  
Artefatos: `eval-results/source-dialogue-comparison-e6827c97-1af2-4849-9ca8-251aa8c1e3cc/summary.json` e `records.jsonl`.

## Resultado técnico

- 10 chamadas reais concluíram com HTTP 200, rota observada, schema válido e uso reportado.
- Não houve parada global, retry ou fallback.
- Seis turnos foram confirmados; quatro propostas foram recusadas pela política.
- O bloco 4 parou após a primeira recusa e pulou dois turnos dependentes, como previsto.
- O lote terminou com código 1 e não aprova verdade semântica, qualidade narrativa, runtime, modelo padrão ou CAP-001.

## Leitura semântica

Qwen apresentou duas saídas terminadas no meio da frase na Oficina. No Arquivo, respondeu à pergunta de Rui, mas terminou novamente no meio da frase e fechou com uma pergunta retrospectiva, sem devolver uma próxima ação. Essa recusa é materialmente correta.

GPT-OSS produziu frases completas e orientação mais clara nos dois cenários. No terceiro turno do Arquivo, porém, inventou a chegada anterior do jogador (`desde que você chegou`); essa recusa de agência continua correta. No terceiro turno da Oficina, a condição `se você observar ... verá` foi classificada como ação executada, embora apenas apresentasse uma possibilidade. Esse caso revelou um falso positivo.

Uma fala completa de NPC como `Você quer ver os vestígios?` também não atribui desejo ao jogador: pergunta por sua preferência. A saída concreta do Qwen não recebe essa exceção porque veio sem interrogação e sem fechamento da fala.

## Correção prospectiva

O validador agora:

- reconhece `se/caso você observar ou examinar ... verá/perceberá/notará` como condição, sem conceder autorização a ações posteriores;
- reconhece perguntas completas e fechadas de preferência feitas por NPC;
- continua recusando afirmações anteriores dentro da mesma fala, citações incompletas, ações posteriores, chegada inventada e perguntas finais não acionáveis.

Verificação: 56 testes do arquivo de regressão e 654 testes focados passaram. A reprodução das quatro propostas recusadas mudou somente o caso condicional do GPT-OSS para aceito.

## Consequência para a escolha do narrador

Este lote favorece GPT-OSS na completude textual e na utilidade das respostas, mas ainda não decide o modelo padrão. Depois da correção prospectiva, o bloco 2 teria três propostas semanticamente admissíveis; o bloco 3 ainda falharia por agência. Qwen mantém falhas de completude e uma pergunta final inadequada. Não se reescrevem os artefatos congelados nem se promove uma reclassificação causal do lote encerrado.

