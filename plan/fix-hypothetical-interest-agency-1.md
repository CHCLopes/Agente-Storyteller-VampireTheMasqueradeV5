---
goal: Corrigir falso positivo delimitado de interesse hipotético e sugestão modal
version: 1
date_created: 2026-09-11
last_updated: 2026-09-11
owner: Agente Storyteller
status: 'Completed'
tags: [agency, regression, local-fix]
---

# Correção local após comparativo encerrado

O lote 61b83a2f mostrou recusa incorreta da fala condicional de Rui: o detector
trata procura/seguir como execução do jogador. Reprodução offline e contraprovas
confirmam o caso. A autorização contínua cobre esta correção local sem redefinir
agência, arquitetura ou produto; o comparativo é histórico imutável.

- Superfície: api/scene_director_service.py e novo tests/test_hypothetical_interest_regressions.py.
- Distinguir interesse hipotético e sugestão modal de execução. Preservar sujeitos,
  offsets e verificações de ações posteriores; não ignorar aspas ou cláusulas inteiras.
- Preservar afirmações diretas, ações coordenadas, aliases, mecânica, segredos, elenco
  e teto de 150 palavras. Sem exceção por modelo ou substituição da narrativa.
- Não alterar avaliadores/corpus/protocolo/artefatos encerrados, targets, rotas/UI,
  fallback, custos ou default. Nenhuma inferência necessária para reproduzir/corrigir.
- Provar com texto exato e casos negativos próximos; revisão independente e suíte
  focada de agência/perfil/ponte/coordenador antes de fechar. Falhas ficam registradas.

| Tarefa | Estado |
|---|---|
| Reproduzir causa e preservar versão auditada | Concluída: checkpoint com 36 arquivos congelados |
| Implementar correção mínima e contraprovas | Concluída: 17 linhas, 48 testes novos |
| Revisar limites e executar suíte final focada | Concluída: 1.097 testes verdes |
| Registrar resultado e próximo passo, sem reclassificar lote | Concluída: relatório e checkpoint |

A preparação do despacho local inativo permanece no plano de transporte. Sua
integração/ativação não é parte desta correção. Qualidade narrativa e escolha de
modelo permanecem não aprovadas pelo comparativo.

[Relatório e evidências](../evals/narrator/reports/hypothetical-interest-fix-2026-09-11.md). Próximo incremento: seletor local inativo do plano de transporte.
