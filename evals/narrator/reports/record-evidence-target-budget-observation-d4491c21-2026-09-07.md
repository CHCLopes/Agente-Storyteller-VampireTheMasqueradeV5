# Observação 3072 encerrada — resposta completa, suportes e fidelidade reprovados

Batch `d4491c21-2f2d-4ffc-b02a-46b5e630ba30`, em 07/09/2026. Uma única abertura fixa, nenhuma narrativa nova, retry, fallback, diagnóstico ou Mara. A janela terminou às 14:35:47 UTC, exit 1. O [summary original](../../../eval-results/20260907T143441Z-b6bb2a4f-595a-45d5-b92c-95b27b56e0e3/summary.json) e o JSONL permanecem intactos; hashes, intervalos e auditoria estão no [relatório estruturado](record-evidence-target-budget-observation-d4491c21-2026-09-07.json).

## Resultado observado

Groq/openai/gpt-oss-120b verificados; HTTP 200, `finish_reason:stop`, request `req_01m1y4qr1ces6afmhynbk6rrfb`. Uso: 2.484 entrada + 1.409 saída = 3.893, incluindo 915 tokens de raciocínio na saída. Conteúdo de raciocínio não foi consultado/retido. Custo indisponível. Espera inicial observada 60,813 s; chamada 4,228 s.

Preflight e resumo foram reconstruídos exatamente; a rejeição pelo contrato congelado foi reproduzida antes de qualquer alteração subsequente no avaliador compartilhado. Schema inicial passou. Envelope rejeitado por `record_evidence_span_invalid`; schema final e admissão não foram alcançados. Seus falsos não representam rejeições executadas dessas etapas.

| Campo | Intervalo | Comprimento | Constatação |
|---|---:|---:|---|
| `/o` | [0,10) | 10 | Em limites e completo. |
| `/l` | [0,25) | 25 | Em limites e completo. |
| `/s` | [0,112) | 125 | Em limites, mas corta “sugerindo” em “sugeri”. |
| `/f/0/s` | [3,66) | 63 | Fora dos limites. |
| `/t/0` | [0,30) | 30 | Em limites; texto semanticamente infiel. |
| `/t/1` | [0,30) | 28 | Fora dos limites. |
| `/q` | [0,21) | 21 | Em limites; convite livre não precisava suporte factual. |

Cinco intervalos em limites não demonstram cobertura. No resumo, “ndo presença.” fica descoberto e um único suporte `suggested` agrupa ambiente estabelecido com sugestão. A verificação estrutural corretamente não promete avaliar implicação ou cobertura semântica.

## Revisão semântica autônoma

“Quem ou o que está observando?” repete a pressuposição indevida de b129ceaa: a narrativa apenas sugere observação. O rótulo `suggested` não corrige a redação. O resumo “sussurro distante sugerindo presença” conserva incerteza; “Personagem percebe” adiciona atribuição explícita de percepção, sem por si só impor decisão voluntária. Lugar e fato ambiental estão fundamentados; a origem do sussurro permanece legitimamente em aberto. Convite final preserva agência; outcome e listas vazias não inventam NPC, resolução mecânica ou pendência concluída. Dois pareceres independentes concordaram com os achados centrais. Esta revisão técnica não equivale à aceitação humana de produto.

A saída 1.409 ficou abaixo até do teto histórico 1.536. Isso não prova que o aumento era necessário nem explica a realização truncada anterior. Não há base neste resultado para novo aumento. Comparações históricas não são A/B causal; não se atribui melhoria ao prompt por contagem isolada. Runtime e CAP-001 seguem não aprovados.

## Continuidade autorizada

Preparar `record-evidence-target-quotes-v1`: protocolo experimental que solicita a citação exata do trecho do campo derivado, com resolução local somente se existir uma única correspondência literal. O registro, a narrativa e as fontes permanecem intactos; não há reconstrução retrospectiva desta amostra. Preservar critérios de fidelidade e a contraprova da pergunta sobre observação. Manter 3.072, uma opening e ausência de retry/fallback. A implementação será verificada antes do novo prompt protegido de chave; nova aprovação do lote não é necessária.
