# Próximo gate — integração do catálogo C

Status: opção E autorizada em 22/10/2026 pelo pedido de executar a opção mais
recomendada, concluir testes/publicação e aguardar as resoluções do brainstorm.

O catálogo exato `intent-paraphrase-catalog.v1` admitiu seis entradas e recusou
seis controles offline. A evidência não prova interpretação aberta nem autoriza
alterar o resolvedor, a UI principal, saves ou defaults.

## Opção E — integrar somente as seis strings ao ensaio A2

Adicionar uma camada opt-in no harness A2 que consulta o catálogo por igualdade
exata e, quando houver correspondência, encaminha a intenção já conhecida ao
mesmo caminho determinístico existente. A integração seria reversível, com banco
próprio, sem API, sem nova regra, sem novo cânone e sem aceitação de variantes
parecidas. Repetição, replay, estado e desfecho continuariam sob o contrato A2.

Critérios: seis entradas chegam ao mesmo efeito que sua intenção canônica; seis
controles permanecem sem avanço; nenhuma chamada de modelo; nenhum arquivo do
produto principal alterado; testes de reload e idempotência preservados.

## Opção F — conservar como estudo offline

Não conectar o catálogo ao A2. Usar o resultado como evidência de que uma pequena
lista revisada reduz bloqueios com baixo custo, enquanto a validação de paráfrases
fora da lista permanece indefinida. Uma futura fonte independente de revisão deve
ser decidida antes de ampliar o catálogo.

## Decisão pedida

E escolhida por delegação explícita. Nenhuma opção fecha CAMP-24.

## Protocolo E antes da execução

Hipótese: as seis frases exatas produzem os mesmos efeitos da entrada canônica
existente, sem nova rolagem em replay/restart ou aceite dos seis controles C.
Modo opt-in `--exact-paraphrases`, banco A2 novo e recibos de admissão em banco
companheiro exclusivo. Recibo registra sessão/operação/texto literal/frase
canônica/versão antes do claim A2; o núcleo congelado conserva somente sua entrada
canônica. A UI reconstrói o texto original pelo recibo validado. Sem normalizar.
O modo E aceita SOMENTE as seis frases; o modo anterior preserva a baseline,
inclusive seu pedido citado de ajuda, que não é uma entrada admitida em E.

Verificar seis pares canônico/paráfrase com investigação simulada em sucesso e
falha; seis controles C, espaços/maiúsculas/near misses; quatro desfechos;
replay/restart/retomada e interrupção entre recibo e claim; isolamento e limites
locais. Primeira falha interrompe a validação para diagnóstico; nenhuma API,
credencial, inferência, fallback, retry silencioso ou gasto: USD 0.
Reexecutar regressão selecionada anterior e conferir os 32 hashes L86. Registrar
resultado real em relatório próprio, sem alterar evidências B/C/L86 anteriores.
Brainstorm segue exclusivamente como texto transferível; aguardar instruções.

## Resultado

E concluída: 39 testes focados e 245 na regressão selecionada passaram; 32 hashes
L86 intactos, zero chamadas/custo. Detalhes, cobertura e limitações em
`evals/narrator/reports/intent-paraphrase-integration-2026-10-22.md`.
Texto para outro chat em `docs/handoffs/brainstorm-npc-decision-narrator-2026-10-22.md`.
Após push confirmado, aguardar resoluções humanas; não abrir outro gate E/F.
