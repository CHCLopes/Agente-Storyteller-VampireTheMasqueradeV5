# Próximo gate — integração do catálogo C

Status: proposta para decisão humana, não aprovada.

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

Escolher E ou F. E testa uma integração experimental mínima e mensurável. F evita
qualquer mudança de comportamento até que a autoridade para novas equivalências
seja definida. Nenhuma opção fecha CAMP-24.
