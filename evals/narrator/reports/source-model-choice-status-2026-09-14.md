# Estado da escolha do narrador — 14/09/2026

O comparativo de diálogo foi encerrado com auditoria técnica e duas leituras
semânticas concordantes. Nenhum candidato satisfaz a regra prospectiva de piloto.
Este documento não escolhe modelo, não altera default e não autoriza nova rodada.

## Evidência atual

| Candidato | Evidência favorável | Limite decisivo |
|---|---|---|
| Qwen via Groq | Três turnos confirmados e úteis na Oficina; boa retomada de elementos no terceiro turno. | Primeiro turno do Arquivo recusado por 167 palavras; faltam três commits nessa cena. A espera da Oficina teve avanço 1. |
| GPT-OSS via Groq | Três turnos confirmados no Arquivo; diálogo e direção espacial claros nos dois primeiros. | Primeiro turno da Oficina recusado historicamente; faltam três commits nessa cena. O terceiro turno confirmado do Arquivo teve avanço 0. |

A recusa de GPT-OSS na Oficina veio de um falso positivo de agência já corrigido
prospectivamente e coberto por 525 testes. A correção não completa os skips nem
reclassifica o lote. A recusa de Qwen por tamanho foi correta. Assim, a ausência
de vencedor não depende de discordância entre revisores.

## O que a comparação permite concluir

O fluxo B, a persistência, os replays, os limites de chamada e a auditoria dos
artefatos funcionaram nas condições do lote. Qwen mostrou melhor continuidade na
Oficina; GPT-OSS mostrou melhor condução inicial no Arquivo. Ambos ainda deixaram
um problema de progressão: indício pouco desenvolvido em Qwen e estagnação
explícita em GPT-OSS.

Repetir as mesmas cenas após a correção apenas completaria material recusado por
um gate antigo. Isso violaria o protocolo que proíbe repetir para forçar vencedor.
Uma nova comparação só é válida com uma pergunta prospectiva distinta, protocolo
próprio e critérios congelados antes das chamadas.

## Próxima decisão arquitetural

A evidência sugere retirar do modelo a responsabilidade exclusiva por decidir se
a cena realmente avançou. A proposta já registrada de resolvedor determinístico
de cenas pode definir resultado, mudança observável e consequência antes da
narração; o LLM então expressaria esse resultado preservando agência, atribuição
e tom. Isso atacaria a falha comum aos dois candidatos e permitiria uma futura
comparação sobre realização narrativa de um estado já resolvido.

O usuário aprovou em 14/09/2026 promover essa proposta para planejamento. O plano
`plan/architecture-scene-resolution-1.md` foi criado com cinco decisões de
arquitetura ainda abertas. O estado correto permanece: nenhum modelo escolhido,
nenhuma nova inferência necessária, resolvedor ainda não implementado e CAP-001
sem aprovação.
