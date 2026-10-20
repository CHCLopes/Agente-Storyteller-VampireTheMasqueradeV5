# HYP-007-L19 — encerramento por HTTP 429

Data: 18/10/2026. Batch: b37735dc-a05a-410c-aa90-afeff8ea534c.

## Observado

Luna low/v5, até 17 chamadas/USD 0,15 estimados autorizados; uma chamada
tentada e zero turnos concluídos. Parada campaign_source_provider_failure,
error_code http_429, CAMP-EVAL-01/R-01. Sem resposta narrativa; geração 2464 ms.
Não permite concluir qualidade narrativa nem causa específica do erro.

Artefatos em eval-results/hybrid-campaign-luna-l19-b37735dc-a05a-410c-aa90-afeff8ea534c/:

- records.jsonl SHA256: 00aa8d74aefddf799d601b68a88e045db8457ae35ec51627f7d4b3460dd6caa4
- summary.json SHA256: 4cd6780ba11e0645ac9a04ab3c1839079d24d80ff06c22e554a403ed295951b2
- Manifesto fechado SHA256: 86fb3ebdaac12ce622248605c2a852b0540e2749ba3f70aa4929cd47e4284163

## Custo final

Indisponível: uma chamada sem usage, zero chamadas precificadas, total null.
Reporter reproduzido com --settled; records_settled true. Zero tokens observados
não prova consumo zero. Não confirmar cobrança nem substituir por USD 0.

## Ações e verificação

Fechados apenas paid_ceiling_authorized/live_inference_authorized. Trava única
preservada; sem retry/fallback/chamada adicional. Nenhuma alteração de runtime.
Testes focados: 34 aprovados em 15,54s, um aviso preexistente python_multipart;
preparação L19, batch híbrido e custo Luna. Resultado no XML
eval-results/hyp-007-l19-closure-2026-10-18.xml. Hashes conferidos após fechamento.
Suíte ampla não repetida: encerramento documental/gate, sem mudança de produto.
L18 aceito anteriormente; nenhum narrador admitido. TASK-013/CAMP-24/MVP abertos.

## Limitação e próxima ação humana

Registro não contém error.code do provedor, Retry-After ou request ID.
HTTP 429 sozinho não distingue limite temporário, saldo esgotado ou quota.
A documentação oficial distingue essas causas:
https://developers.openai.com/api/docs/guides/error-codes

Verificar Billing e Limits na organização/projeto corretos, mantendo teto e
recarga automática inalterados; informar apenas situação não secreta. Sem nova
chave necessária neste checkpoint. Não preparar/executar L20 nem repetir L19
antes de esclarecer o bloqueio e delimitar nova autorização.

Atualização humana posterior: informou limite externo anterior de USD 0,05
atingido e removido, e pediu continuidade. Não altera o registro original,
o custo indisponível ou a conclusão narrativa inconclusiva. L20 foi preparado
separadamente com os mesmos limites locais; L19 não será repetido.
