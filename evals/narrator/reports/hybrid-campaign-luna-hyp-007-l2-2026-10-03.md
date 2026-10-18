# HYP-007-L2 — resultado observado

Lote `1f15ef44-1c18-4d96-b84c-459649b326bc`, executado em 03/10/2026.
Alvo `gpt-5.6-luna`, reasoning `low`, oito percursos sintéticos planejados,
17 chamadas no máximo, teto estimado adicional USD 0,15. Sem retry ou fallback.
O lote parou na primeira falha conforme o protocolo. L1 continua separado.

Integridade: `summary.json` aponta SHA-256 de `records.jsonl`
`23e741bfa5260363057c4058cff6a97a804b4036c6287afc9182bf40cea30e71`;
o hash calculado localmente coincide. A trava de lote único L2 existe.

Foram feitas duas chamadas. A primeira, CAMP-EVAL-01/R-01, foi admitida:
Mara indicou a superfície seca e respondeu em fala direta à pergunta sobre
a tarefa. O uso reportado foi 2.092 tokens de entrada e 137 de saída; o
turno levou 5.761 ms. A segunda, CAMP-EVAL-01/R-05, foi rejeitada por
`campaign_source_policy_failed`; o uso reportado foi 2.621 tokens de entrada
e 104 de saída; o turno levou 4.143 ms. O texto tinha cerca de 20 palavras,
abaixo do mínimo de 30 da política de cena, e ainda descrevia o registro
sendo retirado da mesa seca em vez da bancada do roteiro autorado. O pacote
canônico da chamada informa a condição do registro, o Arquivo e Mara, mas não
codifica a posição exata do objeto. A especificação aprovada descreve o
registro inicialmente na bancada baixa (`spec-architecture-hybrid-campaign-progression.md`,
seção Conteúdo autorado); o contexto enviado omite esse detalhe. Logo, a
origem errada expõe uma lacuna entre especificação e contexto, além de reduzir
a fidelidade ficcional. Não prova isolada de que Luna contrariou um fato
estruturado recebido. A rejeição impediu
commit canônico do segundo turno; o desfecho não foi observado. Não atribuir
`policy_failed` a uma única causa interna mais específica sem diagnóstico
retido; a contagem de palavras basta para explicar a recusa de acordo com o
código vigente.

Custo final **estimado** do lote: USD 0,0012318 para 4.713 tokens de entrada
e 241 de saída, segundo o uso retornado e preços de referência publicados
para Luna (USD 0,20/M entrada; USD 1,20/M saída). A fatura da conta não foi
consultada; o valor não é cobrança confirmada. Não agregar o custo
indisponível de L1 como zero.

Conclusão: L2 não cumpriu a trajetória mínima e não torna o Luna elegível
como narrador. A primeira fala direta é um sinal qualitativo positivo, não
prova de progressão sustentada. Nenhum narrador/default foi admitido. O gate
live foi desativado após a execução. A observação de origem errada do objeto
e o texto excessivamente curto devem informar um experimento prospectivo.
Não converter a localização da bancada em gate retroativo nem repetir L2.
Antes de novo live, decidir como representar e atualizar a posição pública do
objeto sem criar uma afirmação estática falsa depois do resgate. Isso envolve
autoridade canônica e não deve ser resolvido apenas por mais um lembrete no
prompt.
