# Evidência recuperada no Console Groq — 2c1cafde

Data: 07/09/2026. Status: **consulta concluída; causa ainda não demonstrada**.
Continua a [consulta anterior](groq-console-lookup-2c1cafde-2026-09-07.md)
após autenticação do usuário. [Registro estruturado](groq-console-evidence-2c1cafde-2026-09-07.json).

## Identidade e dados observados

O controle de cópia do Request ID devolveu
`req_01m1xtmhhdeyjbew0n7ffxv9tg`, exatamente o external_id do lote.
O controle de cópia do erro devolveu novamente esse ID, com
`created_at: 2026-09-07T11:39:11.789Z`. A linha está no Default Project;
o horário exibido foi 07/09/2026, 08:39:11, coerente com UTC−03:00.

| Campo | Console Groq |
|---|---:|
| Modelo registrado | openai/gpt-oss-120b |
| HTTP | 400 |
| Tokens de entrada | 2.320 |
| Tokens de saída | 768 |
| TTFT | 0,331918 s |
| Latência | 1,959371 s |

O erro copiado contém `invalid_request_error`, `json_validate_failed` e
`param` vazio. A mensagem é:

> Failed to validate JSON. Please adjust your prompt. See 'failed_generation' for more details.

Apesar da referência textual, o objeto copiado **não contém**
`failed_generation`, `finish_reason`, regra/caminho rejeitado ou uso detalhado.
Esses dados também não apareceram no detalhe visual inspecionado. Isso não
prova que inexista informação adicional nos sistemas internos da Groq.

## Comparação com o registro local

A [análise anterior](record-evidence-observation-2c1cafde-2026-09-07.md)
continua correta sobre o que chegou ao avaliador: HTTP 400, sem envelope,
sem uso/modelo na resposta disponível, seguido do skip de Mara. O Console
acrescenta evidência posterior com procedência própria; não se reescreveu
summary.json ou JSONL para preencher retrospectivamente campos do adaptador.

A soma das colunas é 3.088 tokens, calculada localmente; não é campo total
reportado pela API. Não se conhece a separação dos 768 tokens de saída entre
conteúdo e raciocínio, nem o custo. Latência do Console e medição local têm
escopos distintos; não se atribui sua diferença à rede.

Há contabilização de tokens de saída. Portanto a falta de envelope recebido
não permite afirmar que o provedor não gerou nada. Schema/admissão permanecem
sem amostra; nenhum resultado semântico pode ser aprovado.

## O que muda no diagnóstico

Os 768 tokens de saída coincidem com `max_completion_tokens:768` do
[dossiê reconstruído](record-evidence-request-dossier-2c1cafde-2026-09-07.json).
Esse dado sustenta investigar esgotamento do orçamento, incluindo a possibilidade
de interrupção antes de concluir o JSON. Não prova truncamento: ainda faltam
motivo de término, geração recusada ou confirmação específica do provedor.
Uma saída inválida por outro motivo continua possível.

`include_reasoning:false` controla a exposição do raciocínio, e GPT-OSS admite
esforço low/medium/high. Não equivale a selecionar raciocínio desabilitado.
A distribuição dos tokens desta chamada permanece desconhecida.
[Referência oficial Groq](https://console.groq.com/docs/api-reference).

O teto foi enviado conforme o desenho aprovado. Não há defeito local
comprovado nem base para alterar schema, prompt, validação ou orçamento como
correção automática. A revisão independente concordou com esses limites.

## Trabalho concluído e próximo passo

Foram conferidos os hashes de 12 arquivos de implementação, dos dois artefatos
originais e do dossiê; todos permanecem preservados. Nenhum código ou teste
mudou; não foi necessário repetir testes executáveis para esta atualização
documental. Os 30 testes focados pertencem à análise anterior.

Foi preparado o [desenho de diagnóstico do orçamento](record-evidence-budget-hypothesis-2c1cafde-2026-09-07.md),
com uma abertura fixa, teto de 1.536 tokens e observação estrutural delimitada.
É proposta para decisão, não runner implementado ou chamada autorizada.
A [solicitação técnica local](record-evidence-provider-request-2c1cafde-2026-09-07.md)
foi atualizada com os dados recuperados; não foi enviada.

A dependência de login foi resolvida. A consulta existente terminou, sem nova
inferência, acesso a chaves, alterações de conta ou exportação em massa.
A causa requer evidência adicional do provedor ou decisão específica sobre
novo diagnóstico. Autonomia para trabalho local necessário permanece ativa.
CAP-001 e runtime continuam sem aprovação.
