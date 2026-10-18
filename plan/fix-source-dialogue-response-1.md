---
goal: Preparar diagnóstico da falta de resposta de NPC sem alterar o ensaio encerrado
date_created: 2026-09-12
status: 'Completed (offline preparation; live observation pending)'
---

# Resposta de NPC após o uso interativo

Autorização contínua cobre investigação e correção experimental local. O novo
diagnóstico testa a falha concreta observada, sem refazer escolha de modelos.

1. Fechar a auditoria técnica e revisão narrativa de 49fffca2, preservando o
   snapshot parcial e os brutos originais.
2. Autorizar apenas prospectivamente novo SYSTEM experimental, corpus de três
   contextos independentes e critérios fixos de resposta/coerência/agência.
3. Implementar consumidor e launcher protegidos mínimos com APIs/adaptador
   existentes; não editar evaluators, UI, núcleo ou prompts históricos.
4. Verificar sem rede: fontes, casos, preservação de gates, três slots únicos,
   pacing/deadlines, parada, eco de chave, preflight e auditoria dos artefatos.
5. Revisão independente e preflight final. Só então depender do lançamento pelo
   PowerShell do usuário que detém a chave. A execução realiza as três ações
   fixas automaticamente, sem pedir ao usuário que repita manualmente a cena.

Detalhes e limites em ../evals/narrator/source_dialogue_response_protocol_v1.md.
Nenhuma inferência pertence à preparação offline. Não declarar melhora narrativa
antes de observar o novo SYSTEM; o diagnóstico não é adoção de produto.

## Fechamento

Preparação offline concluída com revisão independente e preflight integrado.
A observação real ainda depende somente do lançamento com credencial protegida.
Provas e limites: ../evals/narrator/reports/source-dialogue-response-preparation-2026-09-12.md.
