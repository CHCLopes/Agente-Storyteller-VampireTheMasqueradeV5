# Citações exatas — observação fda8af66 encerrada

Batch `fda8af66-ac22-44d2-839f-c0e587abec70`, em 07/09/2026. Uma abertura fixa, nenhuma narrativa nova, retry, fallback, diagnóstico ou Mara. A janela terminou às 14:58:25 UTC, exit 1. [Summary original](../../../eval-results/20260907T145720Z-f6f7d63d-b888-4d16-b201-46bbc8dee31e/summary.json) e JSONL permanecem intactos; [auditoria estruturada](record-evidence-quotes-observation-fda8af66-2026-09-07.json).

## Resultado e proveniência

Groq/openai/gpt-oss-120b verificados, HTTP 200/stop, request `req_01m1y616n9ejta2ke2ata8thaz`. Uso: 2.482 entrada + 1.128 saída = 3.610; raciocínio contabilizado 725, sem consultar seu conteúdo. Custo desconhecido. Espera inicial 60,716 s e chamada 4,093 s.

Preflight e resumo reconstruídos exatamente; rejeição reproduzida com o contrato intacto, antes de nova alteração no avaliador compartilhado. Schema inicial passou. Envelope recusado por `record_quote_evidence_quote_missing`; schema final e admissão não foram alcançados.

| Campo | Citação resolvida | Intervalo local / comprimento |
|---|---|---|
| `/o` | `unresolved` | [0,10) / 10 |
| `/l` | `corredor de pedra fria` | [0,22) / 22 |
| `/s` | `corredor de pedra fria` | [24,46) / 108 |
| `/f/0/s` | Campo completo | [0,75) / 75 |
| `/t/0` | `sussurro distante` | Ausente no campo de 39 caracteres. |

Os quatro intervalos acima são análise local de correspondência, não uma aceitação parcial persistida pelo executor. A auditoria operacional rejeitou o envelope inteiro. A quinta citação existe na fonte e em outros registros, mas não em `/t/0`: “Quem ou o que está observando ao longe?”. O padrão sustenta confusão entre origem e destino; nenhum defeito do resolvedor foi demonstrado. Não se troca o caminho/citação nem se remove o suporte para fazer a amostra passar.

## Fidelidade e cobertura

A pergunta ainda pressupõe observação em curso que a narrativa apenas sugere. O resumo “com fumaça, chuva” abandona a relação sensorial “cheiro de fumaça e chuva”; o único suporte de `/s` cobre somente o corredor e deixa as demais afirmações sem cobertura declarada. O fato ambiental e o lugar são fundamentados, sem novo NPC ou resolução mecânica.

“O que faço agora?” introduz ambiguidade de ponto de vista no convite final. É uma qualificação de revisão, não uma falha de admissão observada: o gate não foi executado. Correspondência literal, mesmo quando exata, não prova implicação ou cobertura. Comparação com d4491c21 não é A/B causal nem comprova melhoria. Runtime, narrativa e CAP-001 não são aprovados.

## Próximo passo autorizado

Preparar `record-evidence-claim-check-v1`, mudando apenas o SYSTEM. Acrescentar uma conferência curta de citação no campo de destino, afirmações completas/modais, relações sensoriais, pressuposições das perguntas e convite dirigido ao jogador. Exemplos serão independentes da abertura observada, sem gabarito para seus registros. Permanecem USER, protocolo de citações, schemas, fontes, parâmetros e gates. Uma opening, 3.072 tokens, espera/deadline de 60 s, sem retry/fallback. Nenhuma elevação de orçamento ou reparo retrospectivo.
