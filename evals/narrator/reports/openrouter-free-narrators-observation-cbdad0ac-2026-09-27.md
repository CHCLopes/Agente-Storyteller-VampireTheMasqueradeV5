# HYP-005 L1 — observação OpenRouter gratuita

Data da revisão: 2026-09-27  
Batch: `cbdad0ac-216c-4b40-baef-3b73c9ae1621`  
Hipótese: `HYP-005-OPENROUTER-FREE-L1`

## Resultado executivo

O lote foi executado uma única vez, sem retry, reparo, troca de alvo ou fallback.
Foram feitas 15 chamadas dos 24 slots congelados: 1 concluiu o contrato, 14
falharam operacionalmente e 9 foram puladas por dependência ou indisponibilidade
global já observada. O verificador dos artefatos aprovou o lote gravado e o custo
da única resposta concluída foi reportado como exatamente zero.

Nenhum candidato atingiu 8/8 e nenhum narrador é elegível ou admitido.

## Evidência operacional

- NVIDIA Nemotron 3 Super: 7 chamadas, 7 respostas HTTP 200 encerradas por
  `generation_truncated`; o caso dependente foi pulado. Resultado semântico
  inconclusivo, 0/8 concluídos.
- Liquid LFM 2.5 2.6B: 7 chamadas, 1 caso concluído, 6 respostas encerradas por
  `generation_truncated`; o caso dependente foi pulado. O lote é inelegível.
- DeepSeek V4 Flash 0731: a primeira chamada recebeu `http_404` / `model_unavailable`
  para o slug gratuito exato; os sete slots seguintes foram pulados. Resultado
  inconclusivo por indisponibilidade da rota gratuita, 0/8 concluídos.

Hashes congelados:

- preflight: `362db87211b5b862aed7fde883c28f17c4a409bedbe8fce0034efed6f3bb0e2b`
- records: `49c95158c11f59faeeab78330e12f49265e5b0d580646d61c6a59e3e13c73a89`
- summary: `048b1dee67b7d4fc07c45e0b28f27e46965616dd7c1470eff610c03ad1e55c74`

## Revisão semântica independente

Somente `favorable-shutter-result`, do Liquid, pôde ser avaliado. A resposta
preservou a abertura limitada à largura de uma mão, o atrito da madeira, a
corrente de ar, a progressão e a próxima escolha. Entretanto, acrescentou estado
anterior completamente fechado, eco suave, frio, uma sala, luz, poeira e o
ambiente “segurando a respiração”. Essas alegações não pertencem ao plano fechado.

`unlisted_render_claim` é fatal. O único caso concluído falha o gate semântico.
A ficha byte-vinculada está em
`evals/narrator/reviews/openrouter-free-narrators-cbdad0ac-partial-codex.json`.
Os 23 registros incompletos não receberam nota semântica.

## Classificação proposta para aceite humano

- Nemotron: inconclusivo por truncamento operacional; inelegível neste lote.
- Liquid: inelegível; lote incompleto e o único caso concluído falhou um critério
  semântico fatal.
- DeepSeek: inconclusivo por indisponibilidade da rota gratuita exata; inelegível
  neste lote.
- Nenhum candidato elegível; nenhum narrador admitido; nenhum default criado.

Uma repetição com mais tokens ou alteração de configuração constitui hipótese
nova. Ela não está embutida nesta classificação e não deve reutilizar a chave ou
executar chamadas por arrasto.

