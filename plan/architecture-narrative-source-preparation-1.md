---
goal: Produzir rascunhos B a partir de decisões e recibos mecânicos do servidor
date_created: 2026-09-10
status: Completed
product_default_changed: false
---

# Preparação interna de turno B

Incremento seguinte aos leitores de origem concluídos com 444 testes. A autorização
contínua cobre este adaptador local; nenhuma dependência de chave existe neste passo.

## Resultado e limites

Um preparador puro recebe snapshot B revalidado, identidade da operação, instante,
entrada do jogador e preparação tipada de servidor. Produz TurnDraft com uma
declaração explicitamente classificada sem teste ou um teste ordinário já resolvido.
Os IDs são estáveis por sessão/operação, e as revisões vêm do snapshot.

O adaptador não classifica texto livre, não chama H0/H1/H4/H6, não executa RNG,
não recalcula a resolução e não infere efeitos ficcionais. Apenas preserva o recibo
real produzido pelo motor existente. A confiança no chamador servidor continua
explícita: uma etiqueta de produtor ou instância tipada não o autentica.

Não integrar prepare_turn_pipeline inteiro: ele executa leituras/contexto v1 antes
de devolver o rascunho. Sem refatoração dessas rotas, mudanças de ficha/relações,
combate, poderes, alimentação, rerrolagem, abertura, elenco/local novo ou UI.
Preparações fora do recorte ordinário são recusadas, sem converter para declaração.
O rascunho continua sendo entregue à ponte execute_source_turn já existente.

## Execução e verificação

- [x] Novo api/narrative_source_preparation.py com entrada discriminada, erros
  fechados, cópias revalidadas e IDs literais estáveis; apenas os dois pares de
  fatos/eventos autorizados, sem fatos arbitrários ou import de scripts.
- [x] Testes próprios de declaração, resultado ordinário, campo extra/instância
  forjada, recibo ausente/incompatível, efeitos fora do recorte, revisão e identidades.
- [x] Integração local usando calculate_resolution real com dados controlados,
  seguida de FakeLLMAdapter e SQLite temporário: preservar resultado/falha e fonte;
  replay e falha narrativa não rolam novamente nem reclassificam a ação.
- [x] Revisão, verificação focada, relatório e retomada atualizados.

Declaração e investigação ordinária bastam para a prova. Todos os parâmetros
mecânicos vêm do servidor de teste; modelos não fornecem dificuldade, pool,
sucesso ou estado. Conftest bloqueia rede externa e dotenv fica desativado.

Referências: [leitores concluídos](architecture-narrative-source-readers-1.md),
api/orchestrator_service.py (montagem de recibo e fatos em prepare_turn_pipeline),
api/rules_service.py (V5ActionPayload, ResolutionResult, calculate_resolution).

Fechamento: 40 casos próprios e 7 integrações distintas passaram; revisão concluída.
[Relatório, evidências e limites](../evals/narrator/reports/narrative-source-preparation-2026-09-10.md).
