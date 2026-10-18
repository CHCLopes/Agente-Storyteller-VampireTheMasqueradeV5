# Atribuição de cor — preparação verificada

`record-summary-attachment-qwen-observation-v1` foi executada e encerrada sob autorização contínua. PID 24720 confirmado finished em 2026-09-07T19:36:06.2011876Z, exit 2; chave descartada. [Resultado 1edf4d3e](record-summary-attachment-observation-1edf4d3e-2026-09-07.md): A recebeu HTTP 429 sem texto e B não foi chamado. O detalhe externo do Console informa expectativa de saída 1.096 acima do limite OTPM 1.000; o bruto local mantém origem desconhecida. Não há avaliação semântica; não relançar a preparação nem preencher o segundo caso. [Metadados e verificações históricos preservados](record-summary-attachment-v1-2026-09-07.json). O [lote 21cf338b](record-summary-only-observation-21cf338b-2026-09-07.md) permanece encerrado e sua falha de fidelidade não é alterada por este resultado de disponibilidade.

O [desenho](record-summary-attachment-design-21cf338b-2026-09-07.md) observa duas fontes novas do observatório: A atribui verde à carcaça da luminária; B atribui verde à luz emitida. Cada narrativa tem 32 palavras; a segunda unidade é idêntica. O modelo recebe fatos sintéticos autorados, sem condições nomeadas, gabarito ou rubrica. O [dossiê](record-summary-attachment-dossier-21cf338b-2026-09-07.json) conserva SYSTEM record-summary-only-v1, schema SummaryOnlyProposal, modelo Qwen e parâmetros. **Somente messages[1].content muda** para cada fonte nova.

## Escopo e critérios

Groq direta, qwen/qwen3.8-27b, esforço none, temperatura 0,65. No máximo duas chamadas na ordem observatory-a/observatory-b, 3.072 tokens cada e 6.144 no total; espera local inicial e entre inícios de chamadas de pelo menos 60 segundos, deadline de 60 segundos após espera/revalidação. Instâncias independentes, sem conversa compartilhada. Primeiro erro operacional encerra o restante com skips. Sem retry, fallback, diagnóstico, juiz LLM, reparo ou escalada.

Somente summary, string estrita de 8–600 caracteres, preservada literalmente. Até 25 palavras é medição separada, sem alterar o exit ou impedir B. A revisão verifica o portador da cor e todas as demais afirmações; aceita paráfrases fundamentadas, trata ambiguidade explicitamente e deixa cor omitida como não informativa. Acerto isolado não prova taxa, causalidade, confiabilidade ou superioridade. Fonte, SYSTEM, schema e critérios históricos permanecem intactos.

## Verificações concluídas

| Grupo focado | Testes distintos aprovados |
| --- | ---: |
| Executor | 58 |
| Wrapper protegido | 73 |
| Fronteira CAP: 21 novos e 47 existentes | 68 |
| Total | 199 |

São 152 novos e 47 existentes, sem falha material pendente; não houve suíte integral. Etapas intermediárias e repetições não foram somadas. Revisão independente, reconstrução dos dois corpos, preflight final e integração real com SecureString vazia concluídos. A integração teve exit 3 na validação da credencial, zero chamadas/artefatos e stderr vazio. A auditoria confirmou 9 arquivos de preparação, 48 fingerprints históricos e 14 brutos históricos preservados, sem somar conjuntos sobrepostos; evidência completa no JSON. A guarda CAP adiciona somente 12 linhas e mantém a proteção do protocolo anterior. Sucesso de estrutura ou medição não aprova fidelidade.

## Próximo passo e limites após encerramento

Esta preparação foi executada até a parada operacional prevista e seus artefatos foram analisados. Não abrir nova janela, relançar o wrapper ou preencher B; a chave desta execução foi descartada. Preparar offline uma observação operacional independente com orçamento de saída reduzido a no máximo 768 tokens, fonte sintética nova, mesmo Qwen/Groq gratuito e limite de uma chamada. O desenho e a implementação exatos ainda estão em decisão/preparação; não estão declarados prontos e não houve novo envio. A hipótese será observar compatibilidade operacional nesse orçamento, sem garantia de sucesso ou avaliação de narrativa/CAP-001. Não repetir A, preencher B ou reutilizar o par; concluir as verificações locais antes de depender de uma nova entrada protegida de credencial.

Sem novo envio neste registro ou nova aprovação genérica pendente. A falha de disponibilidade não avalia qualidade do modelo. Perguntas, anotações inline, oito campos, atores, runtime e CAP-001 continuam sem aprovação.
