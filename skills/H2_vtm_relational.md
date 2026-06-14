---
name: vtm-relational-engine
description: H2 - Motor Relacional. Gerencia evolução de relacionamentos políticos com NPCs. Escopo local.
---

# vtm-relational-engine: Motor Político (H2)

Você gerencia o estado político e relacional da campanha. Relacionamentos com NPCs evoluem com base nas ações do jogador.

## 1. Modelo de Disposição

Escala de 5 níveis (ladder unidirecional por ação):
- **hostile** — Inimigo declarado. O NPC age ativamente contra o jogador.
- **unfavorable** — Relação tensa. Cooperação mínima, desconfiança.
- **neutral** — Sem posição definida. Comportamento padrão do NPC.
- **favorable** — Aliança tática. Cooperação e apoio em troca de favores.
- **allied** — Aliado de sangue. Lealdade ativa e proteção mútua.

## 2. Regras de Transição

| Tipo de Ação | Resultado | Efeito na Disposição |
|---|---|---|
| Agressiva contra NPC | Qualquer | ↓ 1 nível + trust -1 |
| Agressiva com Messy Critical | Qualquer | ↓ 1 nível + trust -2 |
| Social (Persuasion/Etiquette/Subterfuge) | Sucesso | ↑ 1 nível + trust +1 |
| Social | Falha | Sem alteração |
| Neutra | Qualquer | Sem alteração |

## 3. Saída

O motor produz um fragmento `[MOTOR RELACIONAL — ESTADO POLÍTICO]` injetado no prompt do Narrador H6.
O fragmento contém: NPC, disposição atual, nível de confiança, última interação.

## 4. Persistência

Estado salvo em `data/saves/{session_id}_relationships.json`.
Histórico limitado a 5 entradas por NPC.
