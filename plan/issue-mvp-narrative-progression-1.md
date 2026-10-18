---
title: Progressão narrativa perceptível e responsividade de NPC
status: Confirmed MVP-impact issue; campaign scope and B extension approved; narrative resolution pending
date: 2026-09-28
last_updated: 2026-09-29
---

# Problema do MVP — progressão narrativa e responsividade de NPC

## Decisão e evidência

O usuário confirmou que a ausência de progressão é um problema de grande impacto
para o MVP. Em 29/09/2026, aprovou PROG-ROUTE-B: planejar progressão e campanha
híbrida mínima antes de retomar a admissão do narrador. Luna low é a referência
prioritária solicitada, com benefícios extensíveis aos demais candidatos.
A observação manual Luna `413d4983-ea8a-488c-8687-e31f5c4ac13f` mostrou três
turnos completos: variação ambiental superficial, sensação de momento em loop e
nenhuma resposta de Mara a duas perguntas diretas consecutivas.

Esse problema deve ser resolvido e aceito antes da aceitação integral do MVP.
Recorte e extensão B foram aprovados em DEC-PROG-001/002. O conteúdo causal
do recorte e sua integração B opt-in passaram por testes offline com prosa
autorada; a realização por um modelo e o aceite da experiência continuam
pendentes. [Evidência técnica](../evals/narrator/reports/hybrid-campaign-source-offline-2026-09-29.md).
Nenhum narrador ou lote foi admitido. Espera/custo Luna foram tratados em tarefa
lateral autorizada; essa correção não fecha o problema de progressão.

## Fronteiras conhecidas

O problema cruza responsabilidades distintas que não devem ser confundidas:

- a campanha/estrutura de cena deve oferecer mudanças concretas, consequências e
  direção suficiente para evitar estagnação;
- o resolvedor já tem autoridade delimitada aprovada e um piloto de diálogo com
  Mara; a extensão opt-in para o recorte de campanha foi integrada e testada
  offline, sem promover prosa a estado, mas ainda não validada em experiência;
- o narrador deve realizar verbalmente o avanço autorizado e responder a diálogo
  dirigido, sem substituir progressão por variações atmosféricas;
- a avaliação deve medir progressão separadamente de segurança, fidelidade factual
  e conformidade estrutural.

## Gate de fechamento futuro

O item só poderá ser considerado resolvido quando uma experiência curta e
reproduzível demonstrar, em conjunto:

1. resposta significativa de NPC a diálogo explícito quando não houver razão
   canônica para silêncio;
2. mudança observável de situação, informação, relação, pressão ou opção de ação;
3. continuidade sem repetição meramente cosmética do mesmo momento;
4. preservação de agência, estado canônico, segredos e reprodutibilidade mecânica;
5. começo, desenvolvimento e resolução perceptíveis no recorte mínimo do MVP.

## Relações com o backlog

O item se relaciona diretamente a `CAMP-17`–`CAMP-20`, especialmente `CAMP-18`,
ao resolvedor determinístico de cenas e ao gate de admissão do narrador.
O planejamento agora precede a retomada da admissão, conforme PROG-ROUTE-B.
A proposta de recorte, a fronteira de integração B já implementada e a matriz comum
de verificação estão em
[architecture-hybrid-campaign-progression-1.md](architecture-hybrid-campaign-progression-1.md).

Na inspeção de 29/09, o ensaio Luna herda o prompt ambiental
`narrative-source-progress-v1`, enquanto o beat de Mara pertence a outro caminho.
Isso é uma diferença observável de composição, não uma causa isolada provada
nem motivo para desfazer HYP-006. Segurança técnica e realização narrativa
precisam ser verificadas separadamente no novo recorte.

Evidência primária:
`evals/narrator/reports/openai-luna-manual-observation-413d4983-2026-09-28.md`.
