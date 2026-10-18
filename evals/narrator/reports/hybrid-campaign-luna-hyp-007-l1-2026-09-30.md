# HYP-007-L1 — execução interrompida

Em 30/09/2026, o lote autorizado HYP-007 enviou uma requisição sintética
`CAMP-EVAL-01`, turno 1, e parou em HTTP 400. O resumo registra 1 chamada
tentada, 0 turnos concluídos e `campaign_source_provider_failure`. O hash
SHA-256 de `records.jsonl` confere com `summary.json`:
`bd524cf7dbf2430dee8ad8d4eed1d8b2aea4271b5f16ed06fbcae088149e203f`.

O registro não contém uso de tokens. O custo final é **indisponível**, não USD 0;
nenhuma cobrança foi confirmada ou descartada. Não houve resposta narrativa a
avaliar, progressão admitida, retry ou admissão de narrador.

Diagnóstico local posterior: o JSON Schema enviado com `strict: true` tinha
`protocol` em `properties`, mas não em `required`. A [documentação oficial de
Structured Outputs](https://developers.openai.com/api/docs/guides/structured-outputs)
exige que todos os campos sejam obrigatórios. Isso é causa plausível do 400,
não confirmação do motivo específico, pois o corpo da resposta de erro não foi
retido. A variante de transporte HYP-007 agora inclui todos os campos em
`required` e remove o `default` do schema enviado, mantendo a validação local
de `CampaignSourceProposal`. Treze testes focados e o preflight keyless de 17
turnos passaram, sem chamada ao provedor.

O gate live foi desativado após L1. Uma nova execução não deve reutilizar
silenciosamente este lote nem o mesmo teto agregado. Antes de qualquer L2,
registrar hipótese, novo limite de chamadas e teto estimado, confirmar
autorização humana para gasto adicional e pedir inserção segura da chave. O
resultado de L1 permanece inconclusivo quanto à qualidade narrativa do Luna.
