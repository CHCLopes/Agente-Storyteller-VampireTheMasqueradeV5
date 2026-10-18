# Gate de execução viva — HYP-001

**Data:** 2026-09-22

**Status:** L1 autorizada; credencial protegida disponível; nenhuma chamada realizada

**Decisão:** o usuário respondeu `Aprovo LIVE-HYP-001-L1. credencial pendente`
em 2026-09-22. Em seguida, a entrada mascarada foi concluída no terminal
observável e a confirmação não sensível foi verificada. A implementação e a
execução delimitada estão autorizadas; o lote ainda não foi iniciado.

## Opção L1 — comparação delimitada de dois alvos (recomendada)

Observar as mesmas configurações históricas sob a nova variável HYP-001:

- Qwen: `qwen/qwen3.8-27b`, reasoning `none`;
- GPT-OSS: `openai/gpt-oss-120b`, reasoning `low`;
- provedor proposto: Groq, somente se o preflight confirmar identidade e
  disponibilidade exatas, sem alias ou substituição;
- temperature `0.65`, máximo `768` completion tokens por chamada;
- deadline `60s` e intervalo global mínimo `60s` entre inícios HTTP;
- máximo de 16 chamadas, 12.288 completion tokens teóricos;
- schema estrito `n`/`q`, português brasileiro, 30 a 150 palavras;
- zero retry, reparo, fallback, troca automática ou chamada de juiz;
- conta já autorizada sem compra, upgrade ou gasto pago; payment required,
  quota ou rate limit encerram o lote.

A ordem é congelada antes da execução. Cada candidato completa primeiro sua
cadeia de dois turnos de espera, sem receber fonte do outro. Nos seis casos
independentes, a precedência alterna para reduzir viés de ordem. Falha do primeiro
turno de uma cadeia pula somente seu dependente; falha global de credencial,
segurança, identidade, indisponibilidade ou integridade pula todo o restante.

Consequência: é a única opção que pode comparar os dois candidatos na hipótese
aprovada. Ainda assim, elegibilidade técnica não promove default ou produto.

## Opção L2 — observar apenas GPT-OSS

Máximo de oito chamadas e metade do teto de completion. Economiza cota, mas não
responde qual dos dois candidatos é mais adequado e não pode eliminar Qwen por
ausência. Útil apenas se o objetivo humano mudar para qualificar um único alvo.

## Opção L3 — manter sem inferência

Conserva a preparação offline e nenhum candidato admitido. O checklist do MVP
permanece bloqueado no gate do Narrador.

## Fronteira de credencial

O runner, se autorizado, receberá a credencial apenas no processo filho por
entrada protegida ou ambiente já autorizado. Não lerá `.env`, não imprimirá,
copiará, persistirá ou incluirá segredo em argumento. Ausência de credencial
protegida interrompe antes do primeiro request e requer ação humana específica.

## O que a aprovação L1 autoriza

1. implementar e testar offline o runner específico deste protocolo;
2. executar preflight reconstruído e confirmar hashes/targets/parâmetros;
3. realizar no máximo as 16 chamadas descritas;
4. verificar artefatos sem produção e produzir revisão/relatório;
5. parar sem substituição se qualquer pré-condição falhar.

Não autoriza campanha híbrida, default produtivo, custo pago, fallback,
repetição do lote ou relaxamento de `CAP-001`.

## Prontidão técnica observada após a autorização

- o runner específico está implementado em
  `scripts/evaluate_grounded_progression_live.py` e exige `--live` mais
  `--allow-synthetic-only` para habilitar o caminho de rede;
- o preflight continua sem consultar credencial e reconstrói hashes, alvos,
  schema, parâmetros, ordem e teto antes do opt-in;
- a única entrada de credencial aceita pelo runner é o ambiente dedicado do
  processo `STORYTELLER_GROUNDED_PROGRESSION_GROQ_KEY`; o projeto não possui
  launcher que leia `.env`, copie segredo de outro processo ou aceite chave em
  argumento;
- cancelamento durante a cadência persiste zero chamadas; falha de transporte,
  identidade, credencial, disponibilidade ou integridade encerra o restante;
- os artefatos reconstroem cápsulas, encadeamento por candidato, parada global,
  skips e resumo, rejeitando reclassificação mesmo quando hashes externos são
  recalculados;
- 12 testes próprios do runner e uma matriz relacionada de 421 testes passaram;
- o preflight keyless foi executado depois da matriz: `provider_calls: 0` e
  `credential_inspected: false`;
- nenhuma inferência viva foi executada. O bloqueio de credencial foi satisfeito;
  resta executar o preflight congelado e iniciar o lote único autorizado.
